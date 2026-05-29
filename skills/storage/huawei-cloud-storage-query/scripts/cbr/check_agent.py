import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model.check_agent_request import CheckAgentRequest
from huaweicloudsdkcbr.v1.model.protectable_agent_req import ProtectableAgentReq
from huaweicloudsdkcbr.v1.model.protectable_agent_status_resource import ProtectableAgentStatusResource
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 客户端状态")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--resource_ids", type=str, required=True, help="资源ID列表，多个以英文逗号分隔")
parser.add_argument("--resource_names", type=str, help="资源名称列表，多个以英文逗号分隔，与resource_ids一一对应")
parser.add_argument("--resource_types", type=str, required=True, help="资源类型列表，多个以英文逗号分隔，与resource_ids一一对应，取值: OS::Nova::Server, OS::Cinder::Volume, OS::Sfs::Turbo, OS::Workspace::DesktopV2")
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

    resource_ids = [rid.strip() for rid in args.resource_ids.split(',') if rid.strip()]
    resource_names = [n.strip() for n in args.resource_names.split(',') if n.strip()] if args.resource_names else []
    resource_types = [t.strip() for t in args.resource_types.split(',') if t.strip()]

    if len(resource_types) != len(resource_ids):
        print(f"resource_types 数量({len(resource_types)})与 resource_ids 数量({len(resource_ids)})不一致，必须一一对应")
        exit(1)
    if resource_names and len(resource_names) != len(resource_ids):
        print(f"resource_names 数量({len(resource_names)})与 resource_ids 数量({len(resource_ids)})不一致，必须一一对应")
        exit(1)

    req_body = ProtectableAgentReq()
    agents = []
    for i, rid in enumerate(resource_ids):
        agent_res = ProtectableAgentStatusResource(resource_id=rid, resource_type=resource_types[i])
        if i < len(resource_names):
            agent_res.resource_name = resource_names[i]
        agents.append(agent_res)
    req_body.agent_status = agents

    request = CheckAgentRequest()
    request.body = req_body
    response = client.check_agent(request)

    agent_status = getattr(response, 'agent_status', []) or []

    if not agent_status:
        print(f"没有找到客户端状态信息 (区域: {Region})")
        exit(0)

    output = f"resource_id\tinstalled\tversion\tcode\tmessage\n"
    for agent in agent_status:
        resource_id = getattr(agent, 'resource_id', '')
        installed = getattr(agent, 'installed', '')
        version = getattr(agent, 'version', '')
        code = getattr(agent, 'code', '')
        message = getattr(agent, 'message', '')
        output += f"{resource_id}\t{installed}\t{version}\t{code}\t{message}\n"
    print(output)
except Exception as e:
    print(f"cbr.check_agent 查询失败: {e}")
    exit(1)
