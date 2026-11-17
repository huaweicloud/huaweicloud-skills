#!/usr/bin/env python3
"""
通过 RMS API 获取华为云所有实例，直接转换为 core_instances.json 格式。

合并了原 instances.py 的 RMS 获取逻辑和 generate_core_instance.py 的转换逻辑，
不产生 instances.json 中间文件。

流程（两阶段 + 并发 + 内存转换）：
  1. 调用 hcloud RMS CollectAllResourcesSummary 获取资源概览。
  2. 将概览与 PROVIDER_TYPES 取交集。
  3. 并发遍历每个 provider.type，调用 hcloud RMS ListAllResources，自动翻页。
  4. 内存中将 RMS 资源通过 provider_type_to_service 映射为 core_instances.json 格式。
  5. 写入 core_instances.json。

用法：
    python3 generate_instance.py                          # 写入 core_instances.json
    python3 generate_instance.py --region cn-north-4      # 指定入口 region
    python3 generate_instance.py --output /tmp/my.json    # 指定输出路径
"""

import json
import subprocess
import sys
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from pathlib import Path

from workspace import INTERMEDIATE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("generate-instance")

DEFAULT_OUTPUT = str(Path(INTERMEDIATE_DIR) / "core_instances.json")

# ──────────────────────────────────────────────────────────────────────────────
# PROVIDER_TYPES: 指标基线支持的 provider + type 列表
# ──────────────────────────────────────────────────────────────────────────────
PROVIDER_TYPES = [
    {"provider": "apig", "types": ["instances"]},
    {"provider": "bms", "types": ["servers"]},
    {"provider": "cbh", "types": ["instance"]},
    {"provider": "cbr", "types": ["vault"]},
    {"provider": "ccaas", "types": ["cloud-connections"]},
    {"provider": "cce", "types": ["clusters", "nodes"]},
    {"provider": "cci", "types": ["pods"]},
    {"provider": "cdm", "types": ["clusters"]},
    {"provider": "cdn", "types": ["domains"]},
    {"provider": "cfw", "types": ["cfw_instance"]},
    {"provider": "cph", "types": ["cloudphoneservers", "elasticcloudphones"]},
    {"provider": "csms", "types": ["secrets"]},
    {"provider": "css", "types": ["clusters"]},
    {"provider": "dayu", "types": ["instances"]},
    {"provider": "dcaas", "types": ["directConnect", "vif"]},
    {"provider": "dcs", "types": ["redis", "memcached", "node"]},
    {"provider": "ddm", "types": ["nodes"]},
    {"provider": "cnad", "types": ["instances"]},
    {"provider": "dds", "types": ["nodes"]},
    {"provider": "dli", "types": ["queues", "elasticresourcepool"]},
    {"provider": "dms", "types": ["kafkas", "rabbitmqs", "reliabilitys", "kafka_nodes", "rabbitmq_nodes", "rocketmq_nodes"]},
    {"provider": "drs", "types": ["migrationJob"]},
    {"provider": "dws", "types": ["clusters"]},
    {"provider": "ecs", "types": ["cloudservers"]},
    {"provider": "eg", "types": ["channels", "subscriptions"]},
    {"provider": "vpc", "types": ["publicips", "bandwidths", "global-eips", "internet-bandwidths"]},
    {"provider": "ges", "types": ["graphs"]},
    {"provider": "nosql", "types": ["instances", "nodes"]},
    {"provider": "hss", "types": ["agents"]},
    {"provider": "ief", "types": ["appinstances"]},
    {"provider": "iotda", "types": ["iotda", "iotda_instance", "iotda_standardinstance"]},
    {"provider": "kms", "types": ["keys"]},
    {"provider": "live", "types": ["domain"]},
    {"provider": "modelarts", "types": ["service", "model", "serviceV2"]},
    {"provider": "nat", "types": ["natGateways", "privateNatGateways"]},
    {"provider": "obs", "types": ["buckets"]},
    {"provider": "rds", "types": ["instances", "nodes", "proxies", "proxynodes"]},
    {"provider": "roma", "types": ["instances"]},
    {"provider": "sfsturbo", "types": ["shares"]},
    {"provider": "gaussdbformysql", "types": ["instance", "nodes", "proxies", "proxynodes"]},
    {"provider": "vpnaas", "types": ["vpnConnections", "vpnGateways"]},
    {"provider": "waf", "types": ["instance"]},
]

PAGE_LIMIT = 200
MAX_WORKERS = 10

# ──────────────────────────────────────────────────────────────────────────────
# provider_type_to_service: (provider, type) → 服务简称，None 表示跳过
# ──────────────────────────────────────────────────────────────────────────────

_SIMPLE_PROVIDER_TO_SERVICE = {
    "apig": "APIG", "bms": "BMS", "cbh": "CBH", "cbr": "CBR",
    "ccaas": "CC", "cce": "CCE", "cci": "CCI", "cdm": "CDM",
    "cdn": "CDN", "cfw": "CFW", "cph": "CPH", "csms": "CSMS",
    "css": "CSS", "dayu": "DATAARTS_MIGRATION", "dcaas": "DC",
    "ddm": "DDM", "cnad": "DDOS", "dds": "DDS", "dli": "DLI",
    "drs": "DRS", "dws": "DWS", "ecs": "ECS", "eg": "EG",
    "ges": "GES", "hss": "HSS", "ief": "IES", "iotda": "IoTDA",
    "kms": "KMS", "live": "LIVE", "modelarts": "Modelarts",
    "nat": "NAT", "obs": "OBS", "roma": "ROMA", "sfsturbo": "SFSTurbo",
    "vpnaas": "VPN", "waf": "WAF",
    "rds": "RDS", "nosql": "GeminiDB", "gaussdbformysql": "TaurusDB",
    "dms": "DMS", "dcs": "DCS",
}


def provider_type_to_service(provider, rtype):
    """将 RMS 的 (provider, type) 映射到下游脚本使用的服务简称，None 表示跳过。"""
    # vpc: 按 type 拆分为 EIP / GEIP / VPC
    if provider == "vpc":
        if rtype in ("publicips", "bandwidths"):
            return "EIP"
        if rtype == "global-eips":
            return "GEIP"
        if rtype == "internet-bandwidths":
            return "VPC"
        return None

    # 简单映射
    return _SIMPLE_PROVIDER_TO_SERVICE.get(provider)

# ──────────────────────────────────────────────────────────────────────────────
# 阶段一：获取资源概览
# ──────────────────────────────────────────────────────────────────────────────

def fetch_resource_summary(region="cn-north-4"):
    """调用 hcloud RMS CollectAllResourcesSummary，返回 {provider: set(types)}。"""
    cmd = ["hcloud", "RMS", "CollectAllResourcesSummary", f"--cli-region={region}"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        logger.error(f"CollectAllResourcesSummary 失败: {result.stderr.strip()}")
        sys.exit(1)

    raw = json.loads(result.stdout)
    existing = {}
    for entry in raw:
        provider = (entry.get("provider") or "").lower()
        if not provider:
            continue
        types_set = {t.get("type") for t in entry.get("types", []) if t.get("type")}
        if types_set:
            existing[provider] = types_set
    return existing


# ──────────────────────────────────────────────────────────────────────────────
# 阶段二：取交集
# ──────────────────────────────────────────────────────────────────────────────

def compute_existing_and_indicator_provider_types(existing_provider_types):
    """返回 list of (provider, type) 元组。"""
    result = []
    for pt in PROVIDER_TYPES:
        provider = pt["provider"]
        indicator_types = set(pt["types"])
        existing_types = existing_provider_types.get(provider)
        if not existing_types:
            continue
        for rtype in sorted(indicator_types & existing_types):
            result.append((provider, rtype))
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 阶段三：按 provider.type 获取实例（自动翻页）
# ──────────────────────────────────────────────────────────────────────────────

def fetch_resources_by_type(provider, rtype, region="cn-north-4"):
    """调用 hcloud RMS ListAllResources，自动翻页，返回原始资源列表。"""
    type_filter = f"{provider}.{rtype}"
    all_resources = []
    marker = None
    while True:
        cmd = [
            "hcloud", "RMS", "ListAllResources",
            f"--cli-region={region}",
            f"--type={type_filter}",
            f"--limit={PAGE_LIMIT}",
        ]
        if marker:
            cmd.append(f"--marker={marker}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"ListAllResources({type_filter}) 失败: {result.stderr.strip()}")
        data = json.loads(result.stdout)
        all_resources.extend(data.get("resources", []))
        marker = data.get("page_info", {}).get("next_marker")
        if not marker:
            break
    return all_resources


# ──────────────────────────────────────────────────────────────────────────────
# 阶段四：并发获取
# ──────────────────────────────────────────────────────────────────────────────

def fetch_all_instances_concurrent(provider_type_pairs, region="cn-north-4"):
    """并发获取所有 provider.type 的实例，返回 (all_instances, errors)。"""
    all_instances = []
    errors = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_pt = {}
        for provider, rtype in provider_type_pairs:
            future = executor.submit(fetch_resources_by_type, provider, rtype, region)
            future_to_pt[future] = (provider, rtype)
        for future in as_completed(future_to_pt):
            provider, rtype = future_to_pt[future]
            type_filter = f"{provider}.{rtype}"
            try:
                resources = future.result()
                all_instances.extend(resources)
                logger.info(f"{type_filter}: {len(resources)} 个实例")
            except Exception as e:
                errors.append(f"{type_filter}: {e}")
                logger.warning(f"{type_filter} 失败: {e}")
    return all_instances, errors


# ──────────────────────────────────────────────────────────────────────────────
# 阶段五：内存转换 → core_instances.json 格式
# ──────────────────────────────────────────────────────────────────────────────

def convert_to_core_instances(raw_instances):
    """将 RMS 原始资源列表转换为 core_instances.json 格式。"""
    instances = defaultdict(list)
    skipped = 0
    for r in raw_instances:
        provider = (r.get("provider") or "").lower()
        rtype = r.get("type", "")
        svc = provider_type_to_service(provider, rtype)
        if svc is None:
            skipped += 1
            continue
        inst_id = r.get("id", "")
        if not inst_id:
            skipped += 1
            continue
        inst = {
            "instance_id": inst_id,
            "raw_service": svc,
            "region": r.get("region_id", ""),
            "rms_type": rtype,
            "rms_name": r.get("name", ""),
        }
        instances[svc].append(inst)
    if skipped:
        logger.info(f"跳过 {skipped} 个子资源（nodes/proxies 等）")
    total_count = sum(len(v) for v in instances.values())
    return {"source": "RMS API (generate_instance.py)", "instances": dict(instances), "instance_counts": total_count}


# ──────────────────────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="通过 RMS API 获取华为云实例并直接生成 core_instances.json"
    )
    parser.add_argument("--region", default="cn-north-4", help="RMS API 入口 region")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="输出文件路径")
    args = parser.parse_args()

    # ① 获取资源概览
    logger.info(f"正在通过 RMS CollectAllResourcesSummary 获取资源概览（入口 region: {args.region}）...")
    existing = fetch_resource_summary(args.region)
    logger.info(f"概览返回 provider 数: {len(existing)}")
    for p in sorted(existing.keys()):
        logger.info(f"  {p}: {sorted(existing[p])}")

    # ② 取交集
    pairs = compute_existing_and_indicator_provider_types(existing)
    logger.info(f"交集结果: {len(pairs)} 个 provider.type")
    for provider, rtype in pairs:
        logger.info(f"  {provider}.{rtype}")

    if not pairs:
        logger.warning("没有匹配的 provider.type，输出空结果")
        result = {"source": "RMS API (generate_instance.py)", "instances": {}, "instance_counts": 0}
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"已写入空结果到 {args.output}")
        return

    # ③ 并发获取所有实例
    logger.info(f"开始并发获取（max_workers={MAX_WORKERS}）...")
    raw_instances, errors = fetch_all_instances_concurrent(pairs, args.region)
    if errors:
        logger.warning(f"{len(errors)} 个 provider.type 获取失败:")
        for e in errors:
            logger.warning(f"  {e}")

    logger.info(f"RMS 原始实例总数: {len(raw_instances)}")

    # ④ 内存转换
    result = convert_to_core_instances(raw_instances)
    instances = result["instances"]
    total = sum(len(v) for v in instances.values())
    logger.info(f"转换后: {len(instances)} 个服务, {total} 个实例")

    # ⑤ 写入 core_instances.json
    output_p = Path(args.output)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"已写入 {output_p}")

    # ⑥ 打印各服务实例数
    for svc, insts in sorted(instances.items()):
        regions = set(i["region"] for i in insts if i.get("region"))
        logger.info(f"  {svc}: {len(insts)} 个实例 (regions: {sorted(regions)})")


if __name__ == "__main__":
    main()
