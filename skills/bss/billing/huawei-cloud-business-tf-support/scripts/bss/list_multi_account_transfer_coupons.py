import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListMultiAccountTransferCouponsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询企业多账户可转账代金券")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--offset", type=int, default=0, help="偏移量，默认0")
parser.add_argument("--limit", type=int, default=50, help="页面大小，默认50")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListMultiAccountTransferCouponsRequest()
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_multi_account_transfer_coupons(request)

    total_count = getattr(response, 'total_count', 0)
    avail_transfer_coupons = getattr(response, 'avail_transfer_coupons', []) or []

    output = f"总记录数\t{total_count}\n"
    
    if avail_transfer_coupons:
        output += "\n可转账代金券列表:\n"
        output += "优惠券ID\t促销计划名称\t优惠券余额\t生效时间\t失效时间\n"
        for coupon in avail_transfer_coupons:
            coupon_id = getattr(coupon, 'coupon_id', '')
            plan_name = getattr(coupon, 'plan_name', '')
            balance = getattr(coupon, 'balance', '')
            effective_time = getattr(coupon, 'effective_time', '')
            expire_time = getattr(coupon, 'expire_time', '')
            output += f"{coupon_id}\t{plan_name}\t{balance}\t{effective_time}\t{expire_time}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_multi_account_transfer_coupons 查询失败: {e}")
    exit(1)
