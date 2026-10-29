#!/usr/bin/env python3
"""
DCS master-slave failover — risk detection / assessment / warning module.

Called during the prepare phase to reduce the risk of anomalies during failover:

  1. Detection (detect): read-only probing of instance health, master-slave node
     status, memory level, backup freshness, CES load metrics (CPU/memory/connections/
     latency) and instance configuration.
  2. Assessment (assess): map each detection result to a severity level
     info/unknown/warning/critical using thresholds, aggregate an overall risk level
     (low / medium / blocked), and provide an action recommendation.
  3. Warning (warn): prominent console output + generate risk_assessment.json;
     the execute phase reads this file and blocks failover by default if any
     critical item is present (unless overridden with --force).

Dependencies (all read-only Huawei Cloud APIs):
  - DCS ShowInstance / ListInstances        instance status, topology
  - DCS ShowNodesInformation / ShowInstanceTopology  master-slave nodes and roles
  - DCS ListBackupRecords                   backup records
  - CES ShowMetricData                      monitoring metrics

Threshold definitions and business semantics: see references/risk-model.md.
"""

import datetime
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from config import run_hcloud as _run_hcloud, query_ces_metric, save_json


# ---------------------------------------------------------------------------
# Thresholds (kept in sync with references/risk-model.md)
# ---------------------------------------------------------------------------
THRESH = {
    "mem_warn": 80,           # Memory usage %, above enters warning
    "mem_crit": 90,           # Above enters critical (blocks failover)
    "conn_warn_pct": 70,      # Connection usage % (connections_usage is already a percentage)
    "conn_crit_pct": 90,
    "cpu_warn": 70,           # CPU usage %
    "cpu_crit": 90,
    "rt_warn_ms": 10,         # Max latency ms warning
    "rt_crit_ms": 50,         # Max latency ms critical
    "backup_warn_hours": 48,  # Latest successful backup older than 48h enters warning
    "backup_crit_days": 7,    # Older than 7 days (or beyond retention) enters critical
}

LEVEL_LABEL = {"low": "🟢 低", "medium": "🟠 中（存在预警）", "blocked": "🔴 高（阻止执行）"}


# ---------------------------------------------------------------------------
# Risk detection: per-item real-time probing
# ---------------------------------------------------------------------------

def detect_instance(region, instance_id):
    """Instance status and topology (ShowInstance)."""
    resp = _run_hcloud("DCS", "ShowInstance", region, [f"--instance_id={instance_id}"])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "status": None,
                "cache_mode": None, "az_codes": [], "capacity": None}
    return {"available": True, "error": None,
            "status": resp.get("status"),
            "cache_mode": resp.get("cache_mode"),
            "az_codes": resp.get("az_codes", []),
            "capacity": resp.get("capacity")}


def detect_nodes(region, instance_id):
    """Master-slave node info (ShowNodesInformation)."""
    resp = _run_hcloud("DCS", "ShowNodesInformation", region, [f"--instance_id={instance_id}"])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "nodes": [],
                "master": None, "slave": None}
    nodes = resp.get("nodes", [])
    master = next((n for n in nodes if (n.get("node_type") or "").lower() in ("master", "primary")), None)
    slave = next((n for n in nodes if (n.get("node_type") or "").lower() in ("slave", "replica", "standby")), None)
    return {
        "available": True, "error": None, "nodes": nodes,
        "master": {"node_id": master.get("node_id") if master else None,
                   "az": master.get("az_code") if master else None,
                   "status": master.get("status") if master else None,
                   "ip": master.get("node_ip") if master else None,
                   "group_id": master.get("group_id") if master else None}
        if master else None,
        "slave": {"node_id": slave.get("node_id") if slave else None,
                  "az": slave.get("az_code") if slave else None,
                  "status": slave.get("status") if slave else None,
                  "ip": slave.get("node_ip") if slave else None,
                  "group_id": slave.get("group_id") if slave else None}
        if slave else None,
    }


def detect_backups(region, instance_id, keep_days):
    """Backup freshness (ListBackupRecords)."""
    resp = _run_hcloud("DCS", "ListBackupRecords", region, [f"--instance_id={instance_id}"])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""),
                "latest_age_hours": None, "failed_recent": 0, "keep_days": keep_days}
    backups = resp.get("backup_records", resp.get("records", []))
    now = datetime.datetime.now(datetime.timezone.utc)
    completed_times = []
    failed_recent = 0
    for b in backups:
        status = (b.get("status") or "").upper()
        begin = b.get("begin_time")
        t = None
        if begin:
            try:
                t = datetime.datetime.strptime(begin, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                try:
                    t = datetime.datetime.strptime(begin, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    t = None
        if status in ("SUCCEEDED", "COMPLETED") and t:
            completed_times.append(t)
        if status in ("FAILED", "ERROR") and t and (now - t).total_seconds() <= 7 * 86400:
            failed_recent += 1
    latest = max(completed_times) if completed_times else None
    latest_age_hours = round((now - latest).total_seconds() / 3600, 1) if latest else None
    return {"available": True, "error": None, "latest_age_hours": latest_age_hours,
            "failed_recent": failed_recent, "keep_days": keep_days}


def detect_ces_single(region, instance_id, metric_name, from_ms=None, to_ms=None, period=60):
    """Query a single DCS CES metric, return the latest aggregated average."""
    result = query_ces_metric(region, metric_name, "dcs_instance_id", instance_id,
                              from_ms=from_ms, to_ms=to_ms, period=period)
    if not result["available"]:
        return {"available": False, "error": result["error"], "value": None}
    dps = result["datapoints"]
    if not dps:
        return {"available": False, "error": "CES 未返回数据点", "value": None}
    v = dps[-1].get("average")
    if v is None:
        v = dps[-1].get("value")
    if v is None:
        return {"available": False, "error": "CES 数据点无值", "value": None}
    try:
        return {"available": True, "error": None, "value": float(v)}
    except (TypeError, ValueError):
        return {"available": False, "error": "CES 数据值异常", "value": None}


def detect_ces_load(region, instance_id):
    """Last 1 hour DCS CES load metrics (CPU/memory/connections/latency), latest aggregated average."""
    to_ms = int(datetime.datetime.now().timestamp() * 1000)
    from_ms = to_ms - 3600000
    result = {}
    for item in ("cpu_usage", "memory_usage", "connections_usage", "command_max_rt"):
        result[item] = detect_ces_single(region, instance_id, item, from_ms, to_ms)
    return result


def realtime_safety_check(region, instance_id, group_id=None):
    """Real-time recheck before execute: confirm instance status and node health immediately before failover.

    The risk_assessment.json from prepare is a snapshot and may be stale;
    this function rechecks in real time before failover:
      - Instance status (ShowInstance) is RUNNING
      - Master/slave node status is Active / normal

    Returns {"blocked": bool, "signals": [...]};
    blocked=True means a critical risk was detected in real time, execute should block by default.
    """
    signals = []
    blocked = False

    inst = detect_instance(region, instance_id)
    if not inst.get("available"):
        signals.append({"level": "warning", "title": "实例状态无法查询",
                        "detail": inst.get("error", ""),
                        "suggestion": "请人工确认实例状态"})
    elif inst.get("status") == "RUNNING":
        signals.append({"level": "info", "title": "实例状态正常",
                        "detail": f"status={inst.get('status')}"})
    else:
        signals.append({"level": "critical", "title": "实例状态非 RUNNING",
                        "detail": f"status={inst.get('status')}",
                        "suggestion": "禁止倒换，先恢复实例运行"})
        blocked = True

    nodes = detect_nodes(region, instance_id)
    if not nodes.get("available"):
        signals.append({"level": "warning", "title": "节点状态无法查询",
                        "detail": nodes.get("error", ""),
                        "suggestion": "请人工确认主备节点健康"})
    else:
        master = nodes.get("master")
        slave = nodes.get("slave")
        if not master or not slave:
            signals.append({"level": "critical", "title": "主备节点不完整",
                            "detail": f"master={'有' if master else '无'}, slave={'有' if slave else '无'}",
                            "suggestion": "禁止倒换，确认实例为主备类型且节点完整"})
            blocked = True
        else:
            healthy = lambda s: str(s or "").lower() in ("active", "running", "normal")
            if healthy(master.get("status")) and healthy(slave.get("status")):
                signals.append({"level": "info", "title": "主备节点健康",
                                "detail": f"master={master.get('az')} status={master.get('status')}, "
                                          f"slave={slave.get('az')} status={slave.get('status')}"})
            else:
                signals.append({"level": "critical", "title": "主备节点存在异常状态",
                                "detail": f"master status={master.get('status')}, slave status={slave.get('status')}",
                                "suggestion": "禁止倒换，先恢复节点健康"})
                blocked = True

    return {"blocked": blocked, "signals": signals}


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------

def _item(category, level, title, detail, impact, suggestion):
    return {
        "category": category,
        "level": level,           # info / warning / critical / unknown
        "title": title,
        "detail": detail,
        "impact": impact,
        "suggestion": suggestion,
    }


def _severity(value, warn, crit):
    """Return severity by threshold: None -> unknown (missing data is never misjudged as critical)."""
    if value is None:
        return "unknown"
    if value >= crit:
        return "critical"
    if value >= warn:
        return "warning"
    return "info"


def assess_risks(det):
    """Grade each detection result, aggregate overall risk level and recommendation.

    det is the detection data dict assembled by build_risk_assessment.
    Returns {overall_level, recommendation, block_execution, summary, items}.
    """
    t = THRESH
    items = []
    severity_counts = {"critical": 0, "warning": 0, "info": 0, "unknown": 0}

    def add(it):
        items.append(it)
        severity_counts[it["level"]] = severity_counts.get(it["level"], 0) + 1

    # 1) Instance status
    if det.get("status") == "RUNNING":
        add(_item("实例健康", "info", "实例状态正常", f"status={det.get('status')}", "-", "-"))
    else:
        add(_item("实例健康", "critical", "实例状态非 RUNNING", f"status={det.get('status') or 'N/A'}",
                  "倒换命令可能被拒绝或在异常状态下失败",
                  "等待实例恢复 RUNNING 后再执行演练"))

    # 2) Master-slave nodes
    nodes = det.get("nodes", {})
    if not nodes.get("available"):
        add(_item("主备复制", "unknown", "节点信息不可查询", nodes.get("error", "查询失败"),
                  "无法自动确认主备结构", "execute 前用 hcloud DCS ShowNodesInformation 人工复核"))
    else:
        master = nodes.get("master")
        slave = nodes.get("slave")
        if not master or not slave:
            add(_item("主备复制", "critical", "主备节点不完整",
                      f"master={'有' if master else '无'}, slave={'有' if slave else '无'}",
                      "非主备结构无法执行倒换", "确认实例为主备类型"))
        else:
            healthy = lambda s: str(s or "").lower() in ("active", "running", "normal")
            if healthy(master.get("status")) and healthy(slave.get("status")):
                add(_item("主备复制", "info", "主备节点健康",
                          f"master={master.get('az')} / slave={slave.get('az')}", "-", "-"))
            else:
                add(_item("主备复制", "critical", "主备节点存在异常状态",
                          f"master status={master.get('status')}, slave status={slave.get('status')}",
                          "异常节点可能无法承担倒换", "先恢复节点健康再演练"))

    # 3) Cross-AZ deployment
    master = det.get("nodes", {}).get("master") or {}
    slave = det.get("nodes", {}).get("slave") or {}
    maz, saz = master.get("az"), slave.get("az")
    if maz and saz:
        if maz != saz:
            add(_item("配置", "info", "主备跨可用区部署", f"master AZ={maz}, slave AZ={saz}", "-", "-"))
        else:
            add(_item("配置", "warning", "主备同可用区部署", f"master AZ={maz}, slave AZ={saz}",
                      "AZ 断电演练无法验证跨 AZ 容灾", "如期望验证跨 AZ 容灾，需按跨 AZ 部署实例"))

    # 4) Memory usage (CES)
    mem = det.get("ces", {}).get("memory_usage", {})
    if mem.get("available") and mem.get("value") is not None:
        lvl = _severity(mem["value"], t["mem_warn"], t["mem_crit"])
        if lvl == "critical":
            add(_item("负载", "critical", "内存使用率过高", f"近1小时内存均值={mem['value']:g}%",
                      "新主库需要重建数据，内存压力大时恢复更慢或失败", "等内存回落后再演练"))
        elif lvl == "warning":
            add(_item("负载", "warning", "内存使用率偏高", f"近1小时内存均值={mem['value']:g}%",
                      "倒换后新主库预热期间性能可能下降", "建议低峰期执行"))
        else:
            add(_item("负载", "info", "内存使用率正常", f"近1小时内存均值={mem['value']:g}%", "-", "-"))
    else:
        add(_item("负载", "unknown", "内存使用率无监控数据", mem.get("error") or "CES 未返回指标", "-", "-"))

    # 5) CPU usage
    cpu = det.get("ces", {}).get("cpu_usage", {})
    if cpu.get("available") and cpu.get("value") is not None:
        lvl = _severity(cpu["value"], t["cpu_warn"], t["cpu_crit"])
        if lvl == "critical":
            add(_item("负载", "critical", "CPU 使用率过高", f"近1小时CPU均值={cpu['value']:g}%",
                      "倒换窗口连接中断会显著放大业务影响，恢复期性能可能不足",
                      "等 CPU 回落后（或低峰期）再演练；如必须执行需人工确认放行并通知业务"))
        elif lvl == "warning":
            add(_item("负载", "warning", "CPU 使用率偏高", f"近1小时CPU均值={cpu['value']:g}%",
                      "倒换期间业务中断影响面较大", "建议低峰期执行"))
        else:
            add(_item("负载", "info", "CPU 使用率正常", f"近1小时CPU均值={cpu['value']:g}%", "-", "-"))
    else:
        add(_item("负载", "unknown", "CPU 使用率无监控数据", cpu.get("error") or "CES 未返回指标", "-", "-"))

    # 6) Connection usage (CES connections_usage is already a percentage)
    conn = det.get("ces", {}).get("connections_usage", {})
    if conn.get("available") and conn.get("value") is not None:
        lvl = _severity(conn["value"], t["conn_warn_pct"], t["conn_crit_pct"])
        detail = f"近1小时连接数使用率={conn['value']:g}%"
        if lvl == "critical":
            add(_item("负载", "critical", "连接数接近上限", detail,
                      "倒换瞬间所有连接被断开，大量应用并发重连可能压垮新主库",
                      "先排查连接泄漏/调大 maxclients，错峰演练"))
        elif lvl == "warning":
            add(_item("负载", "warning", "连接数占用偏高", detail,
                      "倒换后瞬时重连风暴风险较高", "建议提前让应用侧准备连接池重连/退避策略"))
        else:
            add(_item("负载", "info", "连接数占用正常", detail, "-", "-"))
    else:
        add(_item("负载", "unknown", "连接数使用率无监控数据", conn.get("error") or "CES 未返回指标",
                  "无法自动评估重连风暴风险", "可忽略或手动确认当前连接数"))

    # 7) Max latency (CES command_max_rt, microseconds)
    rt = det.get("ces", {}).get("command_max_rt", {})
    if rt.get("available") and rt.get("value") is not None:
        rt_ms = rt["value"] / 1000.0
        lvl = _severity(rt_ms, t["rt_warn_ms"], t["rt_crit_ms"])
        if lvl == "critical":
            add(_item("负载", "critical", "实例时延过高", f"近1小时最大时延={rt_ms:g}ms",
                      "实例可能存在性能瓶颈或慢命令，倒换期间风险大",
                      "先排查慢命令/热点 key，等时延回落后再演练"))
        elif lvl == "warning":
            add(_item("负载", "warning", "实例时延偏高", f"近1小时最大时延={rt_ms:g}ms",
                      "倒换窗口业务影响可能加剧", "建议低峰期执行"))
        else:
            add(_item("负载", "info", "实例时延正常", f"近1小时最大时延={rt_ms:g}ms", "-", "-"))
    else:
        add(_item("负载", "unknown", "时延无监控数据", rt.get("error") or "CES 未返回指标", "-", "-"))

    # 8) Backup freshness (data safety net)
    b = det.get("backups", {})
    kd = b.get("keep_days")
    crit_hour = (min(int(kd), t["backup_crit_days"]) if kd else t["backup_crit_days"]) * 24
    if not b.get("available"):
        add(_item("数据安全", "unknown", "备份信息不可查询", b.get("error", "查询失败"),
                  "无法自动确认备份兜底", "通过控制台确认备份策略与最近备份"))
    elif b.get("latest_age_hours") is None:
        add(_item("数据安全", "critical", "无任何成功备份记录", "ListBackupRecords 无成功备份",
                  "倒换异常时缺少恢复兜底", "先完成一次手动备份或确认备份策略再演练"))
    elif b.get("latest_age_hours") <= t["backup_warn_hours"]:
        add(_item("数据安全", "info", "最近备份正常", f"最近成功备份于 {b['latest_age_hours']:g} 小时前", "-", "-"))
    elif b.get("latest_age_hours") <= crit_hour:
        add(_item("数据安全", "warning", "最近备份时间较旧", f"最近成功备份于 {b['latest_age_hours']:g} 小时前",
                  "备份兜底不够新鲜，异常时恢复点较远", "建议先做一次手动备份再演练"))
    else:
        add(_item("数据安全", "critical", "备份缺失或超过保留周期",
                  f"最近成功备份于 {b['latest_age_hours']:g} 小时前（> {crit_hour // 24} 天）",
                  "缺少有效备份兜底", "先完成备份并确认备份任务恢复正常"))
    if b.get("failed_recent", 0) > 0:
        add(_item("数据安全", "warning", "近7天存在失败备份任务", f"{b['failed_recent']} 个 FAILED 备份",
                  "备份链路可能异常，兜底能力下降", "排查备份失败原因，确认最近一次成功备份"))

    # -- Aggregate overall level --
    critical_count = severity_counts["critical"]
    if critical_count > 0:
        overall_level = "blocked"
        block_execution = True
        recommendation = "存在严重风险项，默认阻止执行倒换。如已人工评估并接受风险，经确认放行后强制演练。"
    elif severity_counts["warning"] > 0 or severity_counts["unknown"] > 0:
        overall_level = "medium"
        block_execution = False
        recommendation = "存在预警或未知项，建议人工确认后再执行。"
    else:
        overall_level = "low"
        block_execution = False
        recommendation = "风险较低，可以执行倒换演练。"

    summary = "，".join(
        f"{level} {severity_counts.get(level, 0)} 项"
        for level in ("info", "warning", "unknown", "critical")
        if severity_counts.get(level, 0)
    )

    return {
        "overall_level": overall_level,
        "block_execution": block_execution,
        "recommendation": recommendation,
        "summary": summary,
        "items": items,
    }


def build_risk_assessment(region, instance_id, instance, monitoring, output_dir):
    """Run full risk detection + assessment, write risk_assessment.json.

    instance: instance info dict from prepare (contains capacity / az_codes / cache_mode, etc.).
    monitoring: monitoring config generated by prepare (contains alarm rules, etc., for keep_days context).
    """
    # Detection
    inst = detect_instance(region, instance_id)
    nodes = detect_nodes(region, instance_id)
    master = nodes.get("master") or {}
    keep_days = (instance.get("backup_strategy") or {}).get("keep_days")
    backups = detect_backups(region, instance_id, keep_days)
    ces = detect_ces_load(region, instance_id)

    det = {
        "status": inst.get("status"),
        "cache_mode": inst.get("cache_mode"),
        "az_codes": inst.get("az_codes", []),
        "capacity": inst.get("capacity"),
        "nodes": nodes,
        "backups": backups,
        "ces": ces,
    }

    assessed = assess_risks(det)

    doc = {
        "region": region,
        "instance_id": instance_id,
        "instance_name": instance.get("name", ""),
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_level": assessed["overall_level"],
        "block_execution": assessed["block_execution"],
        "recommendation": assessed["recommendation"],
        "summary": assessed["summary"],
        "items": assessed["items"],
        "detections": det,
    }

    save_path = os.path.join(output_dir, "risk_assessment.json")
    save_json(save_path, doc)
    return doc


def print_risk_summary(risk_doc):
    """Print a prominent risk assessment overview to the console."""
    lvl = risk_doc.get("overall_level", "low")
    print(f"\n  ── 风险评估总览 ──")
    print(f"  总体风险等级: {LEVEL_LABEL.get(lvl, lvl)}")
    print(f"  汇总: {risk_doc.get('summary', '')}")
    print(f"  建议: {risk_doc.get('recommendation', '')}")
    items = risk_doc.get("items", [])
    for it in items:
        if it.get("level") in ("warning", "critical", "unknown"):
            mark = {"critical": "🔴", "warning": "🟠", "unknown": "⚪"}.get(it.get("level"), "•")
            print(f"  {mark} [{it.get('category')}] {it.get('title')} — {it.get('detail')}")
            print(f"      影响: {it.get('impact')}")
            print(f"      建议: {it.get('suggestion')}")
    if risk_doc.get("block_execution"):
        print(f"  🔴 存在严重风险项，execute 阶段默认阻止倒换（需人工确认放行后执行）。")
