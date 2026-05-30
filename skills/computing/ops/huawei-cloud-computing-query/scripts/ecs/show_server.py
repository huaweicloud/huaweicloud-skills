import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowServerRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_id", type=str, required=True, help="服务器 ID（UUID），可通过 list_servers_details.py 获取")
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

    request = ShowServerRequest()
    request.server_id = args.server_id
    response = client.show_server(request)
    server = response.server

    if not server:
        print(f"没有找到 ECS 服务器 (区域: {Region}, 服务器 ID: {args.server_id})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"id: {getattr(server, 'id', '')}\n"
    output += f"name: {getattr(server, 'name', '')}\n"
    output += f"status: {getattr(server, 'status', '')}\n"
    flavor = getattr(server, 'flavor', None)
    if flavor:
        output += f"flavor: {getattr(flavor, 'id', '')}\n"
        output += f"vcpus: {getattr(flavor, 'vcpus', '')}\n"
        ram_mb = getattr(flavor, 'ram', 0)
        ram_gib = str(int(ram_mb) // 1024) if ram_mb else ''
        output += f"ram(GiB): {ram_gib}\n"
    else:
        output += f"flavor: \n"
        output += f"vcpus: \n"
        output += f"ram(GiB): \n"
    image = getattr(server, 'image', None)
    if image:
        output += f"image: {getattr(image, 'id', '')}\n"
    else:
        output += f"image: \n"
    output += f"created: {getattr(server, 'created', '')}\n"
    output += f"updated: {getattr(server, 'updated', '')}\n"
    print(output)
except Exception as e:
    print(f"ecs.server 查询失败: {e}")
    exit(1)
