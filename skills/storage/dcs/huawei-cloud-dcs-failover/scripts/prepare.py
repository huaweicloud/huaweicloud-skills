#!/usr/bin/env python3
"""
DCS master-slave failover — prepare script.

Reads region and instance_id from config/config.json,
queries DCS master-slave instance, checks IAM permissions, runs architecture
hard-gate checks, generates config directory, and runs risk assessment.
The config directory serves as input for the execute phase.

Usage:
  python3 prepare.py
  python3 prepare.py --region cn-south-1 --instance-id <id>
  python3 prepare.py --output-dir /path/to/experiment
"""

import argparse
import datetime
import html
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.join(SCRIPT_DIR, "..")

sys.path.insert(0, SCRIPT_DIR)
from config import (load_config, get_config_path, run_hcloud, save_json, now_str, DCS_CES_METRICS,
                     EXPERIMENTS_DIR, clean_experiments)
import risk

DEFAULT_OUTPUT_BASE = EXPERIMENTS_DIR


def _esc(text):
    """HTML entity escape — prevent cloud API external data from triggering stored XSS in HTML reports."""
    return html.escape(str(text)) if text is not None else ""


def _md_cell(text):
    """Escape Markdown table cell special characters (| and newlines)."""
    if text is None:
        return ""
    s = str(text)
    return s.replace("|", r"\|").replace("\n", " ").replace("\r", " ")


# ---------------------------------------------------------------------------
# Query DCS instances
# ---------------------------------------------------------------------------

def query_dcs_instances(region, target_instance_id):
    """Query all DCS instances in the region, locate the target instance."""
    MAX_PAGES = 50
    all_instances = []
    for page in range(MAX_PAGES):
        extra = ["--limit=100", f"--offset={page * 100}"]
        resp = run_hcloud("DCS", "ListInstances", region, extra)
        if resp.get("_error"):
            return None, resp.get("stderr", "Unknown error")
        page_instances = resp.get("instances", [])
        all_instances.extend(page_instances)
        if len(page_instances) < 100:
            break
    else:
        print(f"  [WARNING] ListInstances 达到最大页数上限 ({MAX_PAGES})")

    target = next((i for i in all_instances if i.get("instance_id") == target_instance_id), None)
    return target, None


def extract_instance_info(inst, region):
    """Extract drill-relevant instance info from ListInstances entry + ShowInstance detail.

    cache_mode / spec_code and other fields are only returned by ShowInstance detail;
    ListInstances may lack them, so ShowInstance is called to fill in.
    """
    az_codes = inst.get("az_codes", [])
    # ShowInstance detail to fill in cache_mode, etc.
    detail = run_hcloud("DCS", "ShowInstance", region, [f"--instance_id={inst.get('instance_id')}"])
    if "_error" not in detail:
        inst = {**inst, **detail}  # 详情字段覆盖列表字段
        az_codes = detail.get("az_codes", az_codes)

    nodes = inst.get("node_list", [])
    master = next((n for n in nodes if (n.get("node_type") or "").lower() in ("master", "primary")), None)
    slave = next((n for n in nodes if (n.get("node_type") or "").lower() in ("slave", "replica", "standby")), None)
    return {
        "id": inst.get("instance_id"),
        "name": inst.get("name"),
        "status": inst.get("status"),
        "cache_mode": inst.get("cache_mode"),
        "engine": inst.get("engine"),
        "engine_version": inst.get("engine_version"),
        "capacity": inst.get("capacity"),
        "flavor": inst.get("spec_code"),
        "az_codes": az_codes,
        "master_az": master.get("az_code") if master else (az_codes[0] if az_codes else None),
        "slave_az": slave.get("az_code") if slave else (az_codes[1] if len(az_codes) > 1 else None),
        "master_name": master.get("name") if master else None,
        "slave_name": slave.get("name") if slave else None,
        "backup_strategy": inst.get("backup_policy") or {},
        "vpc_id": inst.get("vpc_id"),
        "security_group_id": inst.get("security_group_id"),
        "subnet_id": inst.get("subnet_id"),
    }


# ---------------------------------------------------------------------------
# Query IAM permissions (simplified: read-only probe + policy name inference)
# ---------------------------------------------------------------------------

def _action_matches(policy_action, target_action):
    import fnmatch
    return (fnmatch.fnmatchcase(target_action, policy_action) or
            fnmatch.fnmatchcase(policy_action, target_action))


def query_iam_permissions(region):
    """Query current account IAM permissions, check DCS operation permissions.

    Auth readiness is verified via an actual read-only API call (hcloud auth depends on profile).
    Failover permission (dcs:instance:modify) is inferred from precise system policy name patterns
    (dcsfullaccess / dcssysaccess / administratoraccess). System policy GetPolicyV5 does not
    return policy_document, so only name-based inference is possible. Custom policies are deep-checked
    via GetPolicyV5 policy_document. Three states: allow / deny / unknown (advisory, non-blocking).
    """
    dcs_resp = run_hcloud("DCS", "ListInstances", region)
    dcs_access = not dcs_resp.get("_error")
    auth_ready = dcs_access

    status = "unknown"
    if dcs_access:
        _SYSTEM_FULL_ACCESS_PATTERNS = ("dcsfullaccess", "dcssysaccess",
                                        "administratoraccess")
        policy_list = []
        marker = None
        list_error = False
        while True:
            extra = ["--limit=200"]
            if marker:
                extra.append(f"--marker={marker}")
            resp = run_hcloud("IAM", "ListPoliciesV5", region, extra)
            if resp.get("_error"):
                list_error = True
                break
            page_policies = resp.get("policies", [])
            policy_list.extend(page_policies)
            marker = (resp.get("page_info") or {}).get("next_marker")
            if not marker or not page_policies:
                break

        system_full_access = False
        system_matched_name = ""
        checked_custom = 0
        all_checked = True
        for p in policy_list:
            pname = (p.get("policy_name") or p.get("name") or "").lower()
            ptype = p.get("policy_type") or p.get("type") or ""
            if ptype == "system":
                if not system_full_access and any(pat in pname for pat in _SYSTEM_FULL_ACCESS_PATTERNS):
                    system_full_access = True
                    system_matched_name = pname
                continue
            # Custom policy: name pre-filter, then deep-check via GetPolicyV5 policy_document
            checked_custom += 1
            if not any(kw in pname for kw in ("dcs", "redis", "cache", "all", "full", "admin")):
                continue
            detail = run_hcloud("IAM", "GetPolicyV5", region, [f"--policy_id={p.get('policy_id') or p.get('id')}"])
            if detail.get("_error"):
                all_checked = False
                continue
            policy_doc = detail.get("policy", detail).get("policy_document")
            if isinstance(policy_doc, str):
                try:
                    policy_doc = json.loads(policy_doc)
                except json.JSONDecodeError:
                    policy_doc = {}
            if not isinstance(policy_doc, dict):
                all_checked = False
                continue
            statements = policy_doc.get("Statement") or []
            if isinstance(statements, dict):
                statements = [statements]
            for stmt in (statements if isinstance(statements, list) else []):
                actions = stmt.get("Action") or []
                if isinstance(actions, str):
                    actions = [actions]
                effect = stmt.get("Effect", "")
                matched = any(_action_matches(str(a).strip(), "dcs:instance:modify")
                              for a in actions)
                if effect in ("Deny", "deny") and matched:
                    status = "deny"
                    break
                if effect in ("Allow", "allow") and matched and status != "deny":
                    status = "allow"
        print(f"  IAM 策略检查: 自定义策略 {checked_custom} 个")
        if system_full_access:
            print(f"  IAM 系统策略推断: 命中 {system_matched_name}（名称匹配，系统策略无法取证 policy_document）")
        if status not in ("allow", "deny"):
            status = "allow" if system_full_access and not list_error else (
                "deny" if (all_checked and not list_error) else "unknown")

    return {
        "auth_ready": auth_ready,
        "dcs_read_access": dcs_access,
        "dcs_failover_capable": (status == "allow"),
        "dcs_failover_status": status,
        "policy_count": len(policy_list) if dcs_access else 0,
        "system_policy_inferred": system_matched_name if dcs_access else "",
        "checked_at": now_str(),
    }


# ---------------------------------------------------------------------------
# Generate config files
# ---------------------------------------------------------------------------

def generate_experiment_template(instance, region):
    """Generate experiment template experiment.json."""
    return {
        "experiment_name": f"dcs_failover_{instance['name']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "experiment_type": "dcs_failover",
        "description": f"DCS 主备倒换演练（AZ断电模拟）- 实例 {instance['name']}",
        "region": region,
        "target": {
            "instance_id": instance["id"],
            "instance_name": instance["name"],
            "engine": instance["engine"],
            "engine_version": instance["engine_version"],
            "capacity": instance["capacity"],
            "flavor": instance["flavor"],
            "cache_mode": instance["cache_mode"],
        },
        "topology_before": {
            "master_az": instance["master_az"],
            "slave_az": instance["slave_az"],
            "az_codes": instance["az_codes"],
        },
        "safety_checks": {
            "require_ha_type": True,
            "require_running_status": True,
            "require_iam_permission": True,
            "require_cross_az": True,
            "max_failover_duration_seconds": 120,
            "poll_interval_seconds": 5,
        },
        "created_at": now_str(),
    }


def generate_iam_policy(region):
    """Generate IAM policy document iam_policy.json."""
    return {
        "description": "DCS 主备倒换所需的最小权限集",
        "required_permissions": [
            {"action": "dcs:instance:list", "description": "查询 DCS 实例列表", "required": True},
            {"action": "dcs:instance:get", "description": "查询 DCS 实例详情", "required": True},
            {"action": "dcs:instance:modify", "description": "执行 DCS 主备倒换（ChangeMasterStandby）", "required": True},
            {"action": "dcs:instance:getNodes", "description": "查询主备节点信息", "required": True},
            {"action": "dcs:backup:list", "description": "查询备份记录", "required": True},
            {"action": "ces:metricData:get", "description": "查询 CES 监控指标数据", "required": False},
        ],
        "policy_template": {
            "name": "DCSFailoverExperimentPolicy",
            "description": "DCS 主备倒换演练所需权限",
            "statement": [
                {"effect": "Allow", "action": [
                    "dcs:instance:modify",
                    "dcs:instance:getNodes",
                ], "resource": [
                    "dcs:<region>:<domainId>:instance:<instanceId>",
                ]},
                {"effect": "Allow", "action": [
                    "dcs:instance:list",
                    "dcs:instance:get",
                    "dcs:backup:list",
                    "ces:metricData:get",
                ], "resource": ["*"]},
            ],
        },
        "region": region,
        "generated_at": now_str(),
    }


def generate_monitoring_config(instance, region):
    """Generate CES monitoring config monitoring.json."""
    # DCS_CES_METRICS imported at module top
    return {
        "description": "DCS 主备倒换演练监控配置",
        "instance_id": instance["id"],
        "instance_name": instance["name"],
        "region": region,
        "ces_metrics": DCS_CES_METRICS,
        "alarm_rules": [
            {"name": f"failover_mem_high_{instance['name']}", "metric": "memory_usage",
             "threshold": 90, "comparison": ">=", "period": 300, "description": "内存使用率超过 90% 告警"},
            {"name": f"failover_conn_high_{instance['name']}", "metric": "connections_usage",
             "threshold": 90, "comparison": ">=", "period": 300, "description": "连接数使用率超过 90% 告警"},
        ],
        "generated_at": now_str(),
    }


# ---------------------------------------------------------------------------
# Architecture hard-gate checks
# ---------------------------------------------------------------------------

def run_architecture_checks(instance, iam_result):
    """Architecture hard-gate checks + IAM checks. Returns list of check items."""
    checks = []
    checks.append({
        "category": "配置", "item": "config.json 可读取",
        "passed": True, "critical": True,
        "detail": f"region={instance.get('region')}, instance_id={instance['id']}",
    })
    checks.append({
        "category": "实例", "item": "实例存在",
        "passed": True, "critical": True,
        "detail": f"{instance['name']} ({instance['id']})",
    })
    checks.append({
        "category": "实例", "item": "实例为主备类型 (cache_mode=ha)",
        "passed": instance.get("cache_mode") == "ha", "critical": True,
        "detail": f"cache_mode={instance.get('cache_mode', 'N/A')}",
    })
    checks.append({
        "category": "实例", "item": "实例状态为 RUNNING",
        "passed": instance.get("status") == "RUNNING", "critical": True,
        "detail": f"status={instance.get('status', 'N/A')}",
    })
    checks.append({
        "category": "实例", "item": "主节点存在",
        "passed": bool(instance.get("master_az")), "critical": True,
        "detail": f"master AZ={instance.get('master_az', 'N/A')}",
    })
    checks.append({
        "category": "实例", "item": "备节点存在",
        "passed": bool(instance.get("slave_az")), "critical": True,
        "detail": f"slave AZ={instance.get('slave_az', 'N/A')}",
    })
    checks.append({
        "category": "实例", "item": "主备节点跨 AZ",
        "passed": bool(instance.get("master_az") and instance.get("slave_az")
                       and instance.get("master_az") != instance.get("slave_az")),
        "critical": False,
        "detail": f"master AZ={instance.get('master_az', 'N/A')}, slave AZ={instance.get('slave_az', 'N/A')}",
    })
    checks.append({
        "category": "IAM权限", "item": "DCS 实例列表查询权限",
        "passed": iam_result.get("dcs_read_access", False), "critical": True,
        "detail": "dcs:instance:list",
    })
    checks.append({
        "category": "IAM权限", "item": "DCS 主备倒换执行权限",
        "passed": iam_result.get("dcs_failover_capable", False), "critical": False,
        "detail": f"dcs:instance:modify (status={iam_result.get('dcs_failover_status', 'unknown')})",
    })
    checks.append({
        "category": "IAM权限", "item": "hcloud 认证就绪",
        "passed": iam_result.get("auth_ready", False), "critical": True,
        "detail": "通过只读调用验证" if iam_result.get("auth_ready") else "hcloud 未认证，请执行 hcloud configure init",
    })
    checks.append({
        "category": "监控", "item": "CES 监控指标已配置",
        "passed": True, "critical": False,
        "detail": f"{len(DCS_CES_METRICS)} 个指标",
    })
    return checks


# ---------------------------------------------------------------------------
# Readiness report generation (HTML + Markdown)
# ---------------------------------------------------------------------------

def generate_readiness_report_html(checks, instance, region, instance_id, output_dir, risk_doc=None):
    """Generate HTML readiness report."""
    critical_fails = [c for c in checks if c["critical"] and not c["passed"]]
    all_critical_pass = len(critical_fails) == 0
    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])

    check_rows = ""
    for c in checks:
        icon = "&#9989;" if c["passed"] else "&#10060;"
        critical_tag = "&#9888;" if c["critical"] and not c["passed"] else ""
        check_rows += (
            f"\n        <tr><td>{icon}{critical_tag}</td><td>{_esc(c['item'])}</td>"
            f"<td>{_esc(c['category'])}</td><td>{'通过' if c['passed'] else '未通过'}</td>"
            f"<td>{_esc(c['detail'])}</td></tr>"
        )

    risk_html = ""
    if risk_doc:
        lvl = risk_doc.get("overall_level", "low")
        risk_items = ""
        for it in risk_doc.get("items", []):
            if it.get("level") in ("warning", "critical", "unknown"):
                mark = {"critical": "&#128308;", "warning": "&#128992;", "unknown": "&#9898;"}.get(it.get("level"), "•")
                risk_items += (
                    f"\n        <tr><td>{mark}</td><td>{_esc(it.get('level', ''))}</td>"
                    f"<td>{_esc(it.get('category', ''))}</td><td>{_esc(it.get('title', ''))}</td>"
                    f"<td>{_esc(it.get('detail', ''))}</td></tr>"
                )
        risk_html = f"""
  <div class="card">
    <h2>&#128737 风险评估</h2>
    <p class="hint">总体等级: {_esc(lvl)} | 汇总: {_esc(risk_doc.get('summary', ''))} | 建议: {_esc(risk_doc.get('recommendation', ''))}</p>
    <table><thead><tr><th>级别</th><th>等级</th><th>分类</th><th>检测项</th><th>详情</th></tr></thead><tbody>{risk_items}
    </tbody></table>
  </div>"""

    banner_color = "#4caf50" if all_critical_pass else "#e74c3c"
    banner_text = "&#9989; 准备就绪，可以执行 DCS 主备倒换演练" if all_critical_pass else "&#10060; 准备未就绪，存在必需项未通过"

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DCS 主备倒换准备报告 - {_esc(instance['name'])}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,"Microsoft YaHei",sans-serif; background:#f5f7fa; color:#333; line-height:1.6; }}
.c {{ max-width:960px; margin:0 auto; padding:20px; }}
.hd {{ background:linear-gradient(135deg,#e67e22,#764ba2); color:#fff; padding:30px; border-radius:12px; margin-bottom:24px; }}
.hd h1 {{ font-size:24px; margin-bottom:8px; }}
.hd .meta {{ font-size:13px; opacity:.85; }}
.card {{ background:#fff; border-radius:10px; padding:24px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }}
.card h2 {{ font-size:16px; color:#2c3e50; margin-bottom:16px; padding-bottom:10px; border-bottom:2px solid #ecf0f1; }}
.hint {{ color:#7f8c8d; font-size:13px; margin-bottom:10px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ background:#f8f9fa; text-align:left; padding:10px 12px; border-bottom:2px solid #e0e0e0; color:#555; font-weight:600; }}
td {{ padding:8px 12px; border-bottom:1px solid #f0f0f0; }}
.rb {{ text-align:center; padding:16px; border-radius:8px; font-size:18px; font-weight:600; margin-bottom:16px; border:1px solid; }}
.ig {{ display:grid; grid-template-columns:1fr 1fr; gap:12px 24px; }}
.ii {{ display:flex; }}
.ii .lb {{ color:#7f8c8d; min-width:110px; font-size:13px; }}
.ii .vl {{ font-weight:500; font-size:13px; }}
.ft {{ text-align:center; color:#aaa; font-size:12px; margin-top:24px; }}
code {{ background:#f4f4f4; padding:2px 6px; border-radius:3px; font-size:12px; }}
</style>
</head>
<body>
<div class="c">
  <div class="hd">
    <h1>&#128640 DCS 主备倒换准备报告</h1>
    <div class="meta">实例：{_esc(instance['name'])} ｜ 区域：{_esc(region)} ｜ 生成时间：{_esc(now_str())}</div>
  </div>
  <div class="rb" style="background:{banner_color}1a;color:{banner_color};">{banner_text}</div>
  <div class="card">
    <h2>&#128295 实例信息</h2>
    <div class="ig">
      <div class="ii"><span class="lb">实例名称</span><span class="vl">{_esc(instance['name'])}</span></div>
      <div class="ii"><span class="lb">实例 ID</span><span class="vl">{_esc(instance['id'])}</span></div>
      <div class="ii"><span class="lb">引擎</span><span class="vl">{_esc(instance.get('engine', ''))} {_esc(instance.get('engine_version', ''))}</span></div>
      <div class="ii"><span class="lb">容量</span><span class="vl">{_esc(instance.get('capacity', ''))}GB</span></div>
      <div class="ii"><span class="lb">主节点 AZ</span><span class="vl">{_esc(instance.get('master_az', 'N/A'))}</span></div>
      <div class="ii"><span class="lb">备节点 AZ</span><span class="vl">{_esc(instance.get('slave_az', 'N/A'))}</span></div>
    </div>
  </div>
  <div class="card">
    <h2>&#9989 准备检查</h2>
    <p class="hint">总检查项: {total} | 通过: {passed} | 未通过: {total - passed}</p>
    <table><thead><tr><th>结果</th><th>检查项</th><th>分类</th><th>状态</th><th>详情</th></tr></thead><tbody>{check_rows}
    </tbody></table>
  </div>
  {risk_html}
  <div class="ft">本报告由 huawei-cloud-dcs-failover skill 自动生成 ｜ region/instance_id 来自 config/config.json</div>
</div>
</body>
</html>"""

    path = os.path.join(output_dir, "readiness_report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path


def generate_readiness_report_md(checks, instance, region, instance_id, output_dir, risk_doc=None):
    """Generate Markdown readiness report."""
    critical_fails = [c for c in checks if c["critical"] and not c["passed"]]
    all_critical_pass = len(critical_fails) == 0
    lines = [
        f"# DCS 主备倒换准备报告",
        "",
        f"- 实例：{_md_cell(instance['name'])}（{_md_cell(instance['id'])}）",
        f"- 区域：{_md_cell(region)}",
        f"- 生成时间：{now_str()}",
        "",
        "## 准备检查",
        "",
        "| 结果 | 检查项 | 分类 | 状态 | 详情 |",
        "|------|--------|------|------|------|",
    ]
    for c in checks:
        icon = "✅" if c["passed"] else "❌"
        lines.append(f"| {icon} | {_md_cell(c['item'])} | {_md_cell(c['category'])} | {'通过' if c['passed'] else '未通过'} | {_md_cell(c['detail'])} |")

    if risk_doc:
        lines += ["", "## 风险评估", ""]
        lvl = risk_doc.get("overall_level", "low")
        lines.append(f"- 总体等级: {lvl} | 汇总: {risk_doc.get('summary', '')} | 建议: {risk_doc.get('recommendation', '')}")
        lines += ["", "| 级别 | 分类 | 检测项 | 详情 |", "|------|------|--------|------|"]
        for it in risk_doc.get("items", []):
            if it.get("level") in ("warning", "critical", "unknown"):
                lines.append(f"| {it.get('level')} | {_md_cell(it.get('category'))} | {_md_cell(it.get('title'))} | {_md_cell(it.get('detail'))} |")

    lines += ["", "## 结论", ""]
    if all_critical_pass:
        lines.append("✅ 准备就绪，可以执行 DCS 主备倒换演练。")
    else:
        lines.append("❌ 准备未就绪，以下必需项未通过：")
        for cf in critical_fails:
            lines.append(f"- ❌ {_md_cell(cf['item'])} — {_md_cell(cf['detail'])}")

    path = os.path.join(output_dir, "readiness_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DCS 主备倒换实验准备")
    parser.add_argument("--region", default=None, help="华为云区域（默认从 config/config.json 读取）")
    parser.add_argument("--instance-id", default=None, help="实例 ID（默认从 config/config.json 读取）")
    parser.add_argument("--output-dir", default=None, help="输出目录（默认: experiments/）")
    parser.add_argument("--config-dir", default=None, help="配置目录别名，等同 --output-dir")
    args = parser.parse_args()

    # Clean experiments/ before run to avoid stale data
    clean_experiments()

    config_path = get_config_path()
    print(f"[配置] 读取共享配置: {config_path}")
    try:
        cfg = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    region = args.region or cfg["region"]
    instance_id = args.instance_id or cfg["instance_id"]
    print(f"[配置] region={region}, instance_id={instance_id}")

    print(f"\n[1/5] 查询 DCS 实例 (region={region})...")
    target, err = query_dcs_instances(region, instance_id)
    if err:
        print(f"[ERROR] 查询 DCS 实例失败: {err}")
        sys.exit(1)
    if not target:
        print(f"[ERROR] 区域 {region} 中未找到实例 {instance_id}。")
        sys.exit(1)
    instance = extract_instance_info(target, region)
    instance["region"] = region
    print(f"  找到实例: {instance['name']} | status={instance['status']} | cache_mode={instance['cache_mode']} | "
          f"master AZ={instance['master_az']} | slave AZ={instance['slave_az']}")

    # Status / mode check
    if instance["status"] != "RUNNING":
        print(f"[WARNING] 实例状态为 {instance['status']}，非 RUNNING。倒换可能失败。")
    if instance["cache_mode"] != "ha":
        print(f"[WARNING] 实例 cache_mode 为 {instance['cache_mode']}，非主备类型。无法倒换。")

    print(f"\n[2/5] 检查 IAM 权限...")
    iam_result = query_iam_permissions(region)
    print(f"  hcloud 认证就绪: {'是' if iam_result['auth_ready'] else '否'}")
    print(f"  DCS 读权限: {'是' if iam_result['dcs_read_access'] else '否'}")
    _fs = iam_result.get("dcs_failover_status", "unknown")
    _fs_label = {"allow": "是", "deny": "否", "unknown": "未知（无法获取策略详情）"}.get(_fs, "未知")
    print(f"  DCS 倒换权限: {_fs_label}")
    print(f"  DCS 相关策略数: {iam_result['policy_count']}")

    print(f"\n[3/5] 生成配置文件...")
    output_dir = args.output_dir or args.config_dir or DEFAULT_OUTPUT_BASE
    os.makedirs(output_dir, exist_ok=True)

    experiment = generate_experiment_template(instance, region)
    save_json(os.path.join(output_dir, "experiment.json"), experiment)
    print(f"  ✓ experiment.json")

    iam_policy = generate_iam_policy(region)
    iam_policy["iam_check_result"] = iam_result
    save_json(os.path.join(output_dir, "iam_policy.json"), iam_policy)
    print(f"  ✓ iam_policy.json")

    monitoring = generate_monitoring_config(instance, region)
    save_json(os.path.join(output_dir, "monitoring.json"), monitoring)
    print(f"  ✓ monitoring.json")

    print(f"\n[4/5] 运行准备检查与风险评估...")
    checks = run_architecture_checks(instance, iam_result)
    risk_doc = risk.build_risk_assessment(region, instance_id, instance, monitoring, output_dir)
    print(f"  ✓ risk_assessment.json")
    risk.print_risk_summary(risk_doc)

    critical_fails = [c for c in checks if c["critical"] and not c["passed"]]
    all_critical_pass = len(critical_fails) == 0
    total = len(checks)
    passed_count = sum(1 for c in checks if c["passed"])

    html_path = generate_readiness_report_html(checks, instance, region, instance_id, output_dir, risk_doc=risk_doc)
    print(f"  ✓ readiness_report.html")
    md_path = generate_readiness_report_md(checks, instance, region, instance_id, output_dir, risk_doc=risk_doc)
    print(f"  ✓ readiness_report.md")

    print(f"\n  ── 准备检查摘要 ──")
    print(f"  总检查项: {total}  通过: {passed_count}  未通过: {total - passed_count}")
    rlvl_label = {"low": "低", "medium": "中（存在预警）", "blocked": "高（阻止执行）"}.get(
        risk_doc.get("overall_level", "low"), "未知")
    print(f"  总体风险等级: {rlvl_label}  →  {risk_doc.get('recommendation', '')}")
    if all_critical_pass:
        print(f"  结论: ✅ 准备就绪，可以执行 DCS 主备倒换演练")
    else:
        print(f"  结论: ❌ 准备未就绪，以下必需项未通过:")
        for cf in critical_fails:
            print(f"    ❌ {cf['item']} — {cf['detail']}")

    print(f"\n  报告: {html_path}")
    print(f"        {md_path}")
    print(f"\n  下一步: 使用 run.py --phase execute 执行倒换（调用即执行真实倒换）")
    print(f"  命令: python3 execute.py --config-dir {output_dir}")


if __name__ == "__main__":
    main()
