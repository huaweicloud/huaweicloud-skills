"""
DCS master-slave failover drill — shared config and utility module.

Reads region and instance_id from config/config.json,
provides run_hcloud / load_json / save_json / CES query helpers.
Shared by prepare / risk / execute / report phases.
"""

import datetime
import json
import os
import subprocess

# scripts/ -> skill root/config/config.json
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SHARED_CONFIG_PATH = os.path.join(_SCRIPT_DIR, "..", "config", "config.json")
_SKILL_ROOT = os.path.join(_SCRIPT_DIR, "..")

# Intermediate working directory (prepare/execute temp artifacts, cleaned before each run and after report)
EXPERIMENTS_DIR = os.path.join(_SKILL_ROOT, "experiments")
# Final deliverable directory (HTML report)
TEMPLATES_DIR = os.path.join(_SKILL_ROOT, "templates")


def clean_experiments():
    """Remove the experiments/ directory (called before each prepare and after report to avoid stale data).

    Never raises; silently succeeds if the directory does not exist.
    """
    import shutil
    if os.path.isdir(EXPERIMENTS_DIR):
        shutil.rmtree(EXPERIMENTS_DIR, ignore_errors=True)
        print(f"[清理] 已清理 experiments/ 临时目录: {EXPERIMENTS_DIR}")


def clean_templates(max_keep=5):
    """Keep only the newest max_keep HTML reports in templates/, delete older ones.

    Called before each run to prevent unbounded accumulation. Only removes
    failover_report_*.html; other files are left untouched. Never raises.
    """
    import glob
    reports = sorted(glob.glob(os.path.join(TEMPLATES_DIR, "failover_report_*.html")),
                     key=os.path.getmtime, reverse=True)
    if len(reports) <= max_keep:
        return
    for old in reports[max_keep:]:
        try:
            os.remove(old)
            print(f"[清理] 已删除过期报告: {os.path.basename(old)}")
        except OSError as e:
            print(f"[清理] 删除报告失败（忽略）: {os.path.basename(old)} — {e}")


def load_config(config_path=None):
    """
    Read region and instance_id from config/config.json.

    Returns:
        dict: {"region": "...", "instance_id": "..."}
    """
    path = config_path or _SHARED_CONFIG_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"配置文件不存在: {path}\n"
            f"请确保 config/config.json 已创建，包含 region 和 instance_id 字段。"
        )
    with open(path, "r", encoding="utf-8") as f:
        try:
            cfg = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"config.json 格式错误: {path}\n"
                f"JSON 解析失败（行 {e.lineno}，列 {e.colno}）: {e.msg}"
            ) from e

    if not isinstance(cfg, dict):
        raise ValueError(
            f"config.json 顶层必须是 JSON 对象，当前类型为 {type(cfg).__name__}（{path}）"
        )

    region = cfg.get("region")
    if not isinstance(region, str) or not region.strip():
        raise ValueError("config.json 中 region 必须为非空字符串")
    instance_id = cfg.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id.strip():
        raise ValueError("config.json 中 instance_id 必须为非空字符串")

    return {"region": region.strip(), "instance_id": instance_id.strip()}


def get_config_path():
    """Return the absolute path of the shared config file."""
    return os.path.abspath(_SHARED_CONFIG_PATH)


def get_skill_root():
    """Return the absolute path of the skill root directory."""
    return os.path.abspath(_SKILL_ROOT)


def run_hcloud(service, action, region, extra_args=None, timeout=120):
    """Execute an hcloud CLI command and return parsed JSON result.

    Shared by all phases (prepare/execute/risk/report) to avoid duplication.
    On failure returns {"_error": True, "stderr": "..."} instead of raising, for caller convenience.
    """
    import re as _re
    cmd = ["hcloud", service, action, f"--cli-region={region}"]
    if extra_args:
        cmd.extend(extra_args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"_error": True, "stderr": f"hcloud 命令超时（{timeout}s），请检查网络或减少查询范围"}
    except FileNotFoundError:
        return {"_error": True, "stderr": "hcloud 未安装或不在 PATH 中，请参考 references/cli-installation-guide.md 安装"}
    if result.returncode != 0:
        return {"_error": True, "stderr": result.stderr.strip() or result.stdout.strip()}
    # hcloud may append ANSI color codes and diagnostic tables after the JSON payload
    # (terminal width / request diagnostics, etc.). Strip ANSI escape codes and extract
    # the JSON body (up to the last } or ]) before parsing.
    text = _re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    # Detect CLI-level timeout (readTimeout too short): exit code 0 but stdout is a timeout message.
    # The request may or may not have been accepted by the server (synchronous mutation API) —
    # must explicitly flag as timeout so the caller (e.g. execute) can do a read-only recheck,
    # never silently treat as success.
    if ("context deadline exceeded" in text) or ("调用API超时" in text) or ("readTimeout" in text):
        return {"_error": True, "timeout": True,
                "stderr": "hcloud 调用超时（CLI 本地 readTimeout 限制）。请求可能已受理，请只读复核实例状态后重试",
                "stdout": text.strip()}
    # Check whether the output contains a JSON structure ({ or [ as body start)
    json_start = -1
    for marker in ("{", "["):
        idx = text.find(marker)
        if idx != -1 and (json_start == -1 or idx < json_start):
            json_start = idx
    if json_start == -1:
        # No JSON body: exit code 0 means success (mutation APIs like ChangeMasterStandby
        # may return only a text hint or empty body on success, should not be misjudged as failure)
        return {"ok": True, "raw": text.strip()}
    # Extract JSON body: from the first { or [ to the last } or ]
    json_end = -1
    for marker in ("}", "]"):
        idx = text.rfind(marker)
        if idx != -1 and idx > json_end:
            json_end = idx
    if json_end != -1 and json_end > json_start:
        text = text[json_start:json_end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"_error": True, "stderr": "Non-JSON output", "stdout": text.strip()}
    # Huawei Cloud standard error format: exit code 0 but JSON body contains error_msg / error_code
    # (e.g. DCS.4104 instance recovering, DCS.4036 status not allowed, etc.)
    if isinstance(parsed, dict) and ("error_msg" in parsed or "error_code" in parsed
                                       or "error" in parsed and isinstance(parsed["error"], dict)):
        msg = parsed.get("error_msg") or parsed.get("error", {}).get("message", "") if isinstance(parsed.get("error"), dict) else parsed.get("error_msg", "")
        code = parsed.get("error_code") or parsed.get("error", {}).get("code", "") if isinstance(parsed.get("error"), dict) else parsed.get("error_code", "")
        return {"_error": True, "stderr": f"{code}: {msg}", "stdout": result.stdout.strip()}
    return parsed


def load_json(filepath):
    """Load data from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath, data):
    """Save data as a JSON file (UTF-8, 2-space indent)."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now_str():
    """Current timestamp string."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# CES metric query (DCS, namespace SYS.DCS)
# ---------------------------------------------------------------------------

# DCS CES metric -> logical name mapping (kept in sync with references/acceptance-criteria.md)
DCS_CES_METRICS = [
    {"logic_name": "dcs_cpu_util", "metric_name": "cpu_usage", "namespace": "SYS.DCS",
     "description": "CPU usage", "unit": "%"},
    {"logic_name": "dcs_mem_util", "metric_name": "memory_usage", "namespace": "SYS.DCS",
     "description": "Memory usage", "unit": "%"},
    {"logic_name": "dcs_conn_usage", "metric_name": "connections_usage", "namespace": "SYS.DCS",
     "description": "Connection usage", "unit": "%"},
    {"logic_name": "dcs_ops", "metric_name": "instantaneous_ops", "namespace": "SYS.DCS",
     "description": "Instantaneous ops per second", "unit": "count"},
    {"logic_name": "dcs_connected_clients", "metric_name": "connected_clients", "namespace": "SYS.DCS",
     "description": "Connected clients", "unit": "count"},
    {"logic_name": "dcs_command_max_rt", "metric_name": "command_max_rt", "namespace": "SYS.DCS",
     "description": "Max command latency", "unit": "us"},
    {"logic_name": "dcs_in_flow", "metric_name": "instantaneous_input_kbps", "namespace": "SYS.DCS",
     "description": "Instantaneous input flow", "unit": "KiB/s"},
    {"logic_name": "dcs_out_flow", "metric_name": "instantaneous_output_kbps", "namespace": "SYS.DCS",
     "description": "Instantaneous output flow", "unit": "KiB/s"},
]


def query_ces_metric(region, metric_name, dim_key, dim_value, from_ms=None, to_ms=None, period=60):
    """Query a single DCS CES metric (ShowMetricData).

    Args:
        metric_name: CES metric name (e.g. cpu_usage)
        dim_key: CES dimension key (dcs_instance_id)
        dim_value: dimension value (instance ID)
        from_ms/to_ms: millisecond timestamp range; if omitted, only latest datapoint
        period: aggregation period in seconds

    Returns:
        {"available": bool, "error": str|None, "datapoints": list}
    """
    extra_args = [
        f"--metric_name={metric_name}",
        "--namespace=SYS.DCS",
        f"--dim.0={dim_key},{dim_value}",
        f"--period={period}",
        "--filter=average",
    ]
    if from_ms and to_ms:
        extra_args.append(f"--from={from_ms}")
        extra_args.append(f"--to={to_ms}")
    resp = run_hcloud("CES", "ShowMetricData", region, extra_args)
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "datapoints": []}
    return {"available": True, "error": None, "datapoints": resp.get("datapoints", [])}
