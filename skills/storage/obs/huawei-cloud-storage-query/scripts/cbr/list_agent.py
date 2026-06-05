import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListAgentRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 CBR 客户端列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--limit", type=str, help="每页显示条目数，正整数")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
parser.add_argument("--status", type=str, help="状态: normal/abnormal/uninstall")
parser.add_argument("--agent_id", type=str, help="客户端ID，多个以英文逗号分隔")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(agents):
    total = len(agents)
    if Offset >= total:
        print(f"查询结果为空\n\n客户端列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"agent_id\tagent_version\tagent_type\thost_name\thost_ip\thost_os\tstatus\tlast_active_time\n"
    for i in range(Offset, min(total, Offset + 50)):
        agent = agents[i]
        agent_id = getattr(agent, 'agent_id', '')
        agent_version = getattr(agent, 'agent_version', '')
        agent_type = getattr(agent, 'agent_type', '')
        host_name = getattr(agent, 'host_name', '')
        host_ip = getattr(agent, 'host_ip', '')
        host_os = getattr(agent, 'host_os', '')
        status = getattr(agent, 'status', '')
        last_active_time = getattr(agent, 'last_active_time', '')
        output += f"{agent_id}\t{agent_version}\t{agent_type}\t{host_name}\t{host_ip}\t{host_os}\t{status}\t{last_active_time}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n客户端列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
        if end + 1 < total:
            output += f"可以使用 --offset={end + 1} 参数继续获取后续数据"
    print(output)


try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ListAgentRequest()
    if args.limit:
        request.limit = args.limit
    if args.status:
        request.status = args.status
    if args.agent_id:
        request.agent_id = args.agent_id

    response = client.list_agent(request)
    agents = getattr(response, 'agents', []) or []
    count = getattr(response, 'count', 0)

    if not agents:
        print(f"没有找到客户端 (区域: {Region})")
        exit(0)

    render(agents)
except Exception as e:
    print(f"cbr.list_agent 查询失败: {e}")
    exit(1)
