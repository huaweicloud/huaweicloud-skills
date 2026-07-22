import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListMeasureUnitsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询度量单位列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文 en_US：英文。默认为zh_CN")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListMeasureUnitsRequest()
    request.x_language = args.x_language

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_measure_units(request)

    measure_units = getattr(response, 'measure_units', []) or []

    output = ""
    
    if measure_units:
        output += "度量单位列表:\n"
        output += "度量单位ID\t度量单位名称\t英文缩写\t度量类型\n"
        for unit in measure_units:
            measure_id = getattr(unit, 'measure_id', '')
            measure_name = getattr(unit, 'measure_name', '')
            abbreviation = getattr(unit, 'abbreviation', '')
            measure_type = getattr(unit, 'measure_type', '')
            output += f"{measure_id}\t{measure_name}\t{abbreviation}\t{measure_type}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_measure_units 查询失败: {e}")
    exit(1)
