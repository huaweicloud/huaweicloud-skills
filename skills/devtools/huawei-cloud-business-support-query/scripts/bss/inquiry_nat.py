import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials

AK, SK, Region, SecurityToken = load_credentials()

NAT_PUBLIC_SPECS = {
    "1": {"name": "小型", "snat_conn": 10000, "desc": "SNAT最大连接数1万"},
    "2": {"name": "中型", "snat_conn": 50000, "desc": "SNAT最大连接数5万"},
    "3": {"name": "大型", "snat_conn": 200000, "desc": "SNAT最大连接数20万"},
    "4": {"name": "超大型", "snat_conn": 1000000, "desc": "SNAT最大连接数100万"},
}

NAT_PUBLIC_MONTHLY = {
    "1": 306, "2": 765, "3": 1530, "4": 3825,
}

NAT_PUBLIC_PRICES = {
    "cn-north-4": {k: v / 730 for k, v in NAT_PUBLIC_MONTHLY.items()},
    "cn-north-1": {k: v / 730 for k, v in NAT_PUBLIC_MONTHLY.items()},
    "cn-east-2": {k: v / 730 for k, v in NAT_PUBLIC_MONTHLY.items()},
    "cn-east-3": {k: v / 730 for k, v in NAT_PUBLIC_MONTHLY.items()},
    "cn-south-1": {k: v / 730 for k, v in NAT_PUBLIC_MONTHLY.items()},
}

NAT_PRIVATE_SPECS = {
    "Small": {"name": "小型", "desc": "规则数上限200, 并发连接5万"},
    "Medium": {"name": "中型", "desc": "规则数上限500, 并发连接10万"},
    "Large": {"name": "大型", "desc": "规则数上限1000, 并发连接20万"},
    "Extra-large": {"name": "超大型", "desc": "规则数上限2000, 并发连接50万"},
    "Extra-xlarge": {"name": "企业型", "desc": "规则数上限5000, 并发连接100万"},
}

NAT_PRIVATE_MONTHLY = {
    "Small": 146, "Medium": 292, "Large": 584, "Extra-large": 1168, "Extra-xlarge": 2920,
}

NAT_PRIVATE_PRICES = {
    "cn-north-4": {k: v / 730 for k, v in NAT_PRIVATE_MONTHLY.items()},
}

parser = argparse.ArgumentParser(
    description="NAT网关询价 (基于官方规格定价)\n"
    "公网NAT: 按规格(SNAT连接数)按需/包月计费\n"
    "私网NAT: 按规格(规则数/并发连接数)按需/包月计费",
    formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--project_id", type=str, required=True, help="项目ID")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--type", type=str, choices=["public", "private", "all"], default="all",
    help="NAT类型: public-公网NAT private-私网NAT all-全部")
args = parser.parse_args()

Region = args.region

def get_nat_public_specs():
    from huaweicloudsdknat.v2 import NatClient
    from huaweicloudsdknat.v2.model import ListNatGatewaySpecsRequest
    from huaweicloudsdknat.v2.region.nat_region import NatRegion

    http_config = build_http_config()
    creds = BasicCredentials(AK, SK, args.project_id)
    if SecurityToken:
        creds = creds.with_security_token(SecurityToken)

    region_attr = Region.replace("-", "_").upper()
    nat_region = getattr(NatRegion, region_attr, None)
    if not nat_region:
        return []

    client = NatClient.new_builder().with_http_config(http_config).with_credentials(creds).with_region(nat_region).build()
    request = ListNatGatewaySpecsRequest()
    response = client.list_nat_gateway_specs(request)
    return getattr(response, 'specs', []) or []

def get_nat_private_specs():
    from huaweicloudsdknat.v2 import NatClient
    from huaweicloudsdknat.v2.model import ListSpecsRequest
    from huaweicloudsdknat.v2.region.nat_region import NatRegion

    http_config = build_http_config()
    creds = BasicCredentials(AK, SK, args.project_id)
    if SecurityToken:
        creds = creds.with_security_token(SecurityToken)

    region_attr = Region.replace("-", "_").upper()
    nat_region = getattr(NatRegion, region_attr, None)
    if not nat_region:
        return []

    client = NatClient.new_builder().with_http_config(http_config).with_credentials(creds).with_region(nat_region).build()
    request = ListSpecsRequest()
    response = client.list_specs(request)
    return getattr(response, 'specs', []) or []

try:
    print(f"{'='*85}")
    print(f"  NAT网关 询价表 (区域: {Region})")
    print(f"{'='*85}\n")

    if args.type in ("public", "all"):
        try:
            api_specs = get_nat_public_specs()
        except Exception:
            api_specs = []

        prices = NAT_PUBLIC_PRICES.get(Region, NAT_PUBLIC_PRICES.get("cn-north-4"))

        print("一、公网NAT网关 (按规格按需/包月计费)")
        print(f"   规格: 1=小型 2=中型 3=大型 4=超大型\n")

        header = f"{'规格编码':<10} {'规格名':<10} {'SNAT连接数':<14} {'按需(CNY/h)':<14} {'包月(CNY)':<14} 可用"
        print(header)
        print("-" * 75)

        for spec_code, spec_info in NAT_PUBLIC_SPECS.items():
            ondemand = prices.get(spec_code, 0)
            monthly = NAT_PUBLIC_MONTHLY.get(spec_code, ondemand * 730)
            available = spec_code in api_specs if api_specs else "待确认"
            avail_str = "可售" if available == True else ("不可售" if available == False else str(available))
            print(f"{spec_code:<10} {spec_info['name']:<10} {spec_info['snat_conn']:<14,} {ondemand:<14.3f} {monthly:<14.0f} {avail_str}")

        print(f"\n   说明: 公网NAT网关按规格收取网关实例费，EIP和带宽费用另计")

    if args.type in ("private", "all"):
        try:
            api_private_specs = get_nat_private_specs()
        except Exception:
            api_private_specs = []

        private_prices = NAT_PRIVATE_PRICES.get(Region, NAT_PRIVATE_PRICES.get("cn-north-4"))

        print(f"\n二、私网NAT网关 (按规格按需/包月计费)")
        print(f"   规格: Small/Medium/Large/Extra-large/Extra-xlarge\n")

        header = f"{'规格编码':<14} {'规格名':<10} {'按需(CNY/h)':<14} {'包月(CNY)':<14} 说明"
        print(header)
        print("-" * 80)

        for spec_code, spec_info in NAT_PRIVATE_SPECS.items():
            ondemand = private_prices.get(spec_code, 0)
            monthly = NAT_PRIVATE_MONTHLY.get(spec_code, ondemand * 730)
            print(f"{spec_code:<14} {spec_info['name']:<10} {ondemand:<14.3f} {monthly:<14.0f} {spec_info['desc']}")

        private_avail = set()
        for s in api_private_specs:
            code = getattr(s, 'code', '')
            if code:
                private_avail.add(code)
        if private_avail:
            print(f"\n   当前区域可用私网NAT规格: {', '.join(sorted(private_avail))}")


    exit(0)
except Exception as e:
    print(f"NAT网关询价失败: {e}")
    exit(1)
