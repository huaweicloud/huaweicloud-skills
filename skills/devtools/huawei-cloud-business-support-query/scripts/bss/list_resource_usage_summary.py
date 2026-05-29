import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListResourceUsageSummaryRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询资源用量汇总")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文；en_US：英文。默认为zh_CN")
parser.add_argument("--bill_cycle", type=str, required=True, help="账期，东八区时间，格式为yyyy-MM")
parser.add_argument("--service_type_code", type=str, required=True, help="云服务类型，当前仅支持：hws.service.type.cdn/hws.service.type.obs/hws.service.type.vpc/hws.service.type.iec")
parser.add_argument("--resource_type_code", type=str, required=True, help="资源类型编码，当前仅支持：hws.resource.type.cdn/hws.resource.type.obs/hws.resource.type.bandwidth/hws.resource.type.edgebandwidth")
parser.add_argument("--usage_type", type=str, required=True, help="使用量类型编码，目前仅支持：95Peak/95peak_1000/bandwidth95peak/95peak_plus")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--limit", type=int, default=50, help="每次查询的数量限制。默认值为50")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListResourceUsageSummaryRequest()
    if args.x_language:
        request.x_language = args.x_language
    request.bill_cycle = args.bill_cycle
    if args.service_type_code:
        request.service_type_code = args.service_type_code
    if args.resource_type_code:
        request.resource_type_code = args.resource_type_code
    if args.usage_type:
        request.usage_type = args.usage_type
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

    response = client.list_resource_usage_summary(request)

    total_count = getattr(response, 'total_count', 0)
    summary_usage_info_list = getattr(response, 'summary_usage_info_list', []) or []

    output = f"总条数\t{total_count}\n"
    
    if summary_usage_info_list:
        output += "\n资源用量汇总列表:\n"
        output += "resource_id\tactual_days\tband_width\tmonthly_guaranteed_band_width\tmonthly_peak_band_width\tband_width_measure_id\n"
        for info in summary_usage_info_list:
            resource_id = getattr(info, 'resource_id', '')
            actual_days = getattr(info, 'actual_days', '')
            band_width = getattr(info, 'band_width', '')
            monthly_guaranteed_band_width = getattr(info, 'monthly_guaranteed_band_width', '')
            monthly_peak_band_width = getattr(info, 'monthly_peak_band_width', '')
            band_width_measure_id = getattr(info, 'band_width_measure_id', '')
            output += f"{resource_id}\t{actual_days}\t{band_width}\t{monthly_guaranteed_band_width}\t{monthly_peak_band_width}\t{band_width_measure_id}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_resource_usage_summary 查询失败: {e}")
    exit(1)
