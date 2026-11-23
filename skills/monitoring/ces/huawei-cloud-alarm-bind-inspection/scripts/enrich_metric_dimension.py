#!/usr/bin/env python3
"""
Enrich metric_dimension for core instances using hcloud ShowInstance APIs.

This script calls hcloud ShowInstance-class APIs to get instance attributes
and infers the most specific metric dimension route.

Dimension values are sourced from module-level constants
built at startup:
  - SINGLE_DIM_CONSTANTS: {svc: "dim"}  for services with exactly 1 dimension
  - MULTI_DIM_CONSTANTS:  {svc: ["dim1","dim2",...]}  for services with >1 dimensions
Handlers still call ShowInstance APIs to determine WHICH dimension applies,
but return values from these constants by index instead of hardcoded strings.

metric_dimension is a single string representing the most specific dimension,
e.g., "dcs_instance_id,dcs_cluster_redis_node" for a DCS Redis HA instance.
bind_analysis.py uses subset matching: any baseline dimension that is a subset
of metric_dimension is considered applicable to this instance.
"""

import argparse
import json
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
sys_path_scripts = str(Path(__file__).parent)
import sys
sys.path.insert(0, sys_path_scripts)
from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enrich-metric-dimension")
logging.getLogger("httpx").setLevel(logging.WARNING)

DEFAULT_CORE = str(Path(INTERMEDIATE_DIR) / "core_instances.json")

CORE_TO_BASELINE_SVC = {"EIP": "VPC"}

# CCE uses AOM baseline with Chinese dimension names, not in CES indicator baseline
CCE_DIM_CLUSTER = "云服务指标 CCE 集群"
CCE_DIM_NODE = "云服务指标 CCE Master节点"


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


# Dimension constants (module-level)

SINGLE_DIM_CONSTANTS = {
    "CBH": "server_id",
    "CBR": "instance_id",
    "CC": "cloud_connect_id,bwp_id,region_bandwidth_id",
    "CDM": "instance_id",
    "CDN": "domain_name",
    "CFW": "fw_instance_id",
    "CSS": "cluster_id",
    "DATAARTS_MIGRATION": "dm_di_job_id",
    "DDM": "instance_id,node_id",
    "DDS": "mongodb_instance_id,mongodb_node_id",
    "DRS": "instance_id",
    "ER": "er_instance_id",
    "EVS": "disk_name",
    "FunctionGraph": "package-functionname",
    "GES": "instance_id",
    "HSS": "host_id",
    "IES": "site_id",
    "KMS": "key_id",
    "MPC": "mpc_transcode",
    "SFSTurbo": "efs_instance_id",
    "TaurusDB": "gaussdb_mysql_instance_id,gaussdb_mysql_node_id",
    "UPredict": "service_name",
}

MULTI_DIM_CONSTANTS = {
    "APIG": ["instance_id", "instance_id,api_id", "instance_id,node_ip"],
    "BMS": ["instance_id", "instance_id,disk", "instance_id,gpu", "instance_id,mount_point"],
    "CPH": ["instance_id", "instance_id,cph_id", "instance_id,disk_name", "instance_id,gpu_index"],
    "DC": ["direct_connect_id", "history_direct_connect_id", "virtual_interface_id"],
    "DCS": ["dcs_instance_id", "dcs_instance_id,dcs_cluster_proxy2_node", "dcs_instance_id,dcs_cluster_proxy_node", "dcs_instance_id,dcs_cluster_redis_node", "dcs_memcached_instance_id"],
    "DDOS": ["instance_id,zone_ip", "package,ip"],
    "DLI": ["elastic_resource_pool_id", "queue_id"],
    "DMS": ["kafka_instance_id", "kafka_instance_id,connector_task", "kafka_instance_id,kafka_broker", "kafka_instance_id,kafka_groups", "kafka_instance_id,kafka_groups,kafka_groups_topics", "rabbitmq_instance_id", "rabbitmq_instance_id,rabbitmq_node", "rabbitmq_instance_id,rabbitmq_queue", "reliablemq_instance_id", "reliablemq_instance_id,reliablemq_broker", "reliablemq_instance_id,reliablemq_dlq_topics", "reliablemq_instance_id,reliablemq_groups"],
    "DWS": ["datastore_id", "dws_instance_id"],
    "ECS": ["instance_id", "instance_id,disk", "instance_id,mount_point", "instance_id,npu"],
    "EG": ["channel_id", "subscription_id"],
    "ELB": ["lbaas_instance_id", "lbaas_instance_id,available_zone", "lbaas_instance_id,lbaas_listener_id", "lbaas_instance_id,lbaas_pool_id"],
    "GAUSSDB": ["gaussdbv5_instance_id", "gaussdbv5_instance_id,gaussdbv5_node_id", "gaussdbv5_instance_id,gaussdbv5_node_id,gaussdbv5_component_id"],
    "GEIP": ["geip_global_eip_id", "geip_global_eip_segments_id", "geip_internet_bandwidth_id"],
    "GeminiDB": ["cassandra_cluster_id,cassandra_node_id", "influxdb_cluster_id,influxdb_node_id", "mongodb_cluster_id,mongodb_node_id", "redis_cluster_id", "redis_cluster_id,redis_node_id"],
    "LIVE": ["domain", "medialive_cdn"],
    "MaaS": ["maas_api_id", "maas_api_id,maas_key_id", "maas_service_name", "maas_service_name,maas_key_id"],
    "NAT": ["elastic_nat_gateway_id", "nat_gateway_id", "vpc_nat_gateway_id"],
    "OBS": ["bucket_name", "tenant_id"],
    "RDS": ["dbproxy_instance_id,dbproxy_node_id", "mariadb_cluster_id", "postgresql_cluster_id", "rds_cluster_id", "rds_cluster_id,rds_instance_id", "rds_cluster_sqlserver_id"],
    "ROMA": ["instance_id,apic", "instance_id,apic,api_id", "instance_id,fdi", "instance_id,fdi,node_id", "instance_id,fdi,task_id", "instance_id,kafka_instance_id", "instance_id,kafka_instance_id,kafka_broker", "instance_id,link", "instance_id,reliablemq_instance_id", "instance_id,reliablemq_instance_id,reliablemq_broker"],
    "VPC": ["bandwidth_id", "publicip_id"],
    "VPN": ["connection_id", "evpn_connection_id", "evpn_gateway_id"],
    "WAF": ["instance_id", "waf_instance_id"],
}


# B class: single-dimension handlers (no API call)

def handler_single_dim(svc, inst, **kwargs):
    """Return the unique dimension from SINGLE_DIM_CONSTANTS. No API call needed."""
    single_dim = kwargs.get("single_dim_constants", {})
    if svc in single_dim:
        return single_dim[svc]
    logger.warning("Service %s not found in SINGLE_DIM_CONSTANTS", svc)
    return ""


# DCS node-level RMS types (all lowercase, matched via strip().lower())
DCS_NODE_TYPES = {"node", "nodes", "proxy", "proxies", "proxynode", "proxynodes"}

# C class: multi-dimension handlers (call hcloud ShowInstance)
#   Return values come from MULTI_DIM_CONSTANTS[svc][index] instead of
#   hardcoded strings. Index mapping is documented per handler.

def handler_dcs(svc, inst, **kwargs):
    """
    DCS: infer dimension from rms_type and instance attributes.
    MULTI_DIM_CONSTANTS["DCS"] indices:
      [0] dcs_instance_id
      [1] dcs_instance_id,dcs_cluster_proxy2_node
      [2] dcs_instance_id,dcs_cluster_proxy_node
      [3] dcs_instance_id,dcs_cluster_redis_node
      [4] dcs_memcached_instance_id
    """
    C = kwargs["multi_dim_constants"]["DCS"]
    rms_type = inst.get("rms_type", "")
    rms_name = inst.get("rms_name", "")
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")

    # ShowInstance provides cache_mode and engine for both instance and node level
    data = hcloud_cli("DCS", "ShowInstance", region, instance_id=inst_id)
    cache_mode = data.get("cache_mode", "") if data else ""
    engine = data.get("engine", "") if data else ""

    if rms_type.strip().lower() in DCS_NODE_TYPES:
        name_lower = rms_name.lower()
        type_lower = rms_type.strip().lower()
        if "proxy" in name_lower or "proxy" in type_lower:
            # Cluster 模式开启 proxy → proxy2 节点；Proxy/HA 模式 → proxy 节点
            if cache_mode == "cluster":
                return C[1]  # dcs_instance_id,dcs_cluster_proxy2_node
            return C[2]      # dcs_instance_id,dcs_cluster_proxy_node
        return C[3]          # dcs_instance_id,dcs_cluster_redis_node

    if not data:
        logger.warning("DCS ShowInstance failed for %s, leaving empty", inst_id)
        return ""

    if engine == "Memcached":
        return C[4]  # dcs_memcached_instance_id
    return C[0]      # dcs_instance_id


def handler_rds(svc, inst, **kwargs):
    """
    RDS: infer dimension from datastore type and instance type.
    MULTI_DIM_CONSTANTS["RDS"] indices:
      [0] dbproxy_instance_id,dbproxy_node_id
      [1] mariadb_cluster_id
      [2] postgresql_cluster_id
      [3] rds_cluster_id
      [4] rds_cluster_id,rds_instance_id
      [5] rds_cluster_sqlserver_id
    """
    C = kwargs["multi_dim_constants"]["RDS"]
    rms_type = inst.get("rms_type", "")
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")

    # 数据库代理 (DB Proxy) — rms_type 含 proxy 时返回代理维度
    if "proxy" in rms_type.lower():
        return C[0]  # dbproxy_instance_id,dbproxy_node_id

    data = hcloud_cli("RDS", "ListInstances", region, id=inst_id)
    if not data:
        return ""
    instances = data.get("instances", [])
    if not instances:
        return ""
    db_type = instances[0].get("datastore", {}).get("type", "")

    if db_type == "MySQL":
        if rms_type.strip().lower() == "nodes":
            return C[4]  # rds_cluster_id,rds_instance_id
        return C[3]      # rds_cluster_id

    type_map = {
        "MariaDB": C[1],
        "PostgreSQL": C[2],
        "SQLServer": C[5],
    }
    return type_map.get(db_type, "")


def handler_gemini_db(svc, inst, **kwargs):
    """
    GeminiDB (GaussDBforNoSQL): infer dimension from engine.
    MULTI_DIM_CONSTANTS["GeminiDB"] indices:
      [0] cassandra_cluster_id,cassandra_node_id
      [1] influxdb_cluster_id,influxdb_node_id
      [2] mongodb_cluster_id,mongodb_node_id
      [3] redis_cluster_id
      [4] redis_cluster_id,redis_node_id
    """
    C = kwargs["multi_dim_constants"]["GeminiDB"]
    rms_type = inst.get("rms_type", "")
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    rms_name = inst.get("rms_name", "")

    # Bug fix: API param is --id, not --instance_id
    # For instance-level IDs (rms_type=="instances"), query directly.
    # For node-level IDs (rms_type=="nodes"), --id won't match; list all
    # and find the parent instance by name prefix (rms_name starts with instance name).
    if rms_type.strip().lower() == "nodes":
        data = hcloud_cli("GaussDBforNoSQL", "ListInstances", region)
        if not data:
            return ""
        instances = data.get("instances", [])
        engine = ""
        for db_inst in instances:
            db_name = db_inst.get("name", "")
            if db_name and rms_name.startswith(db_name):
                engine = db_inst.get("engine", "")
                break
        if not engine and instances:
            # fallback: if only one instance, assume it's the parent
            if len(instances) == 1:
                engine = instances[0].get("engine", "")
    else:
        data = hcloud_cli("GaussDBforNoSQL", "ListInstances", region, id=inst_id)
        if not data:
            return ""
        instances = data.get("instances", [])
        if not instances:
            return ""
        engine = instances[0].get("engine", "")

    if not engine:
        return ""

    # Redis and rocksDB (Redis-compatible) have instance-level [3] and node-level [4]
    if engine in ("redis", "rocksDB"):
        if rms_type.strip().lower() == "nodes":
            return C[4]  # redis_cluster_id,redis_node_id
        return C[3]      # redis_cluster_id

    engine_map = {
        "cassandra": C[0],
        "influxdb": C[1],
        "mongodb": C[2],
    }
    return engine_map.get(engine, "")


def handler_waf(svc, inst, **kwargs):
    """
    WAF: dedicated (instance_id) or SaaS (waf_instance_id).
    MULTI_DIM_CONSTANTS["WAF"] indices: [0] instance_id, [1] waf_instance_id
    """
    C = kwargs["multi_dim_constants"]["WAF"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("WAF", "ShowInstance", region, instance_id=inst_id)
    if data:
        return C[0]
    return C[1]


def handler_nat(svc, inst, **kwargs):
    """
    NAT: public (nat_gateway_id) or private (vpc_nat_gateway_id).
    MULTI_DIM_CONSTANTS["NAT"] indices:
      [0] elastic_nat_gateway_id, [1] nat_gateway_id, [2] vpc_nat_gateway_id

    elastic_nat_gateway_id 是公网 NAT 网关的旧版维度名，仅 1 个指标
    (端口分配失败丢包数) 使用；nat_gateway_id 有 8 个指标。
    两者指向同一资源，ShowNatGateway API 无 type 字段区分。
    通过 rms_type/rms_name 含 "elastic" 判断，否则返回 nat_gateway_id。
    """
    C = kwargs["multi_dim_constants"]["NAT"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    rms_type = inst.get("rms_type", "")
    rms_name = inst.get("rms_name", "")

    data = hcloud_cli("NAT", "ShowNatGateway", region, nat_gateway_id=inst_id)
    if data:
        # 检查 rms_type/rms_name 或响应中的 type 字段是否标记为 elastic
        gw = data.get("nat_gateway", data)
        gw_type = gw.get("type", "") or gw.get("kind", "")
        if "elastic" in rms_type.lower() or "elastic" in rms_name.lower() or "elastic" in gw_type.lower():
            return C[0]  # elastic_nat_gateway_id
        return C[1]      # nat_gateway_id
    data = hcloud_cli("NAT", "ShowPrivateNat", region, gateway_id=inst_id)
    if data:
        return C[2]      # vpc_nat_gateway_id
    return ""


def handler_dws(svc, inst, **kwargs):
    """
    DWS: build dimension union from cluster details.
    MULTI_DIM_CONSTANTS["DWS"] indices: [0] datastore_id, [1] dws_instance_id
    """
    C = kwargs["multi_dim_constants"]["DWS"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    parts = ["dws_instance_id"]
    data = hcloud_cli("DWS", "ListClusterDetails", region, cluster_id=inst_id)
    if data:
        cluster = data.get("cluster", data)
        if cluster.get("datastore", {}):
            parts.append("datastore_id")
    return ",".join(parts)


def handler_dms(svc, inst, **kwargs):
    """
    DMS: build dimension union from rms_type + sub-resource APIs.
    MULTI_DIM_CONSTANTS["DMS"] indices:
      [0] kafka_instance_id
      [1] kafka_instance_id,connector_task
      [2] kafka_instance_id,kafka_broker
      [3] kafka_instance_id,kafka_groups
      [4] kafka_instance_id,kafka_groups,kafka_groups_topics
      [5] rabbitmq_instance_id
      [6] rabbitmq_instance_id,rabbitmq_node
      [7] rabbitmq_instance_id,rabbitmq_queue
      [8] reliablemq_instance_id
      [9] reliablemq_instance_id,reliablemq_broker
      [10] reliablemq_instance_id,reliablemq_dlq_topics
      [11] reliablemq_instance_id,reliablemq_groups
    """
    C = kwargs["multi_dim_constants"]["DMS"]
    rms_type = inst.get("rms_type", "")
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")

    if rms_type in ("kafkas", "kafka_nodes"):
        parts = ["kafka_instance_id"]
        if rms_type == "kafka_nodes":
            parts.append("kafka_broker")
        data = hcloud_cli("Kafka", "ListConnectorTasks", region, instance_id=inst_id)
        if data and data.get("tasks", []):
            parts.append("connector_task")
        data = hcloud_cli("Kafka", "ListInstanceConsumerGroups", region, instance_id=inst_id)
        if data and data.get("groups", []):
            parts.append("kafka_groups")
        data = hcloud_cli("Kafka", "ListInstanceTopics", region, instance_id=inst_id)
        if data and data.get("topics", []):
            parts.append("kafka_groups_topics")
        return ",".join(parts)

    if rms_type in ("rabbitmqs", "rabbitmq_nodes"):
        parts = ["rabbitmq_instance_id"]
        if rms_type == "rabbitmq_nodes":
            parts.append("rabbitmq_node")
        data = hcloud_cli("RabbitMQ", "ListInstanceQueues", region, instance_id=inst_id)
        if data and data.get("queues", []):
            parts.append("rabbitmq_queue")
        return ",".join(parts)

    if rms_type in ("reliabilitys", "rocketmq_nodes"):
        parts = ["reliablemq_instance_id"]
        if rms_type == "rocketmq_nodes":
            parts.append("reliablemq_broker")
        data = hcloud_cli("RocketMQ", "ListInstanceConsumerGroups", region, instance_id=inst_id)
        if data and data.get("groups", []):
            parts.append("reliablemq_groups")
            parts.append("reliablemq_dlq_topics")
        return ",".join(parts)

    logger.warning("DMS unknown rms_type: %s", rms_type)
    return ""



def handler_ecs(svc, inst, **kwargs):
    """
    ECS: return the most specific single dimension route.
    MULTI_DIM_CONSTANTS["ECS"] indices:
      [0] instance_id, [1] instance_id,disk,
      [2] instance_id,mount_point, [3] instance_id,npu
    ShowServer → volumes_attached (disk), flavor.asic_accelerators (npu).
    Returns ONE dimension, not a union:
      - NPU present      → instance_id,npu
      - volumes present  → instance_id,mount_point
      - otherwise        → instance_id
    """
    C = kwargs["multi_dim_constants"]["ECS"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    data = hcloud_cli("ECS", "ShowServer", region, server_id=inst_id)
    if data:
        server = data.get("server", data)
        flavor = server.get("flavor", {})
        asics = flavor.get("asic_accelerators", [])
        if asics:
            return "instance_id,npu"
        volumes = server.get("os-extended-volumes:volumes_attached", [])
        if volumes:
            return "instance_id,mount_point"
    return "instance_id"


def handler_bms(svc, inst, **kwargs):
    """
    BMS: build dimension union from sub-resources.
    MULTI_DIM_CONSTANTS["BMS"] indices:
      [0] instance_id, [1] instance_id,disk,
      [2] instance_id,gpu, [3] instance_id,mount_point
    ShowBaremetalServerVolumeInfo → disk list.
    """
    C = kwargs["multi_dim_constants"]["BMS"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    rms_name = inst.get("rms_name", "")
    parts = ["instance_id"]
    data = hcloud_cli("BMS", "ShowBaremetalServerVolumeInfo", region, server_id=inst_id)
    if data:
        volumes = data.get("volume_attachments", data.get("volumes", []))
        if volumes:
            parts.append("disk")
            parts.append("mount_point")
    if "gpu" in rms_name.lower():
        parts.append("gpu")
    return ",".join(parts)


def handler_elb(svc, inst, **kwargs):
    """
    ELB: build dimension union from ShowLoadBalancer/v3.
    MULTI_DIM_CONSTANTS["ELB"] indices:
      [0] lbaas_instance_id
      [1] lbaas_instance_id,available_zone
      [2] lbaas_instance_id,lbaas_listener_id
      [3] lbaas_instance_id,lbaas_pool_id
    Returns union covering all applicable sub-resources via subset matching.
    """
    C = kwargs["multi_dim_constants"]["ELB"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    parts = ["lbaas_instance_id"]
    data = hcloud_cli("ELB", "ShowLoadBalancer/v3", region, loadbalancer_id=inst_id)
    if data:
        lb = data.get("loadbalancer", {})
        if lb.get("availability_zone_list", []):
            parts.append("available_zone")
        if lb.get("listeners", []):
            parts.append("lbaas_listener_id")
        if lb.get("pools", []):
            parts.append("lbaas_pool_id")
    return ",".join(parts)


def handler_apig(svc, inst, **kwargs):
    """
    APIG: build dimension union from sub-resources.
    MULTI_DIM_CONSTANTS["APIG"] indices:
      [0] instance_id, [1] instance_id,api_id, [2] instance_id,node_ip
    """
    C = kwargs["multi_dim_constants"]["APIG"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    parts = ["instance_id"]
    data = hcloud_cli("APIG", "ListApisV2", region, instance_id=inst_id, limit="1")
    if data and data.get("size", 0) > 0:
        parts.append("api_id")
    data = hcloud_cli("APIG", "ShowInstanceV2", region, instance_id=inst_id)
    if data and data.get("node_num", 0) > 0:
        parts.append("node_ip")
    return ",".join(parts)


def handler_cph(svc, inst, **kwargs):
    """
    CPH: build dimension union from rms_type + sub-resources.
    MULTI_DIM_CONSTANTS["CPH"] indices:
      [0] instance_id, [1] instance_id,cph_id,
      [2] instance_id,disk_name, [3] instance_id,gpu_index
    """
    C = kwargs["multi_dim_constants"]["CPH"]
    rms_type = inst.get("rms_type", "")
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    parts = ["instance_id"]
    if rms_type == "elasticcloudphones":
        parts.append("cph_id")
    data = hcloud_cli("CPH", "ListCloudPhones", region, server_id=inst_id, limit="1")
    if data:
        phones = data.get("phones", [])
        if phones:
            parts.append("disk_name")
            parts.append("gpu_index")
    return ",".join(parts)


def handler_dc(svc, inst, **kwargs):
    """
    DC: use rms_type to distinguish direct connect vs virtual interface.
    MULTI_DIM_CONSTANTS["DC"] indices:
      [0] direct_connect_id, [2] virtual_interface_id
    rms_type: directConnect→C[0], vif→C[2]
    history_direct_connect_id [1] has no separate RMS type — by design.
    """
    C = kwargs["multi_dim_constants"]["DC"]
    rms_type = inst.get("rms_type", "")
    if rms_type == "vif":
        return C[2]  # virtual_interface_id
    return C[0]      # direct_connect_id


def handler_geip(svc, inst, **kwargs):
    """
    GEIP: build dimension union from global EIP details.
    MULTI_DIM_CONSTANTS["GEIP"] indices:
      [0] geip_global_eip_id
      [1] geip_global_eip_segments_id
      [2] geip_internet_bandwidth_id
    ShowGlobalEip → segment and bandwidth info.
    """
    C = kwargs["multi_dim_constants"]["GEIP"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    parts = ["geip_global_eip_id"]
    data = hcloud_cli("GEIP", "ShowGlobalEip", region, global_eip_id=inst_id)
    if data:
        if data.get("segments", []):
            parts.append("geip_global_eip_segments_id")
        if data.get("internet_bandwidth_id", ""):
            parts.append("geip_internet_bandwidth_id")
    return ",".join(parts)


def handler_vpn(svc, inst, **kwargs):
    """
    VPN: use rms_type to distinguish gateway vs connection.
    MULTI_DIM_CONSTANTS["VPN"] indices:
      [1] evpn_connection_id, [2] evpn_gateway_id
    rms_type: vpnGateways→C[2], vpnConnections→C[1]
    connection_id [0] is legacy dim — by design not covered.
    """
    C = kwargs["multi_dim_constants"]["VPN"]
    rms_type = inst.get("rms_type", "")
    if rms_type == "vpnConnections":
        return C[1]  # evpn_connection_id
    return C[2]      # evpn_gateway_id


def handler_vpc(svc, inst, **kwargs):
    """
    VPC/EIP: use rms_type to distinguish publicip vs bandwidth.
    MULTI_DIM_CONSTANTS["VPC"] indices: [0] bandwidth_id, [1] publicip_id
    rms_type: publicips→C[1], bandwidths→C[0], internet-bandwidths→C[0]
    """
    C = kwargs["multi_dim_constants"]["VPC"]
    rms_type = inst.get("rms_type", "")
    if rms_type == "publicips":
        return C[1]  # publicip_id
    if rms_type in ("bandwidths", "internet-bandwidths"):
        return C[0]  # bandwidth_id
    return C[1]  # default to publicip_id


def handler_eg(svc, inst, **kwargs):
    """
    EG: use rms_type to distinguish channel vs subscription.
    MULTI_DIM_CONSTANTS["EG"] indices: [0] channel_id, [1] subscription_id
    rms_type: channels→C[0], subscriptions→C[1]
    """
    C = kwargs["multi_dim_constants"]["EG"]
    rms_type = inst.get("rms_type", "")
    if rms_type == "subscriptions":
        return C[1]  # subscription_id
    return C[0]      # channel_id


def handler_live(svc, inst, **kwargs):
    """
    LIVE: build dimension union from domain info.
    MULTI_DIM_CONSTANTS["LIVE"] indices: [0] domain, [1] medialive_cdn
    """
    C = kwargs["multi_dim_constants"]["LIVE"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    parts = ["domain"]
    data = hcloud_cli("Live", "ShowDomain", region, domain=inst_id)
    if data:
        domain_info = data.get("domain", data)
        if domain_info.get("cdn_type", "") or domain_info.get("push_domain", ""):
            parts.append("medialive_cdn")
    return ",".join(parts)


def handler_dli(svc, inst, **kwargs):
    """
    DLI: use rms_type to distinguish queue vs elastic resource pool.
    MULTI_DIM_CONSTANTS["DLI"] indices:
      [0] elastic_resource_pool_id, [1] queue_id
    rms_type: queues→C[1], elasticresourcepool→C[0]
    """
    C = kwargs["multi_dim_constants"]["DLI"]
    rms_type = inst.get("rms_type", "")
    if rms_type == "elasticresourcepool":
        return C[0]  # elastic_resource_pool_id
    return C[1]      # queue_id


def handler_ddos(svc, inst, **kwargs):
    """
    DDOS: build dimension union.
    MULTI_DIM_CONSTANTS["DDOS"] indices:
      [0] instance_id,zone_ip, [1] package,ip
    ShowInstance → check for package/IP info.
    """
    C = kwargs["multi_dim_constants"]["DDOS"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")
    parts = ["instance_id", "zone_ip"]
    data = hcloud_cli("CNAD", "ShowInstance", region, instance_id=inst_id)
    if data:
        if data.get("package", {}) or data.get("ip", ""):
            parts.append("package")
            parts.append("ip")
    return ",".join(parts)


def handler_cce(svc, inst, **kwargs):
    """
    CCE: AOM 基线维度为中文，按 rms_type 映射。
    不在 CES 指标基线中，使用模块级常量。
    """
    rms_type = inst.get("rms_type", "")
    if rms_type.strip().lower() == "nodes":
        return CCE_DIM_NODE
    return CCE_DIM_CLUSTER


def handler_obs(svc, inst, **kwargs):
    """
    OBS: each instance is a bucket; metric_dimension = bucket_name.
    MULTI_DIM_CONSTANTS["OBS"] indices: [0] bucket_name, [1] tenant_id
    tenant_id is tenant-level (aggregate, not per-instance), so only
    bucket_name is used as the instance's metric_dimension.
    """
    C = kwargs["multi_dim_constants"]["OBS"]
    return "bucket_name"


# D class: indirect handlers

def handler_gaussdb(svc, inst, **kwargs):
    """
    GAUSSDB (GaussDBforopenGauss/V5): use rms_type to distinguish level.
    MULTI_DIM_CONSTANTS["GAUSSDB"] indices:
      [0] gaussdbv5_instance_id
      [1] gaussdbv5_instance_id,gaussdbv5_node_id
      [2] gaussdbv5_instance_id,gaussdbv5_node_id,gaussdbv5_component_id

    rms_type values based on RMS provider types (gaussdbformysql uses
    instance/nodes/proxies/proxynodes; GAUSSDB/openGauss likely similar).
    NOTE: GAUSSDB is not in PROVIDER_TYPES — rms_type values are assumed.
    Falls back to GaussDBforopenGauss ListInstances API.
    """
    C = kwargs["multi_dim_constants"]["GAUSSDB"]
    rms_type = inst.get("rms_type", "")
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")

    # rms_type 映射（依据 gaussdbformysql provider 的 type 命名惯例）
    if rms_type in ("instance", "instances"):
        return C[0]  # gaussdbv5_instance_id
    if rms_type in ("nodes", "node"):
        return C[1]  # gaussdbv5_instance_id,gaussdbv5_node_id
    if rms_type in ("components", "component"):
        return C[2]  # gaussdbv5_instance_id,gaussdbv5_node_id,gaussdbv5_component_id

    # Fallback: call GaussDBforopenGauss ListInstances
    data = hcloud_cli("GaussDBforopenGauss", "ListInstances", region)
    if not data:
        return ""
    instances = data.get("instances", [])
    for inst_info in instances:
        if inst_info.get("id", "") == inst_id:
            return C[0]  # instance level
    logger.warning("GAUSSDB instance %s not found in GaussDBforopenGauss ListInstances", inst_id)
    return ""


def handler_roma(svc, inst, **kwargs):
    """
    ROMA: determine sub-service (MQ/APIC/FDI/Link) from instance type.
    MULTI_DIM_CONSTANTS["ROMA"] indices:
      [0] instance_id,apic
      [2] instance_id,fdi
      [5] instance_id,kafka_instance_id
      [6] instance_id,kafka_instance_id,kafka_broker
      [7] instance_id,link
      [8] instance_id,reliablemq_instance_id
      [9] instance_id,reliablemq_instance_id,reliablemq_broker

    Step 1: ListMqsInstance for MQ instances (kafka/rabbitmq/rocketmq).
    Step 2: CheckRomaInstanceListV2 for non-MQ instances (apic/fdi/link).
    NOTE: type values for APIC/FDI/Link are assumed from product naming,
    need verification with real ROMA instances.
    """
    C = kwargs["multi_dim_constants"]["ROMA"]
    region = inst.get("region", "")
    inst_id = inst.get("instance_id", "")

    # Step 1: MQ instances
    data = hcloud_cli("ROMA", "ListMqsInstance", region, include_internal="false")
    if data:
        for inst_info in data.get("instances", []):
            if inst_info.get("instance_id") == inst_id:
                inst_type = inst_info.get("type", "")
                if "kafka" in inst_type.lower():
                    return C[6]  # instance_id,kafka_instance_id,kafka_broker
                if "rabbitmq" in inst_type.lower() or "reliable" in inst_type.lower():
                    return C[9]  # instance_id,reliablemq_instance_id,reliablemq_broker
                return C[5]      # instance_id,kafka_instance_id

    # Step 2: non-MQ instances (APIC/FDI/Link)
    data = hcloud_cli("ROMA", "CheckRomaInstanceListV2", region)
    if data:
        for inst_info in data.get("instances", []):
            if inst_info.get("id", "") == inst_id:
                inst_type = inst_info.get("type", "").lower()
                if "apic" in inst_type:
                    return C[0]  # instance_id,apic
                if "fdi" in inst_type:
                    return C[2]  # instance_id,fdi
                if "link" in inst_type:
                    return C[7]  # instance_id,link
                logger.warning("ROMA instance %s has unknown type: %s", inst_id, inst_type)
                return ""

    logger.warning("ROMA instance %s not found in ListMqsInstance or CheckRomaInstanceListV2", inst_id)
    return ""


# Handler registry

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
    "OBS": handler_obs,
    "CCE": handler_cce,
    "DLI": handler_dli,
    "DDOS": handler_ddos,
    "GAUSSDB": handler_gaussdb,
    "ROMA": handler_roma,
}

# Services in baseline with no handler (multi-dim but can't determine which)
UNDETERMINABLE_SERVICES = {"MaaS"}


def _get_handler(svc):
    """Get the appropriate handler for a service."""
    if svc in UNDETERMINABLE_SERVICES:
        return None
    if svc in MULTI_DIM_HANDLERS:
        return MULTI_DIM_HANDLERS[svc]
    if svc in SINGLE_DIM_CONSTANTS:
        return handler_single_dim
    if svc in MULTI_DIM_CONSTANTS:
        # Multi-dim service without a handler — can't determine which dimension
        logger.warning("Service %s has %d dimensions but no handler, leaving empty",
                       svc, len(MULTI_DIM_CONSTANTS[svc]))
        return None
    logger.warning("Service %s not found in baseline constants", svc)
    return None


# Main enrich logic

def enrich(core_path, max_workers=10):
    """
    Enrich metric_dimension for all core instances using ShowInstance APIs.
    Dimension values are sourced from module-level constants and hcloud ShowInstance APIs.
    Writes metric_dimension (single string) and metric_dimension_source='baseline_constant'
    back to core_instances.json.

    Uses ThreadPoolExecutor for concurrent API calls (default 10 workers).
    Each instance is independent — handler reads only its own attributes and
    hcloud_cli spawns a separate subprocess per call, so parallelism is safe.
    """
    core_data = load_json(core_path)
    core_instances = core_data.get("instances", {})

    enriched_count = 0
    skipped_count = 0

    # Phase 1: collect tasks
    # Each task = (core_svc, baseline_svc, handler, inst) that needs a handler call.
    # Undeterminable services and already-enriched instances are handled inline.
    tasks = []

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

            if inst.get("metric_dimension_source") == "baseline_constant":
                logger.info("Already enriched: %s/%s", core_svc, inst_id)
                continue

            tasks.append((core_svc, baseline_svc, handler, inst))

    logger.info("Total tasks to process: %d (max_workers=%d)", len(tasks), max_workers)

    # Phase 2: concurrent execution
    # Worker function — returns result; inst dict is updated by the main thread.
    def _worker(task):
        core_svc, baseline_svc, handler, inst = task
        inst_id = inst.get("instance_id", "")
        try:
            dim = handler(baseline_svc, inst,
                          single_dim_constants=SINGLE_DIM_CONSTANTS,
                          multi_dim_constants=MULTI_DIM_CONSTANTS)
        except Exception as e:
            logger.warning("Handler for %s failed on %s: %s", baseline_svc, inst_id, e)
            dim = ""
        return (core_svc, inst_id, dim, inst)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_worker, t): t for t in tasks}
        for future in as_completed(futures):
            core_svc, inst_id, dim, inst = future.result()
            if dim:
                inst["metric_dimension"] = dim
                inst["metric_dimension_source"] = "baseline_constant"
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
    args = parser.parse_args()
    enrich(args.core)
