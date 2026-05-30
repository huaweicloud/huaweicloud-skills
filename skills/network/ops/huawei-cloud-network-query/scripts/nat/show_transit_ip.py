import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ShowTransitIpRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询中转IP详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--transit_ip_id", type=str, required=True, help="中转 IP ID（必填），可通过 list_transit_ip.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = NatClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(NatRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 NAT 客户端")
        exit(-1)

    request = ShowTransitIpRequest()
    request.transit_ip_id = args.transit_ip_id
    response = client.show_transit_ip(request)
    item = response.transit_ip
    if not item:
        print(f"没有找到中转 IP")
        exit(0)

    id = getattr(item, 'id', '')
    ip_address = getattr(item, 'ip_address', '')
    network_interface_id = getattr(item, 'network_interface_id', '')
    gateway_id = getattr(item, 'gateway_id', '')
    virsubnet_id = getattr(item, 'virsubnet_id', '')
    status = getattr(item, 'status', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    tags = getattr(item, 'tags', [])
    tag_str = ';'.join([f"{getattr(t,'key','')}={getattr(t,'value','')}" for t in tags]) if tags else ''
    output = f"id\tip_address\tnetwork_interface_id\tgateway_id\tvirsubnet_id\tenterprise_project_id\tstatus\tcreated_at\tupdated_at\ttags\n"
    output += f"{id}\t{ip_address}\t{network_interface_id}\t{gateway_id}\t{virsubnet_id}\t{enterprise_project_id}\t{status}\t{created_at}\t{updated_at}\t{tag_str}\n"
    print(output)
except Exception as e:
    print(f"nat.show_transit_ip 查询失败: {e}")
    exit(1)
