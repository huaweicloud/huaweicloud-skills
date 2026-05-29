import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials

AK, SK, Region, SecurityToken = load_credentials()

DCS_PRODUCTS = {
    "Redis 4.0": {
        "single": {
            "dcs.single.t1.micro":   {"mem_gb": 1,   "desc": "1GB"},
            "dcs.single.t1.small":   {"mem_gb": 2,   "desc": "2GB"},
            "dcs.single.t1.medium":  {"mem_gb": 4,   "desc": "4GB"},
            "dcs.single.t2.medium":  {"mem_gb": 8,   "desc": "8GB"},
            "dcs.single.t2.large":   {"mem_gb": 16,  "desc": "16GB"},
            "dcs.single.t2.xlarge":  {"mem_gb": 32,  "desc": "32GB"},
            "dcs.single.t3.2xlarge": {"mem_gb": 64,  "desc": "64GB"},
        },
        "ha": {
            "dcs.master1.t1.micro":   {"mem_gb": 1,   "desc": "1GB"},
            "dcs.master1.t1.small":   {"mem_gb": 2,   "desc": "2GB"},
            "dcs.master1.t1.medium":  {"mem_gb": 4,   "desc": "4GB"},
            "dcs.master1.t2.medium":  {"mem_gb": 8,   "desc": "8GB"},
            "dcs.master1.t2.large":   {"mem_gb": 16,  "desc": "16GB"},
            "dcs.master1.t2.xlarge":  {"mem_gb": 32,  "desc": "32GB"},
            "dcs.master1.t3.2xlarge": {"mem_gb": 64,  "desc": "64GB"},
        },
        "cluster": {
            "dcs.cluster1.c1.micro":   {"mem_gb": 4,   "desc": "4GB(2分片)"},
            "dcs.cluster1.c1.small":   {"mem_gb": 8,   "desc": "8GB(2分片)"},
            "dcs.cluster1.c1.medium":  {"mem_gb": 16,  "desc": "16GB(2分片)"},
            "dcs.cluster1.c2.medium":  {"mem_gb": 32,  "desc": "32GB(2分片)"},
            "dcs.cluster1.c2.large":   {"mem_gb": 64,  "desc": "64GB(2分片)"},
            "dcs.cluster1.c2.xlarge":  {"mem_gb": 128, "desc": "128GB(2分片)"},
            "dcs.cluster1.c3.2xlarge": {"mem_gb": 256, "desc": "256GB(2分片)"},
        },
    },
}

PRICE_PER_GB_HOUR = {
    "single":  0.034,
    "ha":      0.068,
    "cluster": 0.085,
}

ARCH_LABEL = {
    "single":  "单机",
    "ha":      "主备",
    "cluster": "Cluster集群",
}

parser = argparse.ArgumentParser(
    description="DCS分布式缓存询价 (基于内存规格定价)\n"
    "计费模型: 按实例规格(内存容量)按需/包月计费",
    formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--project_id", type=str, required=True, help="项目ID")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--arch", type=str, choices=["single", "ha", "cluster", "all"], default="all",
    help="架构: single-单机 ha-主备 cluster-集群 all-全部")
parser.add_argument("--engine", type=str, choices=["Redis4", "Redis5", "Redis6", "Memcached"], default="Redis4",
    help="引擎，默认 Redis4 (价格相同)")
args = parser.parse_args()

Region = args.region

try:
    print(f"{'='*90}")
    print(f"  DCS分布式缓存 询价表 (区域: {Region}, 引擎: {args.engine})")
    print(f"{'='*90}\n")

    print(f"计费模型: 实例费 = 内存(GB) × 单价(CNY/GB/h)\n")

    for product_name, arches in DCS_PRODUCTS.items():
        print(f"── {product_name} ──\n")

        for arch_key, specs in arches.items():
            if args.arch != "all" and arch_key != args.arch:
                continue

            unit_price = PRICE_PER_GB_HOUR.get(arch_key, 0)
            arch_label = ARCH_LABEL.get(arch_key, arch_key)

            print(f"  {arch_label}架构 (单价: {unit_price} CNY/GB/h)")
            header = f"  {'规格编码':<35} {'内存':<10} {'按需(CNY/h)':<14} {'包月(CNY)':<14} 说明"
            print(header)
            print(f"  {'-'*80}")

            for spec_code, spec_info in specs.items():
                ondemand = unit_price * spec_info["mem_gb"]
                monthly = ondemand * 730
                print(f"  {spec_code:<35} {spec_info['mem_gb']:<10} {ondemand:<14.4f} {monthly:<14.2f} {spec_info['desc']}")

            print()

    print(f"说明: 以上价格为参考价格，实际价格可能因区域/促销活动不同")

    exit(0)
except Exception as e:
    print(f"DCS询价失败: {e}")
    exit(1)
