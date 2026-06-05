import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListCesTargetProjectTagsRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询CES目标项目标签列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--resource_type", type=str, default="CES-alarm", help="资源类型，固定为CES-alarm（告警规则），长度1-32")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListCesTargetProjectTagsRequest()
    request.resource_type = args.resource_type

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_ces_target_project_tags(request)

    tags = getattr(response, 'tags', []) or []

    if not tags:
        print("查询结果为空")
        exit(0)

    output = "CES目标项目标签列表:\n"
    output += "键\t值列表\n"
    
    for tag in tags:
        key = getattr(tag, 'key', '')
        values = getattr(tag, 'values', []) or []
        output += f"{key}\t{','.join(str(v) for v in values)}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_ces_target_project_tags 查询失败: {e}")
    exit(1)
