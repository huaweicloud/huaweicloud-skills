#!/usr/bin/env python3
"""
通过 RMS API 获取华为云所有实例，直接转换为 core_instances.json 格式。

合并了原 core_resources.py 的接口函数，
不依赖 Excel 关键资源标记表，改为通过 RMS API 自动发现实例。

流程（两阶段 + 并发 + 内存转换）：
  1. 调用 hcloud RMS CollectAllResourcesSummary 获取资源概览。
  2. 将概览与 PROVIDER_TYPES 取交集。
  3. 并发遍历每个 provider.type，调用 hcloud RMS ListAllResources，自动翻页。
  4. 内存中将 RMS 资源按 region_id 分组为 {region: [resource_id]} 格式。
  5. 写入 core_instances.json。

同时提供 load_core_regions / load_core_resources / is_core_resource 接口函数，
供 alarm.py 和 analyze_alarm.py 使用，替代原 core_resources.py 的 Excel 读取逻辑。

用法：
    python3 generate_instance.py                          # 写入 <WORKSPACE_DIR>/core_instances.json
    python3 generate_instance.py --region cn-north-4      # 指定 RMS API 入口 region
    python3 generate_instance.py --output /tmp/my.json    # 指定输出路径
"""

import json
import subprocess
import sys
import argparse
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from pathlib import Path

from workspace import WORKSPACE_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("generate-instance")

DEFAULT_OUTPUT = str(Path(WORKSPACE_DIR) / "core_instances.json")

# PROVIDER_TYPES: 指标基线支持的 provider + type 列表
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
    {"provider": "dms", "types": ["kafkas", "rabbitmqs", "reliabilitys",
                 "kafka_nodes", "rabbitmq_nodes", "rocketmq_nodes"]},
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
DEFAULT_REGION = "cn-north-4"


# 阶段一：获取资源概览

def fetch_resource_summary(region=DEFAULT_REGION):
    """调用 hcloud RMS CollectAllResourcesSummary，返回 {provider: set(types)}。"""
    cmd = ["hcloud", "RMS", "CollectAllResourcesSummary", f"--cli-region={region}"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        logger.error(f"CollectAllResourcesSummary 失败: {result.stderr.strip()}")
        raise RuntimeError(f"CollectAllResourcesSummary failed: {result.stderr.strip()}")

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.error(f"CollectAllResourcesSummary 返回非 JSON 输出 (rc=0): {e}")
        logger.error(f"stdout 前 500 字符: {result.stdout[:500]}")
        raise RuntimeError(
            "CollectAllResourcesSummary 返回了非 JSON 内容（rc=0），"
            "通常是因为当前账号缺少 rms:resources:list 权限。"
            f" region={region}。请检查 IAM 权限后重试。"
        ) from e
    existing = {}
    for entry in raw:
        provider = (entry.get("provider") or "").lower()
        if not provider:
            continue
        types_set = {t.get("type") for t in entry.get("types", []) if t.get("type")}
        if types_set:
            existing[provider] = types_set
    return existing


# 阶段二：取交集

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


# 阶段三：按 provider.type 获取实例（自动翻页）

def fetch_resources_by_type(provider, rtype, region=DEFAULT_REGION):
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
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"ListAllResources({type_filter}) 返回了非 JSON 内容（rc=0），"
                "通常是因为当前账号缺少 rms:resources:list 权限。"
                f" region={region}。请检查 IAM 权限后重试。"
            ) from e
        all_resources.extend(data.get("resources", []))
        marker = data.get("page_info", {}).get("next_marker")
        if not marker:
            break
    return all_resources


# 阶段四：并发获取

def fetch_all_instances_concurrent(provider_type_pairs, region=DEFAULT_REGION):
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


# 阶段五：内存转换 → core_instances.json 格式

def convert_to_core_instances(raw_instances):
    """将 RMS 原始资源列表按 region_id 分组为 {region: [resource_id]} 格式。

    包含所有子资源（nodes/proxies 等），不做服务级过滤——
    降噪分析需要覆盖尽可能多的告警源。
    """
    resources = defaultdict(list)
    skipped = 0
    for r in raw_instances:
        inst_id = r.get("id", "")
        region_id = r.get("region_id", "")
        if not inst_id or not region_id:
            skipped += 1
            continue
        resources[region_id].append(inst_id)

    if skipped:
        logger.info(f"跳过 {skipped} 个无 id 或无 region_id 的资源")

    return {"source": "RMS API (generate_instance.py)", "resources": dict(resources)}


# 接口函数：供 alarm.py / analyze_alarm.py 调用（替代原 core_resources.py）

def _resolve_json_path(json_path=None):
    """解析 core_instances.json 路径，默认使用 WORKSPACE_DIR 下的文件。"""
    if json_path:
        return json_path
    return str(Path(WORKSPACE_DIR) / "core_instances.json")


def load_core_regions(json_path=None):
    """从 core_instances.json 读取，返回所有 region 列表。

    Args:
        json_path: core_instances.json 路径，默认 <WORKSPACE_DIR>/core_instances.json

    Returns:
        list[str]，region 名称列表，保持出现顺序。
    """
    path = _resolve_json_path(json_path)
    if not os.path.exists(path):
        print(f"[WARN] core_instances.json 不存在: {path}")
        print("  请先运行: python3 scripts/generate_instance.py")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    regions = list(data.get("resources", {}).keys())
    print(f"Loaded {len(regions)} regions from core_instances.json: {regions}")
    return regions


def load_core_resources(json_path=None, region=None):
    """从 core_instances.json 读取核心资源 resource_id 集合。

    Args:
        json_path: core_instances.json 路径，默认 <WORKSPACE_DIR>/core_instances.json
        region: 指定区域时返回 set[str]；None 时返回 {region: set(resource_ids)} 字典。

    Returns:
        region=None → dict[str, set[str]]
        region=指定 → set[str]
    """
    path = _resolve_json_path(json_path)
    if not os.path.exists(path):
        print(f"[WARN] core_instances.json 不存在: {path}")
        print("  请先运行: python3 scripts/generate_instance.py")
        return set() if region else {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", {})

    if region is None:
        region_map = {}
        for r, ids in resources.items():
            region_map[r] = set(ids)
        total = sum(len(v) for v in region_map.values())
        print(f"Loaded {total} core resources across {len(region_map)} regions from core_instances.json")
        return region_map

    core_ids = set(resources.get(region, []))
    print(f"Loaded {len(core_ids)} core resources for region {region} from core_instances.json")
    return core_ids


def is_core_resource(alarm, core_ids):
    """判断告警的 resourceId 是否在核心资源集合中。

    仅用 resource_id 精确匹配（UUID 对 UUID）。
    core_ids 为空时返回 False（未加载 = 不标记）。
    """
    if not core_ids:
        return False
    res = alarm.get('alarm_resource') or {}
    resource_id = res.get('resourceId', '')
    return bool(resource_id and resource_id in core_ids)


# 主流程

def main():
    parser = argparse.ArgumentParser(
        description="通过 RMS API 获取华为云实例并直接生成 core_instances.json"
    )
    parser.add_argument("--region", default=DEFAULT_REGION, help="RMS API 入口 region")
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
        result = {"source": "RMS API (generate_instance.py)", "resources": {}}
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
    resources = result["resources"]
    total = sum(len(v) for v in resources.values())
    logger.info(f"转换后: {len(resources)} 个 region, {total} 个实例")

    # ⑤ 写入 core_instances.json
    output_p = Path(args.output)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"已写入 {output_p}")

    # ⑥ 打印各 region 实例数
    for r, ids in sorted(resources.items()):
        logger.info(f"  {r}: {len(ids)} 个实例")


if __name__ == "__main__":
    main()
