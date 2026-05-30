import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowServerRemoteConsoleRequest, ShowServerRemoteConsoleRequestBody, GetServerRemoteConsoleOption
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器远程控制台")
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

    request = ShowServerRemoteConsoleRequest()
    request.server_id = args.server_id
    body = ShowServerRemoteConsoleRequestBody()
    option = GetServerRemoteConsoleOption()
    option.type = "novnc"
    option.protocol = "vnc"
    body.remote_console = option
    request.body = body
    response = client.show_server_remote_console(request)
    remote_console = response.remote_console

    if not remote_console:
        print(f"没有找到 ECS 服务器远程控制台 (区域: {Region}, 服务器 ID: {args.server_id})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"type: {getattr(remote_console, 'type', '')}\n"
    output += f"url: {getattr(remote_console, 'url', '')}\n"
    output += f"protocol: {getattr(remote_console, 'protocol', '')}\n"
    print(output)
except Exception as e:
    print(f"ecs.server_remote_console 查询失败: {e}")
    exit(1)
