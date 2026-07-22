import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListCitiesRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询城市列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_cn", help="语言，默认zh_cn，可选：zh_cn-中文 en_us-英文")
parser.add_argument("--province_code", type=str, required=True, help="省份编码，可通过 list_provinces.py 获取")
parser.add_argument("--offset", type=int, default=0, help="偏移量，默认0")
parser.add_argument("--limit", type=int, default=50, help="每次查询数量，默认50")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListCitiesRequest()
    request.x_language = args.x_language
    request.province_code = args.province_code
    request.offset = args.offset
    request.limit = args.limit

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_cities(request)

    count = getattr(response, 'count', 0)
    cities = getattr(response, 'cities', []) or []

    output = f"查询个数\t{count}\n"
    
    if cities:
        output += "\n城市列表:\n"
        output += "城市编码\t城市名称\n"
        for city in cities:
            code = getattr(city, 'code', '')
            name = getattr(city, 'name', '')
            output += f"{code}\t{name}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_cities 查询失败: {e}")
    exit(1)
