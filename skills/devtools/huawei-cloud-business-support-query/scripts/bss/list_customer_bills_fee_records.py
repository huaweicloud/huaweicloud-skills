import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListCustomerBillsFeeRecordsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户账单费用记录")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文 en_US：英文。默认为zh_CN")
parser.add_argument("--bill_cycle", type=str, required=True, help="查询的流水账单所在账期，东八区时间，格式为YYYY-MM")
parser.add_argument("--provider_type", type=int, help="服务商。1：华为云 2：云商店。为空时查询包含华为云和云商店在内的全部服务商。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--service_type_code", type=str, help="云服务类型编码，例如OBS的云服务类型编码为hws.service.type.obs。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--resource_type_code", type=str, help="资源类型编码，例如ECS的VM为hws.resource.type.vm。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--region_code", type=str, help="云服务区编码，例如cn-north-1。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--charging_mode", type=int, help="计费模式。1-包年/包月 3-按需 10-预留实例 11-节省计划。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--bill_type", type=int, help="账单类型。1-消费-新购 2-消费-续订 3-消费-变更 4-退款-退订 5-消费-使用 8-消费-自动续订 9-调账-补偿 14-消费-服务支持计划月末扣费 16-调账-扣费 18-消费-按月付费 20-退款-变更 23-消费-节省计划抵扣 24-退款-包年/包月转按需 25-消费-抹零补扣 103-消费-按年付费。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--trade_id", type=str, help="订单ID或交易ID。账单类型为1、2、3、4和8时此处为订单ID，账单类型为其它场景时此处为交易ID。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目标识（企业项目ID）。default项目对应ID：0，未归集项目对应ID：null。此参数不携带或携带值为空时，不作为筛选条件，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--include_zero_record", type=bool, help="是否包含应付金额为0的记录。true-包含 false-不包含。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--status", type=int, help="支付状态。1-已支付 2-未结清 3-未出账。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--method", type=str, default="all", help="查询流水账单的方式。oneself：客户自己 sub_customer：企业子客户 all：客户自己和企业子客户。此参数不携带或携带值为空时，默认值为all")
parser.add_argument("--sub_customer_id", type=str, help="企业子账号ID。如果method取值不为sub_customer，则该参数无效；如果method取值为sub_customer，则该参数不能为空")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--limit", type=int, default=50, help="页面大小。默认值为50")
parser.add_argument("--bill_date_begin", type=str, help="查询的流水账单的开始日期，东八区时间，格式为YYYY-MM-DD。必须和bill_cycle在同一个月，且与bill_date_end同时出现。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--bill_date_end", type=str, help="查询的流水账单的结束日期，东八区时间，格式为YYYY-MM-DD。必须和bill_cycle在同一个月，且与bill_date_begin同时出现。此参数不携带或携带值为空时，不作为筛选条件")
args = parser.parse_args()

if args.method == "sub_customer" and not args.sub_customer_id:
    parser.error("当 method=sub_customer 时，必须指定 sub_customer_id")

if (args.bill_date_begin is not None) != (args.bill_date_end is not None):
    parser.error("bill_date_begin 和 bill_date_end 必须同时指定或同时不指定")

if args.region is not None:
    Region = args.region

try:
    request = ListCustomerBillsFeeRecordsRequest()
    request.x_language = args.x_language
    request.bill_cycle = args.bill_cycle
    if args.provider_type is not None:
        request.provider_type = args.provider_type
    if args.service_type_code:
        request.service_type_code = args.service_type_code
    if args.resource_type_code:
        request.resource_type_code = args.resource_type_code
    if args.region_code:
        request.region_code = args.region_code
    if args.charging_mode is not None:
        request.charging_mode = args.charging_mode
    if args.bill_type is not None:
        request.bill_type = args.bill_type
    if args.trade_id:
        request.trade_id = args.trade_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.include_zero_record is not None:
        request.include_zero_record = args.include_zero_record
    if args.status is not None:
        request.status = args.status
    request.method = args.method
    if args.sub_customer_id:
        request.sub_customer_id = args.sub_customer_id
    request.offset = args.offset
    request.limit = args.limit
    if args.bill_date_begin:
        request.bill_date_begin = args.bill_date_begin
    if args.bill_date_end:
        request.bill_date_end = args.bill_date_end

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_customer_bills_fee_records(request)

    total_count = getattr(response, 'total_count', 0)
    records = getattr(response, 'records', []) or []
    currency = getattr(response, 'currency', '')

    output = f"总记录数\t{total_count}\t币种\t{currency}\n"
    if records:
        output += "\n费用记录列表:\n"
        output += "账期\t客户ID\t云服务类型编码\t云服务类型名称\t资源类型编码\t资源类型名称\t区域编码\t区域名称\t企业项目ID\t企业项目名称\t计费模式\t消费时间\t交易时间\t服务商\t交易ID\t账单类型\t支付状态\t官网价\t折扣金额\t抹零金额\t应付金额\t现金支付\t信用额度支付\t代金券支付\t现金券支付\t储值卡支付\t奖励金支付\t欠费金额\t欠费核销金额\t客户登录名称\n"
        for record in records:
            bill_cycle = getattr(record, 'bill_cycle', '')
            customer_id = getattr(record, 'customer_id', '')
            service_type_code = getattr(record, 'service_type_code', '')
            service_type_name = getattr(record, 'service_type_name', '')
            resource_type_code = getattr(record, 'resource_type_code', '')
            resource_type_name = getattr(record, 'resource_type_name', '')
            region_code = getattr(record, 'region_code', '')
            region_name = getattr(record, 'region_name', '')
            enterprise_project_id = getattr(record, 'enterprise_project_id', '')
            enterprise_project_name = getattr(record, 'enterprise_project_name', '')
            charging_mode = getattr(record, 'charging_mode', '')
            consume_time = getattr(record, 'consume_time', '')
            trade_time = getattr(record, 'trade_time', '')
            provider_type = getattr(record, 'provider_type', '')
            trade_id = getattr(record, 'trade_id', '')
            bill_type = getattr(record, 'bill_type', '')
            status = getattr(record, 'status', '')
            official_amount = getattr(record, 'official_amount', '')
            official_discount_amount = getattr(record, 'official_discount_amount', '')
            erase_amount = getattr(record, 'erase_amount', '')
            consume_amount = getattr(record, 'consume_amount', '')
            cash_amount = getattr(record, 'cash_amount', '')
            credit_amount = getattr(record, 'credit_amount', '')
            coupon_amount = getattr(record, 'coupon_amount', '')
            flexipurchase_coupon_amount = getattr(record, 'flexipurchase_coupon_amount', '')
            stored_value_card_amount = getattr(record, 'stored_value_card_amount', '')
            bonus_amount = getattr(record, 'bonus_amount', '')
            debt_amount = getattr(record, 'debt_amount', '')
            writeoff_amount = getattr(record, 'writeoff_amount', '')
            account_name = getattr(record, 'account_name', '')
            output += f"{bill_cycle}\t{customer_id}\t{service_type_code}\t{service_type_name}\t{resource_type_code}\t{resource_type_name}\t{region_code}\t{region_name}\t{enterprise_project_id}\t{enterprise_project_name}\t{charging_mode}\t{consume_time}\t{trade_time}\t{provider_type}\t{trade_id}\t{bill_type}\t{status}\t{official_amount}\t{official_discount_amount}\t{erase_amount}\t{consume_amount}\t{cash_amount}\t{credit_amount}\t{coupon_amount}\t{flexipurchase_coupon_amount}\t{stored_value_card_amount}\t{bonus_amount}\t{debt_amount}\t{writeoff_amount}\t{account_name}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_customer_bills_fee_records 查询失败: {e}")
    exit(1)
