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
from config import load_config, get_config_path, run_hcloud, load_json, save_json
import risk
from ces_config import ENGINE_CES_CONFIG, get_engine_ces_config, resolve_ces_dim_value, query_ces_metric


# ---------------------------------------------------------------------------
# 查询实例
# ---------------------------------------------------------------------------

def get_instance(region, instance_id):
    """查询单个 RDS 实例（marker 分页拉取，避免实例多时漏查）"""
    marker = None
    while True:
        extra = ["--limit=100"]
        if marker:
            extra.append(f"--marker={marker}")
        resp = run_hcloud("RDS", "ListInstances", region, extra_args=extra)
        if resp.get("_error"):
            return None, resp.get("stderr")
        instances = resp.get("instances", [])
        for inst in instances:
            if inst.get("id") == instance_id:
                return inst, None
        marker = (resp.get("page_info") or {}).get("next_marker")
        if not marker or not instances:
            break
    return None, f"Instance {instance_id} not found"


def get_node_info(node):
    if not node:
        return {"name": "N/A", "role": "N/A", "status": "N/A", "az": "N/A", "id": "N/A"}
    return {
        "name": node.get("name", "N/A"),
        "role": node.get("role", "N/A"),
        "status": node.get("status", "N/A"),
        "az": node.get("availability_zone", "N/A"),
        "id": node.get("id", "N/A"),
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


def collect_ces_metrics(region, instance_id, metric_names, from_ms=None, to_ms=None,
                        node_id=None, engine="MySQL"):
    """收集 CES 监控指标（引擎自适应）

    根据引擎类型选择正确的维度名、维度值和指标名映射（与 ces_config.py ENGINE_CES_CONFIG 一致）：
      - MySQL/TaurusDB: dim=rds_instance_id, value=节点 ID
      - MariaDB:        dim=mariadb_cluster_id, value=实例 ID
      - PostgreSQL:     dim=postgresql_cluster_id, value=实例 ID
      - SQL Server:     dim=rds_cluster_sqlserver_id, value=实例 ID

    Args:
        engine: 引擎字符串，如 'PostgreSQL 18'、'MySQL 8.0'
        node_id: 主节点 ID（仅 MySQL/TaurusDB 用作维度值，其余引擎用 instance_id）
    """
    print("  [监控] 收集 CES 指标...")
    try:
        ces_config = get_engine_ces_config(engine)
        dim_key, dim_value = resolve_ces_dim_value(engine, instance_id, node_id)
    except ValueError as e:
        print(f"  [监控] {e}，CES 指标采集跳过")
        return [{"metric_name": m, "available": False, "error": str(e)} for m in metric_names]
    metric_map = ces_config["metric_map"]

    metrics_data = []
    for metric_name in metric_names:
        actual_metric = metric_map.get(metric_name, metric_name)
        result = query_ces_metric(run_hcloud, region, actual_metric, dim_key, dim_value,
                                  from_ms=from_ms, to_ms=to_ms)
        if result["available"]:
            dp = result["datapoints"]
            metrics_data.append({"metric_name": metric_name, "available": True,
                                 "datapoints": dp[-20:] if dp else []})
        else:
            metrics_data.append({"metric_name": metric_name, "available": False,
                                 "error": result["error"]})
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


def poll_failover(region, instance_id, old_slave_id, max_wait=120, interval=5):
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
        nm_id = nm.get("id") if nm else None

        print(f"  [{elapsed}s] status={status}, master={nm_name}, slave={ns_name}")
        timeline.append({"elapsed": elapsed, "status": status, "master": nm_name or "", "slave": ns_name or ""})

        # 用节点 ID 匹配（比 name 更稳定唯一），避免 name 冲突导致误判
        if nm_id and old_slave_id and nm_id == old_slave_id:
            after_master = get_node_info(nm)
            after_slave = get_node_info(ns)
            # 备节点已提升为主，但实例状态可能仍为 SWITCHOVER
            # 继续轮询直到状态恢复 ACTIVE 再置 success；等待 ACTIVE 超时则置 timeout
            while elapsed < max_wait:
                time.sleep(interval)
                elapsed = int(time.time() - start)
                inst2, _ = get_instance(region, instance_id)
                if inst2 is None:
                    break
                status2 = inst2.get("status")
                nodes2 = inst2.get("nodes", [])
                nm2 = next((n for n in nodes2 if n.get("role") == "master"), None)
                ns2 = next((n for n in nodes2 if n.get("role") == "slave"), None)
                nm_name2 = nm2.get("name") if nm2 else None
                ns_name2 = ns2.get("name") if ns2 else None
                print(f"  [{elapsed}s] status={status2}, master={nm_name2}, slave={ns_name2}")
                timeline.append({"elapsed": elapsed, "status": status2, "master": nm_name2 or "", "slave": ns_name2 or ""})
                if status2 == "ACTIVE":
                    result = "success"
                    break
            # 等待 ACTIVE 超时：倒换已完成但实例未恢复 ACTIVE，报 timeout 而非 success
            if result != "success":
                result = "timeout"
                print(f"  [警告] 倒换已完成（备节点已提升为主），但实例状态未恢复 ACTIVE，超时退出。")
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
    parser.add_argument("--force", action="store_true", help="跳过 prepare 阶段检测出的严重风险拦截（需人工确认已评估风险）")
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

    # 优先使用 experiment.json 中的 target.instance_id（prepare 阶段选定的实例），
    # 覆盖 config.json 中的值——prepare 可能自动选中了唯一 HA 实例但未回写 config.json
    exp_instance_id = experiment.get("target", {}).get("instance_id")
    if exp_instance_id and exp_instance_id != instance_id:
        instance_id = exp_instance_id
        print(f"[配置] instance_id 已从 experiment.json 覆盖为 {instance_id}")

    instance_name = experiment["target"].get("instance_name", instance_id)
    safety = experiment.get("safety_checks", {})

    print(f"[配置] 实验名称: {experiment.get('experiment_name', 'N/A')}")
    print(f"[配置] region={region} (来自 config.json)")
    print(f"[配置] instance_id={instance_id}")
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

    # 节点存在性检查：nodes 为空或 role 缺失时明确退出，避免 poll_failover 恒超时
    if not master or not slave:
        print(f"[ERROR] 实例缺少主/备节点（master={'有' if master else '无'}, slave={'有' if slave else '无'}）。")
        print(f"  nodes 返回 {len(nodes)} 个节点，无法执行倒换。请确认实例为 HA 类型且节点信息完整。")
        sys.exit(1)
    if before_slave.get("id", "N/A") == "N/A" or before_master.get("id", "N/A") == "N/A":
        print(f"[ERROR] 主/备节点缺少 id 字段（master_id={before_master.get('id')}, slave_id={before_slave.get('id')}）。")
        print(f"  倒换判定依赖节点 id 匹配，缺少 id 将导致轮询恒超时。请确认 API 返回了完整的节点信息。")
        sys.exit(1)

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

    # IAM 权限检查（与 prepare.py 一致：建议性检查，不阻断 execute）
    # allow：确认有权限，正常执行
    # deny：确认无权限，阻止执行（除非 --force）
    # unknown：无法确认（系统策略无法取证），仅提示不阻断——实际 API 调用决定成败
    iam_status = iam_check.get("rds_failover_status", "unknown")
    if iam_status == "deny":
        print(f"\n[安全拦截] 确认无倒换权限（status=deny），阻止执行。")
        if not args.yes:
            print(f"  （预演模式不执行变更；实际执行前请检查 IAM 策略是否包含 rds:instance:switchover）")
        elif not args.force:
            print(f"[ERROR] 已阻止执行。请确认 IAM 权限后重新运行 prepare，"
                  f"或使用 --force 人工放行。")
            sys.exit(1)
        else:
            print(f"[警告] 已使用 --force 跳过 IAM 权限拦截，请确认已人工确认倒换权限。")
    elif iam_status == "unknown":
        print(f"\n[安全提示] 倒换权限未知（status=unknown，系统策略无法取证）。")
        print(f"  此为建议性检查，不阻断执行——实际 API 调用决定成败。")
        if args.yes and not args.force:
            print(f"  如需确认权限，请检查 IAM 策略是否包含 rds:instance:switchover。")

    print(f"  安全检查: {'全部通过' if all(checks.values()) else '部分未通过'}")
    for k, v in checks.items():
        print(f"    {k}: {'✓' if v else '✗'}")

    print(f"\n  倒换后，备节点 {before_slave['name']} (AZ={before_slave['az']}) 将被提升为主节点。")

    # ── 风险预警与拦截（读取 prepare 阶段生成的 risk_assessment.json）──
    # 先校验风险评估与当前实例/区域一致，防止"换了实例还拿旧评估放行"
    risk_path = os.path.join(config_dir, "risk_assessment.json")
    risk_blocked = False
    if os.path.isfile(risk_path):
        risk_doc = load_json(risk_path)
        risk_inst = risk_doc.get("instance_id")
        risk_region = risk_doc.get("region")
        risk_mismatch = (risk_inst and risk_inst != instance_id) or (risk_region and risk_region != region)
        if risk_mismatch:
            print(f"\n[风险拦截] risk_assessment.json 与当前待倒换实例不一致！")
            print(f"  风险评估对象: instance={risk_inst} region={risk_region}")
            print(f"  当前待倒换实例: {instance_id} region={region}")
            if not args.yes:
                print(f"  （预演模式不执行变更；实际执行前请重新运行 prepare 生成当前实例的风险评估）")
            elif not args.force:
                print(f"[ERROR] 已阻止执行。请先运行 prepare 生成当前实例的风险评估，"
                      f"或确认实例无误后使用 --force 人工放行。")
                sys.exit(1)
            else:
                print(f"[警告] 已使用 --force 对不一致的风险评估强制演练，请人工确认实例与风险。")
        else:
            rlvl = risk_doc.get("overall_level", "low")
            print(f"\n[风险提示] 总体风险等级: {rlvl}（来源: risk_assessment.json，与当前实例一致）")
            risk_items = risk_doc.get("items", [])
            for it in risk_items:
                if it.get("level") in ("critical", "warning", "unknown"):
                    mark = {"critical": "🔴", "warning": "🟠", "unknown": "⚪"}.get(it.get("level"), "•")
                    print(f"  {mark} [{it.get('category')}] {it.get('title')} — {it.get('detail')}")
                    print(f"      影响: {it.get('impact')}")
            risk_blocked = risk_doc.get("block_execution", False)
            if risk_blocked:
                print(f"\n[风险拦截] prepare 阶段检测到严重风险项，默认阻止倒换。")
                if not args.yes:
                    print(f"  （预演模式不执行变更，仅提示；实际执行时需 --force 跳过拦截）")
                elif not args.force:
                    print(f"[ERROR] 已阻止执行。如已人工评估并接受风险，请使用 --force 强制演练。")
                    sys.exit(1)
                else:
                    print(f"[警告] 已使用 --force 强制跳过严重风险拦截，请确认已人工评估风险。")
            elif rlvl == "medium" and args.yes:
                unk_count = sum(1 for it in risk_items if it.get("level") == "unknown")
                if unk_count and not any(it.get("level") == "warning" for it in risk_items):
                    print(f"[预警] 存在 {unk_count} 项无法评估的风险项（接口不可用或无数据），请确认无风险后再继续。")
                else:
                    print(f"[预警] 存在预警项，请确认已评估后再继续。")
    else:
        print(f"\n[风险提示] 未找到 risk_assessment.json（未运行 prepare 或 prepare 版本过旧），跳过风险拦截。")

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

    # ── 执行前实时复核（prepare 风险快照可能过期：复核复制状态与复制延迟）──
    print(f"\n[实时复核] 倒换前复核主备复制状态与复制延迟...")
    rt = risk.realtime_safety_check(region, instance_id, master.get("id") if master else None, engine=experiment["target"].get("engine", "MySQL"))
    for sig in rt["signals"]:
        mark = {"critical": "🔴", "warning": "🟠", "info": "🟢"}.get(sig.get("level"), "•")
        print(f"  {mark} {sig.get('title')} — {sig.get('detail')}")
        if sig.get("suggestion"):
            print(f"      建议: {sig.get('suggestion')}")
    if rt["blocked"]:
        if not args.force:
            print(f"[ERROR] 实时复核发现严重风险，已阻止倒换。如确需演练请使用 --force（不推荐）。")
            sys.exit(1)
        print(f"[警告] 实时复核发现严重风险，已使用 --force 强制演练，请人工确认。")

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
    poll_result = poll_failover(region, instance_id, before_slave["id"], max_wait, interval)

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
    engine = experiment["target"].get("engine", "MySQL")
    ces_metrics = collect_ces_metrics(region, instance_id, metric_names, from_ms, to_ms,
                                      node_id=master_node_id, engine=engine)
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
