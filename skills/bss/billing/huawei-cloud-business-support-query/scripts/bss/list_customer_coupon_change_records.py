import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListCustomerCouponChangeRecordsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户优惠券收支明细")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--balance_type", type=str, default="BALANCE_TYPE_COUPON", help="账户类型。该参数必填。BALANCE_TYPE_COUPON：代金券账户")
parser.add_argument("--revenue_expense_type", type=str, help="收支类型。REVENUE：收入 EXPENSE：支出。此参数不携带时，不作为筛选条件；此参数携带值不允许为空、空串，有枚举值校验")
parser.add_argument("--trade_type", type=str, help="交易类型。ADJUST：激活 DEDEUCT：消费 REFUND：退券 RFROZEN：冻结 EXPIRED：过期清零 COUPONADJUST：划拨 COUPONCANCEL：回收。此参数不携带时，不作为筛选条件；此参数携带值不允许为空、空串，有枚举值校验")
parser.add_argument("--trade_id", type=str, help="交易ID/订单ID。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--trade_time_begin", type=str, help="查询收支明细的开始日期，东八区时间，格式为YYYY-MM-DD。此参数不携带、携带值为空时，默认值为一年前的当天日期；此参数不允许携带值为空串")
parser.add_argument("--trade_time_end", type=str, help="查询收支明细的结束日期，东八区时间，格式为YYYY-MM-DD。此参数不携带、携带值为空时，默认值为当前日期；此参数不允许携带值为空串")
parser.add_argument("--coupon_id", type=str, help="优惠券ID。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--limit", type=int, default=50, help="每次查询的数量，默认值为50")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    request = ListCustomerCouponChangeRecordsRequest()
    request.balance_type = args.balance_type
    if args.revenue_expense_type:
        request.revenue_expense_type = args.revenue_expense_type
    if args.trade_type:
        request.trade_type = args.trade_type
    if args.trade_id:
        request.trade_id = args.trade_id
    if args.trade_time_begin:
        request.trade_time_begin = args.trade_time_begin
    if args.trade_time_end:
        request.trade_time_end = args.trade_time_end
    if args.coupon_id:
        request.coupon_id = args.coupon_id
    request.offset = args.offset
    request.limit = args.limit

    response = client.list_customer_coupon_change_records(request)

    total_count = getattr(response, 'total_count', 0)
    currency = getattr(response, 'currency', 'CNY')
    records = getattr(response, 'records', []) or []

    if not records:
        print(f"没有找到优惠券收支明细记录 (区域: {Region})")
        exit(0)

    output = "coupon_id\ttrade_detail_type\ttrade_time\ttrade_id\tchange_amount\tbalance_after_change\trevenue_expense_type\tbill_cycle\taccount_name\tcloud_service_type_name\tresource_type_name\tcurrency\n"
    for record in records:
        coupon_id = getattr(record, 'coupon_id', '')
        trade_detail_type = getattr(record, 'trade_detail_type', '')
        trade_time = getattr(record, 'trade_time', '')
        trade_id = getattr(record, 'trade_id', '')
        change_amount = getattr(record, 'change_amount', '')
        balance_after_change = getattr(record, 'balance_after_change', '')
        revenue_expense_type = getattr(record, 'revenue_expense_type', '')
        bill_cycle = getattr(record, 'bill_cycle', '')
        account_name = getattr(record, 'account_name', '')
        cloud_service_type_name = getattr(record, 'cloud_service_type_name', '')
        resource_type_name = getattr(record, 'resource_type_name', '')
        output += f"{coupon_id}\t{trade_detail_type}\t{trade_time}\t{trade_id}\t{change_amount}\t{balance_after_change}\t{revenue_expense_type}\t{bill_cycle}\t{account_name}\t{cloud_service_type_name}\t{resource_type_name}\t{currency}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_customer_coupon_change_records 查询失败: {e}")
    exit(1)
