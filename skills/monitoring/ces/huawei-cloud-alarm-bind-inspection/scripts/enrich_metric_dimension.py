#!/usr/bin/env python3
"""
Enrich metric_dimension for core instances using hcloud ShowInstance APIs.

This script calls hcloud ShowInstance-class APIs to get instance attributes
and infers the most specific metric dimension route.

metric_dimension is a single string representing the most specific dimension,
e.g., "dcs_instance_id,dcs_cluster_redis_node" for a DCS Redis HA instance.
bind_analysis.py uses subset matching: any baseline dimension that is a subset
of metric_dimension is considered applicable to this instance.
"""

import json
import subprocess
import argparse
import logging
from pathlib import Path

sys_path_scripts = str(Path(__file__).parent)
import sys
sys.path.insert(0, sys_path_scripts)
from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enrich-metric-dimension")
logging.getLogger("httpx").setLevel(logging.WARNING)

DEFAULT_CORE = str(Path(INTERMEDIATE_DIR) / "core_instances.json")
DEFAULT_BASELINE = str(Path(INTERMEDIATE_DIR) / "indicator_baseline.json")

CORE_TO_BASELINE_SVC = {"EIP": "VPC"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def hcloud_cli(service, operation, region, **params):
    """Call hcloud CLI and return parsed JSON response, or None on failure."""
    cmd = ["hcloud", service, operation, f"--cli-region={region}"]
    for k, v in params.items():
        cmd.append(f"--{k}={v}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.warning("hcloud %s %s failed: %s",
                           service, operation, result.stderr.strip()[:200])
            return None
        # hcloud returns returncode=0 + stdout [USE_ERROR] for unsupported operations
        if "[USE_ERROR]" in result.stdout:
            logger.warning("hcloud %s %s unsupported operation: %s",
                           service, operation, result.stdout.strip()[:200])
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("hcloud %s %s timed out", service, operation)
        return None
    except Exception as e:
        logger.warning("hcloud %s %s error: %s", service, operation, e)
        return None


def get_baseline_dims(baseline_records, svc):
    """Get all baseline dimensions for a service."""
    dims = set()
    for rec in baseline_records:
        if rec.get("云服务简称") == svc:
            dim = rec.get("指标维度", "")
            if dim:
                dims.add(dim)
    return dims


def _fallback_single_or_empty(svc, inst, baseline_records, **kwargs):
    """Fallback: if baseline has exactly 1 dimension, use it; otherwise empty."""
    dims = get_baseline_dims(baseline_records, svc)
    if len(dims) == 1:
        return dims.pop()
    logger.warning("Service %s has %d dimensions, no handler, leaving empty", svc, len(dims))
    return ""


# ── B class: single-dimension handlers (no API call) ──────────────────────

def handler_single_dim(svc, inst, baseline_records, **kwargs):
    """Read the unique dimension from baseline. No API call needed."""
    dims = get_baseline_dims(baseline_records, svc)
    if len(dims) == 1:
        return dims.pop()
    if len(dims) == 0:
        logger.warning("No baseline dimensions found for %s", svc)
        return ""
    logger.warning("Service %s has %d dimensions in baseline, expected 1: %s",
                   svc, len(dims), sorted(dims))
    return ""


# ── C class: multi-dimension handlers (call hcloud ShowInstance) ───────────

def handler_dcs(svc, inst, baseline_records, **kwargs):
    """
    DCS: infer dimension from engine, cache_mode, proxy_links.
    Verified: engine=Redis, cache_mode=ha, proxy_links=None
      -> "dcs_instance_id,dcs_cluster_redis_node"
    """
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("DCS", "ShowInstance", region, instance_id=inst_id)
    if not data:
        logger.warning("DCS ShowInstance failed for %s, leaving empty", inst_id)
        return ""

    engine = data.get("engine", "")
    cache_mode = data.get("cache_mode", "")
    proxy_links = data.get("proxy_links")

    if engine == "Memcached":
        return "dcs_memcached_instance_id"

    base = "dcs_instance_id"
    if cache_mode in ("ha", "cluster", "master/standby", "replication"):
        return f"{base},dcs_cluster_redis_node"
    if proxy_links:
        return f"{base},dcs_cluster_proxy_node"
    return base


def handler_rds(svc, inst, baseline_records, **kwargs):
    """RDS: infer dimension from datastore type."""
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("RDS", "ListInstances", region, instance_id=inst_id)
    if not data:
        return ""
    instances = data.get("instances", [])
    if not instances:
        return ""
    db_type = instances[0].get("datastore", {}).get("type", "")
    type_map = {
        "MySQL": "rds_cluster_id,rds_instance_id",
        "MariaDB": "mariadb_cluster_id",
        "PostgreSQL": "postgresql_cluster_id",
        "SQLServer": "rds_cluster_sqlserver_id",
    }
    return type_map.get(db_type, "")


def handler_gemini_db(svc, inst, baseline_records, **kwargs):
    """GeminiDB (GaussDBforNoSQL): infer dimension from engine."""
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("GaussDBforNoSQL", "ListInstances", region, instance_id=inst_id)
    if not data:
        return ""
    instances = data.get("instances", [])
    if not instances:
        return ""
    engine = instances[0].get("engine", "")
    engine_map = {
        "cassandra": "cassandra_cluster_id,cassandra_node_id",
        "influxdb": "influxdb_cluster_id,influxdb_node_id",
        "mongodb": "mongodb_cluster_id,mongodb_node_id",
        "redis": "redis_cluster_id,redis_node_id",
    }
    return engine_map.get(engine, "")


def handler_waf(svc, inst, baseline_records, **kwargs):
    """WAF: dedicated (instance_id) or SaaS (waf_instance_id)."""
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("WAF", "ShowInstance", region, instance_id=inst_id)
    if data:
        return "instance_id"
    return "waf_instance_id"


def handler_nat(svc, inst, baseline_records, **kwargs):
    """NAT: public (nat_gateway_id) or private (vpc_nat_gateway_id)."""
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("NAT", "ShowNatGateway", region, nat_gateway_id=inst_id)
    if data:
        return "nat_gateway_id"
    data = hcloud_cli("NAT", "ShowPrivateNat", region, gateway_id=inst_id)
    if data:
        return "vpc_nat_gateway_id"
    return ""


def handler_dws(svc, inst, baseline_records, **kwargs):
    """DWS: cluster dimension."""
    return "dws_instance_id"


def handler_dms(svc, inst, baseline_records, **kwargs):
    """DMS: try Kafka, RabbitMQ, RocketMQ in turn."""
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("Kafka", "ShowInstance", region, instance_id=inst_id)
    if data:
        return "kafka_instance_id,kafka_broker"
    data = hcloud_cli("RabbitMQ", "ShowInstance", region, instance_id=inst_id)
    if data:
        return "rabbitmq_instance_id,rabbitmq_node"
    data = hcloud_cli("RocketMQ", "ShowInstance", region, instance_id=inst_id)
    if data:
        return "reliablemq_instance_id,reliablemq_broker"
    return ""


def handler_ecs(svc, inst, baseline_records, **kwargs):
    """ECS: main dimension is instance_id."""
    return "instance_id"


def handler_bms(svc, inst, baseline_records, **kwargs):
    """BMS: main dimension is instance_id."""
    return "instance_id"


def handler_elb(svc, inst, baseline_records, **kwargs):
    """
    ELB: ShowLoadBalancer/v3 returns listeners[] and pools[] arrays.
    Verified: listeners and pools fields present (may be empty).
    If listeners exist -> lbaas_instance_id,lbaas_listener_id
    If pools exist but no listeners -> lbaas_instance_id,lbaas_pool_id
    Otherwise -> lbaas_instance_id
    """
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("ELB", "ShowLoadBalancer/v3", region, loadbalancer_id=inst_id)
    if not data:
        return "lbaas_instance_id"
    lb = data.get("loadbalancer", {})
    listeners = lb.get("listeners", [])
    pools = lb.get("pools", [])
    if listeners:
        return "lbaas_instance_id,lbaas_listener_id"
    if pools:
        return "lbaas_instance_id,lbaas_pool_id"
    return "lbaas_instance_id"


def handler_apig(svc, inst, baseline_records, **kwargs):
    """APIG: main dimension is instance_id."""
    return "instance_id"


def handler_cph(svc, inst, baseline_records, **kwargs):
    """CPH: main dimension is instance_id."""
    return "instance_id"


def handler_dc(svc, inst, baseline_records, **kwargs):
    """DC: main dimension is direct_connect_id."""
    return "direct_connect_id"


def handler_geip(svc, inst, baseline_records, **kwargs):
    """GEIP: main dimension is geip_global_eip_id."""
    return "geip_global_eip_id"


def handler_vpn(svc, inst, baseline_records, **kwargs):
    """VPN: main dimension is evpn_gateway_id."""
    return "evpn_gateway_id"


def handler_vpc(svc, inst, baseline_records, **kwargs):
    """
    VPC/EIP: ShowPublicip/v3 returns bandwidth object.
    Verified: bandwidth field present with {id, size, share_type, ...}.
    publicip_id is the instance dimension; bandwidth_id is a separate resource.
    """
    return "publicip_id"


def handler_eg(svc, inst, baseline_records, **kwargs):
    """
    EG: ShowDetailOfChannel does NOT return subscription info.
    Verified: only returns {created_time, cross_account, description, id, name, provider_type, updated_time}.
    Sub-dimension subscription_id requires separate ListSubscriptions call (not implemented).
    """
    return "channel_id"


def handler_live(svc, inst, baseline_records, **kwargs):
    """LIVE: main dimension is domain."""
    return "domain"


# ── D class: indirect handlers ─────────────────────────────────────────────

def handler_gaussdb(svc, inst, baseline_records, **kwargs):
    """GAUSSDB: try ListGaussMySqlInstances, may not cover openGauss."""
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("GaussDB", "ListGaussMySqlInstances", region)
    if not data:
        return ""
    instances = data.get("instances", [])
    for inst_info in instances:
        if inst_info.get("instance_id") == inst_id:
            return "gaussdbv5_instance_id,gaussdbv5_node_id"
    logger.warning("GAUSSDB instance %s not found in ListGaussMySqlInstances", inst_id)
    return ""


def handler_roma(svc, inst, baseline_records, **kwargs):
    """ROMA: try ListMqsInstance for MQ sub-services."""
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("ROMA", "ListMqsInstance", region, include_internal="false")
    if not data:
        return ""
    instances = data.get("instances", [])
    for inst_info in instances:
        if inst_info.get("instance_id") == inst_id:
            inst_type = inst_info.get("type", "")
            if "kafka" in inst_type.lower():
                return "instance_id,kafka_instance_id,kafka_broker"
            elif "rabbitmq" in inst_type.lower() or "reliable" in inst_type.lower():
                return "instance_id,reliablemq_instance_id,reliablemq_broker"
            return "instance_id,kafka_instance_id"
    logger.warning("ROMA instance %s not found in ListMqsInstance", inst_id)
    return ""


# ── A class: special handling ──────────────────────────────────────────────

def handler_obs(svc, inst, baseline_records, **kwargs):
    """OBS: bucket_name is the instance dimension."""
    return "bucket_name"


# ── Handler registry ───────────────────────────────────────────────────────

SINGLE_DIM_SERVICES = {
    "CBH", "CBR", "CC", "CDM", "CDN", "CFW", "CSS", "DATAARTS_MIGRATION",
    "DDM", "DDS", "DRS", "ER", "EVS", "FunctionGraph", "GES", "HSS",
    "IES", "KMS", "MPC", "SFSTurbo", "TaurusDB", "UPredict",
}

MULTI_DIM_HANDLERS = {
    "DCS": handler_dcs,
    "RDS": handler_rds,
    "GeminiDB": handler_gemini_db,
    "WAF": handler_waf,
    "NAT": handler_nat,
    "DWS": handler_dws,
    "DMS": handler_dms,
    "ECS": handler_ecs,
    "BMS": handler_bms,
    "ELB": handler_elb,
    "APIG": handler_apig,
    "CPH": handler_cph,
    "DC": handler_dc,
    "GEIP": handler_geip,
    "VPN": handler_vpn,
    "VPC": handler_vpc,
    "EG": handler_eg,
    "LIVE": handler_live,
}

INDIRECT_HANDLERS = {
    "GAUSSDB": handler_gaussdb,
    "ROMA": handler_roma,
}

SPECIAL_HANDLERS = {
    "OBS": handler_obs,
}

UNDETERMINABLE_SERVICES = {"MaaS"}


def _get_handler(svc):
    """Get the appropriate handler for a service."""
    if svc in UNDETERMINABLE_SERVICES:
        return None
    if svc in SPECIAL_HANDLERS:
        return SPECIAL_HANDLERS[svc]
    if svc in MULTI_DIM_HANDLERS:
        return MULTI_DIM_HANDLERS[svc]
    if svc in INDIRECT_HANDLERS:
        return INDIRECT_HANDLERS[svc]
    if svc in SINGLE_DIM_SERVICES:
        return handler_single_dim
    return _fallback_single_or_empty


# ── Main enrich logic ──────────────────────────────────────────────────────

def enrich(core_path, baseline_path):
    """
    Enrich metric_dimension for all core instances using ShowInstance APIs.
    Writes metric_dimension (single string) and metric_dimension_source='showinstance'
    back to core_instances.json.
    """
    core_data = load_json(core_path)
    baseline_data = load_json(baseline_path)
    baseline_records = baseline_data.get("records", [])
    core_instances = core_data.get("instances", {})

    enriched_count = 0
    skipped_count = 0

    for core_svc, insts in core_instances.items():
        baseline_svc = CORE_TO_BASELINE_SVC.get(core_svc, core_svc)
        handler = _get_handler(baseline_svc)

        if handler is None:
            for inst in insts:
                logger.warning("Service %s is undeterminable, skipping %s",
                               baseline_svc, inst.get("instance_id", ""))
                skipped_count += 1
            continue

        for inst in insts:
            inst_id = inst.get("instance_id", "")

            if inst.get("metric_dimension_source") == "showinstance":
                logger.info("Already enriched by showinstance: %s/%s", core_svc, inst_id)
                continue

            try:
                dim = handler(baseline_svc, inst, baseline_records)
            except Exception as e:
                logger.warning("Handler for %s failed on %s: %s", baseline_svc, inst_id, e)
                dim = ""

            if dim:
                inst["metric_dimension"] = dim
                inst["metric_dimension_source"] = "showinstance"
                enriched_count += 1
                logger.info("Enriched %s/%s: metric_dimension=%s", core_svc, inst_id, dim)
            else:
                logger.warning("Could not determine metric_dimension for %s/%s",
                               core_svc, inst_id)
                skipped_count += 1

    save_json(core_data, core_path)
    logger.info("Done: enriched %d instances, skipped %d", enriched_count, skipped_count)
    return core_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enrich metric_dimension using hcloud ShowInstance APIs")
    parser.add_argument("--core", default=DEFAULT_CORE,
                        help="Path to core_instances.json")
    parser.add_argument("--baseline", default=DEFAULT_BASELINE,
                        help="Path to indicator_baseline.json")
    args = parser.parse_args()
    enrich(args.core, args.baseline)
