import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowListenerRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 监听器详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--listener_id", type=str, required=True, help="监听器ID，可通过 list_listeners.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ShowListenerRequest()
    request.listener_id = args.listener_id
    response = client.show_listener(request)
    item = response.listener
    if not item:
        print(f"没有找到监听器")
        exit(0)

    # 输出详情
    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    protocol = getattr(item, 'protocol', '')
    protocol_port = getattr(item, 'protocol_port', '')
    loadbalancers = getattr(item, 'loadbalancers', [])
    loadbalancer_id = getattr(loadbalancers[0], 'id', '') if loadbalancers else ''
    default_pool_id = getattr(item, 'default_pool_id', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    connection_limit = getattr(item, 'connection_limit', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    tls_ciphers_policy = getattr(item, 'tls_ciphers_policy', '')
    security_policy_id = getattr(item, 'security_policy_id', '')
    http2_enable = getattr(item, 'http2_enable', '')
    keepalive_timeout = getattr(item, 'keepalive_timeout', '')
    client_timeout = getattr(item, 'client_timeout', '')
    member_timeout = getattr(item, 'member_timeout', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')

    output = f"id: {id}\n"
    output += f"name: {name}\n"
    output += f"description: {description}\n"
    output += f"protocol: {protocol}\n"
    output += f"protocol_port: {protocol_port}\n"
    output += f"loadbalancer_id: {loadbalancer_id}\n"
    output += f"default_pool_id: {default_pool_id}\n"
    output += f"admin_state_up: {admin_state_up}\n"
    output += f"connection_limit: {connection_limit}\n"
    output += f"enterprise_project_id: {enterprise_project_id}\n"
    output += f"tls_ciphers_policy: {tls_ciphers_policy}\n"
    output += f"security_policy_id: {security_policy_id}\n"
    output += f"http2_enable: {http2_enable}\n"
    output += f"keepalive_timeout: {keepalive_timeout}\n"
    output += f"client_timeout: {client_timeout}\n"
    output += f"member_timeout: {member_timeout}\n"
    output += f"created_at: {created_at}\n"
    output += f"updated_at: {updated_at}\n"
    print(output)
except Exception as e:
    print(f"elb.show_listener 查询失败: {e}")
    exit(1)
