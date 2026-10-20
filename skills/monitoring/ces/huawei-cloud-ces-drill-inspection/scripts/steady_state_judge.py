#!/usr/bin/env python3
"""Steady-state judgment engine: instance-level → service-level → global conclusion.

Architecture:
  - ECS / RDS / DCS have dedicated judgment functions (checking primary/standby roles, cross-AZ, etc.)
  - Other services use judge_generic_instance() (checking status + az)
  - JUDGE_FUNC dynamic registration: dedicated functions first, then generic for SERVICE_API_MAP services
"""

import logging
from typing import Any

from status_collector import NO_STANDBY

logger = logging.getLogger(__name__)


# ── Dedicated judgment functions ─────────────────────────────────────

def judge_ecs_instance(instance: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Judge ECS instance steady state."""
    expected_status = rules.get("expected_status")
    checks = []
    status = instance.get("status", "UNKNOWN")

    if expected_status:
        if status == expected_status:
            checks.append({"name": f"状态 = {status}", "ok": True})
        else:
            checks.append({"name": f"状态 = {status} (期望 = {expected_status})", "ok": False})
    else:
        logger.warning("ECS: expected_status not configured, skipping status check")
        checks.append({"name": f"状态 = {status} (期望状态未配置)", "ok": True})

    az = instance.get("az", "")
    checks.append({"name": f"可用区 = {az}", "ok": bool(az)})

    cpu = instance.get("cpu")
    checks.append({"name": f"CPU核数 = {float(cpu)}" if cpu is not None else "CPU核数 = 未知", "ok": cpu is not None})

    ram = instance.get("ram")
    checks.append({"name": f"内存 = {float(ram)/1024:.1f}GB" if ram is not None else "内存 = 未知", "ok": ram is not None})

    return _build_judgment(checks)


def judge_rds_instance(instance: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Judge RDS instance steady state."""
    expected_status = rules.get("expected_status")
    expected_role = rules.get("expected_primary_role")
    checks = []

    # Switchover strategy: check if present, no value (single-node instance) is normal
    switch_strategy = instance.get("switch_strategy", "")
    checks.append({"name": f"切换策略 = {switch_strategy}" if switch_strategy else "切换策略 = 无 (单机实例)", "ok": True})

    primary_role = instance.get("primary_role", "")
    if expected_role:
        if primary_role == expected_role:
            checks.append({"name": f"主节点角色 = {primary_role}", "ok": True})
        else:
            checks.append({"name": f"主节点角色 = {primary_role} (期望 = {expected_role})", "ok": False})
    else:
        logger.warning("RDS: expected_primary_role not configured, skipping role check")
        checks.append({"name": f"主节点角色 = {primary_role} (期望角色未配置)", "ok": True})

    # Primary status + instance status (checked for all instances)
    for label, key in [("主节点状态", "primary_status"), ("实例状态", "status")]:
        val = instance.get(key, "")
        if expected_status:
            if val == expected_status:
                checks.append({"name": f"{label} = {val}", "ok": True})
            else:
                checks.append({"name": f"{label} = {val} (期望 = {expected_status})", "ok": False})
        else:
            checks.append({"name": f"{label} = {val} (期望状态未配置)", "ok": True})

    # Standby status: no standby is normal, otherwise compare with expected status
    standby_status = instance.get("standby_status", "")
    if standby_status == NO_STANDBY:
        checks.append({"name": "备节点状态 = 无备节点", "ok": True})
    elif expected_status:
        if standby_status == expected_status:
            checks.append({"name": f"备节点状态 = {standby_status}", "ok": True})
        else:
            checks.append({"name": f"备节点状态 = {standby_status} (期望 = {expected_status})", "ok": False})
    else:
        checks.append({"name": f"备节点状态 = {standby_status} (期望状态未配置)", "ok": True})

    # Primary AZ (checked for all instances)
    primary_az = instance.get("primary_az", "")
    checks.append({"name": f"主节点可用区 = {primary_az}", "ok": bool(primary_az)})

    # Standby AZ: no standby is normal, otherwise check non-empty
    standby_az = instance.get("standby_az", "")
    if standby_az == NO_STANDBY:
        checks.append({"name": "备节点可用区 = 无备节点", "ok": True})
    else:
        checks.append({"name": f"备节点可用区 = {standby_az}", "ok": bool(standby_az)})

    cross_az = instance.get("cross_az", False)
    checks.append({"name": f"跨可用区部署 = {'是' if cross_az else '否'}", "ok": True})

    backup_days = instance.get("backup_keep_days")
    checks.append({"name": f"备份保留 = {float(backup_days)} 天" if backup_days is not None else "备份保留 = 未知", "ok": backup_days is not None})

    return _build_judgment(checks)


def judge_redis_instance(instance: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Judge Redis(DCS) instance steady state."""
    expected_status = rules.get("expected_status")
    checks = []
    status = instance.get("status", "UNKNOWN")

    if expected_status:
        if status == expected_status:
            checks.append({"name": f"状态 = {status}", "ok": True})
        else:
            checks.append({"name": f"状态 = {status} (期望 = {expected_status})", "ok": False})
    else:
        logger.warning("Redis: expected_status not configured, skipping status check")
        checks.append({"name": f"状态 = {status} (期望状态未配置)", "ok": True})

    mem_usage = instance.get("memory_usage")
    checks.append({"name": f"内存使用率 = {float(mem_usage)}%" if mem_usage is not None else "内存使用率 = 未知", "ok": mem_usage is not None})

    cross_az = instance.get("cross_az", False)
    checks.append({"name": f"跨可用区部署 = {'是' if cross_az else '否'}", "ok": True})

    return _build_judgment(checks)


# ── Generic judgment function ────────────────────────────────────────

def judge_generic_instance(instance: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Generic instance steady-state judgment.

    Checks:
      1. Instance status == expected_status (if expected_status is configured)
      2. AZ non-empty (if instance has az field)
    """
    checks = []
    expected_status = rules.get("expected_status")

    status = instance.get("status", "UNKNOWN")
    if expected_status:
        if status == expected_status:
            checks.append({"name": f"状态 = {status}", "ok": True})
        else:
            checks.append({"name": f"状态 = {status} (期望 = {expected_status})", "ok": False})
    else:
        # No expected_status configured (e.g. APIG), just record status
        checks.append({"name": f"状态 = {status}", "ok": True})

    az = instance.get("az", "")
    if az:
        checks.append({"name": f"可用区 = {az}", "ok": True})
    # Empty AZ is not a failure (many services have no AZ concept)

    return _build_judgment(checks)


# ── Judgment function registration ───────────────────────────────────

def _build_judgment(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Build judgment result from check list."""
    total = len(checks)
    ok_count = sum(1 for c in checks if c["ok"])
    if ok_count == total:
        verdict = "ok"
    elif ok_count == 0:
        verdict = "err"
    else:
        verdict = "warn"
    return {
        "checks": checks,
        "total": total,
        "ok_count": ok_count,
        "fail_count": total - ok_count,
        "verdict": verdict,
    }


# Dedicated judgment function registration
JUDGE_FUNC: dict[str, Any] = {
    "ecs": judge_ecs_instance,
    "rds": judge_rds_instance,
    "redis": judge_redis_instance,
}
def _auto_register_generic():
    """Auto-register generic judgment functions for all services in SERVICE_API_MAP."""
    try:
        from status_collector import SERVICE_API_MAP
        for svc in SERVICE_API_MAP:
            if svc not in JUDGE_FUNC:
                JUDGE_FUNC[svc] = judge_generic_instance
    except ImportError:
        pass


_auto_register_generic()


def judge_all_instances(
    instances_by_service: dict[str, list[dict[str, Any]]],
    steady_state_rules: dict[str, Any],
) -> dict[str, Any]:
    """Run steady-state judgment for all instances.

    Returns:
    {
        "services": {service: {instances, total_checks, ok_checks, fail_checks, verdict, ...}},
        "global": {total_checks, ok_checks, fail_checks, verdict, summary, affected_services}
    }
    """
    services_result = {}
    global_total = 0
    global_ok = 0
    global_fail = 0
    affected_services = []

    for service, instances in instances_by_service.items():
        rules = steady_state_rules.get(service, {})
        judge_fn = JUDGE_FUNC.get(service, judge_generic_instance)  # default to generic

        svc_instances = []
        svc_total = svc_ok = svc_fail = 0
        svc_ok_inst = svc_warn_inst = svc_err_inst = 0

        for inst in instances:
            judgment = judge_fn(inst, rules)
            inst["_is_normal"] = judgment["verdict"] == "ok"
            inst["_verdict"] = judgment["verdict"]
            svc_instances.append({"instance": inst, "judgment": judgment})
            svc_total += judgment["total"]
            svc_ok += judgment["ok_count"]
            svc_fail += judgment["fail_count"]
            if judgment["verdict"] == "ok":
                svc_ok_inst += 1
            elif judgment["verdict"] == "warn":
                svc_warn_inst += 1
            else:
                svc_err_inst += 1

        svc_verdict = "ok" if svc_fail == 0 else ("err" if svc_ok == 0 else "warn")
        services_result[service] = {
            "instances": svc_instances,
            "total_checks": svc_total,
            "ok_checks": svc_ok,
            "fail_checks": svc_fail,
            "verdict": svc_verdict,
            "instance_count": len(instances),
            "ok_count": svc_ok_inst,
            "warn_count": svc_warn_inst,
            "err_count": svc_err_inst,
        }
        global_total += svc_total
        global_ok += svc_ok
        global_fail += svc_fail
        if svc_fail > 0:
            affected_services.append(service)

    global_verdict = "ok" if global_fail == 0 else ("err" if global_ok == 0 else "warn")
    if global_fail > 0:
        svc_names = ", ".join(affected_services)
        global_summary = f"Found {global_fail} anomalies across {len(affected_services)} services ({svc_names}), immediate investigation recommended."
    else:
        global_summary = f"All {global_total} checks passed, no anomalies detected."

    return {
        "services": services_result,
        "global": {
            "total_checks": global_total,
            "ok_checks": global_ok,
            "fail_checks": global_fail,
            "verdict": global_verdict,
            "summary": global_summary,
            "affected_services": affected_services,
        },
    }
