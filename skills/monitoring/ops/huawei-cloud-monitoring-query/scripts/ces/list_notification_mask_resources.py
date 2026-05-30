import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListNotificationMaskResourcesRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询通知屏蔽规则关联的资源列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--notification_mask_id", type=str, required=True, help="屏蔽规则ID，只能包含字母和数字，长度1-64，可通过 list_notification_masks.py 获取")
parser.add_argument("--offset", type=int, help="分页偏移量，范围0-10000，默认0")
parser.add_argument("--limit", type=int, default=100, help="分页大小，范围1-100，默认100")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListNotificationMaskResourcesRequest()
    request.notification_mask_id = args.notification_mask_id
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_notification_mask_resources(request)

    resources = getattr(response, 'resources', []) or []
    count = getattr(response, 'count', 0)

    if not resources:
        print("查询结果为空")
        exit(0)

    output = f"屏蔽规则 {args.notification_mask_id} 关联的资源列表（共{count}个）:\n"
    
    for idx, resource in enumerate(resources, 1):
        namespace = getattr(resource, 'namespace', '')
        dimensions = getattr(resource, 'dimensions', []) or []
        output += f"资源 {idx} (命名空间: {namespace}):\n"
        for dim in dimensions:
            name = getattr(dim, 'name', '')
            value = getattr(dim, 'value', '')
            output += f"  {name}: {value}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_notification_mask_resources 查询失败: {e}")
    exit(1)
