import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListCustomerAccountChangeRecordsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户账户收支明细")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--balance_type", type=str, required=True, help="账户类型。BALANCE_TYPE_DEBIT：现金账户 BALANCE_TYPE_CREDIT：信用账户")
parser.add_argument("--revenue_expense_type", type=str, help="收支类型。REVENUE：收入 EXPENSE：支出")
parser.add_argument("--trade_type", type=str, help="交易类型。RECHARGE：充值 DEDEUCT-消费 REFUND-退款 RFROZEN-冻结 TRANS-转账 ADJUST-调账 BEUNBIND-解绑/关联模式切换导致的回收 EXPIRED-过期清零 BONUSCONVERT-奖励金转换 TRADE_MODE_TRANSFER-交易模式变更 DEPOSIT-保证金 BEADJUST-经销商拨款 BERETRIEVE-经销商回收。此参数不携带、携带值为空时，不作为筛选条件")
parser.add_argument("--trade_time_begin", type=str, help="查询收支明细的开始日期")
parser.add_argument("--trade_time_end", type=str, help="查询收支明细的结束日期")
parser.add_argument("--trade_id", type=str, help="交易ID/订单ID")
parser.add_argument("--payment_channel_id", type=str, help="交易渠道。可以一次查询多个，用逗号分隔。1-支付宝 2-银行转账 4-支付宝/网银 5-微信支付 6-提现 7-激励返点 10-交易模式变更 11-调账 317-银联 319-Huawei Pay 320-华为支付")
parser.add_argument("--payment_channel_no", type=str, help="交易渠道流水号")
parser.add_argument("--offset", type=int, default=0, help="偏移量")
parser.add_argument("--limit", type=int, default=50, help="每页的显示条数，默认50")
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

    request = ListCustomerAccountChangeRecordsRequest()
    request.balance_type = args.balance_type
    if args.revenue_expense_type:
        request.revenue_expense_type = args.revenue_expense_type
    if args.trade_type:
        request.trade_type = args.trade_type
    if args.trade_time_begin:
        request.trade_time_begin = args.trade_time_begin
    if args.trade_time_end:
        request.trade_time_end = args.trade_time_end
    if args.trade_id:
        request.trade_id = args.trade_id
    if args.payment_channel_id:
        request.payment_channel_id = args.payment_channel_id
    if args.payment_channel_no:
        request.payment_channel_no = args.payment_channel_no
    request.offset = args.offset
    request.limit = args.limit

    response = client.list_customer_account_change_records(request)

    total_count = getattr(response, 'total_count', 0)
    currency = getattr(response, 'currency', 'CNY')
    records = getattr(response, 'records', []) or []

    if not records:
        print(f"没有找到账户收支明细记录 (区域: {Region})")
        exit(0)

    output = "account_change_id\ttrade_detail_type\ttrade_time\ttrade_id\tchange_amount\tbalance_after_change\trevenue_expense_type\tbill_cycle\tpayment_channel_id\tpayment_channel_no\tconsume_time\taccount_name\tcloud_service_type_name\tresource_type_name\tcurrency\n"
    for record in records:
        account_change_id = getattr(record, 'account_change_id', '')
        trade_detail_type = getattr(record, 'trade_detail_type', '')
        trade_time = getattr(record, 'trade_time', '')
        trade_id = getattr(record, 'trade_id', '')
        change_amount = getattr(record, 'change_amount', '')
        balance_after_change = getattr(record, 'balance_after_change', '')
        revenue_expense_type = getattr(record, 'revenue_expense_type', '')
        bill_cycle = getattr(record, 'bill_cycle', '')
        payment_channel_id = getattr(record, 'payment_channel_id', '')
        payment_channel_no = getattr(record, 'payment_channel_no', '')
        consume_time = getattr(record, 'consume_time', '')
        account_name = getattr(record, 'account_name', '')
        cloud_service_type_name = getattr(record, 'cloud_service_type_name', '')
        resource_type_name = getattr(record, 'resource_type_name', '')
        output += f"{account_change_id}\t{trade_detail_type}\t{trade_time}\t{trade_id}\t{change_amount}\t{balance_after_change}\t{revenue_expense_type}\t{bill_cycle}\t{payment_channel_id}\t{payment_channel_no}\t{consume_time}\t{account_name}\t{cloud_service_type_name}\t{resource_type_name}\t{currency}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_customer_account_change_records 查询失败: {e}")
    exit(1)
