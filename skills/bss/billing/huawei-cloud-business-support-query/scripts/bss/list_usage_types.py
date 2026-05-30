import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListUsageTypesRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询使用量类型列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文；en_US：英文。缺省为zh_CN")
parser.add_argument("--resource_type_code", type=str, help="资源类型编码，例如hws.resource.type.vm。此参数不携带或携带值为空时，不作为筛选条件；携带值为空串时，作为筛选条件")
parser.add_argument("--limit", type=int, default=50, help="每次查询的数量，默认值为50")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListUsageTypesRequest()
    if args.x_language:
        request.x_language = args.x_language
    if args.resource_type_code:
        request.resource_type_code = args.resource_type_code
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

    response = client.list_usage_types(request)

    total_count = getattr(response, 'total_count', 0)
    usage_types = getattr(response, 'usage_types', []) or []

    output = f"总记录数\t{total_count}\n"
    
    if usage_types:
        output += "\n使用量类型列表:\n"
        output += "code\tname\tresource_type_code\tservice_type_code\tresource_type_name\tservice_type_name\n"
        for usage in usage_types:
            code = getattr(usage, 'code', '')
            name = getattr(usage, 'name', '')
            resource_type_code = getattr(usage, 'resource_type_code', '')
            service_type_code = getattr(usage, 'service_type_code', '')
            resource_type_name = getattr(usage, 'resource_type_name', '')
            service_type_name = getattr(usage, 'service_type_name', '')
            output += f"{code}\t{name}\t{resource_type_code}\t{service_type_code}\t{resource_type_name}\t{service_type_name}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_usage_types 查询失败: {e}")
    exit(1)
