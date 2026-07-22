import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListProvincesRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询省份列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_cn", help="语言。zh_cn：中文；en_us：英文。默认为zh_cn")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--limit", type=int, default=50, help="每次查询的数量，最大1000")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListProvincesRequest()
    if args.x_language:
        request.x_language = args.x_language
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_provinces(request)

    count = getattr(response, 'count', 0)
    provinces = getattr(response, 'provinces', []) or []

    output = f"查询个数\t{count}\n"
    
    if provinces:
        output += "\n省份列表:\n"
        output += "省份编码\t省份名称\n"
        for province in provinces:
            code = getattr(province, 'code', '')
            name = getattr(province, 'name', '')
            output += f"{code}\t{name}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_provinces 查询失败: {e}")
    exit(1)
