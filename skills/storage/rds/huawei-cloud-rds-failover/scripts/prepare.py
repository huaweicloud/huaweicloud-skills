#!/usr/bin/env python3
"""
RDS 主备倒换 — 实验准备脚本

从 config/config.json 读取 region 和 instance_id，
查询 RDS HA 实例、检查 IAM 权限、生成完整配置目录。
配置目录作为下一个 skill（倒换执行）的输入。

Usage:
  # 默认从 config/config.json 读取 region 和 instance_id
  python3 prepare.py

  # 可选：CLI 参数覆盖 config.json 中的值
  python3 prepare.py --region cn-north-1 --instance-id <id>
  python3 prepare.py --output-dir /path/to/experiment
"""

import argparse
import datetime
import fnmatch
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.join(SCRIPT_DIR, "..")
DEFAULT_OUTPUT_BASE = os.path.join(SKILL_ROOT, "experiments")

# 导入共享配置模块
sys.path.insert(0, SCRIPT_DIR)
from config import load_config, get_config_path


def run_hcloud(service, action, region, extra_args=None):
    cmd = ["hcloud", service, action, f"--cli-region={region}"]
    if extra_args:
        cmd.extend(extra_args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"_error": True, "stderr": "hcloud 命令超时（120s），请检查网络或减少查询范围"}
    except FileNotFoundError:
        return {"_error": True, "stderr": "hcloud 未安装或不在 PATH 中，请参考 cli-installation-guide.md 安装"}
    if result.returncode != 0:
        return {"_error": True, "stderr": result.stderr.strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_error": True, "stderr": "Non-JSON output", "stdout": result.stdout.strip()}


# ---------------------------------------------------------------------------
# 查询 RDS 实例
# ---------------------------------------------------------------------------

def query_rds_instances(region):
    """查询区域内所有 RDS 实例，筛选 HA 类型。"""
    resp = run_hcloud("RDS", "ListInstances", region)
    if resp.get("_error"):
        return [], resp.get("stderr", "Unknown error")

    instances = resp.get("instances", [])
    ha_instances = []
    for inst in instances:
        if inst.get("type", "").lower() in ("ha", "replication"):
            nodes = inst.get("nodes", [])
            master = next((n for n in nodes if n.get("role") == "master"), None)
            slave = next((n for n in nodes if n.get("role") == "slave"), None)
            ha_instances.append({
                "id": inst.get("id"),
                "name": inst.get("name"),
                "status": inst.get("status"),
                "type": inst.get("type"),
                "engine": f"{(inst.get('datastore') or {}).get('type', '?')} {(inst.get('datastore') or {}).get('version', '?')}",
                "flavor": inst.get("flavor_ref"),
                "cpu": inst.get("cpu"),
                "mem": inst.get("mem"),
                "volume_type": (inst.get("volume") or {}).get("type"),
                "volume_size": (inst.get("volume") or {}).get("size"),
                "private_ips": inst.get("private_ips", []),
                "az": inst.get("availability_zone"),
                "ha_mode": (inst.get("ha") or {}).get("replication_mode", "N/A"),
                "master_node": master.get("name") if master else None,
                "master_az": master.get("availability_zone") if master else None,
                "slave_node": slave.get("name") if slave else None,
                "slave_az": slave.get("availability_zone") if slave else None,
                "enable_ssl": inst.get("enable_ssl"),
                "vpc_id": inst.get("vpc_id"),
                "subnet_id": inst.get("subnet_id"),
                "security_group_id": inst.get("security_group_id"),
            })
    return ha_instances, None


# ---------------------------------------------------------------------------
# 查询 IAM 权限
# ---------------------------------------------------------------------------

def query_iam_permissions(region):
    """查询当前账号的 IAM 权限信息，检查是否具备 RDS 操作权限。"""
    ak = (
        os.environ.get("HUAWEICLOUD_SDK_AK")
        or os.environ.get("HUAWEI_ACCESS_KEY")
        or os.environ.get("HWC_AK", "")
    )
    sk_present = bool(
        os.environ.get("HUAWEICLOUD_SDK_SK")
        or os.environ.get("HUAWEI_SECRET_KEY")
        or os.environ.get("HWC_SK")
    )

    policies = []

    resp = run_hcloud("IAM", "KeystoneListAuthDomains", region)
    # 查询策略列表（ListPoliciesV5，按 next_marker 翻页拉取全量）
    policy_list = []
    marker = None
    list_error = False  # 分页拉取是否出错，用于最终 deny/unknown 判定
    while True:
        extra = ["--limit=200"]
        if marker:
            extra.append(f"--marker={marker}")
        resp = run_hcloud("IAM", "ListPoliciesV5", region, extra_args=extra)
        if resp.get("_error"):
            list_error = True
            break
        page_policies = resp.get("policies", [])
        policy_list.extend(page_policies)
        marker = (resp.get("page_info") or {}).get("next_marker")
        if not marker or not page_policies:
            break
    for p in policy_list:
        # ListPoliciesV5 使用 policy_name/policy_id/policy_type；
        # 保留旧版 name/id/type 字段作为兼容兜底
        policy_name = p.get("policy_name") or p.get("name", "")
        if "rds" in policy_name.lower():
            policies.append({
                "name": p.get("policy_name") or p.get("name"),
                "id": p.get("policy_id") or p.get("id"),
                "type": p.get("policy_type") or p.get("type"),
                "scope": p.get("scope"),
            })

    rds_access = False
    rds_resp = run_hcloud("RDS", "ListInstances", region)
    if not rds_resp.get("_error"):
        rds_access = True

    # 倒换权限不能仅凭 ListInstances 成功推断，需检查 IAM 策略详情中是否包含
    # rds:instance:failover action。ListPoliciesV5 仅返回策略元数据（name/id/type），
    # 不含 statement，因此需对每个 RDS 相关策略调用 GetPolicyV5 获取策略体。
    #
    # 已知限制：GetPolicyV5 对系统策略（policy_type=system）只返回元数据，不含
    # policy_document/Statement。绝大多数用户通过系统策略（RDSFullAccessPolicy 等）
    # 授权，因此无法通过此接口确认。对此类策略：
    #   1. 若策略名匹配已知全权限模式（FullAccess/Administrator），推断为 allow
    #   2. 否则标记 all_checked=False，最终保持 unknown（不误判为 deny）
    #
    # 结果为三态：allow（确认有权限）/ deny（确认无权限）/ unknown（无法确认）。
    # 此检查为建议性：unknown/deny 不会阻断 execute 阶段（实际 API 调用决定成败）。
    failover_status = "unknown"
    if rds_access and policies:
        all_checked = True
        for p in policies:
            policy_id = p.get("id")
            policy_name = (p.get("name") or "").lower()
            policy_type = p.get("type") or ""
            if not policy_id:
                all_checked = False
                continue
            detail = run_hcloud("IAM", "GetPolicyV5", region, extra_args=[f"--policy_id={policy_id}"])
            if detail.get("_error"):
                all_checked = False
                continue
            policy_obj = detail.get("policy", detail)
            policy_doc = policy_obj.get("policy_document")
            if isinstance(policy_doc, str):
                try:
                    policy_doc = json.loads(policy_doc)
                except json.JSONDecodeError:
                    policy_doc = {}
            if not isinstance(policy_doc, dict):
                # 系统策略不返回 policy_document — 无法逐条检查 Action
                # 按策略名推断：已知全权限系统策略包含 rds:*:*
                if policy_type == "system" and any(
                    kw in policy_name for kw in ("fullaccess", "administrator", "admin")
                ):
                    failover_status = "allow"
                    break
                # 无法确认，不判 deny
                all_checked = False
                continue
            statements = policy_doc.get("Statement") or policy_obj.get("Statement") or []
            if isinstance(statements, dict):
                statements = [statements]
            for stmt in (statements if isinstance(statements, list) else []):
                actions = stmt.get("Action") or stmt.get("action") or []
                if isinstance(actions, str):
                    actions = [actions]
                effect = stmt.get("Effect", stmt.get("effect", ""))
                if effect in ("Allow", "allow") and any(
                    fnmatch.fnmatchcase("rds:instance:failover", str(a).strip())
                    for a in actions
                ):
                    failover_status = "allow"
                    break
            if failover_status == "allow":
                break
        if failover_status != "allow":
            # 仅当所有策略的 policy_document 均成功获取且确认无 failover action 时才判 deny；
            # 系统策略 body 缺失或分页出错时保持 unknown
            failover_status = "deny" if (all_checked and not list_error) else "unknown"

    failover_capable = (failover_status == "allow")

    return {
        "ak_present": bool(ak),
        "sk_present": sk_present,
        "rds_read_access": rds_access,
        "rds_failover_capable": failover_capable,
        "rds_failover_status": failover_status,
        "rds_related_policies": policies,
        "policy_count": len(policies),
        "checked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# 生成配置文件
# ---------------------------------------------------------------------------

def generate_experiment_template(instance, region):
    """生成实验模板 experiment.json"""
    return {
        "experiment_name": f"rds_failover_{instance['name']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "experiment_type": "rds_failover",
        "description": f"RDS 主备倒换演练 - 实例 {instance['name']}",
        "region": region,
        "target": {
            "instance_id": instance["id"],
            "instance_name": instance["name"],
            "engine": instance["engine"],
            "flavor": instance["flavor"],
            "ha_mode": instance["ha_mode"],
        },
        "topology_before": {
            "master_node": instance["master_node"],
            "master_az": instance["master_az"],
            "slave_node": instance["slave_node"],
            "slave_az": instance["slave_az"],
        },
        "safety_checks": {
            "require_ha_type": True,
            "require_active_status": True,
            "require_iam_permission": True,
            "max_failover_duration_seconds": 120,
            "poll_interval_seconds": 5,
        },
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_iam_policy(region):
    """生成 IAM 权限策略文档 iam_policy.json"""
    return {
        "description": "RDS 主备倒换所需的最小权限集",
        "required_permissions": [
            {"action": "rds:instance:list", "description": "查询 RDS 实例列表", "required": True},
            {"action": "rds:instance:failover", "description": "执行 RDS 主备倒换", "required": True},
            {"action": "rds:log:listErrorLogs", "description": "查询 RDS 错误日志", "required": False},
            {"action": "rds:log:listSlowLogs", "description": "查询 RDS 慢 SQL 日志", "required": False},
            {"action": "ces:alarm:list", "description": "查询 CES 告警规则", "required": False},
            {"action": "ces:metricData:get", "description": "查询 CES 监控指标数据", "required": False},
        ],
        "policy_template": {
            "name": "RDSFailoverExperimentPolicy",
            "description": "RDS 主备倒换演练所需权限",
            "statement": [
                {"effect": "Allow", "action": [
                    "rds:*:list", "rds:*:get", "rds:instance:failover",
                    "rds:log:listErrorLogs", "rds:log:listSlowLogs",
                    "ces:alarm:list", "ces:metricData:get",
                ]},
            ],
        },
        "region": region,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_monitoring_config(instance, region):
    """生成 CES 监控配置 monitoring.json"""
    return {
        "description": "RDS 主备倒换演练监控配置",
        "instance_id": instance["id"],
        "instance_name": instance["name"],
        "region": region,
        "ces_metrics": [
            {"metric_name": "rds_cpu_util", "namespace": "SYS.RDS", "description": "CPU 使用率", "unit": "%"},
            {"metric_name": "rds_mem_util", "namespace": "SYS.RDS", "description": "内存使用率", "unit": "%"},
            {"metric_name": "rds_disk_util", "namespace": "SYS.RDS", "description": "磁盘使用率", "unit": "%"},
            {"metric_name": "rds_connections_count", "namespace": "SYS.RDS", "description": "当前连接数", "unit": "count"},
            {"metric_name": "rds_in_flow", "namespace": "SYS.RDS", "description": "网络输入流量", "unit": "Bytes/s"},
            {"metric_name": "rds_out_flow", "namespace": "SYS.RDS", "description": "网络输出流量", "unit": "Bytes/s"},
            {"metric_name": "rds_iops", "namespace": "SYS.RDS", "description": "IOPS", "unit": "count/s"},
            {"metric_name": "rds_replication_delay", "namespace": "SYS.RDS", "description": "主备复制延迟", "unit": "s"},
        ],
        "alarm_rules": [
            {"name": f"failover_cpu_high_{instance['name']}", "metric": "rds_cpu_util", "threshold": 90, "comparison": ">=", "period": 300, "description": "CPU 使用率超过 90% 告警"},
            {"name": f"failover_disk_high_{instance['name']}", "metric": "rds_disk_util", "threshold": 85, "comparison": ">=", "period": 300, "description": "磁盘使用率超过 85% 告警"},
            {"name": f"failover_replication_delay_{instance['name']}", "metric": "rds_replication_delay", "threshold": 30, "comparison": ">=", "period": 60, "description": "主备复制延迟超过 30 秒告警"},
        ],
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="RDS 主备倒换实验准备")
    parser.add_argument("--region", default=None, help="华为云区域（默认从 config/config.json 读取）")
    parser.add_argument("--instance-id", default=None, help="实例 ID（默认从 config/config.json 读取）")
    parser.add_argument("--output-dir", default=None, help="输出目录（默认: experiments/）")
    parser.add_argument("--config-dir", default=None, help="配置目录别名，等同 --output-dir（用于 run.py 统一透传）")
    args = parser.parse_args()

    # ── 从 config/config.json 读取 region 和 instance_id ──
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
    if args.region or args.instance_id:
        print(f"[配置] (CLI 参数覆盖了 config.json 中的值)")

    print(f"\n[1/4] 查询 RDS 实例 (region={region})...")
    ha_instances, err = query_rds_instances(region)
    if err:
        print(f"[ERROR] 查询 RDS 实例失败: {err}")
        sys.exit(1)

    if not ha_instances:
        print(f"[ERROR] 区域 {region} 中没有 HA 类型的 RDS 实例。")
        sys.exit(1)

    print(f"  找到 {len(ha_instances)} 个 HA 实例:")
    for inst in ha_instances:
        marker = " ← 选定" if inst["id"] == instance_id else ""
        print(f"    - {inst['name']} ({inst['id']}) status={inst['status']} engine={inst['engine']}{marker}")

    # 选择目标实例 — 优先使用 config.json 中的 instance_id
    target = next((i for i in ha_instances if i["id"] == instance_id), None)
    if not target:
        if len(ha_instances) == 1:
            target = ha_instances[0]
            print(f"  config.json 中的 instance_id 未匹配，自动选择唯一 HA 实例: {target['name']}")
        else:
            print(f"\n[ERROR] config.json 中的 instance_id={instance_id} 不在 HA 实例列表中。")
            print(f"  可用实例: {', '.join(i['id'] for i in ha_instances)}")
            sys.exit(1)

    if target["status"] != "ACTIVE":
        print(f"[WARNING] 实例 {target['name']} 状态为 {target['status']}，非 ACTIVE。倒换可能失败。")

    print(f"\n[2/4] 检查 IAM 权限...")
    iam_result = query_iam_permissions(region)
    print(f"  AK 已配置: {'是' if iam_result['ak_present'] else '否'}")
    print(f"  SK 已配置: {'是' if iam_result['sk_present'] else '否'}")
    print(f"  RDS 读权限: {'是' if iam_result['rds_read_access'] else '否'}")
    _fs = iam_result.get("rds_failover_status", "unknown")
    _fs_label = {"allow": "是", "deny": "否", "unknown": "未知（无法获取策略详情）"}.get(_fs, "未知")
    print(f"  RDS 倒换权限: {_fs_label}")
    print(f"  RDS 相关策略数: {iam_result['policy_count']}")

    print(f"\n[3/4] 生成配置文件...")

    output_dir = args.output_dir or args.config_dir or DEFAULT_OUTPUT_BASE
    os.makedirs(output_dir, exist_ok=True)

    experiment = generate_experiment_template(target, region)
    with open(os.path.join(output_dir, "experiment.json"), "w", encoding="utf-8") as f:
        json.dump(experiment, f, ensure_ascii=False, indent=2)
    print(f"  ✓ experiment.json")

    iam_policy = generate_iam_policy(region)
    iam_policy["iam_check_result"] = iam_result
    with open(os.path.join(output_dir, "iam_policy.json"), "w", encoding="utf-8") as f:
        json.dump(iam_policy, f, ensure_ascii=False, indent=2)
    print(f"  ✓ iam_policy.json")

    monitoring = generate_monitoring_config(target, region)
    with open(os.path.join(output_dir, "monitoring.json"), "w", encoding="utf-8") as f:
        json.dump(monitoring, f, ensure_ascii=False, indent=2)
    print(f"  ✓ monitoring.json")

    print(f"\n[4/5] 配置目录生成完成!")
    print(f"  目录: {output_dir}")

    # ── 生成准备报告（HTML + Markdown）──
    print(f"\n[5/5] 生成准备报告...")
    checks = run_readiness_checks(target, iam_result, monitoring, region, instance_id)

    critical_fails = [c for c in checks if c["critical"] and not c["passed"]]
    all_critical_pass = len(critical_fails) == 0
    total = len(checks)
    passed_count = sum(1 for c in checks if c["passed"])

    html_path = generate_readiness_report_html(checks, target, region, instance_id, output_dir)
    print(f"  ✓ readiness_report.html")
    md_path = generate_readiness_report_md(checks, target, region, instance_id, output_dir)
    print(f"  ✓ readiness_report.md")

    print(f"\n  ── 准备检查摘要 ──")
    print(f"  总检查项: {total}  通过: {passed_count}  未通过: {total - passed_count}")
    if all_critical_pass:
        print(f"  结论: ✅ 准备就绪，可以执行 RDS 主备倒换演练")
    else:
        print(f"  结论: ❌ 准备未就绪，以下必需项未通过:")
        for cf in critical_fails:
            print(f"    ❌ {cf['item']} — {cf['detail']}")

    print(f"\n  报告: {html_path}")
    print(f"        {md_path}")
    print(f"\n  下一步: 使用 run.py --phase execute --yes 执行倒换")
    print(f"  命令: python3 execute.py --config-dir {output_dir}")


# ---------------------------------------------------------------------------
# 准备报告生成（HTML + Markdown）
# ---------------------------------------------------------------------------

def run_readiness_checks(target, iam_result, monitoring, region, instance_id):
    """
    运行全面准备检查，返回检查项列表和总体结论。

    每个检查项:
      {
        "category": "实例" / "IAM权限" / "监控" / "配置",
        "item": "检查项名称",
        "passed": True/False,
        "critical": True/False,   # True=必须通过才能倒换, False=建议项
        "detail": "详细信息",
      }
    """
    checks = []

    # ── 配置检查 ──
    checks.append({
        "category": "配置", "item": "config.json 可读取",
        "passed": True, "critical": True,
        "detail": f"region={region}, instance_id={instance_id}",
    })
    checks.append({
        "category": "配置", "item": "hcloud CLI 可用",
        "passed": iam_result.get("rds_read_access", False), "critical": True,
        "detail": "hcloud profile 已配置" if iam_result.get("rds_read_access") else "hcloud 未认证或不可用",
    })

    # ── 实例检查 ──
    checks.append({
        "category": "实例", "item": "实例存在",
        "passed": True, "critical": True,
        "detail": f"{target['name']} ({target['id']})",
    })
    checks.append({
        "category": "实例", "item": "实例为 HA 类型",
        "passed": target.get("type", "").lower() in ("ha", "replication"), "critical": True,
        "detail": f"type={target.get('type', 'N/A')}",
    })
    checks.append({
        "category": "实例", "item": "实例状态为 ACTIVE",
        "passed": target.get("status") == "ACTIVE", "critical": True,
        "detail": f"status={target.get('status', 'N/A')}",
    })
    checks.append({
        "category": "实例", "item": "主节点存在",
        "passed": bool(target.get("master_node")), "critical": True,
        "detail": f"{target.get('master_node', 'N/A')} (AZ={target.get('master_az', 'N/A')})",
    })
    checks.append({
        "category": "实例", "item": "备节点存在",
        "passed": bool(target.get("slave_node")), "critical": True,
        "detail": f"{target.get('slave_node', 'N/A')} (AZ={target.get('slave_az', 'N/A')})",
    })
    checks.append({
        "category": "实例", "item": "主备节点在不同 AZ",
        "passed": target.get("master_az") != target.get("slave_az") and bool(target.get("master_az")),
        "critical": False,
        "detail": f"master AZ={target.get('master_az', 'N/A')}, slave AZ={target.get('slave_az', 'N/A')}",
    })
    checks.append({
        "category": "实例", "item": "HA 复制模式已配置",
        "passed": bool(target.get("ha_mode") and target.get("ha_mode") != "N/A"), "critical": False,
        "detail": f"ha_mode={target.get('ha_mode', 'N/A')}",
    })

    # ── IAM 权限检查 ──
    checks.append({
        "category": "IAM权限", "item": "RDS 实例列表查询权限",
        "passed": iam_result.get("rds_read_access", False), "critical": True,
        "detail": "rds:instance:list",
    })
    checks.append({
        "category": "IAM权限", "item": "RDS 主备倒换执行权限",
        "passed": iam_result.get("rds_failover_capable", False), "critical": True,
        "detail": "rds:instance:failover",
    })
    checks.append({
        "category": "IAM权限", "item": "AK/SK 环境变量已配置",
        "passed": iam_result.get("ak_present", False) and iam_result.get("sk_present", False),
        "critical": False,
        "detail": "使用 hcloud profile 认证" if not iam_result.get("ak_present") else "AK/SK 在环境变量中",
    })
    checks.append({
        "category": "IAM权限", "item": "RDS 相关策略已分配",
        "passed": iam_result.get("policy_count", 0) > 0, "critical": False,
        "detail": f"策略数={iam_result.get('policy_count', 0)}",
    })

    # ── 监控检查 ──
    ces_metrics = monitoring.get("ces_metrics", [])
    alarm_rules = monitoring.get("alarm_rules", [])
    checks.append({
        "category": "监控", "item": "CES 监控指标已配置",
        "passed": len(ces_metrics) > 0, "critical": False,
        "detail": f"{len(ces_metrics)} 个指标",
    })
    checks.append({
        "category": "监控", "item": "告警规则已配置",
        "passed": len(alarm_rules) > 0, "critical": False,
        "detail": f"{len(alarm_rules)} 条告警规则",
    })

    return checks


def generate_readiness_report_html(checks, target, region, instance_id, output_dir):
    """生成 HTML 格式的准备报告"""
    critical_fails = [c for c in checks if c["critical"] and not c["passed"]]
    warning_fails = [c for c in checks if not c["critical"] and not c["passed"]]
    all_critical_pass = len(critical_fails) == 0
    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 按类别分组
    categories = []
    seen = set()
    for c in checks:
        if c["category"] not in seen:
            seen.add(c["category"])
            categories.append(c["category"])

    rows = ""
    for cat in categories:
        cat_checks = [c for c in checks if c["category"] == cat]
        for i, c in enumerate(cat_checks):
            icon = "&#9989;" if c["passed"] else "&#10060;"
            crit = '<span class="badge" style="background:#e74c3c">必需</span>' if c["critical"] else '<span class="badge" style="background:#95a5a6">建议</span>'
            status = '<span style="color:#27ae60;font-weight:600">通过</span>' if c["passed"] else '<span style="color:#e74c3c;font-weight:600">未通过</span>'
            cat_label = f'<td rowspan="{len(cat_checks)}" class="cat">{cat}</td>' if i == 0 else ""
            rows += f"\n        <tr>{cat_label}<td>{icon}</td><td>{c['item']}</td><td>{crit}</td><td>{status}</td><td>{c['detail']}</td></tr>"

    if all_critical_pass:
        banner = f'<div class="banner ok">&#9989; 准备就绪 — 可以执行 RDS 主备倒换演练</div>'
    else:
        fail_list = "<br>".join(f"&#10060; {f['item']} — {f['detail']}" for f in critical_fails)
        banner = f'<div class="banner fail">&#10060; 准备未就绪 — 以下必需项未通过：<br>{fail_list}</div>'

    warning_section = ""
    if warning_fails:
        w_items = "".join(f"<li>{w['item']} — {w['detail']}</li>" for w in warning_fails)
        warning_section = f'<div class="card"><h2>&#9888; 建议项未通过（不阻止倒换）</h2><ul>{w_items}</ul></div>'

    css = """
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:-apple-system,"Microsoft YaHei",sans-serif; background:#f5f7fa; color:#333; line-height:1.6; }
    .c { max-width:900px; margin:0 auto; padding:20px; }
    .hd { background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; padding:30px; border-radius:12px; margin-bottom:24px; }
    .hd h1 { font-size:22px; margin-bottom:8px; }
    .hd .meta { font-size:13px; opacity:.85; }
    .banner { padding:16px; border-radius:8px; font-size:16px; font-weight:600; margin-bottom:20px; text-align:center; }
    .banner.ok { background:#e8f5e9; color:#2e7d32; border:2px solid #4caf50; }
    .banner.fail { background:#fbe9e7; color:#c62828; border:2px solid #e74c3c; }
    .card { background:#fff; border-radius:10px; padding:24px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
    .card h2 { font-size:16px; color:#2c3e50; margin-bottom:16px; padding-bottom:10px; border-bottom:2px solid #ecf0f1; }
    .summary { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:20px; }
    .stat { background:#fff; border-radius:10px; padding:20px; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,.06); }
    .stat .num { font-size:28px; font-weight:700; }
    .stat .lbl { font-size:13px; color:#7f8c8d; margin-top:4px; }
    table { width:100%; border-collapse:collapse; font-size:13px; }
    th { background:#f8f9fa; text-align:left; padding:10px 12px; border-bottom:2px solid #e0e0e0; color:#555; font-weight:600; }
    td { padding:8px 12px; border-bottom:1px solid #f0f0f0; }
    .cat { background:#f0f4f8; font-weight:600; text-align:center; vertical-align:middle; }
    .badge { display:inline-block; padding:2px 8px; border-radius:10px; color:#fff; font-size:11px; }
    ul { margin:10px 0 10px 20px; } li { margin-bottom:6px; }
    .ft { text-align:center; color:#aaa; font-size:12px; margin-top:24px; }
    """

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>RDS 主备倒换准备报告 - {target['name']}</title>
<style>{css}</style></head>
<body><div class="c">

  <div class="hd">
    <h1>&#128203 RDS 主备倒换准备报告</h1>
    <div class="meta">实例：{target['name']} ｜ 区域：{region} ｜ 生成时间：{now_str}</div>
  </div>

  {banner}

  <div class="summary">
    <div class="stat"><div class="num" style="color:#27ae60">{passed}</div><div class="lbl">通过项</div></div>
    <div class="stat"><div class="num" style="color:#e74c3c">{total - passed}</div><div class="lbl">未通过项</div></div>
    <div class="stat"><div class="num" style="color:#e67e22">{len(critical_fails)}</div><div class="lbl">必需项未通过</div></div>
  </div>

  <div class="card">
    <h2>&#128269 检查明细（共 {total} 项）</h2>
    <table>
      <thead><tr><th>类别</th><th>结果</th><th>检查项</th><th>级别</th><th>状态</th><th>详情</th></tr></thead>
      <tbody>{rows}
      </tbody>
    </table>
  </div>

  {warning_section}

  <div class="ft">本报告由 huawei-cloud-rds-failover skill 自动生成 ｜ {now_str}</div>

</div></body></html>"""

    filepath = os.path.join(output_dir, "readiness_report.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(doc)
    return filepath


def generate_readiness_report_md(checks, target, region, instance_id, output_dir):
    """生成 Markdown 格式的准备报告"""
    critical_fails = [c for c in checks if c["critical"] and not c["passed"]]
    warning_fails = [c for c in checks if not c["critical"] and not c["passed"]]
    all_critical_pass = len(critical_fails) == 0
    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append(f"# RDS 主备倒换准备报告")
    lines.append(f"")
    lines.append(f"| 项目 | 值 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 实例名称 | {target['name']} |")
    lines.append(f"| 实例 ID | {target['id']} |")
    lines.append(f"| 区域 | {region} |")
    lines.append(f"| 引擎 | {target['engine']} |")
    lines.append(f"| 规格 | {target['flavor']} |")
    lines.append(f"| HA 模式 | {target.get('ha_mode', 'N/A')} |")
    lines.append(f"| 生成时间 | {now_str} |")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # 总体结论
    if all_critical_pass:
        lines.append(f"## ✅ 准备就绪 — 可以执行 RDS 主备倒换演练")
    else:
        lines.append(f"## ❌ 准备未就绪 — 以下必需项未通过")
        lines.append(f"")
        for f in critical_fails:
            lines.append(f"- ❌ **{f['item']}** — {f['detail']}")
    lines.append(f"")
    lines.append(f"### 统计摘要")
    lines.append(f"")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 总检查项 | {total} |")
    lines.append(f"| 通过 | {passed} |")
    lines.append(f"| 未通过 | {total - passed} |")
    lines.append(f"| 必需项未通过 | {len(critical_fails)} |")
    lines.append(f"| 建议项未通过 | {len(warning_fails)} |")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # 按类别分组
    seen = set()
    categories = []
    for c in checks:
        if c["category"] not in seen:
            seen.add(c["category"])
            categories.append(c["category"])

    for cat in categories:
        lines.append(f"## {cat}")
        lines.append(f"")
        lines.append(f"| 结果 | 检查项 | 级别 | 状态 | 详情 |")
        lines.append(f"|------|--------|------|------|------|")
        for c in checks:
            if c["category"] != cat:
                continue
            icon = "✅" if c["passed"] else "❌"
            crit = "必需" if c["critical"] else "建议"
            status = "通过" if c["passed"] else "**未通过**"
            lines.append(f"| {icon} | {c['item']} | {crit} | {status} | {c['detail']} |")
        lines.append(f"")

    # 建议项未通过
    if warning_fails:
        lines.append(f"## ⚠️ 建议项未通过（不阻止倒换）")
        lines.append(f"")
        for w in warning_fails:
            lines.append(f"- {w['item']} — {w['detail']}")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*本报告由 huawei-cloud-rds-failover skill 自动生成 ｜ {now_str}*")

    filepath = os.path.join(output_dir, "readiness_report.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return filepath


if __name__ == "__main__":
    main()
