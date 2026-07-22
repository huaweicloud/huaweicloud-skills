import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListServiceTypesRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_LIMIT = 1000

parser = argparse.ArgumentParser(description="查询服务类型列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文；en_US：英文。缺省为zh_CN")
parser.add_argument("--service_type_name", type=str, nargs='*', help="云服务类型名称，支持批量传入多个，模糊匹配（客户端过滤）。例如：abbreviation-ECS service_type_name-弹性云服务器")
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

    # 分页查询，全量拉取
    offset = 0
    all_types = []
    total_count = 0
    fetched = 0

    MAX_PAGES = 1000
    for _page in range(MAX_PAGES):
        request = ListServiceTypesRequest()
        if args.x_language:
            request.x_language = args.x_language
        request.limit = PAGE_LIMIT
        request.offset = offset

        response = client.list_service_types(request)
        total_count = getattr(response, 'total_count', 0)
        page_types = getattr(response, 'service_types', []) or []
        all_types.extend(page_types)

        fetched += len(page_types)
        if fetched >= total_count or not page_types:
            break

        offset += PAGE_LIMIT

    service_type_names = args.service_type_name or []

    result = {}
    if service_type_names:
        for name in service_type_names:
            matched = [s for s in all_types if name in getattr(s, 'service_type_name', '')]
            result[name] = matched
    else:
        result = {"all": all_types}

    # 输出
    output = f"总记录数\t{total_count}\n"

    for key, services in result.items():
        output += f"\n--- {key} ---\n"
        if services:
            output += f"匹配记录数\t{len(services)}\n"
            output += "service_type_code\tservice_type_name\tabbreviation\n"
            for service in services:
                service_type_code = getattr(service, 'service_type_code', '')
                service_type_name = getattr(service, 'service_type_name', '')
                abbreviation = getattr(service, 'abbreviation', '') or ''
                output += f"{service_type_code}\t{service_type_name}\t{abbreviation}\n"
        else:
            output += "匹配记录数\t0\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_service_types 查询失败: {e}")
    exit(1)
