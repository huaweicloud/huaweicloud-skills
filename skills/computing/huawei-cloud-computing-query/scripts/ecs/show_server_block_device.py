import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowServerBlockDeviceRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器块设备详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_id", type=str, required=True, help="服务器 ID（UUID），可通过 list_servers_details.py 获取")
parser.add_argument("--volume_id", type=str, required=True, help="卷 ID，可通过 list_server_block_devices.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ECS 客户端")
        exit(-1)

    request = ShowServerBlockDeviceRequest()
    request.server_id = args.server_id
    request.volume_id = args.volume_id
    response = client.show_server_block_device(request)
    attachment = response.volume_attachment

    if not attachment:
        print(f"没有找到 ECS 服务器块设备 (区域: {Region}, 服务器 ID: {args.server_id}, 卷 ID: {args.volume_id})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"volume_id: {getattr(attachment, 'volume_id', '')}\n"
    output += f"device: {getattr(attachment, 'device', '')}\n"
    output += f"boot_index: {getattr(attachment, 'boot_index', '')}\n"
    output += f"size: {getattr(attachment, 'size', '')}\n"
    print(output)
except Exception as e:
    print(f"ecs.server_block_device 查询失败: {e}")
    exit(1)
