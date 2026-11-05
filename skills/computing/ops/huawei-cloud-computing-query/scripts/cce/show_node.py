import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import ShowNodeRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 参数
parser = argparse.ArgumentParser(description="查询 CCE 节点详情")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--cluster_id", type=str, required=True, help="集群 ID（UUID），可通过 list_clusters.py 获取")
parser.add_argument("--node_id", type=str, required=True, help="节点 ID（UUID），可通过 list_nodes.py 获取")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

Region = args.region


# 渲染
def render(node):
    metadata = getattr(node, 'metadata', None)
    spec = getattr(node, 'spec', None)
    status = getattr(node, 'status', None)

    output = ""
    output += f"id: {getattr(metadata, 'uid', '') if metadata else ''}\n"
    output += f"name: {getattr(metadata, 'name', '') if metadata else ''}\n"
    output += f"status: {getattr(status, 'phase', '') if status else ''}\n"
    output += f"flavor: {getattr(spec, 'flavor', '') if spec else ''}\n"
    output += f"az: {getattr(spec, 'az', '') if spec else ''}\n"
    output += f"os: {getattr(spec, 'os', '') if spec else ''}\n"
    output += f"billing_mode: {getattr(spec, 'billing_mode', '') if spec else ''}\n"
    output += f"ecs_group_id: {getattr(spec, 'ecs_group_id', '') if spec else ''}\n"
    output += f"partition: {getattr(spec, 'partition', '') if spec else ''}\n"
    output += f"created: {getattr(metadata, 'creation_timestamp', '') if metadata else ''}\n"
    output += f"updated: {getattr(metadata, 'update_timestamp', '') if metadata else ''}\n"

    # 运行状态
    output += f"server_id: {getattr(status, 'server_id', '') if status else ''}\n"
    output += f"private_ip: {getattr(status, 'private_ip', '') if status else ''}\n"
    output += f"public_ip: {getattr(status, 'public_ip', '') if status else ''}\n"
    output += f"job_id: {getattr(status, 'job_id', '') if status else ''}\n"
    output += f"last_probe_time: {getattr(status, 'last_probe_time', '') if status else ''}\n"
    output += f"configuration_up_to_date: {getattr(status, 'configuration_up_to_date', '') if status else ''}\n"

    # 登录方式（只展示密钥名，不输出任何凭据值）
    login = getattr(spec, 'login', None) if spec else None
    output += f"ssh_key: {getattr(login, 'ssh_key', '') if login else ''}\n"

    # 磁盘
    root_volume = getattr(spec, 'root_volume', None) if spec else None
    if root_volume:
        output += f"root_volume: {getattr(root_volume, 'volumetype', '')} {getattr(root_volume, 'size', '')}GB\n"
    else:
        output += "root_volume: \n"
    data_volumes = getattr(spec, 'data_volumes', None) if spec else None
    if data_volumes:
        volume_text = "; ".join(f"{getattr(v, 'volumetype', '')} {getattr(v, 'size', '')}GB" for v in data_volumes)
        output += f"data_volumes: {volume_text}\n"
    else:
        output += "data_volumes: \n"

    # 节点池归属
    owner_references = getattr(metadata, 'owner_references', None) if metadata else None
    if owner_references:
        output += f"nodepool_name: {getattr(owner_references, 'nodepool_name', '')}\n"
        output += f"nodepool_id: {getattr(owner_references, 'nodepool_id', '')}\n"
    else:
        output += "nodepool_name: \n"
        output += "nodepool_id: \n"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()
    # 未指定 project_id 则自动获取
    if not args.project_id:
        args.project_id = get_project_id(Region, AK, SK, SecurityToken)
        if not args.project_id:
            print(f"无法获取项目 ID (region={Region})，请检查凭据或手动指定 --project_id")
            exit(-1)

    client = CceClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CceRegion.value_of(Region)).build()
    if not client:
        print("无法获取 CCE 客户端")
        exit(-1)

    request = ShowNodeRequest()
    request.cluster_id = args.cluster_id
    request.node_id = args.node_id

    response = client.show_node(request)
    node = response
    if not node or not getattr(node, 'metadata', None):
        print(f"没有找到 CCE 节点 (区域: {Region}, 集群 ID: {args.cluster_id}, 节点 ID: {args.node_id})")
        exit(0)

    # 渲染结果
    render(node)
except Exception as e:
    print(f"cce.node 查询失败: {e}")
    exit(1)
