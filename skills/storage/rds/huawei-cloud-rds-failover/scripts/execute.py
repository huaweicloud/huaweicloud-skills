#!/usr/bin/env python3
"""
RDS 主备倒换 — 执行脚本

从 config/config.json 读取 region 和 instance_id，
加载实验准备 skill 生成的配置目录，安全执行主备倒换，
收集日志和监控数据，保存执行结果。

Usage:
  # 预演（不实际执行）— region/instance_id 从 config/config.json 读取
  python3 execute.py --config-dir <path>

  # 实际执行
  python3 execute.py --config-dir <path> --yes
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.join(SCRIPT_DIR, "..")

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
        return {"_error": True, "stderr": "hcloud command timed out (120s)"}
    if result.returncode != 0:
        return {"_error": True, "stderr": result.stderr.strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_error": True, "stderr": "Non-JSON output", "stdout": result.stdout.strip()}


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 查询实例
# ---------------------------------------------------------------------------

def get_instance(region, instance_id):
    resp = run_hcloud("RDS", "ListInstances", region)
    if resp.get("_error"):
        return None, resp.get("stderr")
    for inst in resp.get("instances", []):
        if inst.get("id") == instance_id:
            return inst, None
    return None, f"Instance {instance_id} not found"


def get_node_info(node):
    if not node:
        return {"name": "N/A", "role": "N/A", "status": "N/A", "az": "N/A"}
    return {
        "name": node.get("name", "N/A"),
        "role": node.get("role", "N/A"),
        "status": node.get("status", "N/A"),
        "az": node.get("availability_zone", "N/A"),
    }


# ---------------------------------------------------------------------------
# 收集日志
# ---------------------------------------------------------------------------

def collect_error_logs(region, instance_id, start_time, end_time):
    """收集倒换期间的 RDS 错误日志"""
    print("  [日志] 收集错误日志...")
    resp = run_hcloud("RDS", "ListErrorLogs", region, [
        f"--instance_id={instance_id}",
        f"--start_date={start_time}",
        f"--end_date={end_time}",
    ])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "logs": []}
    logs = resp.get("error_log_list", resp.get("logs", []))
    return {"available": True, "count": len(logs), "logs": logs[:50]}


def collect_slow_logs(region, instance_id, start_time, end_time):
    """收集倒换期间的慢 SQL 日志"""
    print("  [日志] 收集慢 SQL 日志...")
    resp = run_hcloud("RDS", "ListSlowLogs", region, [
        f"--instance_id={instance_id}",
        f"--start_date={start_time}",
        f"--end_date={end_time}",
    ])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "logs": []}
    logs = resp.get("slow_log_list", resp.get("logs", []))
    return {"available": True, "count": len(logs), "logs": logs[:50]}


# ---------------------------------------------------------------------------
# 收集 CES 监控指标
# ---------------------------------------------------------------------------

# CES 指标名映射: 脚本逻辑名 -> 华为云实际指标名
CES_METRIC_MAP = {
    "rds_cpu_util": "rds001_cpu_util",
    "rds_mem_util": "rds002_mem_util",
    "rds_disk_util": "rds039_disk_util",
    "rds_connections_count": "rds006_conn_count",
    "rds_in_flow": "rds004_bytes_in",
    "rds_out_flow": "rds005_bytes_out",
    "rds_iops": "rds003_iops",
    "rds_replication_delay": "rds073_replication_delay",
}


def collect_ces_metrics(region, instance_id, metric_names, from_ms=None, to_ms=None, node_id=None):
    """收集 CES 监控指标

    华为云 RDS CES 指标使用 rds_instance_id 维度（值为节点 ID），
    指标名为 rds001_cpu_util 等格式，需通过 CES_METRIC_MAP 映射。
    """
    print("  [监控] 收集 CES 指标...")
    metrics_data = []
    # 维度 key 固定为 rds_instance_id，维度值优先使用 node_id，回退到 instance_id
    dim_key = "rds_instance_id"
    dim_value = node_id if node_id else instance_id
    for metric_name in metric_names:
        actual_metric = CES_METRIC_MAP.get(metric_name, metric_name)
        extra_args = [
            f"--metric_name={actual_metric}",
            f"--namespace=SYS.RDS",
            f"--dim.0={dim_key},{dim_value}",
            f"--period=300",
            f"--filter=average",
        ]
        if from_ms and to_ms:
            extra_args.append(f"--from={from_ms}")
            extra_args.append(f"--to={to_ms}")
        resp = run_hcloud("CES", "ShowMetricData", region, extra_args)
        if resp.get("_error"):
            metrics_data.append({"metric_name": metric_name, "available": False, "error": resp.get("stderr", "")})
        else:
            datapoints = resp.get("datapoints", [])
            metrics_data.append({"metric_name": metric_name, "available": True, "datapoints": datapoints[-20:] if datapoints else []})
    return metrics_data


def query_alarm_rules(region):
    """查询当前告警规则状态"""
    print("  [监控] 查询告警规则...")
    resp = run_hcloud("CES", "ListAlarmRules", region)
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "rules": []}
    rules = resp.get("alarm_rules", [])
    return {
        "available": True, "count": len(rules),
        "rules": [{"name": r.get("alarm_name"), "status": r.get("alarm_status"),
                    "metric": (r.get("metric") or {}).get("metric_name"), "level": r.get("alarm_level")}
                   for r in rules[:20]],
    }


# ---------------------------------------------------------------------------
# 执行倒换
# ---------------------------------------------------------------------------

def execute_failover(region, instance_id):
    """调用 StartFailover API"""
    resp = run_hcloud("RDS", "StartFailover", region, [f"--instance_id={instance_id}"])
    if resp.get("_error"):
        return None, resp.get("stderr")
    return resp, None


def poll_failover(region, instance_id, old_slave_name, max_wait=120, interval=5):
    """轮询等待倒换完成，返回时间线"""
    timeline = []
    result = "timeout"
    after_master = {}
    after_slave = {}
    start = time.time()

    while True:
        elapsed = int(time.time() - start)
        if elapsed >= max_wait:
            break

        inst, err = get_instance(region, instance_id)
        if inst is None:
            timeline.append({"elapsed": elapsed, "status": "ERROR", "master": "", "slave": ""})
            time.sleep(interval)
            continue

        status = inst.get("status")
        nodes = inst.get("nodes", [])
        nm = next((n for n in nodes if n.get("role") == "master"), None)
        ns = next((n for n in nodes if n.get("role") == "slave"), None)
        nm_name = nm.get("name") if nm else None
        ns_name = ns.get("name") if ns else None

        print(f"  [{elapsed}s] status={status}, master={nm_name}, slave={ns_name}")
        timeline.append({"elapsed": elapsed, "status": status, "master": nm_name or "", "slave": ns_name or ""})

        if nm_name and old_slave_name and nm_name == old_slave_name:
            after_master = get_node_info(nm)
            after_slave = get_node_info(ns)
            result = "success"
            break

        time.sleep(interval)

    if result == "timeout":
        inst, _ = get_instance(region, instance_id)
        if inst:
            nodes = inst.get("nodes", [])
            after_master = get_node_info(next((n for n in nodes if n.get("role") == "master"), None))
            after_slave = get_node_info(next((n for n in nodes if n.get("role") == "slave"), None))

    elapsed = int(time.time() - start)
    return {"timeline": timeline, "after_master": after_master, "after_slave": after_slave, "result": result, "duration_seconds": elapsed}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="RDS 主备倒换执行")
    parser.add_argument("--config-dir", required=True, help="实验准备 skill 生成的配置目录")
    parser.add_argument("--yes", action="store_true", help="实际执行（默认预演）")
    args = parser.parse_args()

    config_dir = args.config_dir
    if not os.path.isdir(config_dir):
        print(f"[ERROR] 配置目录不存在: {config_dir}")
        sys.exit(1)

    # ── 从 config/config.json 读取 region 和 instance_id ──
    config_path = get_config_path()
    print(f"[配置] 读取共享配置: {config_path}")
    try:
        cfg = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    region = cfg["region"]
    instance_id = cfg["instance_id"]

    # 加载实验配置（safety checks、monitoring 等）
    experiment = load_json(os.path.join(config_dir, "experiment.json"))
    iam_policy = load_json(os.path.join(config_dir, "iam_policy.json"))
    monitoring = load_json(os.path.join(config_dir, "monitoring.json"))

    instance_name = experiment["target"].get("instance_name", instance_id)
    safety = experiment.get("safety_checks", {})

    print(f"[配置] 实验名称: {experiment.get('experiment_name', 'N/A')}")
    print(f"[配置] region={region} (来自 config.json)")
    print(f"[配置] instance_id={instance_id} (来自 config.json)")
    print(f"[配置] 目标实例: {instance_name}")

    # 预检查
    print(f"\n[预检查] 查询实例状态...")
    inst, err = get_instance(region, instance_id)
    if err:
        print(f"[ERROR] {err}")
        sys.exit(1)

    status = inst.get("status")
    inst_type = inst.get("type")
    nodes = inst.get("nodes", [])
    master = next((n for n in nodes if n.get("role") == "master"), None)
    slave = next((n for n in nodes if n.get("role") == "slave"), None)
    before_master = get_node_info(master)
    before_slave = get_node_info(slave)

    print(f"  实例: {instance_name} | 状态: {status} | 类型: {inst_type}")
    print(f"  主节点: {before_master['name']} (AZ={before_master['az']})")
    print(f"  备节点: {before_slave['name']} (AZ={before_slave['az']})")

    # 安全检查
    checks = {"instance_found": True, "status_active": status == "ACTIVE",
              "is_ha": inst_type and inst_type.lower() in ("ha", "replication")}

    if safety.get("require_ha_type") and not checks["is_ha"]:
        print(f"[ERROR] 实例非 HA 类型，无法倒换。")
        sys.exit(1)
    if safety.get("require_active_status") and not checks["status_active"]:
        print(f"[ERROR] 实例状态为 {status}，非 ACTIVE，无法倒换。")
        sys.exit(1)

    iam_check = iam_policy.get("iam_check_result", {})
    checks["iam_rds_access"] = iam_check.get("rds_read_access", False)
    checks["iam_failover_capable"] = iam_check.get("rds_failover_capable", False)

    print(f"  安全检查: {'全部通过' if all(checks.values()) else '部分未通过'}")
    for k, v in checks.items():
        print(f"    {k}: {'✓' if v else '✗'}")

    print(f"\n  倒换后，备节点 {before_slave['name']} (AZ={before_slave['az']}) 将被提升为主节点。")

    if not args.yes:
        print("\n[预演] 传入 --yes 执行倒换。未做任何变更。")
        save_json(os.path.join(config_dir, "execution_result.json"), {
            "mode": "dry-run",
            "checks": checks,
            "before_master": before_master,
            "before_slave": before_slave,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return

    # 执行倒换
    start_time = datetime.datetime.now()
    start_str = start_time.astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")  # 日志API要求ISO8601带时区偏移(如+0800)，不能用字面Z
    print(f"\n[执行] 调用 StartFailover...")
    failover_resp, failover_err = execute_failover(region, instance_id)
    if failover_err:
        print(f"[ERROR] 倒换失败: {failover_err}")
        sys.exit(1)

    workflow_id = failover_resp.get("workflowId", "N/A")
    print(f"[OK] 倒换命令已提交, workflowId={workflow_id}")

    # 轮询等待
    print(f"\n[轮询] 等待倒换完成...")
    max_wait = safety.get("max_failover_duration_seconds", 120)
    interval = safety.get("poll_interval_seconds", 5)
    poll_result = poll_failover(region, instance_id, before_slave["name"], max_wait, interval)

    if poll_result["result"] == "success":
        print(f"\n[成功] 倒换完成! 耗时 {poll_result['duration_seconds']} 秒")
    else:
        print(f"\n[超时] 倒换未在 {max_wait}s 内完成。")

    end_time = datetime.datetime.now()
    end_str = end_time.astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")  # 日志API要求ISO8601带时区偏移(如+0800)，不能用字面Z

    # 收集日志和监控
    print(f"\n[收集] 倒换期间日志和监控数据...")
    error_logs = collect_error_logs(region, instance_id, start_str, end_str)
    slow_logs = collect_slow_logs(region, instance_id, start_str, end_str)
    metric_names = [m["metric_name"] for m in monitoring.get("ces_metrics", [])]
    from_ms = int(start_time.timestamp() * 1000) - 600000  # 前推10分钟确保覆盖聚合周期
    to_ms = int(end_time.timestamp() * 1000)
    # 使用倒换前主节点的 node ID 作为 CES 维度值
    master_node_id = master.get("id") if master else None
    ces_metrics = collect_ces_metrics(region, instance_id, metric_names, from_ms, to_ms, node_id=master_node_id)
    alarm_rules = query_alarm_rules(region)

    # 保存执行结果
    execution_result = {
        "mode": "execute",
        "experiment_name": experiment.get("experiment_name", ""),
        "region": region,
        "instance_id": instance_id,
        "instance_name": instance_name,
        "engine": experiment["target"].get("engine", ""),
        "flavor": experiment["target"].get("flavor", ""),
        "workflow_id": workflow_id,
        "checks": checks,
        "before_master": before_master,
        "before_slave": before_slave,
        "after_master": poll_result["after_master"],
        "after_slave": poll_result["after_slave"],
        "timeline": poll_result["timeline"],
        "result": poll_result["result"],
        "duration_seconds": poll_result["duration_seconds"],
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "error_logs": error_logs,
        "slow_logs": slow_logs,
        "ces_metrics": ces_metrics,
        "alarm_rules": alarm_rules,
    }

    result_path = os.path.join(config_dir, "execution_result.json")
    save_json(result_path, execution_result)
    print(f"\n[完成] 执行结果已保存: {result_path}")
    print(f"\n  下一步: 使用 run.py --phase report 生成报告")
    print(f"  命令: python3 report.py --config-dir {config_dir}")


if __name__ == "__main__":
    main()
