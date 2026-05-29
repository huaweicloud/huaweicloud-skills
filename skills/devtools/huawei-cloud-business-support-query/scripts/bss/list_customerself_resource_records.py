import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListCustomerselfResourceRecordsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户资源消费记录")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文 en_US：英文。默认为zh_CN")
parser.add_argument("--cycle", type=str, required=True, help="查询的资源消费记录所在账期，东八区时间，格式为YYYY-MM")
parser.add_argument("--cloud_service_type", type=str, help="云服务类型编码。不携带时不作为筛选条件")
parser.add_argument("--res_region", type=str, help="云服务区编码。不携带时不作为筛选条件")
parser.add_argument("--charge_mode", type=str, help="计费模式。1：包年/包月 3：按需 10：预留实例 11：节省计划。不携带时不作为筛选条件")
parser.add_argument("--bill_type", type=int, help="账单类型。不携带或null时返回所有")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--limit", type=int, default=50, help="每次查询数量限制。默认值为50")
parser.add_argument("--resource_id", type=str, help="资源ID。不携带时不作为筛选条件")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID。不携带时不作为筛选条件，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--include_zero_record", type=bool, help="是否包含应付金额为0的记录。不携带时不作为筛选条件")
parser.add_argument("--method", type=str, default="all", help="查询方式。oneself：客户自己 sub_customer：企业子客户 all：客户自己和企业子客户。默认all")
parser.add_argument("--sub_customer_id", type=str, help="企业子账号ID。method不为sub_customer时无效")
parser.add_argument("--trade_id", type=str, help="订单ID或交易ID。不携带时不作为筛选条件")
parser.add_argument("--bill_date_begin", type=str, help="查询开始日期，格式：YYYY-MM-DD。必须与bill_date_end同时使用")
parser.add_argument("--bill_date_end", type=str, help="查询结束日期，格式：YYYY-MM-DD。必须与bill_date_begin同时使用")
parser.add_argument("--statistic_type", type=int, default=3, help="统计类型。1：按账期 3：按明细。默认值为3")
args = parser.parse_args()

if args.method == "sub_customer" and not args.sub_customer_id:
    parser.error("当 method=sub_customer 时，必须指定 sub_customer_id")

if (args.bill_date_begin is not None) != (args.bill_date_end is not None):
    parser.error("bill_date_begin 和 bill_date_end 必须同时指定或同时不指定")

if args.region is not None:
    Region = args.region

try:
    request = ListCustomerselfResourceRecordsRequest()
    request.x_language = args.x_language
    request.cycle = args.cycle
    if args.cloud_service_type:
        request.cloud_service_type = args.cloud_service_type
    if args.res_region:
        request.region = args.res_region
    if args.charge_mode:
        request.charge_mode = args.charge_mode
    if args.bill_type is not None:
        request.bill_type = args.bill_type
    request.offset = args.offset
    request.limit = args.limit
    if args.resource_id:
        request.resource_id = args.resource_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.include_zero_record is not None:
        request.include_zero_record = args.include_zero_record
    request.method = args.method
    if args.sub_customer_id:
        request.sub_customer_id = args.sub_customer_id
    if args.trade_id:
        request.trade_id = args.trade_id
    if args.bill_date_begin:
        request.bill_date_begin = args.bill_date_begin
    if args.bill_date_end:
        request.bill_date_end = args.bill_date_end
    if args.statistic_type is not None:
        request.statistic_type = args.statistic_type

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_customerself_resource_records(request)

    total_count = getattr(response, 'total_count', 0)
    fee_records = getattr(response, 'fee_records', []) or []
    currency = getattr(response, 'currency', '')

    output = f"总记录数\t{total_count}\t币种\t{currency}\n"
    if fee_records:
        output += "\n资源费用记录列表:\n"
        output += "消费日期\t账单类型\t客户ID\t区域编码\t区域名称\t云服务类型编码\t资源类型编码\t云服务类型名称\t资源类型名称\t资源ID\t资源名称\t资源标签\t产品ID\t产品名称\t产品规格描述\tSKU编码\t订单ID或交易ID\t交易时间\t企业项目ID\t企业项目名称\t计费模式\t订单ID\t周期类型\t使用量类型\t使用量\t使用量单位\t官网价\t优惠金额\t应付金额\t现金支付\t信用额度支付\t代金券支付\t现金券支付\t储值卡支付\t奖励金支付\t欠费金额\t欠费核销金额\t金额单位\t消费时间\t客户登录名称\n"
        for record in fee_records:
            bill_date = getattr(record, 'bill_date', '')
            bill_type = getattr(record, 'bill_type', '')
            customer_id = getattr(record, 'customer_id', '')
            region = getattr(record, 'region', '')
            region_name = getattr(record, 'region_name', '')
            cloud_service_type = getattr(record, 'cloud_service_type', '')
            resource_type = getattr(record, 'resource_type', '')
            cloud_service_type_name = getattr(record, 'cloud_service_type_name', '')
            resource_type_name = getattr(record, 'resource_type_name', '')
            resource_id = getattr(record, 'resource_id', '')
            resource_name = getattr(record, 'resource_name', '')
            resource_tag = getattr(record, 'resource_tag', '')
            product_id = getattr(record, 'product_id', '')
            product_name = getattr(record, 'product_name', '')
            product_spec_desc = getattr(record, 'product_spec_desc', '')
            sku_code = getattr(record, 'sku_code', '')
            trade_id = getattr(record, 'trade_id', '')
            trade_time = getattr(record, 'trade_time', '')
            enterprise_project_id = getattr(record, 'enterprise_project_id', '')
            enterprise_project_name = getattr(record, 'enterprise_project_name', '')
            charge_mode = getattr(record, 'charge_mode', '')
            order_id = getattr(record, 'order_id', '')
            period_type = getattr(record, 'period_type', '')
            usage_type = getattr(record, 'usage_type', '')
            usage = getattr(record, 'usage', '')
            usage_measure_id = getattr(record, 'usage_measure_id', '')
            official_amount = getattr(record, 'official_amount', '')
            discount_amount = getattr(record, 'discount_amount', '')
            amount = getattr(record, 'amount', '')
            cash_amount = getattr(record, 'cash_amount', '')
            credit_amount = getattr(record, 'credit_amount', '')
            coupon_amount = getattr(record, 'coupon_amount', '')
            flexipurchase_coupon_amount = getattr(record, 'flexipurchase_coupon_amount', '')
            stored_card_amount = getattr(record, 'stored_card_amount', '')
            bonus_amount = getattr(record, 'bonus_amount', '')
            debt_amount = getattr(record, 'debt_amount', '')
            adjustment_amount = getattr(record, 'adjustment_amount', '')
            measure_id = getattr(record, 'measure_id', '')
            consume_time = getattr(record, 'consume_time', '')
            account_name = getattr(record, 'account_name', '')
            output += f"{bill_date}\t{bill_type}\t{customer_id}\t{region}\t{region_name}\t{cloud_service_type}\t{resource_type}\t{cloud_service_type_name}\t{resource_type_name}\t{resource_id}\t{resource_name}\t{resource_tag}\t{product_id}\t{product_name}\t{product_spec_desc}\t{sku_code}\t{trade_id}\t{trade_time}\t{enterprise_project_id}\t{enterprise_project_name}\t{charge_mode}\t{order_id}\t{period_type}\t{usage_type}\t{usage}\t{usage_measure_id}\t{official_amount}\t{discount_amount}\t{amount}\t{cash_amount}\t{credit_amount}\t{coupon_amount}\t{flexipurchase_coupon_amount}\t{stored_card_amount}\t{bonus_amount}\t{debt_amount}\t{adjustment_amount}\t{measure_id}\t{consume_time}\t{account_name}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_customerself_resource_records 查询失败: {e}")
    exit(1)
