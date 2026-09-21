#!/usr/bin/env python3
"""
RDS 主备倒换 — 结果报告脚本

从 config/config.json 读取 region 和 instance_id，
读取配置目录和执行结果，生成综合 HTML 报告。
"""

import argparse
import datetime
import html
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.join(SCRIPT_DIR, "..")
REPORT_DIR = os.path.join(SKILL_ROOT, "report")

# 导入共享配置模块
sys.path.insert(0, SCRIPT_DIR)
from config import load_config, get_config_path


def load_json(filepath):
    """加载 JSON 文件，校验存在性与格式"""
    if not os.path.isfile(filepath):
        print(f"[ERROR] 文件不存在: {filepath}")
        print("请先运行前置阶段（prepare / execute），或检查 --config-dir 路径是否正确。")
        sys.exit(1)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 格式错误: {filepath}")
        print(f"  解析失败: {e}")
        sys.exit(1)


def esc(text):
    return html.escape(str(text))


def build_timeline_rows(exec_result):
    rows = ""
    for e in (exec_result.get("timeline") or []):
        st = esc(e.get("status", ""))
        sc = "#e67e22" if "SWITCHOVER" in st else ("#27ae60" if "ACTIVE" in st else "#7f8c8d")
        rows += (
            f"\n        <tr><td>{esc(e.get('elapsed',0))}s</td>"
            f"<td><span class=\"badge\" style=\"background:{sc}\">{st}</span></td>"
            f"<td>{esc(e.get('master',''))}</td>"
            f"<td>{esc(e.get('slave',''))}</td></tr>"
        )
    return rows


def build_check_rows(exec_result):
    checks = exec_result.get("checks") or {}
    labels = {
        "instance_found": "实例存在",
        "status_active": "实例状态 ACTIVE",
        "is_ha": "实例为 HA 类型",
        "iam_rds_access": "IAM RDS 读权限",
        "iam_failover_capable": "IAM 倒换权限",
    }
    rows = ""
    for k, v in checks.items():
        icon = "&#9989;" if v else "&#10060;"
        rows += f"\n        <tr><td>{icon}</td><td>{esc(labels.get(k, k))}</td><td>{'通过' if v else '未通过'}</td></tr>"
    return rows


def build_perm_rows(iam_policy):
    rows = ""
    for p in (iam_policy.get("required_permissions") or []):
        label = "是" if p.get("required") else "否"
        rows += (
            f"\n        <tr><td><code>{esc(p.get('action',''))}</code></td>"
            f"<td>{esc(p.get('description',''))}</td><td>{label}</td></tr>"
        )
    return rows


def build_log_section(title, icon, logs_data, columns):
    if logs_data.get("available") and logs_data.get("logs"):
        rows = ""
        for log in logs_data["logs"][:20]:
            cells = "".join(f"<td>{esc(log.get(c,''))[:100]}</td>" for c in columns)
            rows += f"\n        <tr>{cells}</tr>"
        ths = "".join(f"<th>{h}</th>" for h in columns)
        count = logs_data.get("count", 0)
        return f"""
  <div class="card">
    <h2>{icon} {title}（倒换期间）</h2>
    <p class="hint">共 {count} 条，展示前 {min(20, count)} 条</p>
    <table><thead><tr>{ths}</tr></thead><tbody>{rows}
    </tbody></table>
  </div>"""
    return f"""
  <div class="card">
    <h2>{icon} {title}（倒换期间）</h2>
    <p class="hint">倒换期间无{title}，或日志接口未返回数据。</p>
  </div>"""


def build_metric_rows(exec_result):
    rows = ""
    for m in (exec_result.get("ces_metrics") or []):
        name = m.get("metric_name", "")
        if m.get("available"):
            dps = m.get("datapoints", [])
            if dps:
                values = []
                for d in dps:
                    avg_val = d.get("average")
                    if avg_val is None:
                        avg_val = d.get("value")
                    if avg_val is not None:
                        values.append(avg_val)
                if values:
                    avg = sum(values) / len(values)
                    latest = values[-1]
                    rows += f"\n        <tr><td><code>{esc(name)}</code></td><td>{len(dps)}</td><td>{avg:.2f}</td><td>{latest:.2f}</td></tr>"
                else:
                    rows += f"\n        <tr><td><code>{esc(name)}</code></td><td>{len(dps)}</td><td>-</td><td>-</td></tr>"
            else:
                rows += f"\n        <tr><td><code>{esc(name)}</code></td><td>0</td><td>-</td><td>-</td></tr>"
        else:
            rows += f"\n        <tr><td><code>{esc(name)}</code></td><td colspan=\"3\" class=\"muted\">不可用</td></tr>"
    return rows


def build_alarm_section(exec_result):
    alarms = exec_result.get("alarm_rules") or {}
    if alarms.get("available") and alarms.get("rules"):
        rows = ""
        for r in alarms["rules"]:
            rows += (
                f"\n        <tr><td>{esc(r.get('name',''))}</td>"
                f"<td>{esc(r.get('metric',''))}</td>"
                f"<td>{esc(r.get('status',''))}</td>"
                f"<td>{esc(r.get('level',''))}</td></tr>"
            )
        return f"""
  <div class="card">
    <h2>&#128680 告警规则状态</h2>
    <p class="hint">共 {alarms.get('count',0)} 条规则</p>
    <table><thead><tr><th>规则名称</th><th>指标</th><th>状态</th><th>级别</th></tr></thead><tbody>{rows}
    </tbody></table>
  </div>"""
    return """
  <div class="card">
    <h2>&#128680 告警规则状态</h2>
    <p class="hint">当前无告警规则，或告警接口未返回数据。</p>
  </div>"""


CSS = """
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:-apple-system,"Microsoft YaHei",sans-serif; background:#f5f7fa; color:#333; line-height:1.6; }
    .c { max-width:960px; margin:0 auto; padding:20px; }
    .hd { background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; padding:30px; border-radius:12px; margin-bottom:24px; }
    .hd h1 { font-size:24px; margin-bottom:8px; }
    .hd .meta { font-size:13px; opacity:.85; }
    .card { background:#fff; border-radius:10px; padding:24px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
    .card h2 { font-size:16px; color:#2c3e50; margin-bottom:16px; padding-bottom:10px; border-bottom:2px solid #ecf0f1; }
    .hint { color:#7f8c8d; font-size:13px; margin-bottom:10px; }
    .ig { display:grid; grid-template-columns:1fr 1fr; gap:12px 24px; }
    .ii { display:flex; }
    .ii .lb { color:#7f8c8d; min-width:110px; font-size:13px; }
    .ii .vl { font-weight:500; font-size:13px; }
    .tp { display:flex; gap:20px; margin-top:10px; }
    .nb { flex:1; border-radius:8px; padding:16px; text-align:center; }
    .nm { background:#e8f5e9; border:2px solid #4caf50; }
    .ns { background:#e3f2fd; border:2px solid #2196f3; }
    .nb .role { font-size:20px; margin-bottom:6px; }
    .nb .name { font-weight:600; font-size:14px; }
    .nb .det { font-size:12px; color:#666; margin-top:4px; }
    .arrow { text-align:center; font-size:28px; color:#aaa; margin:12px 0; }
    table { width:100%; border-collapse:collapse; font-size:13px; }
    th { background:#f8f9fa; text-align:left; padding:10px 12px; border-bottom:2px solid #e0e0e0; color:#555; font-weight:600; }
    td { padding:8px 12px; border-bottom:1px solid #f0f0f0; }
    tr:hover td { background:#fafbfc; }
    .badge { display:inline-block; padding:2px 10px; border-radius:12px; color:#fff; font-size:12px; }
    .rb { text-align:center; padding:16px; border-radius:8px; font-size:18px; font-weight:600; margin-bottom:16px; }
    .ft { text-align:center; color:#aaa; font-size:12px; margin-top:24px; }
    .muted { color:#bbb; }
    code { background:#f4f4f4; padding:2px 6px; border-radius:3px; font-size:12px; }
"""


def generate_report(config_dir, cfg):
    experiment = load_json(os.path.join(config_dir, "experiment.json"))
    iam_policy = load_json(os.path.join(config_dir, "iam_policy.json"))
    monitoring = load_json(os.path.join(config_dir, "monitoring.json"))

    result_path = os.path.join(config_dir, "execution_result.json")
    if not os.path.isfile(result_path):
        print(f"[ERROR] 执行结果文件不存在: {result_path}")
        print("请先运行 execute.py --yes 执行倒换。")
        sys.exit(1)
    exec_result = load_json(result_path)

    os.makedirs(REPORT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(REPORT_DIR, f"failover_report_{ts}.html")

    result_text = exec_result.get("result", "unknown")
    # 区分 success/failed/timeout/unknown 四种状态，各自匹配文案与颜色
    RESULT_STYLES = {
        "success": ("#27ae60", "&#9989; 成功"),
        "failed":  ("#e74c3c", "&#10060; 失败"),
        "timeout": ("#e67e22", "&#9203; 超时"),
        "unknown": ("#7f8c8d", "&#2754; 未知"),
    }
    rc, rl = RESULT_STYLES.get(result_text, RESULT_STYLES["unknown"])
    dur = exec_result.get("duration_seconds", 0)
    inst_name = exec_result.get("instance_name", "")
    inst_id = cfg["instance_id"]
    region = cfg["region"]
    engine_val = exec_result.get("engine", "")
    flavor_val = exec_result.get("flavor", "")
    wf = exec_result.get("workflow_id", "N/A")
    st_time = exec_result.get("start_time", "")
    ed_time = exec_result.get("end_time", "")
    bm = exec_result.get("before_master", {})
    bs = exec_result.get("before_slave", {})
    am = exec_result.get("after_master", {})
    asl = exec_result.get("after_slave", {})

    timeline_rows = build_timeline_rows(exec_result)
    check_rows = build_check_rows(exec_result)
    perm_rows = build_perm_rows(iam_policy)
    metric_rows = build_metric_rows(exec_result)

    mon_metrics = monitoring.get("ces_metrics") or []
    mon_list = ", ".join(m.get("metric_name", "") for m in mon_metrics)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    exp_name = experiment.get("experiment_name", "")

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RDS 主备倒换演练报告 - {esc(inst_name)}</title>
  <style>{CSS}</style>
</head>
<body>
<div class="c">

  <div class="hd">
    <h1>&#128202 RDS 主备倒换演练报告</h1>
    <div class="meta">实验：{esc(exp_name)} ｜ 生成时间：{esc(now_str)} ｜ 区域：{esc(region)} ｜ 配置来源：config/config.json</div>
  </div>

  <div class="rb" style="background:{rc}1a;color:{rc};border:1px solid {rc};">{rl} ｜ 倒换耗时：{dur} 秒 ｜ 工作流：{esc(wf)}</div>

  <div class="card">
    <h2>&#128295 实例信息</h2>
    <div class="ig">
      <div class="ii"><span class="lb">实例名称</span><span class="vl">{esc(inst_name)}</span></div>
      <div class="ii"><span class="lb">实例 ID</span><span class="vl">{esc(inst_id)}</span></div>
      <div class="ii"><span class="lb">数据库引擎</span><span class="vl">{esc(engine_val)}</span></div>
      <div class="ii"><span class="lb">规格</span><span class="vl">{esc(flavor_val)}</span></div>
      <div class="ii"><span class="lb">开始时间</span><span class="vl">{esc(st_time)}</span></div>
      <div class="ii"><span class="lb">结束时间</span><span class="vl">{esc(ed_time)}</span></div>
    </div>
  </div>

  <div class="card">
    <h2>&#128737 安全检查</h2>
    <table><thead><tr><th>结果</th><th>检查项</th><th>状态</th></tr></thead><tbody>{check_rows}
    </tbody></table>
  </div>

  <div class="card">
    <h2>&#128273 IAM 权限</h2>
    <p class="hint">倒换所需的最小权限集</p>
    <table><thead><tr><th>权限动作</th><th>说明</th><th>必需</th></tr></thead><tbody>{perm_rows}
    </tbody></table>
  </div>

  <div class="card">
    <h2>&#128260 主备拓扑变化</h2>
    <p class="hint">倒换前</p>
    <div class="tp">
      <div class="nb nm"><div class="role">&#9733 主节点</div><div class="name">{esc(bm.get('name','N/A'))}</div><div class="det">AZ: {esc(bm.get('az','N/A'))} ｜ 状态: {esc(bm.get('status','N/A'))}</div></div>
      <div class="nb ns"><div class="role">&#9675 备节点</div><div class="name">{esc(bs.get('name','N/A'))}</div><div class="det">AZ: {esc(bs.get('az','N/A'))} ｜ 状态: {esc(bs.get('status','N/A'))}</div></div>
    </div>
    <div class="arrow">&#11015</div>
    <p class="hint">倒换后</p>
    <div class="tp">
      <div class="nb nm"><div class="role">&#9733 主节点</div><div class="name">{esc(am.get('name','N/A'))}</div><div class="det">AZ: {esc(am.get('az','N/A'))} ｜ 状态: {esc(am.get('status','N/A'))}</div></div>
      <div class="nb ns"><div class="role">&#9675 备节点</div><div class="name">{esc(asl.get('name','N/A'))}</div><div class="det">AZ: {esc(asl.get('az','N/A'))} ｜ 状态: {esc(asl.get('status','N/A'))}</div></div>
    </div>
  </div>

  <div class="card">
    <h2>&#9201 倒换时间线</h2>
    <table><thead><tr><th>耗时</th><th>实例状态</th><th>主节点</th><th>备节点</th></tr></thead><tbody>{timeline_rows}
    </tbody></table>
  </div>

  <div class="card">
    <h2>&#128201 CES 监控指标</h2>
    <p class="hint">监控指标：{esc(mon_list)}</p>
    <table><thead><tr><th>指标</th><th>数据点数</th><th>平均值</th><th>最新值</th></tr></thead><tbody>{metric_rows}
    </tbody></table>
  </div>

  <div class="ft">本报告由 huawei-cloud-rds-failover skill 自动生成 ｜ region/instance_id 来自 config/config.json ｜ {esc(now_str)}</div>

</div>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"[完成] HTML 报告已生成: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="RDS 主备倒换结果报告")
    parser.add_argument("--config-dir", required=True, help="配置目录路径")
    args = parser.parse_args()

    if not os.path.isdir(args.config_dir):
        print(f"[ERROR] 配置目录不存在: {args.config_dir}")
        sys.exit(1)

    # 从 config/config.json 读取 region 和 instance_id
    config_path = get_config_path()
    print(f"[配置] 读取共享配置: {config_path}")
    try:
        cfg = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"[配置] region={cfg['region']}, instance_id={cfg['instance_id']}")
    generate_report(args.config_dir, cfg)


if __name__ == "__main__":
    main()
