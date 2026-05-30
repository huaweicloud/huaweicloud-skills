import argparse
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListCostsRequest, ListCostsReq, TimeCondition, GroupBy
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询成本列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言，默认zh_CN，可选：zh_CN-中文 en_US-英文")
parser.add_argument("--time_measure_id", type=int, default=2, help="时间单位。1：天 2：月。默认按月(2)")
parser.add_argument("--begin_time", type=str, help="查询开始时间。当time_measure_id=1时格式为YYYY-MM-DD；当time_measure_id=2时格式为YYYY-MM。不传时默认当月")
parser.add_argument("--end_time", type=str, help="查询结束时间，格式同begin_time。不传时默认当月")
parser.add_argument("--group_by_key", type=str, default="CLOUD_SERVICE_TYPE", help="分组维度key。如果type为dimension，此处取值如下：CLOUD_SERVICE_TYPE 产品类型 RESOURCE_TYPE 产品 ASSOCIATED_ACCOUNT 关联账号 REGION_CODE 区域 AZ_CODE 可用区 ENTERPRISE_PROJECT_ID 企业项目 RES_SPEC_CODE 产品规格 CHARGING_MODE 计费模式 USAGE_TYPE 使用量类型 BILL_TYPE 账单大类 BE_ID 运营实体 PAYER_ACCOUNT_ID 支付账号 RESOURCE_ID 资源")
parser.add_argument("--cost_type", type=str, default="ORIGINAL_COST", help="成本类型。ORIGINAL_COST：原始成本 AMORTIZED_COST：摊销成本")
parser.add_argument("--amount_type", type=str, default="PAYMENT_AMOUNT", help="金额类型。PAYMENT_AMOUNT：应付 NET_AMOUNT：实付")
parser.add_argument("--limit", type=int, default=50, help="每次查询的记录数，默认为50")
parser.add_argument("--offset", type=int, default=0, help="偏移量，默认为0")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

now = datetime.now()
current_month = now.strftime("%Y-%m")
current_day = now.strftime("%Y-%m-%d")
if args.begin_time is None:
    args.begin_time = current_month if args.time_measure_id == 2 else current_day
if args.end_time is None:
    args.end_time = current_month if args.time_measure_id == 2 else current_day

def validate_time_format(time_str, measure_id, param_name):
    if measure_id == 2:
        try:
            datetime.strptime(time_str, "%Y-%m")
        except ValueError:
            print(f"错误: {param_name} 格式应为 YYYY-MM (time_measure_id=2时), 实际值: {time_str}")
            exit(-1)
    else:
        try:
            datetime.strptime(time_str, "%Y-%m-%d")
        except ValueError:
            print(f"错误: {param_name} 格式应为 YYYY-MM-DD (time_measure_id=1时), 实际值: {time_str}")
            exit(-1)

validate_time_format(args.begin_time, args.time_measure_id, "begin_time")
validate_time_format(args.end_time, args.time_measure_id, "end_time")

try:
    time_condition = TimeCondition()
    time_condition.time_measure_id = args.time_measure_id
    time_condition.begin_time = args.begin_time
    time_condition.end_time = args.end_time

    group_by = GroupBy()
    group_by.type = "dimension"
    group_by.key = args.group_by_key

    body = ListCostsReq()
    body.time_condition = time_condition
    body.groupby = [group_by]
    body.cost_type = args.cost_type
    body.amount_type = args.amount_type
    body.offset = args.offset
    body.limit = args.limit

    request = ListCostsRequest()
    request.x_language = args.x_language
    request.body = body

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_costs(request)

    currency = getattr(response, 'currency', '')
    total_count = getattr(response, 'total_count', 0)
    cost_data = getattr(response, 'cost_data', []) or []

    output = f"货币\t{currency}\n"
    output += f"总记录数\t{total_count}\n"
    
    if cost_data:
        output += "\n成本数据列表:\n"
        output += "维度值\t成本汇总金额\t官网价汇总金额\t明细时间\t明细金额\t明细官网价\n"
        for data in cost_data:
            dimensions = getattr(data, 'dimensions', []) or []
            dimension_value = dimensions[0].value if dimensions else ''
            amount_by_costs = getattr(data, 'amount_by_costs', '')
            official_amount_by_costs = getattr(data, 'official_amount_by_costs', '')
            costs = getattr(data, 'costs', []) or []
            if costs:
                for cost_item in costs:
                    time_dimension_value = getattr(cost_item, 'time_dimension_value', '')
                    amount = getattr(cost_item, 'amount', '')
                    official_amount = getattr(cost_item, 'official_amount', '')
                    output += f"{dimension_value}\t{amount_by_costs}\t{official_amount_by_costs}\t{time_dimension_value}\t{amount}\t{official_amount}\n"
            else:
                output += f"{dimension_value}\t{amount_by_costs}\t{official_amount_by_costs}\t\t\t\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_costs 查询失败: {e}")
    exit(1)
