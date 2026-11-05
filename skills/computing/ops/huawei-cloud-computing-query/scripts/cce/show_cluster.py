import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import ShowClusterRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 参数
parser = argparse.ArgumentParser(description="查询 CCE 集群详情")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--cluster_id", type=str, required=True, help="集群 ID（UUID），可通过 list_clusters.py 获取")
parser.add_argument("--detail", type=str, help="是否返回集群详细信息，取值 true 或 false，不传则仅返回基本信息")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

Region = args.region


# 渲染
def render(cluster):
    metadata = getattr(cluster, 'metadata', None)
    spec = getattr(cluster, 'spec', None)
    status = getattr(cluster, 'status', None)

    output = ""
    output += f"id: {getattr(metadata, 'uid', '') if metadata else ''}\n"
    output += f"name: {getattr(metadata, 'name', '') if metadata else ''}\n"
    output += f"alias: {getattr(metadata, 'alias', '') if metadata else ''}\n"
    output += f"status: {getattr(status, 'phase', '') if status else ''}\n"
    output += f"type: {getattr(spec, 'type', '') if spec else ''}\n"
    output += f"category: {getattr(spec, 'category', '') if spec else ''}\n"
    output += f"version: {getattr(spec, 'version', '') if spec else ''}\n"
    output += f"platform_version: {getattr(spec, 'platform_version', '') if spec else ''}\n"
    output += f"flavor: {getattr(spec, 'flavor', '') if spec else ''}\n"
    output += f"az: {getattr(spec, 'az', '') if spec else ''}\n"
    output += f"billing_mode: {getattr(spec, 'billing_mode', '') if spec else ''}\n"
    output += f"kube_proxy_mode: {getattr(spec, 'kube_proxy_mode', '') if spec else ''}\n"
    output += f"ipv6enable: {getattr(spec, 'ipv6enable', '') if spec else ''}\n"
    output += f"deletion_protection: {getattr(spec, 'deletion_protection', '') if spec else ''}\n"
    output += f"description: {getattr(spec, 'description', '') if spec else ''}\n"
    output += f"created: {getattr(metadata, 'creation_timestamp', '') if metadata else ''}\n"
    output += f"updated: {getattr(metadata, 'update_timestamp', '') if metadata else ''}\n"

    # 网络信息
    container_network = getattr(spec, 'container_network', None) if spec else None
    container_mode = getattr(container_network, 'mode', '') if container_network else ''
    container_cidr = getattr(container_network, 'cidr', '') if container_network else ''
    output += f"container_network: {container_mode}{' / ' + container_cidr if container_cidr else ''}\n"
    service_network = getattr(spec, 'service_network', None) if spec else None
    output += f"service_network: {getattr(service_network, 'i_pv4_cidr', '') if service_network else ''}\n"
    host_network = getattr(spec, 'host_network', None) if spec else None
    if host_network:
        output += f"host_network: vpc={getattr(host_network, 'vpc', '')} subnet={getattr(host_network, 'subnet', '')} security_group={getattr(host_network, 'security_group', '')}\n"
    else:
        output += "host_network: \n"
    eni_network = getattr(spec, 'eni_network', None) if spec else None
    output += f"eni_network: {getattr(eni_network, 'eni_subnet_id', '') if eni_network else ''}\n"

    # 访问地址
    endpoints = getattr(status, 'endpoints', None) if status else None
    if endpoints:
        endpoint_text = "; ".join(f"{getattr(ep, 'type', '')}={getattr(ep, 'url', '')}" for ep in endpoints)
    else:
        endpoint_text = ""
    output += f"endpoints: {endpoint_text}\n"

    # 异常与锁定信息
    output += f"is_locked: {getattr(status, 'is_locked', '') if status else ''}\n"
    output += f"reason: {getattr(status, 'reason', '') if status else ''}\n"
    output += f"message: {getattr(status, 'message', '') if status else ''}\n"

    # 状态条件
    conditions = getattr(status, 'conditions', None) if status else None
    if conditions:
        condition_text = "; ".join(f"{getattr(c, 'type', '')}={getattr(c, 'status', '')}" for c in conditions)
        output += f"conditions: {condition_text}\n"
    else:
        output += "conditions: \n"

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

    request = ShowClusterRequest()
    request.cluster_id = args.cluster_id
    if args.detail:
        request.detail = args.detail

    response = client.show_cluster(request)
    cluster = response
    if not cluster or not getattr(cluster, 'metadata', None):
        print(f"没有找到 CCE 集群 (区域: {Region}, 集群 ID: {args.cluster_id})")
        exit(0)

    # 渲染结果
    render(cluster)
except Exception as e:
    print(f"cce.cluster 查询失败: {e}")
    exit(1)
