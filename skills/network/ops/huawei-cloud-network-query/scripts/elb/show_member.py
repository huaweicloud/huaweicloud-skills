import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowMemberRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 后端服务器详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--pool_id", type=str, required=True, help="后端服务器组 ID（必填），可通过 list_pools.py 获取")
parser.add_argument("--member_id", type=str, required=True, help="后端服务器 ID（必填）")
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

    request = ShowMemberRequest()
    request.pool_id = args.pool_id
    request.member_id = args.member_id
    response = client.show_member(request)
    item = response.member
    if not item:
        print(f"没有找到后端服务器")
        exit(0)

    # 输出详情
    output = f"id\tname\taddress\tprotocol_port\tweight\tadmin_state_up\toperating_status\tsubnet_cidr_id\tip_version\n"
    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    address = getattr(item, 'address', '')
    protocol_port = getattr(item, 'protocol_port', '')
    weight = getattr(item, 'weight', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    operating_status = getattr(item, 'operating_status', '')
    subnet_cidr_id = getattr(item, 'subnet_cidr_id', '')
    ip_version = getattr(item, 'ip_version', '')
    output += f"{id}\t{name}\t{address}\t{protocol_port}\t{weight}\t{admin_state_up}\t{operating_status}\t{subnet_cidr_id}\t{ip_version}\n"
    print(output)
except Exception as e:
    print(f"elb.show_member 查询失败: {e}")
    exit(1)
