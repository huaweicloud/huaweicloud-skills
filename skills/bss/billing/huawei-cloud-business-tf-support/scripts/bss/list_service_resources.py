import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListServiceResourcesRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询服务资源列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文；en_US：英文。缺省为zh_CN")
parser.add_argument("--service_type_code", type=str, required=True, help="云服务类型编码，例如hws.service.type.obs")
parser.add_argument("--limit", type=int, default=100, help="每次查询的数量，默认值为100。此参数不支持携带值为空")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListServiceResourcesRequest()
    if args.x_language:
        request.x_language = args.x_language
    request.service_type_code = args.service_type_code
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

    response = client.list_service_resources(request)

    total_count = getattr(response, 'total_count', 0)
    infos = getattr(response, 'infos', []) or []

    output = f"总记录数\t{total_count}\n"
    
    if infos:
        output += "\n服务资源列表:\n"
        output += "resource_type_code\tproduct_owner_service\tname\tdescription\n"
        for info in infos:
            basic_info = getattr(info, 'basic_info', None)
            if basic_info:
                resource_type_code = getattr(basic_info, 'resource_type_code', '')
                product_owner_service = getattr(basic_info, 'product_owner_service', '')
                name = getattr(basic_info, 'name', '')
                description = getattr(basic_info, 'description', '')
            else:
                resource_type_code = ''
                product_owner_service = ''
                name = ''
                description = ''
            output += f"{resource_type_code}\t{product_owner_service}\t{name}\t{description}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_service_resources 查询失败: {e}")
    exit(1)
