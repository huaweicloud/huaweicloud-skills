import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowAgentRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 客户端详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--agent_id", type=str, required=True, help="客户端ID，可通过 list_agent.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ShowAgentRequest()
    request.agent_id = args.agent_id
    response = client.show_agent(request)
    agent = getattr(response, 'agent', None)

    if not agent:
        print(f"没有找到客户端 (区域: {Region}, 客户端 ID: {args.agent_id})")
        exit(0)

    output = ""
    output += f"agent_id: {getattr(agent, 'agent_id', '')}\n"
    output += f"agent_version: {getattr(agent, 'agent_version', '')}\n"
    output += f"agent_type: {getattr(agent, 'agent_type', '')}\n"
    output += f"host_name: {getattr(agent, 'host_name', '')}\n"
    output += f"host_nickname: {getattr(agent, 'host_nickname', '')}\n"
    output += f"host_ip: {getattr(agent, 'host_ip', '')}\n"
    output += f"host_os: {getattr(agent, 'host_os', '')}\n"
    output += f"status: {getattr(agent, 'status', '')}\n"
    output += f"last_active_time: {getattr(agent, 'last_active_time', '')}\n"
    output += f"created_at: {getattr(agent, 'created_at', '')}\n"
    output += f"updated_at: {getattr(agent, 'updated_at', '')}\n"

    paths = getattr(agent, 'paths', []) or []
    if paths:
        output += f"\npaths ({len(paths)}):\n"
        for path in paths:
            output += f"  id: {getattr(path, 'id', '')}\n"
            output += f"  dir_path: {getattr(path, 'dir_path', '')}\n"
            output += f"  status: {getattr(path, 'status', '')}\n"
            exclude_paths = getattr(path, 'exclude_paths', []) or []
            output += f"  exclude_paths: {exclude_paths}\n"

    print(output)
except Exception as e:
    print(f"cbr.show_agent 查询失败: {e}")
    exit(1)
