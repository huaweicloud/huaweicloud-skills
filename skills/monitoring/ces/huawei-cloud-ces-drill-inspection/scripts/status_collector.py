#!/usr/bin/env python3
"""Instance status collection: ECS / RDS / DCS(Redis) and 16 other cloud services via hcloud CLI.

Architecture:
  - ECS / RDS / DCS have dedicated collection functions (complex response parsing)
  - Other services use SERVICE_API_MAP + collect_generic() for generic collection
  - collect_all_status() iterates config.services for dynamic dispatch
"""

import logging
from typing import Any

from hcloud_executor import parallel_execute

logger = logging.getLogger(__name__)

# ── Dedicated services (complex parsing logic) ───────────────────────

def collect_ecs(regions: list[str], instance_ids: list[str], name_filter: list[str],
                max_workers: int = 10, hcloud_cmd: str = "hcloud", timeout: int = 60) -> list[dict[str, Any]]:
    """Collect ECS instance status."""
    tasks = []
    for region in regions:
        tasks.append({"args": ["ECS", "ListServersDetails"], "region": region, "key": f"ecs:{region}", "service": "ecs"})
    raw_results = parallel_execute(tasks, max_workers=max_workers, hcloud_cmd=hcloud_cmd, default_timeout=timeout)

    instances = []
    for r in raw_results:
        region = r["region"]
        data = r["result"]
        if "_error" in data:
            logger.warning("ECS collect failed for %s: %s", region, data["_error"])
            continue
        for srv in data.get("servers", []):
            inst_id = srv.get("id", "")
            name = srv.get("name", "")
            if instance_ids and inst_id not in instance_ids:
                continue
            if name_filter and not any(f in name for f in name_filter):
                continue
            flavor = srv.get("flavor", {})
            instances.append({
                "service": "ecs", "instance_id": inst_id, "name": name,
                "status": srv.get("status", "UNKNOWN"), "region": region,
                "az": srv.get("OS-EXT-AZ:availability_zone", ""),
                "cpu": flavor.get("vcpus"), "ram": flavor.get("ram"), "raw": srv,
            })
    return instances


# Sentinel value for "no standby node"
NO_STANDBY = "no_standby"


def collect_rds(regions: list[str], instance_ids: list[str],
                max_workers: int = 10, hcloud_cmd: str = "hcloud", timeout: int = 60) -> list[dict[str, Any]]:
    """Collect RDS instance status."""
    tasks = []
    for region in regions:
        tasks.append({"args": ["RDS", "ListInstances"], "region": region, "key": f"rds:{region}", "service": "rds"})
    raw_results = parallel_execute(tasks, max_workers=max_workers, hcloud_cmd=hcloud_cmd, default_timeout=timeout)

    instances = []
    for r in raw_results:
        region = r["region"]
        data = r["result"]
        if "_error" in data:
            logger.warning("RDS collect failed for %s: %s", region, data["_error"])
            continue
        for db in data.get("instances", []):
            inst_id = db.get("id", "")
            if instance_ids and inst_id not in instance_ids:
                continue
            nodes = db.get("nodes", [])
            primary_node = next((n for n in nodes if n.get("role") == "master"), None)
            standby_node = next((n for n in nodes if n.get("role") in ("slave", "standby")), None)
            primary_az = primary_node.get("availability_zone", "") if primary_node else ""
            if standby_node:
                standby_az = standby_node.get("availability_zone", "")
                standby_status = standby_node.get("status", "")
            else:
                standby_az = NO_STANDBY
                standby_status = NO_STANDBY
            cross_az = bool(primary_az and standby_az and standby_az != NO_STANDBY and primary_az != standby_az)
            instances.append({
                "service": "rds", "instance_id": inst_id, "name": db.get("name", ""),
                "status": db.get("status", "UNKNOWN"), "region": region, "az": primary_az,
                "primary_az": primary_az, "standby_az": standby_az,
                "primary_role": primary_node.get("role", "") if primary_node else "",
                "primary_status": primary_node.get("status", "") if primary_node else "",
                "standby_status": standby_status,
                "cross_az": cross_az,
                "instance_type": db.get("type", ""),
                "switch_strategy": db.get("switch_strategy", ""),
                "backup_keep_days": db.get("backup_strategy", {}).get("keep_days") if isinstance(db.get("backup_strategy"), dict) else None,
                "raw": db,
            })
    return instances


def collect_redis(regions: list[str], instance_ids: list[str],
                  max_workers: int = 10, hcloud_cmd: str = "hcloud", timeout: int = 60) -> list[dict[str, Any]]:
    """Collect DCS(Redis) instance status."""
    tasks = []
    for region in regions:
        tasks.append({"args": ["DCS", "ListInstances"], "region": region, "key": f"redis:{region}", "service": "redis"})
    raw_results = parallel_execute(tasks, max_workers=max_workers, hcloud_cmd=hcloud_cmd, default_timeout=timeout)

    instances = []
    for r in raw_results:
        region = r["region"]
        data = r["result"]
        if "_error" in data:
            logger.warning("DCS collect failed for %s: %s", region, data["_error"])
            continue
        for inst in data.get("instances", data.get("cache_instances", [])):
            inst_id = inst.get("instance_id", inst.get("id", ""))
            if instance_ids and inst_id not in instance_ids:
                continue
            cross_az = inst.get("cross_az_backup", inst.get("cross_az", False))
            sub_nodes = inst.get("node_list", inst.get("nodes", []))
            dim_resource_id = sub_nodes[0].get("resource_id", inst_id) if sub_nodes else inst_id
            # DCS API returns az_codes (list), take first as primary AZ
            az_codes = inst.get("az_codes", [])
            az = az_codes[0] if isinstance(az_codes, list) and az_codes else ""
            instances.append({
                "service": "redis", "instance_id": inst_id, "name": inst.get("name", ""),
                "status": inst.get("status", "UNKNOWN"), "region": region,
                "az": az,
                "memory_usage": round(inst.get("used_memory", 0) / inst.get("max_memory", 1) * 100, 2) if inst.get("max_memory") else None, "cross_az": bool(cross_az),
                "dim_resource_id": dim_resource_id, "raw": inst,
            })
    return instances


# ── Generic service config table ─────────────────────────────────────
# Each entry defines: hcloud command, response list field, status field, AZ field
# id_field / name_field support dot-nested paths (e.g. "metadata.uid"), default "id" / "name"
# status_field / az_field also support dot-nested paths (e.g. "status.phase")

SERVICE_API_MAP: dict[str, dict[str, Any]] = {
    "elb": {
        "hcloud_service": "ELB", "hcloud_action": "ListLoadBalancers/v3",
        "response_field": "loadbalancers",
        "status_field": "provisioning_status",
        "az_field": None,
    },
    "eip": {
        "hcloud_service": "EIP", "hcloud_action": "ListPublicips/v3",
        "response_field": "publicips",
        "status_field": "status",
        "az_field": None,
    },
    "nat": {
        "hcloud_service": "NAT", "hcloud_action": "ListNatGateways",
        "response_field": "nat_gateways",
        "status_field": "status",
        "az_field": None,
    },
    "vpcep": {
        "hcloud_service": "VPCEP", "hcloud_action": "ListEndpoints",
        "response_field": "endpoints",
        "status_field": "status",
        "az_field": None,
    },
    "evs": {
        "hcloud_service": "EVS", "hcloud_action": "ListVolumes",
        "response_field": "volumes",
        "status_field": "status",
        "az_field": "availability_zone",
    },
    "cce": {
        "hcloud_service": "CCE", "hcloud_action": "ListClusters",
        "response_field": "items",
        "status_field": "status.phase",
        "id_field": "metadata.uid",
        "name_field": "metadata.name",
        "az_field": None,
    },
    "css": {
        "hcloud_service": "CSS", "hcloud_action": "ListClustersDetails",
        "response_field": "clusters",
        "status_field": "status",
        "az_field": None,
    },
    "dds": {
        "hcloud_service": "DDS", "hcloud_action": "ListInstances",
        "response_field": "instances",
        "status_field": "status",
        "az_field": "availability_zone",
    },
    "dws": {
        "hcloud_service": "DWS", "hcloud_action": "ListClusters",
        "response_field": "clusters",
        "status_field": "status",
        "az_field": None,
    },
    "dc": {
        "hcloud_service": "DC", "hcloud_action": "ListDirectConnects",
        "response_field": "direct_connects",
        "status_field": "status",
        "az_field": None,
    },
    "er": {
        "hcloud_service": "ER", "hcloud_action": "ListEnterpriseRouters",
        "response_field": "instances",
        "status_field": "state",
        "az_field": None,
    },
    "efsturbo": {
        "hcloud_service": "SFSTurbo", "hcloud_action": "ListShares",
        "response_field": "shares",
        "status_field": "status",
        "az_field": "availability_zone",
    },
    "apig": {
        "hcloud_service": "APIG", "hcloud_action": "ListInstancesV2",
        "response_field": "instances",
        "status_field": "status",
        "az_field": None,
    },
    "taurusdb": {
        "hcloud_service": "GaussDB", "hcloud_action": "ListGaussMySqlInstances",
        "response_field": "instances",
        "status_field": "status",
        "az_field": None,
    },
    "geminidb": {
        "hcloud_service": "GaussDBforNoSQL", "hcloud_action": "ListInstances",
        "response_field": "instances",
        "status_field": "status",
        "az_field": None,
    },
    "dms": {
        "hcloud_service": "Kafka", "hcloud_action": "ListInstances",
        "response_field": "instances",
        "status_field": "status",
        "az_field": None,
    },
}


def _get_nested(obj: dict[str, Any], path: str) -> str:
    """Get value from nested dict by dot path, e.g. _get_nested(item, "metadata.uid")."""
    if not path:
        return ""
    val: Any = obj
    for part in path.split("."):
        if isinstance(val, dict):
            val = val.get(part, "")
        else:
            return ""
    return val if val is not None else ""


def collect_generic(
    service: str, api_cfg: dict[str, Any], regions: list[str],
    instance_ids: list[str], name_filter: list[str],
    max_workers: int = 10, hcloud_cmd: str = "hcloud", timeout: int = 60,
    engine: str | None = None,
) -> list[dict[str, Any]]:
    """Generic instance status collection.

    Driven by SERVICE_API_MAP config, suitable for services with simple response structures.
    Supports dot-nested paths for id_field / name_field / status_field / az_field.
    """
    hc_svc = api_cfg["hcloud_service"]
    hc_action = api_cfg["hcloud_action"]
    resp_field = api_cfg["response_field"]
    status_field = api_cfg.get("status_field", "status")
    az_field = api_cfg.get("az_field")
    id_field = api_cfg.get("id_field", "id")
    name_field = api_cfg.get("name_field", "name")

    extra_args = list(api_cfg.get("extra_args", []))
    if engine:
        extra_args.append(f"--engine={engine}")
    tasks = []
    for region in regions:
        tasks.append({
            "args": [hc_svc, hc_action] + extra_args,
            "region": region,
            "key": f"{service}:{region}",
            "service": service,
        })
    raw_results = parallel_execute(tasks, max_workers=max_workers, hcloud_cmd=hcloud_cmd, default_timeout=timeout)

    instances = []
    for r in raw_results:
        region = r["region"]
        data = r["result"]
        if "_error" in data:
            logger.warning("%s collect failed for %s: %s", service.upper(), region, data["_error"])
            continue
        items = data.get(resp_field, [])
        for item in items:
            inst_id = _get_nested(item, id_field)
            name = _get_nested(item, name_field)
            if instance_ids and inst_id not in instance_ids:
                continue
            if name_filter and not any(f in name for f in name_filter):
                continue
            inst = {
                "service": service,
                "instance_id": inst_id,
                "name": name,
                "status": _get_nested(item, status_field) or "UNKNOWN" if status_field else "N/A",
                "region": region,
                "az": _get_nested(item, az_field) if az_field else "",
                "raw": item,
            }
            instances.append(inst)
    return instances


# DMS engine → hcloud service/action mapping
DMS_ENGINE_MAP = {
    "kafka":    {"hcloud_service": "Kafka",    "hcloud_action": "ListInstances"},
    "rabbitmq": {"hcloud_service": "RabbitMQ", "hcloud_action": "ListInstancesDetails"},
    "rocketmq": {"hcloud_service": "RocketMQ", "hcloud_action": "ListInstances"},
}


# ── Dedicated service registration ───────────────────────────────────
# Services with complex parsing use dedicated functions, others use generic

DEDICATED_COLLECTORS = {
    "ecs": collect_ecs,
    "rds": collect_rds,
    "redis": collect_redis,
}


def collect_all_status(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Collect instance status for all services based on config.

    Iterates config.services, dynamically dispatches to dedicated or generic collection functions.
    Returns {service_name: [instance, ...], ...}
    """
    from config_loader import get_runtime
    rt = get_runtime(config)

    regions = config.get("regions", [])
    services_cfg = config.get("services", {})
    max_workers = rt["max_workers"]
    hcloud_cmd = rt["hcloud_cmd"]
    timeout = rt["hcloud_timeout"]
    result = {}

    for svc_name, svc_cfg in services_cfg.items():
        if not svc_cfg.get("enabled", False):
            continue

        inst_ids = svc_cfg.get("instance_ids", [])
        name_flt = svc_cfg.get("name_filter", [])

        # Dedicated functions first
        if svc_name in DEDICATED_COLLECTORS:
            if svc_name == "ecs":
                result["ecs"] = DEDICATED_COLLECTORS["ecs"](
                    regions, inst_ids, name_flt, max_workers, hcloud_cmd, timeout)
            else:
                result[svc_name] = DEDICATED_COLLECTORS[svc_name](
                    regions, inst_ids, max_workers, hcloud_cmd, timeout)
            logger.info("%s: collected %d instances", svc_name.upper(), len(result[svc_name]))

        # Generic function
        elif svc_name in SERVICE_API_MAP:
            api_cfg = dict(SERVICE_API_MAP[svc_name])
            # DMS: dynamically select hcloud service and action based on engine
            if svc_name == "dms":
                engine = svc_cfg.get("engine", "kafka")
                if engine not in DMS_ENGINE_MAP:
                    logger.warning("DMS: unknown engine '%s', using kafka", engine)
                    engine = "kafka"
                api_cfg.update(DMS_ENGINE_MAP[engine])
            result[svc_name] = collect_generic(
                svc_name, api_cfg, regions,
                inst_ids, name_flt, max_workers, hcloud_cmd, timeout,
                engine=svc_cfg.get("engine"))
            logger.info("%s: collected %d instances", svc_name.upper(), len(result[svc_name]))

        else:
            logger.warning("%s: no collector configured, skipped", svc_name.upper())

    return result
