import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListCustomerselfResourceRecordDetailsRequest
from huaweicloudsdkbss.v2.model import QueryResRecordsDetailReq
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户资源消费记录明细")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN-中文 en_US-英文。默认为zh_CN")
parser.add_argument("--cycle", type=str, required=True, help="查询的资源详单所在账期，东八区时间，格式为YYYY-MM。不支持2019年1月份之前的资源详单")
parser.add_argument("--cloud_service_type", type=str, help="云服务类型编码。不携带或空串或null时，不作为筛选条件")
parser.add_argument("--resource_type", type=str, help="资源类型编码。不携带或空串或null时，不作为筛选条件")
parser.add_argument("--res_region", type=str, help="云服务区编码。不携带或空串或null时，不作为筛选条件")
parser.add_argument("--res_instance_id", type=str, help="资源实例ID。不携带或空串或null时，不作为筛选条件")
parser.add_argument("--charge_mode", type=int, help="计费模式：1-包年/包月 3-按需 10-预留实例 11-节省计划。不携带或null时返回所有")
parser.add_argument("--bill_type", type=int, help="账单类型。1：消费-新购 2：消费-续订 3：消费-变更 4：退款-退订 5：消费-使用 8：消费-自动续订 9：调账-补偿 14：消费-服务支持计划月末扣费 16：调账-扣费 18：消费-按月付费 20：退款-变更 23：消费-节省计划抵扣 24：退款-包年/包月转按需 25：消费-抹零补扣 103：消费-按年付费。不携带或null时返回所有")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID。不携带或空串或null时，不作为筛选条件，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--include_zero_record", type=bool, help="是否包含应付金额为0的记录。不携带或空串或null时，不作为筛选条件")
parser.add_argument("--offset", type=int, default=0, help="偏移量，默认0")
parser.add_argument("--limit", type=int, default=50, help="页面大小，默认值为50")
parser.add_argument("--method", type=str, default="all", help="查询方式：oneself-客户自己 sub_customer-企业子客户 all-客户自己和企业子客户。默认all")
parser.add_argument("--sub_customer_id", type=str, help="企业子账号ID。method不为sub_customer时无效")
parser.add_argument("--statistic_type", type=int, default=1, help="统计类型：1-按账期 2-按天 3-按明细。默认值为1")
parser.add_argument("--query_type", type=str, default="BILLCYCLE", help="查询类型：BILLCYCLE-按月 DAILY-按天。默认BILLCYCLE。仅当statistic_type=2或3时支持DAILY")
parser.add_argument("--bill_cycle_begin", type=str, help="账期开始时间，格式：YYYY-MM-DD。当query_type=DAILY时必填")
parser.add_argument("--bill_cycle_end", type=str, help="账期结束时间，格式：YYYY-MM-DD。当query_type=DAILY时必填")
parser.add_argument("--payer_account_id", type=str, help="支付账号ID")
args = parser.parse_args()

if args.method == "sub_customer" and not args.sub_customer_id:
    parser.error("当 method=sub_customer 时，必须指定 sub_customer_id")

if args.query_type == "DAILY":
    if args.statistic_type not in [2, 3]:
        parser.error("仅当 statistic_type=2 或 3 时，才支持 query_type=DAILY")
    if not args.bill_cycle_begin:
        parser.error("当 query_type=DAILY 时，必须指定 bill_cycle_begin")
    if not args.bill_cycle_end:
        parser.error("当 query_type=DAILY 时，必须指定 bill_cycle_end")

if args.region is not None:
    Region = args.region

try:
    body = QueryResRecordsDetailReq()
    body.cycle = args.cycle
    if args.cloud_service_type:
        body.cloud_service_type = args.cloud_service_type
    if args.resource_type:
        body.resource_type = args.resource_type
    if args.res_region:
        body.region = args.res_region
    if args.res_instance_id:
        body.res_instance_id = args.res_instance_id
    if args.charge_mode is not None:
        body.charge_mode = args.charge_mode
    if args.bill_type is not None:
        body.bill_type = args.bill_type
    if args.enterprise_project_id:
        body.enterprise_project_id = args.enterprise_project_id
    if args.include_zero_record is not None:
        body.include_zero_record = args.include_zero_record
    body.offset = args.offset
    body.limit = args.limit
    body.method = args.method
    if args.sub_customer_id:
        body.sub_customer_id = args.sub_customer_id
    body.statistic_type = args.statistic_type
    body.query_type = args.query_type
    if args.bill_cycle_begin:
        body.bill_cycle_begin = args.bill_cycle_begin
    if args.bill_cycle_end:
        body.bill_cycle_end = args.bill_cycle_end
    if args.payer_account_id:
        body.payer_account_id = args.payer_account_id

    request = ListCustomerselfResourceRecordDetailsRequest()
    request.x_language = args.x_language
    request.body = body

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_customerself_resource_record_details(request)

    total_count = getattr(response, 'total_count', 0)
    monthly_records = getattr(response, 'monthly_records', []) or []
    currency = getattr(response, 'currency', '')

    output = f"总记录数\t{total_count}\t币种\t{currency}\n"
    if monthly_records:
        output += "\n资源详单列表:\n"
        output += "账期\t消费日期\t账单类型\t客户ID\t区域编码\t区域名称\t云服务类型编码\t资源类型编码\t云服务类型名称\t资源类型名称\t资源实例ID\t资源名称\t资源标签\tSKU编码\t企业项目ID\t企业项目名称\t计费模式\t消费金额\t现金支付\t信用额度支付\t代金券支付\t现金券支付\t储值卡支付\t奖励金支付\t欠费金额\t欠费核销金额\t官网价\t折扣金额\t金额单位\t周期类型\t订单ID或交易ID\t产品规格描述\t支付账号ID\t客户登录名称\n"
        for record in monthly_records:
            cycle = getattr(record, 'cycle', '')
            bill_date = getattr(record, 'bill_date', '')
            bill_type = getattr(record, 'bill_type', '')
            customer_id = getattr(record, 'customer_id', '')
            region = getattr(record, 'region', '')
            region_name = getattr(record, 'region_name', '')
            cloud_service_type = getattr(record, 'cloud_service_type', '')
            resource_type_code = getattr(record, 'resource_type_code', '')
            cloud_service_type_name = getattr(record, 'cloud_service_type_name', '')
            resource_type_name = getattr(record, 'resource_type_name', '')
            res_instance_id = getattr(record, 'res_instance_id', '')
            resource_name = getattr(record, 'resource_name', '')
            resource_tag = getattr(record, 'resource_tag', '')
            sku_code = getattr(record, 'sku_code', '')
            enterprise_project_id = getattr(record, 'enterprise_project_id', '')
            enterprise_project_name = getattr(record, 'enterprise_project_name', '')
            charge_mode = getattr(record, 'charge_mode', '')
            consume_amount = getattr(record, 'consume_amount', '')
            cash_amount = getattr(record, 'cash_amount', '')
            credit_amount = getattr(record, 'credit_amount', '')
            coupon_amount = getattr(record, 'coupon_amount', '')
            flexipurchase_coupon_amount = getattr(record, 'flexipurchase_coupon_amount', '')
            stored_card_amount = getattr(record, 'stored_card_amount', '')
            bonus_amount = getattr(record, 'bonus_amount', '')
            debt_amount = getattr(record, 'debt_amount', '')
            adjustment_amount = getattr(record, 'adjustment_amount', '')
            official_amount = getattr(record, 'official_amount', '')
            discount_amount = getattr(record, 'discount_amount', '')
            measure_id = getattr(record, 'measure_id', '')
            period_type = getattr(record, 'period_type', '')
            trade_id = getattr(record, 'trade_id', '')
            product_spec_desc = getattr(record, 'product_spec_desc', '')
            payer_account_id = getattr(record, 'payer_account_id', '')
            account_name = getattr(record, 'account_name', '')
            output += f"{cycle}\t{bill_date}\t{bill_type}\t{customer_id}\t{region}\t{region_name}\t{cloud_service_type}\t{resource_type_code}\t{cloud_service_type_name}\t{resource_type_name}\t{res_instance_id}\t{resource_name}\t{resource_tag}\t{sku_code}\t{enterprise_project_id}\t{enterprise_project_name}\t{charge_mode}\t{consume_amount}\t{cash_amount}\t{credit_amount}\t{coupon_amount}\t{flexipurchase_coupon_amount}\t{stored_card_amount}\t{bonus_amount}\t{debt_amount}\t{adjustment_amount}\t{official_amount}\t{discount_amount}\t{measure_id}\t{period_type}\t{trade_id}\t{product_spec_desc}\t{payer_account_id}\t{account_name}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_customerself_resource_record_details 查询失败: {e}")
    exit(1)
