import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListCustomerBillsMonthlyBreakDownRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户账单月度分摊明细")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文 en_US-英文。默认为zh_CN")
parser.add_argument("--shared_month", type=str, required=True, help="查询分摊成本的月份，东八区时间，格式：YYYY-MM")
parser.add_argument("--service_type_code", type=str, help="云服务类型编码，例如OBS的云服务类型编码为hws.service.type.obs。此参数不携带或携带值为空时，不作为筛选条件；携带值为空串时，作为筛选条件")
parser.add_argument("--resource_type_code", type=str, help="资源类型编码，例如ECS的VM为hws.resource.type.vm。此参数不携带或携带值为空时，不作为筛选条件；携带值为空串时，作为筛选条件")
parser.add_argument("--region_code", type=str, help="云服务区编码，例如cn-north-1。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--charging_mode", type=int, help="计费模式。1-包年/包月 3-按需 10-预留实例 11-节省计划。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--bill_type", type=int, help="账单类型。1-消费-新购 2-消费-续订 3-消费-变更 4-退款-退订 5-消费-使用 8-消费-自动续订 9-调账-补偿 14-消费-服务支持计划月末扣费 16-调账-扣费 18-消费-按月付费 20-退款-变更 23-消费-节省计划抵扣 24-退款-包年/包月转按需 25-消费-抹零补扣 103-消费-按年付费。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--resource_id", type=str, help="资源ID。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--resource_name", type=str, help="资源名称。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目标识（企业项目ID）。此参数不携带或携带值为空时，不作为筛选条件，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--method", type=str, default="all", help="查询资源消费记录的方式。oneself-客户自己 sub_customer-企业子客户 all-客户自己和企业子客户。默认为all")
parser.add_argument("--sub_customer_id", type=str, help="企业子账号ID。此参数不携带或携带值为空或携带值为空串时，不作为筛选条件。如果method取值不为sub_customer，则该参数无效")
parser.add_argument("--limit", type=int, default=50, help="每次查询的数量限制。默认值为50")
parser.add_argument("--offset", type=int, default=0, help="偏移量，默认值为0")
args = parser.parse_args()

if args.method == "sub_customer" and not args.sub_customer_id:
    parser.error("当 method=sub_customer 时，必须指定 sub_customer_id")

if args.region is not None:
    Region = args.region

try:
    request = ListCustomerBillsMonthlyBreakDownRequest()
    request.x_language = args.x_language
    request.shared_month = args.shared_month
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
    if args.resource_id:
        request.resource_id = args.resource_id
    if args.resource_name:
        request.resource_name = args.resource_name
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    request.method = args.method
    if args.sub_customer_id:
        request.sub_customer_id = args.sub_customer_id
    request.limit = args.limit
    request.offset = args.offset

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_customer_bills_monthly_break_down(request)

    currency = getattr(response, 'currency', '')
    total_count = getattr(response, 'total_count', 0)
    details = getattr(response, 'details', []) or []

    output = f"货币\t{currency}\n"
    output += f"总记录数\t{total_count}\n"
    
    if details:
        output += "\n分摊成本记录列表:\n"
        output += "分摊月份\t账期\t账单类型\t客户ID\t区域编码\t区域名称\t云服务类型编码\t资源类型编码\t云服务类型名称\t资源类型名称\t生效时间\t失效时间\t资源ID\t资源名称\t资源标签\t产品规格描述\t企业项目ID\t企业项目名称\t计费模式\t订单ID\t周期类型\t使用量类型\t使用量\t使用量单位\t套餐内使用量\t套餐内使用量单位\t预留实例使用量\t预留实例使用量单位\t消费金额\t期初已分摊金额\t当月分摊金额\t期末未分摊金额\t现金分摊金额\t信用额度分摊金额\t代金券分摊金额\t现金券分摊金额\t储值卡分摊金额\t奖励金分摊金额\n"
        for detail in details:
            shared_month = getattr(detail, 'shared_month', '')
            bill_cycle = getattr(detail, 'bill_cycle', '')
            bill_type = getattr(detail, 'bill_type', '')
            customer_id = getattr(detail, 'customer_id', '')
            region_code = getattr(detail, 'region_code', '')
            region_name = getattr(detail, 'region_name', '')
            service_type_code = getattr(detail, 'service_type_code', '')
            resource_type_code = getattr(detail, 'resource_type_code', '')
            service_type_name = getattr(detail, 'service_type_name', '')
            resource_type_name = getattr(detail, 'resource_type_name', '')
            effective_time = getattr(detail, 'effective_time', '')
            expire_time = getattr(detail, 'expire_time', '')
            resource_id = getattr(detail, 'resource_id', '')
            resource_name = getattr(detail, 'resource_name', '')
            resource_tag = getattr(detail, 'resource_tag', '')
            product_spec_desc = getattr(detail, 'product_spec_desc', '')
            enterprise_project_id = getattr(detail, 'enterprise_project_id', '')
            enterprise_project_name = getattr(detail, 'enterprise_project_name', '')
            charging_mode = getattr(detail, 'charging_mode', '')
            order_id = getattr(detail, 'order_id', '')
            period_type = getattr(detail, 'period_type', '')
            usage_type = getattr(detail, 'usage_type', '')
            usage = getattr(detail, 'usage', '')
            usage_measure_id = getattr(detail, 'usage_measure_id', '')
            free_resource_usage = getattr(detail, 'free_resource_usage', '')
            free_resource_measure_id = getattr(detail, 'free_resource_measure_id', '')
            ri_usage = getattr(detail, 'ri_usage', '')
            ri_usage_measure_id = getattr(detail, 'ri_usage_measure_id', '')
            consume_amount = getattr(detail, 'consume_amount', '')
            past_months_amortized_amount = getattr(detail, 'past_months_amortized_amount', '')
            current_month_amortized_amount = getattr(detail, 'current_month_amortized_amount', '')
            future_months_amortized_amount = getattr(detail, 'future_months_amortized_amount', '')
            amortized_cash_amount = getattr(detail, 'amortized_cash_amount', '')
            amortized_credit_amount = getattr(detail, 'amortized_credit_amount', '')
            amortized_coupon_amount = getattr(detail, 'amortized_coupon_amount', '')
            amortized_flexipurchase_coupon_amount = getattr(detail, 'amortized_flexipurchase_coupon_amount', '')
            amortized_stored_value_card_amount = getattr(detail, 'amortized_stored_value_card_amount', '')
            amortized_bonus_amount = getattr(detail, 'amortized_bonus_amount', '')
            output += f"{shared_month}\t{bill_cycle}\t{bill_type}\t{customer_id}\t{region_code}\t{region_name}\t{service_type_code}\t{resource_type_code}\t{service_type_name}\t{resource_type_name}\t{effective_time}\t{expire_time}\t{resource_id}\t{resource_name}\t{resource_tag}\t{product_spec_desc}\t{enterprise_project_id}\t{enterprise_project_name}\t{charging_mode}\t{order_id}\t{period_type}\t{usage_type}\t{usage}\t{usage_measure_id}\t{free_resource_usage}\t{free_resource_measure_id}\t{ri_usage}\t{ri_usage_measure_id}\t{consume_amount}\t{past_months_amortized_amount}\t{current_month_amortized_amount}\t{future_months_amortized_amount}\t{amortized_cash_amount}\t{amortized_credit_amount}\t{amortized_coupon_amount}\t{amortized_flexipurchase_coupon_amount}\t{amortized_stored_value_card_amount}\t{amortized_bonus_amount}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_customer_bills_monthly_break_down 查询失败: {e}")
    exit(1)
