#!/usr/bin/env python3
"""AZ resource topology graph data construction: Region → AZ → Instance."""

import logging
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)


def build_topology(judgment_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Build AZ topology data.

    Returns:
    [
        {
            "region": "your-region",
            "azs": [
                {
                    "az": "your-region-a",
                    "running_count": 3,
                    "abnormal_count": 1,
                    "services": {
                        "ecs": {"running": 2, "abnormal": 1, "instances": [{"name", "verdict", "role"}, ...]},
                        "rds": {...},
                    }
                },
                ...
            ]
        },
        ...
    ]
    """
    region_map = OrderedDict()

    for service, svc_data in judgment_result["services"].items():
        for item in svc_data["instances"]:
            inst = item["instance"]
            judgment = item["judgment"]
            region = inst.get("region", "unknown")
            az = inst.get("az", "unknown")
            verdict = judgment["verdict"]

            # RDS: primary and standby AZ assigned separately
            if service == "rds":
                _add_rds_to_topology(region_map, inst, verdict, service)
                continue

            # ECS / Redis: single AZ
            if region not in region_map:
                region_map[region] = OrderedDict()
            if az not in region_map[region]:
                region_map[region][az] = {}
            az_data = region_map[region][az]
            if service not in az_data:
                az_data[service] = {"running": 0, "abnormal": 0, "instances": []}

            is_normal = verdict == "ok"
            if is_normal:
                az_data[service]["running"] += 1
            else:
                az_data[service]["abnormal"] += 1
            az_data[service]["instances"].append({
                "name": inst.get("name", ""),
                "instance_id": inst.get("instance_id", ""),
                "verdict": verdict,
                "role": None,
            })

    # Convert to list format
    result = []
    for region, az_map in region_map.items():
        azs = []
        for az, services in az_map.items():
            running = sum(s["running"] for s in services.values())
            abnormal = sum(s["abnormal"] for s in services.values())
            azs.append({
                "az": az,
                "running_count": running,
                "abnormal_count": abnormal,
                "services": services,
            })
        result.append({"region": region, "azs": azs})
    return result
def _add_rds_to_topology(region_map: OrderedDict, inst: dict, verdict: str, service: str):
    """Add RDS primary and standby nodes to their respective AZs."""
    region = inst.get("region", "unknown")
    primary_az = inst.get("primary_az", "")
    standby_az = inst.get("standby_az", "")
    name = inst.get("name", "")
    inst_id = inst.get("instance_id", "")

    if region not in region_map:
        region_map[region] = OrderedDict()

    # Primary node
    if primary_az:
        if primary_az not in region_map[region]:
            region_map[region][primary_az] = {}
        az_data = region_map[region][primary_az]
        if service not in az_data:
            az_data[service] = {"running": 0, "abnormal": 0, "instances": []}
        is_normal = verdict == "ok"
        if is_normal:
            az_data[service]["running"] += 1
        else:
            az_data[service]["abnormal"] += 1
        az_data[service]["instances"].append({
            "name": name,
            "instance_id": inst_id,
            "verdict": verdict,
            "role": "master",
        })

    # Standby node
    if standby_az and standby_az != primary_az:
        if standby_az not in region_map[region]:
            region_map[region][standby_az] = {}
        az_data = region_map[region][standby_az]
        if service not in az_data:
            az_data[service] = {"running": 0, "abnormal": 0, "instances": []}
        is_normal = verdict == "ok"
        if is_normal:
            az_data[service]["running"] += 1
        else:
            az_data[service]["abnormal"] += 1
        az_data[service]["instances"].append({
            "name": name,
            "instance_id": inst_id,
            "verdict": verdict,
            "role": "standby",
        })
