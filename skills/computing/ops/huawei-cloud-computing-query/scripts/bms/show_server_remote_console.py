import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkbms.v1 import BmsClient
from huaweicloudsdkbms.v1.model import ShowServerRemoteConsoleRequest, ShowServerRemoteConsoleReq, RemoteConsole
from huaweicloudsdkbms.v1.region.bms_region import BmsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="获取裸金属服务器VNC远程登录地址")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_id", type=str, required=True, help="裸金属服务器ID，可通过 list_bare_metal_servers.py 获取")
parser.add_argument("--protocol", type=str, default="vnc", help="远程登录协议，默认 vnc")
parser.add_argument("--type", type=str, default="novnc", help="远程登录类型，默认 novnc")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = BmsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)
    ).with_region(BmsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 BMS 客户端")
        exit(-1)

    # 构建请求
    request = ShowServerRemoteConsoleRequest()
    request.server_id = args.server_id
    request.body = ShowServerRemoteConsoleReq(
        remote_console=RemoteConsole(
            protocol=args.protocol,
            type=args.type
        )
    )

    response = client.show_server_remote_console(request)
    remote_console = response.remote_console

    if not remote_console:
        print(f"没有找到远程登录信息 (区域: {Region}, 服务器ID: {args.server_id})")
        exit(0)

    # 渲染
    output = ""
    output += f"protocol: {getattr(remote_console, 'protocol', '')}\n"
    output += f"type: {getattr(remote_console, 'type', '')}\n"
    output += f"url: {getattr(remote_console, 'url', '')}\n"

    print(output)
except Exception as e:
    print(f"bms.show_server_remote_console 查询失败: {e}")
    exit(1)
