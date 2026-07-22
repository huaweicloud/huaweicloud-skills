import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListFreeResourceUsagesRequest, ListFreeResourceUsagesReq
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询免费资源使用量")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文 en_US：英文。默认为zh_CN")
parser.add_argument("--free_resource_ids", type=str, nargs='+', required=True, help="资源项ID列表（可多个），每个最大64字节。资源项ID来自查询资源包列表接口的响应")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    body = ListFreeResourceUsagesReq()
    body.free_resource_ids = args.free_resource_ids

    request = ListFreeResourceUsagesRequest()
    request.x_language = args.x_language
    request.body = body

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_free_resource_usages(request)

    free_resources = getattr(response, 'free_resources', []) or []

    if not free_resources:
        print("查询结果为空")
        exit(0)

    output = "免费资源使用量列表:\n"
    output += "资源项ID\t资源项类型名称\t重置周期\t重置周期类别\t使用量类型名称\t开始时间\t结束时间\t资源剩余额度\t资源原始额度\t度量单位\n"
    
    for resource in free_resources:
        free_resource_id = getattr(resource, 'free_resource_id', '')
        free_resource_type_name = getattr(resource, 'free_resource_type_name', '')
        quota_reuse_cycle = getattr(resource, 'quota_reuse_cycle', '')
        quota_reuse_cycle_type = getattr(resource, 'quota_reuse_cycle_type', '')
        usage_type_name = getattr(resource, 'usage_type_name', '')
        start_time = getattr(resource, 'start_time', '')
        end_time = getattr(resource, 'end_time', '')
        amount = getattr(resource, 'amount', '')
        original_amount = getattr(resource, 'original_amount', '')
        measure_id = getattr(resource, 'measure_id', '')
        output += f"{free_resource_id}\t{free_resource_type_name}\t{quota_reuse_cycle}\t{quota_reuse_cycle_type}\t{usage_type_name}\t{start_time}\t{end_time}\t{amount}\t{original_amount}\t{measure_id}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_free_resource_usages 查询失败: {e}")
    exit(1)
