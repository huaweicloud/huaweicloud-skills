import argparse
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ShowCustomerMonthlySumRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户月汇总账单")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bill_cycle", type=str, required=False, help="查询消费汇总数据所在的账期，东八区时间，格式为YYYY-MM。不指定则默认使用当前月份")
parser.add_argument("--service_type_code", type=str, help="云服务类型编码，例如OBS的云服务类型编码为hws.service.type.obs。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID。default项目对应ID：0；未归集项目对应ID：-1。此参数不携带或携带值为空时，不作为筛选条件，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始，默认0")
parser.add_argument("--limit", type=int, default=50, help="每次查询的数量，默认50")
parser.add_argument("--method", type=str, default="all", help="查询方式。oneself：自身；sub_customer：企业子客户；all：自己和企业子客户。默认all")
parser.add_argument("--sub_customer_id", type=str, help="企业子客户的账号ID。如果method取值不为sub_customer，则该参数无效；如果method取值为sub_customer，则该参数不能为空")
args = parser.parse_args()

if args.method == "sub_customer" and not args.sub_customer_id:
    parser.error("当 method=sub_customer 时，必须指定 sub_customer_id")

# 如果未指定 bill_cycle，使用当前年月
bill_cycle = args.bill_cycle
if not bill_cycle:
    now = datetime.now()
    bill_cycle = now.strftime("%Y-%m")
    print(f"[提示] 未指定账期，使用当前月份: {bill_cycle}\n")

if args.region is not None:
    Region = args.region

try:
    request = ShowCustomerMonthlySumRequest()
    request.bill_cycle = bill_cycle
    if args.service_type_code:
        request.service_type_code = args.service_type_code
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    request.offset = args.offset
    request.limit = args.limit
    request.method = args.method
    if args.sub_customer_id:
        request.sub_customer_id = args.sub_customer_id

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.show_customer_monthly_sum(request)

    total_count = getattr(response, 'total_count', 0)
    consume_amount = getattr(response, 'consume_amount', '')
    debt_amount = getattr(response, 'debt_amount', '')
    coupon_amount = getattr(response, 'coupon_amount', '')
    flexipurchase_coupon_amount = getattr(response, 'flexipurchase_coupon_amount', '')
    stored_value_card_amount = getattr(response, 'stored_value_card_amount', '')
    cash_amount = getattr(response, 'cash_amount', '')
    credit_amount = getattr(response, 'credit_amount', '')
    writeoff_amount = getattr(response, 'writeoff_amount', '')
    measure_id = getattr(response, 'measure_id', '')
    currency = getattr(response, 'currency', '')
    bill_sums = getattr(response, 'bill_sums', []) or []

    output = f"总条数\t{total_count}\n"
    output += f"总金额\t{consume_amount}\n"
    output += f"欠费金额\t{debt_amount}\n"
    output += f"代金券金额\t{coupon_amount}\n"
    output += f"现金券金额\t{flexipurchase_coupon_amount}\n"
    output += f"储值卡金额\t{stored_value_card_amount}\n"
    output += f"现金账户金额\t{cash_amount}\n"
    output += f"信用账户金额\t{credit_amount}\n"
    output += f"欠费核销金额\t{writeoff_amount}\n"
    output += f"金额单位\t{measure_id}\n"
    output += f"币种\t{currency}\n"
    
    if bill_sums:
        output += "\n账单记录列表:\n"
        output += "账期\t云服务类型编码\t云服务类型\t资源类型编码\t资源类型\t计费模式\t官网价\t折扣金额\t抹零金额\t应付金额\t代金券抵扣\t现金券抵扣\t储值卡抵扣\t现金支付\t信用账户\t欠费金额\t欠费核销\t金额单位\t账单类型\t客户ID\t客户名称\n"
        for record in bill_sums:
            bill_cycle = getattr(record, 'bill_cycle', '')
            service_type_code = getattr(record, 'service_type_code', '')
            service_type_name = getattr(record, 'service_type_name', '')
            resource_type_code = getattr(record, 'resource_type_code', '')
            resource_type_name = getattr(record, 'resource_type_name', '')
            charging_mode = getattr(record, 'charging_mode', '')
            mode_str = {1: '包年/包月', 3: '按需', 10: '预留实例'}.get(charging_mode, str(charging_mode))
            official_amount = getattr(record, 'official_amount', 0)
            official_discount_amount = getattr(record, 'official_discount_amount', 0)
            truncated_amount = getattr(record, 'truncated_amount', 0)
            consume_amount = getattr(record, 'consume_amount', 0)
            coupon_amount = getattr(record, 'coupon_amount', 0)
            flexipurchase_coupon_amount = getattr(record, 'flexipurchase_coupon_amount', 0)
            stored_value_card_amount = getattr(record, 'stored_value_card_amount', 0)
            cash_amount = getattr(record, 'cash_amount', 0)
            credit_amount = getattr(record, 'credit_amount', 0)
            debt_amount = getattr(record, 'debt_amount', 0)
            writeoff_amount = getattr(record, 'writeoff_amount', 0)
            measure_id = getattr(record, 'measure_id', '')
            bill_type = getattr(record, 'bill_type', '')
            bill_type_str = {1: '消费', 2: '退款', 3: '调账'}.get(bill_type, str(bill_type))
            customer_id = getattr(record, 'customer_id', '')
            account_name = getattr(record, 'account_name', '')
            output += f"{bill_cycle}\t{service_type_code}\t{service_type_name}\t{resource_type_code}\t{resource_type_name}\t{mode_str}\t{official_amount}\t{official_discount_amount}\t{truncated_amount}\t{consume_amount}\t{coupon_amount}\t{flexipurchase_coupon_amount}\t{stored_value_card_amount}\t{cash_amount}\t{credit_amount}\t{debt_amount}\t{writeoff_amount}\t{measure_id}\t{bill_type_str}\t{customer_id}\t{account_name}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.show_customer_monthly_sum 查询失败: {e}")
    exit(1)
