import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListFreeResourcesUsageRecordsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询免费资源使用记录")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--free_resource_id", type=str, help="资源项ID，一个资源包中会含有多个资源项，一个使用量类型对应一个资源项。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--product_id", type=str, help="产品ID，即资源包ID。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--resource_type_code", type=str, help="资源类型编码，例如ECS的VM为hws.resource.type.vm。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--deduct_time_begin", type=str, required=True, help="资源抵扣的起始时间，东八区时间，格式为YYYY-MM-DD")
parser.add_argument("--deduct_time_end", type=str, required=True, help="资源抵扣的结束时间，东八区时间，格式为YYYY-MM-DD。抵扣结束时间-抵扣起始时间<=90天")
parser.add_argument("--limit", type=int, default=50, help="每次查询的数量限制。默认值为50")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListFreeResourcesUsageRecordsRequest()
    if args.free_resource_id:
        request.free_resource_id = args.free_resource_id
    if args.product_id:
        request.product_id = args.product_id
    if args.resource_type_code:
        request.resource_type_code = args.resource_type_code
    request.deduct_time_begin = args.deduct_time_begin
    request.deduct_time_end = args.deduct_time_end
    if args.limit is not None:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_free_resources_usage_records(request)

    total_count = getattr(response, 'total_count', 0)
    free_resource_records = getattr(response, 'free_resource_records', []) or []

    output = f"总记录数\t{total_count}\n"
    
    if free_resource_records:
        output += "\n资源包使用明细记录:\n"
        output += "抵扣时间\t资源项ID\t资源ID\t资源类型编码\t资源类型名称\t资源标签\t产品ID\t产品名称\t使用量类型\t抵扣前余量\t抵扣后余量\t抵扣量\t度量单位\t使用开始时间\t使用结束时间\n"
        for record in free_resource_records:
            deduct_time = getattr(record, 'deduct_time', '')
            free_resource_id = getattr(record, 'free_resource_id', '')
            resource_id = getattr(record, 'resource_id', '')
            resource_type_code = getattr(record, 'resource_type_code', '')
            resource_type_name = getattr(record, 'resource_type_name', '')
            resource_tag = getattr(record, 'resource_tag', '')
            product_id = getattr(record, 'product_id', '')
            product_name = getattr(record, 'product_name', '')
            usage_type_code = getattr(record, 'usage_type_code', '')
            available_amount = getattr(record, 'available_amount', '')
            remaining_amount = getattr(record, 'remaining_amount', '')
            used_amount = getattr(record, 'used_amount', '')
            measure_id = getattr(record, 'measure_id', '')
            effective_time = getattr(record, 'effective_time', '')
            expire_time = getattr(record, 'expire_time', '')
            output += f"{deduct_time}\t{free_resource_id}\t{resource_id}\t{resource_type_code}\t{resource_type_name}\t{resource_tag}\t{product_id}\t{product_name}\t{usage_type_code}\t{available_amount}\t{remaining_amount}\t{used_amount}\t{measure_id}\t{effective_time}\t{expire_time}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_free_resources_usage_records 查询失败: {e}")
    exit(1)
