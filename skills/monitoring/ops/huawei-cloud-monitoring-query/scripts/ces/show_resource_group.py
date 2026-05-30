import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ShowResourceGroupRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询资源分组详情")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--group_id", type=str, required=True, help="资源分组ID，可通过 list_resource_groups.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowResourceGroupRequest()
    request.group_id = args.group_id

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.show_resource_group(request)

    group_id = getattr(response, 'group_id', '')
    group_name = getattr(response, 'group_name', '')
    type = getattr(response, 'type', '')
    status = getattr(response, 'status', '')
    create_time = getattr(response, 'create_time', '')

    output = "资源分组详情:\n"
    output += f"分组ID: {group_id}\n"
    output += f"名称: {group_name}\n"
    output += f"类型: {type}\n"
    output += f"状态: {status}\n"
    output += f"创建时间: {create_time}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.show_resource_group 查询失败: {e}")
    exit(1)
