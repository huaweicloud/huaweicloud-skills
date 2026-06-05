import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials

AK, SK, Region, SecurityToken = load_credentials()

LCU_UNIT_PRICE = 0.05

LCU_PERFORMANCE = {
    "L4": {"新建连接/s": 800, "并发连接": 100000, "流量GB/h": 1},
    "L7": {"新建连接/s": 25, "并发连接": 3000, "流量GB/h": 1, "规则评估/s": 1000},
}

REGION_MAP_NAMES = {
    "cn-north-1", "cn-north-4", "cn-east-2", "cn-east-3",
    "cn-south-1", "cn-south-2", "cn-southwest-2",
    "ap-southeast-1", "ap-southeast-2", "ap-southeast-3",
    "af-south-1", "sa-brazil-1", "la-north-2",
}

parser = argparse.ArgumentParser(
    description="ELB弹性负载均衡询价 (基于LCU计费模型)\n"
    "独享型=LCU费+实例费, 共享型=免费\n",
    formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--project_id", type=str, required=True, help="项目ID")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--type", type=str, choices=["L4", "L7", "elastic", "all"], default="all",
    help="规格类型: L4-网络型固定 L7-应用型固定 elastic-弹性 all-全部")
parser.add_argument("--az_count", type=int, default=1, help="可用区数量(1-3)，LCU数=单AZ×AZ数，默认1")
parser.add_argument("--show_sold_out", action="store_true", help="显示已售罄规格")
args = parser.parse_args()

Region = args.region

def get_elb_flavors():
    from huaweicloudsdkelb.v3 import ElbClient
    from huaweicloudsdkelb.v3.model import ListFlavorsRequest
    from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

    http_config = build_http_config()
    creds = BasicCredentials(AK, SK, args.project_id)
    if SecurityToken:
        creds = creds.with_security_token(SecurityToken)

    region_attr = Region.replace("-", "_").upper()
    elb_region = getattr(ElbRegion, region_attr, None)
    if not elb_region:
        print(f"不支持的区域: {Region}")
        return []

    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(creds).with_region(elb_region).build()
    request = ListFlavorsRequest()
    request.limit = 2000
    response = client.list_flavors(request)
    return getattr(response, 'flavors', []) or []

def classify_type(ftype):
    if ftype in ("L4", "L7"):
        return "fixed", ftype
    elif "elastic" in (ftype or ""):
        return "elastic", ftype
    return "other", ftype

try:
    flavors = get_elb_flavors()
    az = args.az_count

    fixed_flavors = []
    elastic_flavors = []
    for f in flavors:
        category, base_type = classify_type(f.type)
        lcu = getattr(f.info, 'lcu', None) if f.info else None
        entry = {
            "name": f.name or "(unknown)",
            "type": f.type or "",
            "category": category,
            "base_type": base_type,
            "lcu_per_az": lcu if lcu is not None else 0,
            "sold_out": f.flavor_sold_out or False,
            "info": f.info,
        }
        if category == "fixed":
            fixed_flavors.append(entry)
        elif category == "elastic":
            elastic_flavors.append(entry)

    print(f"{'='*90}")
    print(f"  ELB弹性负载均衡 询价表 (区域: {Region}, 可用区数: {az})")
    print(f"{'='*90}\n")
    print(f"计费模型: 独享型 = LCU费(0.05 CNY/LCU/h) + 实例费(仅弹性规格)")
    print(f"          共享型 = 免费\n")

    if fixed_flavors:
        print("一、独享型 - 固定规格 (按需/包月均可用)")
        print(f"   LCU费 = LCU单价({LCU_UNIT_PRICE} CNY) × 规格LCU数 × AZ数({az})\n")

        header = f"{'规格名':<38} {'协议':<6} {'LCU/AZ':<8} {'LCU合计':<8} {'按需(CNY/h)':<14} {'包月(CNY)':<14} 状态"
        print(header)
        print("-" * 100)

        filtered = sorted(fixed_flavors, key=lambda x: (x["base_type"], x["lcu_per_az"]))
        for item in filtered:
            if args.type != "all" and item["base_type"] != args.type:
                continue
            if item["sold_out"] and not args.show_sold_out:
                continue

            total_lcu = item["lcu_per_az"] * az
            ondemand_hour = LCU_UNIT_PRICE * total_lcu
            monthly = ondemand_hour * 730

            status = "售罄" if item["sold_out"] else "可售"
            print(f"{item['name']:<38} {item['base_type']:<6} {item['lcu_per_az']:<8} {total_lcu:<8} "
                  f"{ondemand_hour:<14.3f} {monthly:<14.2f} {status}")

    if elastic_flavors:
        print(f"\n二、独享型 - 弹性规格 (仅按需)")
        print(f"   费用 = 实例费(按规格) + LCU费(按实际使用量)\n")

        header = f"{'规格名':<38} {'类型':<18} {'LCU基数':<8} 状态"
        print(header)
        print("-" * 75)

        for item in sorted(elastic_flavors, key=lambda x: x["type"]):
            if args.type not in ("all", "elastic"):
                continue
            if item["sold_out"] and not args.show_sold_out:
                continue
            status = "售罄" if item["sold_out"] else "可售"
            lcu_str = str(item["lcu_per_az"]) if item["lcu_per_az"] else "按量"
            print(f"{item['name']:<38} {item['type']:<18} {lcu_str:<8} {status}")

        print(f"\n   弹性规格LCU计费 - 单位LCU性能指标:")
        for proto, perf in LCU_PERFORMANCE.items():
            items = [f"{k}={v}" for k, v in perf.items()]
            print(f"     {proto}: {', '.join(items)}")
        print(f"     LCU费 = 0.05 CNY × max(各指标折算LCU数), 不足1LCU按1计")

    print(f"\n三、共享型ELB: 免费 (性能有限，并发5万/新建5000/CPS5000)")

    total_fixed = len([f for f in fixed_flavors if not f["sold_out"]])
    total_elastic = len([e for e in elastic_flavors if not e["sold_out"]])
    print(f"\n统计: 固定规格可售{total_fixed}个, 弹性规格可售{total_elastic}个")
    print(f"实际价格请以控制台为准")

    exit(0)
except Exception as e:
    print(f"ELB询价失败: {e}")
    exit(1)
