import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListConversionsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询度量单位换算信息")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言，默认zh_CN，枚举：zh_CN-中文 en_US-英文")
parser.add_argument("--measure_type", type=int, help="度量类型：1-货币 2-时长 3-流量 4-数量 7-容量 9-行数 10-周期 11-频率 12-个数 16-带宽速率 19-带宽速率（1000进制） 20-性能测试用量 27-核数*时长 28-内存*时长 29-IOPS*时长 30-吞吐量*时长 31-个/时长 40-流量（1000进制） 41-1K Tokens 98-缓存带宽x时长 104-tokens 108-数量*时长。此参数不携带或携带值为空或携带值为null时，不作为筛选条件；不支持携带值为空串")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListConversionsRequest()
    request.x_language = args.x_language
    request.measure_type = args.measure_type

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_conversions(request)

    conversions = getattr(response, 'conversions', []) or []

    output = ""
    
    if conversions:
        output += "度量单位换算列表:\n"
        output += "度量类型\t度量单位ID\t转换后单位ID\t转换比率\n"
        for conversion in conversions:
            measure_type = getattr(conversion, 'measure_type', '')
            measure_id = getattr(conversion, 'measure_id', '')
            ref_measure_id = getattr(conversion, 'ref_measure_id', '')
            conversion_ratio = getattr(conversion, 'conversion_ratio', '')
            output += f"{measure_type}\t{measure_id}\t{ref_measure_id}\t{conversion_ratio}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_conversions 查询失败: {e}")
    exit(1)
