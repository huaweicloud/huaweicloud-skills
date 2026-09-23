#!/usr/bin/env python3
"""
RDS 主备倒换 —— 风险检测 / 风险评估 / 风险预警 模块

在 prepare 阶段调用，帮助降低主备倒换演练出现异常的风险：

  1. 风险检测（detect）: 实时探测主备复制状态、存储水位、备份新鲜度、近 24h 错误日志、
     CES 负载指标（CPU/内存/磁盘/连接数/复制延迟）与实例配置（复制模式、切换策略、max_connections）。
  2. 风险评估（assess）: 对每项检测结果按阈值映射为 提示(info) / 预警(warning) / 严重(critical)，
     汇总总体风险等级（low / medium / blocked），并给出操作建议。
  3. 风险预警（warn）: 控制台醒目输出 + 生成 risk_assessment.json；
     execute 阶段读取该文件，存在 critical 项时默认阻止倒换（除非人工 --force）。

依赖的华为云接口（均为只读查询，不会修改云上资源）:
  - RDS ShowReplicationStatus      主备复制状态
  - RDS ShowStorageUsedSpace       存储用量
  - RDS ListBackups                备份列表
  - RDS ListErrorLogs              近24小时错误日志
  - RDS ShowInstanceConfiguration  实例参数（max_connections 等）
  - CES ShowMetricData             监控指标（CPU/内存/磁盘/连接数/复制延迟）

阈值定义与业务含义见 references/risk-model.md。
"""

import datetime
import html
import json
import os
import subprocess
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from config import run_hcloud as _run_hcloud
from ces_config import get_engine_ces_config, resolve_ces_dim_value, query_ces_metric


# ---------------------------------------------------------------------------
# 阈值（与 references/risk-model.md 保持一致）
# ---------------------------------------------------------------------------
THRESH = {
    "cpu_warn": 70,          # CPU 使用率 %，超过进入预警
    "cpu_crit": 90,          # CPU 使用率 %，超过进入严重（阻止倒换）
    "mem_warn": 80,          # 内存使用率 %
    "mem_crit": 90,
    "disk_warn": 80,         # 磁盘使用率 %（CES + 存储用量交叉）
    "disk_crit": 95,
    "storage_warn": 80,      # 存储空间使用率 %（ShowStorageUsedSpace）
    "storage_crit": 95,
    "conn_warn_pct": 70,     # 连接数占 max_connections 比例 %
    "conn_crit_pct": 90,
    "repl_delay_warn": 5,    # 主备复制延迟 s（reliability 策略等待 <5s 才切）
    "repl_delay_crit": 30,
    "error_log_warn": 10,    # 近24h ERROR 级日志条数
    "error_log_crit": 50,
    "backup_warn_hours": 48, # 最近成功备份超过 48h 预警
    "backup_crit_days": 7,   # 超过 7 天（或超过保留周期）严重
}

LEVEL_LABEL = {"low": "🟢 低", "medium": "🟠 中（存在预警）", "blocked": "🔴 高（阻止执行）"}


# ---------------------------------------------------------------------------
# hcloud 只读查询（从 config.py 共享导入）
# ---------------------------------------------------------------------------


def _latest_average(datapoints):
    """取 CES 返回的最近一个周期均值；无数据返回 None"""
    if not datapoints:
        return None
    v = datapoints[-1].get("average")
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fmt_dt(dt):
    """ISO8601 带时区偏移（如 2026-09-22T14:30:00+0800），日志 API 要求，不能用 Z"""
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


# ---------------------------------------------------------------------------
# 风险检测：逐项实时探测
# ---------------------------------------------------------------------------

def detect_replication(region, instance_id):
    """主备复制状态（RDS ShowReplicationStatus）"""
    resp = _run_hcloud("RDS", "ShowReplicationStatus", region, [f"--instance_id={instance_id}"])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "status": None}
    return {"available": True, "status": (resp.get("replication_status") or "unknown").lower(), "error": None}


def detect_storage(region, instance_id, volume_size):
    """存储空间使用率（ShowStorageUsedSpace 返回 used 为字符串 GB，总量取自 ListInstances volume.size）"""
    resp = _run_hcloud("RDS", "ShowStorageUsedSpace", region, [f"--instance_id={instance_id}"])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "used_gb": None,
                "total_gb": volume_size, "used_pct": None}
    used = None
    raw = resp.get("used") or resp.get("storage_used_space")
    try:
        used = float(raw)
    except (TypeError, ValueError):
        used = None
    # total 同样做异常防护：volume_size 可能非数值（云 API 字段异常）
    total = None
    try:
        total = float(volume_size) if volume_size else None
    except (TypeError, ValueError):
        total = None
    pct = round(used / total * 100, 1) if (used is not None and total is not None and total > 0) else None
    # 区分两种状态：
    #   - API 调用失败（resp._error）：available=False, error=错误信息
    #   - 接口成功但 volume_size（总量）未知：available=True（已取到 used），
    #     total_gb=None, used_pct=None, partial=True 标记数据不完整
    api_failed = resp.get("_error")
    if api_failed:
        return {"available": False, "error": resp.get("stderr", ""), "partial": False,
                "used_gb": None, "total_gb": None, "used_pct": None}
    # 接口成功，used 可能为 None（字段缺失）或数值
    total_unknown = (total is None)
    return {"available": used is not None, "error": None, "partial": total_unknown,
            "used_gb": used, "total_gb": total, "used_pct": pct}


def detect_backups(region, instance_id, keep_days):
    """备份新鲜度（ListBackups）"""
    resp = _run_hcloud("RDS", "ListBackups", region, [f"--instance_id={instance_id}"])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""),
                "latest_age_hours": None, "failed_recent": 0, "keep_days": keep_days}
    backups = resp.get("backups", [])
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
                t = None
        if status == "COMPLETED" and t:
            completed_times.append(t)
        if status == "FAILED" and t and (now - t).total_seconds() <= 7 * 86400:
            failed_recent += 1
    latest = max(completed_times) if completed_times else None
    latest_age_hours = round((now - latest).total_seconds() / 3600, 1) if latest else None
    return {"available": True, "error": None, "latest_age_hours": latest_age_hours,
            "failed_recent": failed_recent, "keep_days": keep_days}


def detect_recent_errors(region, instance_id):
    """近 24h ERROR 级错误日志条数（ListErrorLogs）"""
    end = datetime.datetime.now().astimezone()
    start = end - datetime.timedelta(hours=24)
    resp = _run_hcloud("RDS", "ListErrorLogs", region, [
        f"--instance_id={instance_id}",
        f"--start_date={_fmt_dt(start)}",
        f"--end_date={_fmt_dt(end)}",
    ])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "error_count": None, "total_count": None}
    logs = resp.get("error_log_list", [])
    err_count = sum(1 for l in logs if (l.get("level") or "").upper() == "ERROR")
    return {"available": True, "error": None, "error_count": err_count, "total_count": len(logs)}


def detect_params(region, instance_id):
    """实例参数：max_connections（连接数占比用）与 MySQL 持久化参数（提示级，仅 MySQL/MariaDB）"""
    resp = _run_hcloud("RDS", "ShowInstanceConfiguration", region, [f"--instance_id={instance_id}"])
    if resp.get("_error"):
        return {"available": False, "error": resp.get("stderr", ""), "max_connections": None,
                "innodb_flush_log_at_trx_commit": None, "sync_binlog": None}
    params = resp.get("configuration_parameters", [])
    d = {p.get("name"): p.get("value") for p in params if isinstance(p, dict)}
    mc = None
    try:
        mc = int(d.get("max_connections") or 0)
    except (TypeError, ValueError):
        mc = None
    return {"available": mc is not None, "error": None, "max_connections": mc,
            "innodb_flush_log_at_trx_commit": d.get("innodb_flush_log_at_trx_commit"),
            "sync_binlog": d.get("sync_binlog")}

def detect_ces_single(region, instance_id, node_id, metric_name, key,
                      dim_key="rds_instance_id", dim_value=None):
    """查询单个 CES 指标近 1 小时数据，取最近聚合点均值。

    metric_name 为华为云实际指标名（如 rds073_replication_delay），
    key 为脚本逻辑名，用于返回结果。
    dim_key 为 CES 维度名（如 rds_instance_id / postgresql_cluster_id），
    dim_value 为维度值（节点 ID 或实例 ID，取决于引擎）；
    未传 dim_value 时回退到 node_id（兼容旧调用）。

    CES 查询逻辑已抽取到 ces_config.query_ces_metric 公共 helper，
    与 execute.py collect_ces_metrics 共用同一实现，消除维护漂移。
    """
    actual_dim_value = dim_value if dim_value is not None else node_id
    to_ms = int(datetime.datetime.now().timestamp() * 1000)
    from_ms = to_ms - 3600000  # 近 1 小时
    result = query_ces_metric(_run_hcloud, region, metric_name, dim_key, actual_dim_value,
                              from_ms=from_ms, to_ms=to_ms)
    if not result["available"]:
        return {"available": False, "error": result["error"], "value": None}
    return {"available": True, "error": None, "value": _latest_average(result["datapoints"])}


def detect_ces_load(region, instance_id, node_id, engine="MySQL"):
    """近 1 小时 CES 负载指标（CPU/内存/磁盘/连接数/复制延迟），取最近聚合点均值。

    根据引擎类型自适应选择正确的 CES 维度名、维度值和指标名：
      - MySQL/TaurusDB: dim=rds_instance_id, value=节点 ID
      - PostgreSQL:    dim=postgresql_cluster_id, value=实例 ID
      - SQLServer:     dim=rds_cluster_sqlserver_id, value=实例 ID
      - MariaDB:       dim=mariadb_cluster_id, value=实例 ID
    引擎映射与 execute.py 的 collect_ces_metrics 共用 ces_config.ENGINE_CES_CONFIG。
    """
    try:
        ces_cfg = get_engine_ces_config(engine)
        dim_key, dim_value = resolve_ces_dim_value(engine, instance_id, node_id)
    except ValueError as e:
        # 未知引擎或 node_id 缺失 — 所有 CES 负载指标标记为不可用（→ unknown）
        print(f"  [风险检测] {e}")
        return {k: {"available": False, "error": str(e)} for k in
                ("cpu_util", "mem_util", "disk_util", "conn_count", "replication_delay")}
    mm = ces_cfg["metric_map"]
    metric_keys = [
        (mm["rds_cpu_util"], "cpu_util"),
        (mm["rds_mem_util"], "mem_util"),
        (mm["rds_disk_util"], "disk_util"),
        (mm["rds_connections_count"], "conn_count"),
        (mm["rds_replication_delay"], "replication_delay"),
    ]
    result = {}
    for metric, key in metric_keys:
        result[key] = detect_ces_single(region, instance_id, node_id, metric, key,
                                        dim_key=dim_key, dim_value=dim_value)
    return result

def realtime_safety_check(region, instance_id, node_id=None, engine="MySQL"):
    """execute 阶段执行前的实时复核：只查变化最快、对倒换成败最关键的两项。

    prepare 生成的 risk_assessment.json 是快照，可能过期；
    倒换前用本函数实时复核：
      - 主备复制状态（RDS ShowReplicationStatus）
      - 近 5 分钟复制延迟（CES，按引擎选择正确的指标名和维度）

    engine 参数用于选择正确的 CES 维度名/维度值/指标名，
    与 execute.py 的 collect_ces_metrics 共用 ces_config.ENGINE_CES_CONFIG。

    返回 {"blocked": bool, "signals": [...]}；
    blocked=True 表示实时发现严重风险，execute 应默认阻止倒换。
    """
    signals = []
    blocked = False

    rep = detect_replication(region, instance_id)
    if not rep.get("available"):
        signals.append({"level": "warning", "title": "实时复制状态无法查询",
                        "detail": rep.get("error", ""),
                        "suggestion": "请人工确认主备复制链路健康"})
    elif rep.get("status") == "normal":
        signals.append({"level": "info", "title": "实时复制状态正常",
                        "detail": "replication_status=normal"})
    else:
        signals.append({"level": "critical", "title": "实时复制状态异常",
                        "detail": f"replication_status={rep.get('status')}",
                        "suggestion": "禁止倒换，先排查复制链路"})
        blocked = True

    if node_id:
        rd = {}
        try:
            ces_cfg = get_engine_ces_config(engine)
        except ValueError as e:
            # 未知引擎 — 无法复核复制延迟，标记 unknown 不阻断
            print(f"  [实时复核] {e}，复制延迟复核跳过")
            ces_cfg = None
        if ces_cfg:
            try:
                dim_key, dim_value = resolve_ces_dim_value(engine, instance_id, node_id)
            except ValueError as e:
                # node_id 缺失 — 无法复核复制延迟
                print(f"  [实时复核] {e}，复制延迟复核跳过")
                rd = {"available": False, "error": str(e), "value": None}
            else:
                repl_metric = ces_cfg["metric_map"]["rds_replication_delay"]
                rd = detect_ces_single(region, instance_id, node_id, repl_metric, "replication_delay",
                                        dim_key=dim_key, dim_value=dim_value)
        if rd.get("available") and rd.get("value") is not None:
            v = rd["value"]
            if v >= THRESH["repl_delay_crit"]:
                signals.append({"level": "critical", "title": "实时复制延迟过高",
                                "detail": f"近5分钟复制延迟={v:g}s",
                                "suggestion": "禁止倒换，等待复制追平（可靠性优先会等待延迟<5s）"})
                blocked = True
            elif v >= THRESH["repl_delay_warn"]:
                signals.append({"level": "warning", "title": "实时复制延迟偏高",
                                "detail": f"近5分钟复制延迟={v:g}s",
                                "suggestion": "倒换窗口会拉长，建议等待延迟回落"})
            else:
                signals.append({"level": "info", "title": "实时复制延迟正常",
                                "detail": f"近5分钟复制延迟={v:g}s"})
        else:
            signals.append({"level": "warning", "title": "实时复制延迟无监控数据",
                            "detail": rd.get("error") or "CES 未返回复制延迟指标",
                            "suggestion": "以复制状态复核结果为准，必要时人工确认"})

    return {"blocked": blocked, "signals": signals}


# ---------------------------------------------------------------------------
# 风险评估
# ---------------------------------------------------------------------------

def _item(category, level, title, detail, impact, suggestion):
    return {
        "category": category,
        "level": level,           # info / warning / critical
        "title": title,
        "detail": detail,
        "impact": impact,
        "suggestion": suggestion,
    }


def _severity(value, warn, crit):
    """按阈值返回等级：value 为 None 时返回 unknown（数据缺失不误判为严重）"""
    if value is None:
        return "unknown"
    if value >= crit:
        return "critical"
    if value >= warn:
        return "warning"
    return "info"


def assess_risks(det):
    """对检测结果逐项定级，汇总总体风险等级与操作建议。

    det 为 build_risk_assessment 组装的检测数据字典，字段见该函数。
    返回 {overall_level, recommendation, block_execution, summary, items}。
    """
    t = THRESH
    items = []
    severity_counts = {"critical": 0, "warning": 0, "info": 0, "unknown": 0}

    def add(it):
        items.append(it)
        severity_counts[it["level"]] = severity_counts.get(it["level"], 0) + 1

    # 1) 实例状态
    if det.get("status") == "ACTIVE":
        add(_item("实例健康", "info", "实例状态正常", f"status={det.get('status')}", "-", "-"))
    else:
        add(_item("实例健康", "critical", "实例状态非 ACTIVE", f"status={det.get('status')}",
                  "倒换命令可能被拒绝或在异常状态下失败",
                  "等待实例恢复 ACTIVE 后再执行演练"))

    # 2) 主备复制状态
    r = det.get("replication", {})
    if not r.get("available"):
        add(_item("主备复制", "unknown", "主备复制状态不可查询", r.get("error", "查询失败"),
                  "无法自动确认复制链路健康", "execute 前用 hcloud RDS ShowReplicationStatus 人工复核"))
    elif r.get("status") == "normal":
        add(_item("主备复制", "info", "主备复制状态正常", "replication_status=normal", "-", "-"))
    else:
        add(_item("主备复制", "critical", "主备复制状态异常", f"replication_status={r.get('status')}",
                  "备库可能落后或失效，倒换后可能丢数据或失败",
                  "先排查复制链路并恢复 normal 后再演练"))

    # 3) 主备复制延迟（CES rds073，近 1h 均值）
    d = det.get("ces", {}).get("replication_delay", {})
    if d.get("available") and d.get("value") is not None:
        lvl = _severity(d["value"], t["repl_delay_warn"], t["repl_delay_crit"])
        if lvl == "critical":
            add(_item("主备复制", "critical", "主备复制延迟过高", f"近1小时延迟均值={d['value']:g}s",
                      "延迟 >30s 时倒换窗口显著拉长，可能超时或丢失未复制数据",
                      "等待复制追平后再演练（可靠性优先模式会等待延迟回落<5s）"))
        elif lvl == "warning":
            add(_item("主备复制", "warning", "主备复制延迟偏高", f"近1小时延迟均值={d['value']:g}s",
                      "倒换耗时可能增加，可靠性优先模式下会等待延迟回落后才切换",
                      "建议低峰期执行，并关注延迟走势"))
        else:
            add(_item("主备复制", "info", "主备复制延迟正常", f"近1小时延迟均值={d['value']:g}s", "-", "-"))
    else:
        add(_item("主备复制", "unknown", "复制延迟无监控数据", d.get("error") or "CES 未返回复制延迟指标",
                  "无法自动评估延迟风险", "手动检查复制状态，或确认监控维度/权限"))

    # 4) 存储空间使用率（ShowStorageUsedSpace）
    s = det.get("storage", {})
    if s.get("available"):
        lvl = _severity(s["used_pct"], t["storage_warn"], t["storage_crit"])
        detail = f"已用 {s['used_gb']:g}GB / 总量 {s['total_gb']:g}GB（{s['used_pct']:g}%）"
        if lvl == "critical":
            add(_item("存储", "critical", "存储空间使用率过高", detail,
                      "磁盘接近写满时倒换/恢复可能失败",
                      "先扩容或清理数据，释放存储空间后再演练"))
        elif lvl == "warning":
            add(_item("存储", "warning", "存储空间使用率偏高", detail,
                      "倒换期间日志/监控采集可能加剧存储压力",
                      "建议先释放空间或扩容，再安排演练"))
        else:
            add(_item("存储", "info", "存储空间充足", detail, "-", "-"))
    else:
        if s.get("partial"):
            # 接口成功但总量（volume_size）未知——已取到 used 但无法计算使用率
            add(_item("存储", "unknown", "存储总量未知，无法计算使用率",
                      f"已获取已用空间={s.get('used_gb')}GB，但实例总量(volume_size)未传入",
                      "无法自动评估磁盘水位", "通过控制台确认存储总量或扩容配置"))
        else:
            add(_item("存储", "unknown", "存储用量不可查询", s.get("error", "查询失败"),
                      "无法自动评估磁盘水位", "通过控制台确认存储使用情况"))

    # 5) 磁盘使用率（CES rds039，与 4 交叉验证）
    disk = det.get("ces", {}).get("disk_util", {})
    if disk.get("available") and disk.get("value") is not None:
        lvl = _severity(disk["value"], t["disk_warn"], t["disk_crit"])
        if lvl == "critical":
            add(_item("存储", "critical", "磁盘使用率过高（监控）", f"近1小时磁盘使用率均值={disk['value']:g}%",
                      "磁盘接近写满，倒换/恢复可能失败", "优先扩容或清理数据"))
        elif lvl == "warning":
            add(_item("存储", "warning", "磁盘使用率偏高（监控）", f"近1小时磁盘使用率均值={disk['value']:g}%",
                      "磁盘水位偏高，倒换期间可能加剧", "建议先释放空间"))
        else:
            add(_item("存储", "info", "磁盘使用率正常（监控）", f"近1小时磁盘使用率均值={disk['value']:g}%", "-", "-"))
    else:
        add(_item("存储", "unknown", "磁盘使用率无监控数据", disk.get("error") or "CES 未返回指标",
                  "-", "以存储用量探测结果为准"))

    # 6) CPU 使用率
    cpu = det.get("ces", {}).get("cpu_util", {})
    if cpu.get("available") and cpu.get("value") is not None:
        lvl = _severity(cpu["value"], t["cpu_warn"], t["cpu_crit"])
        if lvl == "critical":
            add(_item("负载", "critical", "CPU 使用率过高", f"近1小时CPU均值={cpu['value']:g}%",
                      "倒换窗口的连接中断会显著放大业务影响，恢复期性能可能不足",
                      "等 CPU 回落后（或低峰期）再演练；如必须执行请 --force 并通知业务"))
        elif lvl == "warning":
            add(_item("负载", "warning", "CPU 使用率偏高", f"近1小时CPU均值={cpu['value']:g}%",
                      "倒换期间业务中断影响面较大", "建议低峰期执行"))
        else:
            add(_item("负载", "info", "CPU 使用率正常", f"近1小时CPU均值={cpu['value']:g}%", "-", "-"))
    else:
        add(_item("负载", "unknown", "CPU 使用率无监控数据", cpu.get("error") or "CES 未返回指标", "-", "-"))

    # 7) 内存使用率
    mem = det.get("ces", {}).get("mem_util", {})
    if mem.get("available") and mem.get("value") is not None:
        lvl = _severity(mem["value"], t["mem_warn"], t["mem_crit"])
        if lvl == "critical":
            add(_item("负载", "critical", "内存使用率过高", f"近1小时内存均值={mem['value']:g}%",
                      "新主库需要重建缓冲池，内存压力大时恢复更慢", "等内存回落后再演练"))
        elif lvl == "warning":
            add(_item("负载", "warning", "内存使用率偏高", f"近1小时内存均值={mem['value']:g}%",
                      "倒换后新主库缓冲池预热期间性能可能下降", "建议低峰期执行"))
        else:
            add(_item("负载", "info", "内存使用率正常", f"近1小时内存均值={mem['value']:g}%", "-", "-"))
    else:
        add(_item("负载", "unknown", "内存使用率无监控数据", mem.get("error") or "CES 未返回指标", "-", "-"))

    # 8) 连接数占比（当前连接数 / max_connections）
    conn = det.get("ces", {}).get("conn_count", {})
    mc = det.get("params", {}).get("max_connections")
    if conn.get("available") and conn.get("value") is not None and mc:
        pct = conn["value"] / float(mc) * 100
        lvl = _severity(pct, t["conn_warn_pct"], t["conn_crit_pct"])
        pct_str = f"{pct:.1f}" if pct < 10 else f"{pct:.0f}"
        detail = f"近1小时连接数={conn['value']:g} / max_connections={mc}（{pct_str}%）"
        if lvl == "critical":
            add(_item("负载", "critical", "连接数接近上限", detail,
                      "倒换瞬间所有连接被断开，大量应用并发重连可能压垮新主库",
                      "先排查连接泄漏/调大 max_connections，错峰演练"))
        elif lvl == "warning":
            add(_item("负载", "warning", "连接数占用偏高", detail,
                      "倒换后瞬时重连风暴风险较高", "建议提前让应用侧准备连接池重连/退避策略"))
        else:
            add(_item("负载", "info", "连接数占用正常", detail, "-", "-"))
    else:
        add(_item("负载", "unknown", "连接数占比无法评估",
                  (conn.get("error") if conn.get("available") is False else None)
                  or ("未取到 max_connections 参数" if not mc else "CES 未返回连接数指标"),
                  "无法自动评估重连风暴风险", "可忽略或手动确认当前连接数"))

    # 9) 备份新鲜度（数据安全兜底）
    b = det.get("backups", {})
    kd = b.get("keep_days")
    crit_hour = (min(int(kd), t["backup_crit_days"]) if kd else t["backup_crit_days"]) * 24
    if not b.get("available"):
        add(_item("数据安全", "unknown", "备份信息不可查询", b.get("error", "查询失败"),
                  "无法自动确认备份兜底", "通过控制台确认备份策略与最近备份"))
    elif b.get("latest_age_hours") is None:
        add(_item("数据安全", "critical", "无任何成功备份记录", "ListBackups 无 COMPLETED 备份",
                  "倒换异常时缺少恢复兜底", "先完成一次手动备份或确认备份策略再演练"))
    elif b.get("latest_age_hours") <= t["backup_warn_hours"]:
        add(_item("数据安全", "info", "最近备份正常", f"最近成功备份于 {b['latest_age_hours']:g} 小时前", "-", "-"))
    elif b.get("latest_age_hours") <= crit_hour:
        add(_item("数据安全", "warning", "最近备份时间较旧", f"最近成功备份于 {b['latest_age_hours']:g} 小时前",
                  "备份兜底不够新鲜，异常时恢复点较远", "建议先做一次手动备份再演练"))
    else:
        add(_item("数据安全", "critical", "备份缺失或超过保留周期", f"最近成功备份于 {b['latest_age_hours']:g} 小时前（> {crit_hour // 24} 天）",
                  "缺少有效备份兜底", "先完成备份并确认备份任务恢复正常"))
    if b.get("failed_recent", 0) > 0:
        add(_item("数据安全", "warning", "近7天存在失败备份任务", f"{b['failed_recent']} 个 FAILED 备份",
                  "备份链路可能异常，兜底能力下降", "排查备份失败原因，确认最近一次成功备份"))

    # 10) 近 24h ERROR 错误日志
    e = det.get("recent_errors", {})
    if e.get("available"):
        lvl = _severity(e["error_count"], t["error_log_warn"], t["error_log_crit"])
        if lvl == "critical":
            add(_item("日志", "critical", "近24小时错误日志过多", f"ERROR 级 {e['error_count']} 条",
                      "实例可能存在持续异常，倒换可能触发连锁故障", "先结合错误日志定位根因再演练"))
        elif lvl == "warning":
            add(_item("日志", "warning", "近24小时错误日志偏多", f"ERROR 级 {e['error_count']} 条",
                      "存在异常信号（部分客户端断连类 ERROR 属常见噪音）", "抽查错误日志，确认无致命错误"))
        else:
            add(_item("日志", "info", "近24小时错误日志正常", f"ERROR 级 {e['error_count']} 条", "-", "-"))
    else:
        add(_item("日志", "unknown", "错误日志不可查询", e.get("error", "查询失败"),
                  "无法自动评估近期异常", "execute 阶段仍会收集倒换期间错误日志"))

    # 11) 复制模式
    ha_mode = (det.get("ha_mode") or "").lower()
    if ha_mode in ("semisync", "semi-sync", "sync"):
        add(_item("配置", "info", "复制模式为同步/半同步", f"replication_mode={det.get('ha_mode')}",
                  "正常倒换基本不丢失已提交数据（RPO≈0）", "-"))
    elif ha_mode == "async":
        add(_item("配置", "warning", "异步复制模式", "replication_mode=async",
                  "存在未复制数据丢失窗口（RPO>0），倒换可能丢少量数据",
                  "如对数据零丢失有要求，建议先评估复制延迟并确认可接受"))
    else:
        add(_item("配置", "info", "复制模式未知", f"replication_mode={det.get('ha_mode') or 'N/A'}",
                  "-", "可手动确认实例 HA 复制模式"))

    # 12) 切换策略
    ss = (det.get("switch_strategy") or "").lower()
    if ss == "availability":
        add(_item("配置", "warning", "切换策略为可用性优先", "switch_strategy=availability",
                  "切主时不强制等待数据追平，极端情况下可能丢失数据",
                  "确认业务可接受该数据风险，或评估改为 reliability"))
    elif ss == "reliability":
        add(_item("配置", "info", "切换策略为可靠性优先", "switch_strategy=reliability",
                  "切主会等待复制追平，优先保证数据一致性", "-"))
    else:
        add(_item("配置", "info", "切换策略未知", f"switch_strategy={det.get('switch_strategy') or 'N/A'}", "-", "-"))

    # 13) 主备跨 AZ
    maz, saz = det.get("master_az"), det.get("slave_az")
    if maz and saz:
        if maz != saz:
            add(_item("配置", "info", "主备跨可用区部署", f"master AZ={maz}, slave AZ={saz}", "-", "-"))
        else:
            add(_item("配置", "warning", "主备同可用区部署", f"master AZ={maz}, slave AZ={saz}",
                      "倒换无法提供跨 AZ 容灾能力，演练价值打折", "如期望验证跨 AZ 容灾，需按跨 AZ 部署实例"))

    # 14) MySQL/MariaDB 持久化参数（提示级；engine 可能含版本号如 "MySQL 8.0"）
    engine = (det.get("engine") or "").strip().lower()
    engine_type = engine.split()[0] if engine else ""
    if engine_type in ("mysql", "mariadb") and det.get("params", {}).get("available"):
        flush = det.get("params", {}).get("innodb_flush_log_at_trx_commit")
        syncb = det.get("params", {}).get("sync_binlog")
        if flush is not None and str(flush) != "1":
            add(_item("配置", "info", f"innodb_flush_log_at_trx_commit={flush}（≠1）",
                      "崩溃/强制切换时最多可能丢失约 1s 已提交事务的 redo",
                      "影响故障恢复精度，不影响主备复制链路", "如对 RPO 有严格要求可评估改为 1（性能略降）"))
        if syncb is not None and str(syncb) != "1":
            add(_item("配置", "info", f"sync_binlog={syncb}（≠1）",
                      "binlog 批量落盘，故障时可能丢失部分已提交事务的 binlog 记录",
                      "影响基于 binlog 的恢复精度，不影响主备复制链路", "如对恢复精度有严格要求可评估改为 1"))

    # ---- 汇总 ----
    criticals = [i for i in items if i["level"] == "critical"]
    warnings = [i for i in items if i["level"] == "warning"]
    unknowns = [i for i in items if i["level"] == "unknown"]
    if criticals:
        overall = "blocked"
        recommendation = ("阻止执行：存在 " + str(len(criticals)) + " 项严重风险（见预警列表）。"
                          "如已人工评估并接受风险，可在 execute 阶段加 --force 强制演练。")
    elif warnings:
        overall = "medium"
        recommendation = ("可执行但建议先处理 " + str(len(warnings)) + " 项预警；如确认风险可接受，可继续演练。")
    elif unknowns:
        overall = "medium"
        recommendation = ("存在 " + str(len(unknowns)) + " 项无法评估的风险项（接口不可用或无数据），"
                          "该项不会自动放行，请人工确认后再执行；如确认无风险可继续演练。")
    else:
        overall = "low"
        recommendation = "风险低，可执行。"

    return {
        "overall_level": overall,
        "recommendation": recommendation,
        "block_execution": overall == "blocked",
        "summary": {"critical": len(criticals), "warning": len(warnings),
                    "unknown": len(unknowns),
                    "info": len(items) - len(criticals) - len(warnings) - len(unknowns),
                    "total": len(items)},
        "items": items,
    }


# ---------------------------------------------------------------------------
# 组装：检测 + 评估 + 落盘
# ---------------------------------------------------------------------------

def build_risk_assessment(region, instance_id, target, monitoring, output_dir):
    """执行风险检测与评估，将结果写入 <output_dir>/risk_assessment.json，并返回完整结果。

    target 为 prepare 阶段 query_rds_instances 生成的实例信息字典；
    monitoring 供节点 ID 兼容使用（当前优先使用 target.master_node_id）。
    """
    det = {
        "status": target.get("status"),
        "engine": target.get("engine", "").lower(),
        "ha_mode": target.get("ha_mode"),
        "switch_strategy": target.get("switch_strategy", ""),
        "master_az": target.get("master_az"),
        "slave_az": target.get("slave_az"),
        "keep_days": (target.get("backup_strategy") or {}).get("keep_days"),
    }

    det["replication"] = detect_replication(region, instance_id)
    det["storage"] = detect_storage(region, instance_id, target.get("volume_size"))
    det["backups"] = detect_backups(region, instance_id, det["keep_days"])
    det["recent_errors"] = detect_recent_errors(region, instance_id)
    det["params"] = detect_params(region, instance_id)
    node_id = target.get("master_node_id") or instance_id
    engine = target.get("engine", "MySQL")
    det["ces"] = detect_ces_load(region, instance_id, node_id, engine=engine)

    assessment = assess_risks(det)

    doc = {
        "region": region,
        "instance_id": instance_id,
        "instance_name": target.get("name"),
        "engine": target.get("engine"),
        "assessed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "node_id_used_for_ces": node_id,
        "thresholds": THRESH,
        "detections": {
            "instance_status": det["status"],
            "replication_status": det["replication"].get("status") if det["replication"].get("available") else None,
            "replication_error": det["replication"].get("error"),
            "storage_used_pct": det["storage"].get("used_pct"),
            "storage_detail": f"{det['storage'].get('used_gb')}GB/{det['storage'].get('total_gb')}GB" if det["storage"].get("available") else None,
            "latest_backup_age_hours": det["backups"].get("latest_age_hours"),
            "backup_failed_recent": det["backups"].get("failed_recent"),
            "error_log_24h": det["recent_errors"].get("error_count"),
            "max_connections": det["params"].get("max_connections"),
            "ces_last_hour": {k: (v.get("value") if v.get("available") else None)
                              for k, v in det["ces"].items()},
        },
        **assessment,
    }
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "risk_assessment.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return doc


# ---------------------------------------------------------------------------
# 风险预警：控制台输出 + 报告片段
# ---------------------------------------------------------------------------

def print_risk_summary(risk):
    """控制台醒目输出风险评估总览与预警项"""
    lvl = risk.get("overall_level", "low")
    label = LEVEL_LABEL.get(lvl, lvl)
    print(f"\n  ── 风险评估总览 ──")
    print(f"  总体风险等级: {label}")
    s = risk.get("summary", {})
    print(f"  严重项 {s.get('critical', 0)} / 预警项 {s.get('warning', 0)} / 未知项 {s.get('unknown', 0)} / 提示项 {s.get('info', 0)}")
    for it in risk.get("items", []):
        if it.get("level") in ("critical", "warning", "unknown"):
            mark = {"critical": "🔴", "warning": "🟠", "unknown": "⚪"}.get(it.get("level"), "•")
            print(f"    {mark} [{it.get('category')}] {it.get('title')} — {it.get('detail')}")
            if it.get("impact") != "-":
                print(f"        影响: {it.get('impact')}")
            if it.get("suggestion") != "-":
                print(f"        建议: {it.get('suggestion')}")
    print(f"  结论: {risk.get('recommendation', '')}")


def risk_section_md(risk):
    """生成 Markdown 报告中的风险检测/评估/预警章节（行列表）"""
    lvl = risk.get("overall_level", "low")
    label = LEVEL_LABEL.get(lvl, lvl)
    s = risk.get("summary", {})
    lines = [
        "",
        "## 🔬 风险检测 / 评估 / 预警",
        "",
        f"**总体风险等级**：{label}（严重 {s.get('critical', 0)} · 预警 {s.get('warning', 0)} · 未知 {s.get('unknown', 0)} · 提示 {s.get('info', 0)}）",
        "",
        f"**结论**：{risk.get('recommendation', '')}",
        "",
        "| 等级 | 类别 | 检测项 | 详情 | 影响 | 建议 |",
        "|------|------|--------|------|------|------|",
    ]
    for it in risk.get("items", []):
        mark = {"critical": "🔴 严重", "warning": "🟠 预警", "unknown": "⚪ 未知", "info": "🟢 提示"}.get(it.get("level"), it.get("level"))
        title = it.get("title", "").replace("|", "\\|")
        detail = (it.get("detail") or "").replace("|", "\\|")
        impact = (it.get("impact") or "").replace("|", "\\|")
        sugg = (it.get("suggestion") or "").replace("|", "\\|")
        lines.append(f"| {mark} | {it.get('category')} | {title} | {detail} | {impact} | {sugg} |")
    lines.append("")
    return lines


def risk_section_html(risk):
    """生成 HTML 报告中的风险检测/评估/预警章节

    所有来自云 API 的外部数据（类别、检测项、详情、影响、建议、结论）均经
    html.escape 转义后插入，防止日志/实例名称中的恶意 HTML/JS 在浏览器执行（存储型 XSS）。
    """
    lvl = risk.get("overall_level", "low")
    label = LEVEL_LABEL.get(lvl, lvl)
    s = risk.get("summary", {})
    color = {"low": "#27ae60", "medium": "#e67e22", "blocked": "#e74c3c"}.get(lvl, "#333")
    rows = ""
    for it in risk.get("items", []):
        mark = {"critical": "&#128308;", "warning": "&#128992;", "unknown": "&#9898;", "info": "&#128994;"}.get(it.get("level"), "&#9898;")
        badge_color = {"critical": "#e74c3c", "warning": "#e67e22", "unknown": "#95a5a6", "info": "#27ae60"}.get(it.get("level"), "#95a5a6")
        lvl_text = {"critical": "严重", "warning": "预警", "unknown": "未知", "info": "提示"}.get(it.get("level"), it.get("level"))
        rows += (
            f'<tr><td>{mark} <span class="badge" style="background:{badge_color}">{lvl_text}</span></td>'
            f'<td>{html.escape(str(it.get("category") or ""))}</td>'
            f'<td>{html.escape(str(it.get("title") or ""))}</td>'
            f'<td>{html.escape(str(it.get("detail") or ""))}</td>'
            f'<td>{html.escape(str(it.get("impact") or ""))}</td>'
            f'<td>{html.escape(str(it.get("suggestion") or ""))}</td></tr>'
        )
    return f"""
  <div class="card" style="border:2px solid {color};">
    <h2>&#128269; 风险检测 / 评估 / 预警&nbsp;<span class="badge" style="background:{color};font-size:13px;">总体等级: {label}</span></h2>
    <p><strong>严重 {s.get('critical', 0)} 项 · 预警 {s.get('warning', 0)} 项 · 未知 {s.get('unknown', 0)} 项 · 提示 {s.get('info', 0)} 项</strong></p>
    <p><strong>结论：</strong>{html.escape(str(risk.get('recommendation') or ''))}</p>
    <table>
      <thead><tr><th>等级</th><th>类别</th><th>检测项</th><th>详情</th><th>影响</th><th>建议</th></tr></thead>
      <tbody>{rows}
      </tbody>
    </table>
  </div>
"""