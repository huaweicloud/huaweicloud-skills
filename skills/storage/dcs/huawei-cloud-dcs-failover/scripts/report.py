#!/usr/bin/env python3
"""
DCS master-slave failover — report script.

Reads region and instance_id from config/config.json,
reads config directory and execution result, generates a comprehensive HTML report.

Usage:
  python3 report.py --config-dir <path>
"""

import argparse
import datetime
import html
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.join(SCRIPT_DIR, "..")

sys.path.insert(0, SCRIPT_DIR)
from config import load_config, get_config_path, load_json, now_str, TEMPLATES_DIR, clean_experiments

# Final report output directory (HTML)
REPORT_DIR = TEMPLATES_DIR


def esc(text):
    """HTML entity escape — prevent external data from triggering stored XSS."""
    return html.escape(str(text))



# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_timeline_rows(exec_result):
    """Failover timeline: use node_id (master_id/slave_id) as node identifier,
    combined with AZ, to直观 show node changes before/after failover (IP/name unchanged but node_id swapped).
    """
    rows = ""
    for e in (exec_result.get("timeline") or []):
        st = esc(e.get("status", ""))
        sc = "#e67e22" if "SWITCHOVER" in st or "RESTART" in st else ("#27ae60" if "RUNNING" in st else "#7f8c8d")
        master_id = e.get("master_id", "")
        slave_id = e.get("slave_id", "")
        master_az = e.get("master_az", "")
        slave_az = e.get("slave_az", "")
        # Abbreviated node_id display (keep end, truncate if too long), IP as auxiliary info
        master_label = esc(f"{shorten_id(master_id)}({master_az})")
        slave_label = esc(f"{shorten_id(slave_id)}({slave_az})")
        if not master_id:
            master_label = esc(e.get('master', ''))
        if not slave_id:
            slave_label = esc(e.get('slave', ''))
        rows += (f"\n        <tr><td>{esc(e.get('elapsed', 0))}s</td>"
                 f"<td><span class=\"badge\" style=\"background:{sc}\">{st}</span></td>"
                 f"<td>{master_label}</td>"
                 f"<td>{slave_label}</td></tr>")
    return rows


def shorten_id(node_id):
    """Abbreviate long node_id: keep first 12 chars + ... + last 4 chars."""
    if not node_id:
        return ""
    if len(node_id) <= 20:
        return node_id
    return f"{node_id[:12]}...{node_id[-4:]}"


def build_check_rows(exec_result):
    checks = exec_result.get("checks") or {}
    labels = {"instance_found": "实例存在", "status_running": "实例状态 RUNNING",
              "is_ha": "实例为主备类型", "iam_dcs_access": "IAM DCS 读权限",
              "iam_failover_capable": "IAM 倒换权限"}
    rows = ""
    for k, v in checks.items():
        icon = "&#9989;" if v else "&#10060;"
        rows += (f"\n        <tr><td>{icon}</td><td>{esc(labels.get(k, k))}</td><td>{'通过' if v else '未通过'}</td></tr>")
    return rows


def build_consistency_section(exec_result):
    cons = exec_result.get("consistency_check", {})
    rows = ""
    for c in cons.get("checks", []):
        icon = "&#9989;" if c.get("ok") else "&#10060;"
        rows += (f"\n        <tr><td>{icon}</td><td>{esc(c.get('name', ''))}</td><td>{esc(c.get('value', ''))}</td></tr>")
    return f"""
  <div class="card">
    <h2>&#128270 数据一致性检查</h2>
    <table><thead><tr><th>结果</th><th>检查项</th><th>值</th></tr></thead><tbody>{rows}
    </tbody></table>
  </div>"""


CSS = """
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:-apple-system,"Microsoft YaHei",sans-serif; background:#f5f7fa; color:#333; line-height:1.6; }
    .c { max-width:960px; margin:0 auto; padding:20px; }
    .hd { background:linear-gradient(135deg,#e67e22,#764ba2); color:#fff; padding:30px; border-radius:12px; margin-bottom:24px; }
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
    result_path = os.path.join(config_dir, "execution_result.json")
    if not os.path.isfile(result_path):
        print(f"[ERROR] 执行结果文件不存在: {result_path}")
        print("请先运行 execute.py 执行倒换。")
        sys.exit(1)
    exec_result = load_json(result_path)

    os.makedirs(REPORT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(REPORT_DIR, f"failover_report_{ts}.html")

    result_text = exec_result.get("result", "unknown")
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
    engine_val = f"{exec_result.get('engine', '')} {exec_result.get('engine_version', '')}".strip()
    capacity = exec_result.get("capacity", "")
    st_time = exec_result.get("start_time", "")
    ed_time = exec_result.get("end_time", "")
    bm = exec_result.get("before_master", {})
    bs = exec_result.get("before_slave", {})
    am = exec_result.get("after_master", {})
    asl = exec_result.get("after_slave", {})

    timeline_rows = build_timeline_rows(exec_result)
    check_rows = build_check_rows(exec_result)
    consistency_html = build_consistency_section(exec_result)

    now_str_ = now_str()

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DCS 主备倒换演练报告 - {esc(inst_name)}</title>
  <style>{CSS}</style>
</head>
<body>
<div class="c">

  <div class="hd">
    <h1>&#9889 DCS 主备倒换演练报告</h1>
    <div class="meta">生成时间：{esc(now_str_)} ｜ 区域：{esc(region)}</div>
  </div>

  <div class="rb" style="background:{rc}1a;color:{rc};border:1px solid {rc};">{rl} ｜ 倒换耗时：{dur} 秒</div>

  <div class="card">
    <h2>&#128295 实例信息</h2>
    <div class="ig">
      <div class="ii"><span class="lb">实例名称</span><span class="vl">{esc(inst_name)}</span></div>
      <div class="ii"><span class="lb">实例 ID</span><span class="vl">{esc(inst_id)}</span></div>
      <div class="ii"><span class="lb">引擎</span><span class="vl">{esc(engine_val)}</span></div>
      <div class="ii"><span class="lb">容量</span><span class="vl">{esc(capacity)}GB</span></div>
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
    <h2>&#128260 主备拓扑变化</h2>
    <p class="hint">倒换前</p>
    <div class="tp">
      <div class="nb nm"><div class="role">&#9733 主节点</div><div class="name">{esc(bm.get('name', 'N/A'))}</div><div class="det">AZ: {esc(bm.get('az', 'N/A'))} ｜ 状态: {esc(bm.get('status', 'N/A'))} ｜ node_id: {esc(bm.get('id', 'N/A'))}</div></div>
      <div class="nb ns"><div class="role">&#9675 备节点</div><div class="name">{esc(bs.get('name', 'N/A'))}</div><div class="det">AZ: {esc(bs.get('az', 'N/A'))} ｜ 状态: {esc(bs.get('status', 'N/A'))} ｜ node_id: {esc(bs.get('id', 'N/A'))}</div></div>
    </div>
    <div class="arrow">&#11015</div>
    <p class="hint">倒换后</p>
    <div class="tp">
      <div class="nb nm"><div class="role">&#9733 主节点</div><div class="name">{esc(am.get('name', 'N/A'))}</div><div class="det">AZ: {esc(am.get('az', 'N/A'))} ｜ 状态: {esc(am.get('status', 'N/A'))} ｜ node_id: {esc(am.get('id', 'N/A'))}</div></div>
      <div class="nb ns"><div class="role">&#9675 备节点</div><div class="name">{esc(asl.get('name', 'N/A'))}</div><div class="det">AZ: {esc(asl.get('az', 'N/A'))} ｜ 状态: {esc(asl.get('status', 'N/A'))} ｜ node_id: {esc(asl.get('id', 'N/A'))}</div></div>
    </div>
  </div>

  <div class="card">
    <h2>&#9201 倒换时间线</h2>
    <table><thead><tr><th>耗时</th><th>实例状态</th><th>主节点</th><th>备节点</th></tr></thead><tbody>{timeline_rows}
    </tbody></table>
  </div>

  {consistency_html}

  <div class="ft">本报告由 huawei-cloud-dcs-failover skill 自动生成 ｜ region/instance_id 来自 config/config.json ｜ {esc(now_str_)}</div>

</div>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"[完成] HTML 报告已生成: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="DCS 主备倒换结果报告")
    parser.add_argument("--config-dir", required=True, help="配置目录路径")
    args = parser.parse_args()

    if not os.path.isdir(args.config_dir):
        print(f"[ERROR] 配置目录不存在: {args.config_dir}")
        sys.exit(1)

    config_path = get_config_path()
    print(f"[配置] 读取共享配置: {config_path}")
    try:
        cfg = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"[配置] region={cfg['region']}, instance_id={cfg['instance_id']}")
    generate_report(args.config_dir, cfg)

    # Clean experiments/ temp files after report generation
    clean_experiments()


if __name__ == "__main__":
    main()
