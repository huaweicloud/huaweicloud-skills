import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowFirewallRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询防火墙详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--firewall_id", type=str, required=True, help="防火墙 ID（必填），可通过 list_firewall.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 VPC 客户端")
        exit(-1)

    request = ShowFirewallRequest()
    request.firewall_id = args.firewall_id
    response = client.show_firewall(request)
    item = response.firewall
    if not item:
        print(f"没有找到防火墙")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    project_id = getattr(item, 'project_id', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    status = getattr(item, 'status', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    tags = getattr(item, 'tags', [])
    associations = getattr(item, 'associations', [])
    ingress_rules = getattr(item, 'ingress_rules', [])
    egress_rules = getattr(item, 'egress_rules', [])
    fw_type = getattr(item, 'type', '')
    output = f"id\tname\tdescription\tproject_id\tcreated_at\tupdated_at\tadmin_state_up\tstatus\tenterprise_project_id\ttags\tassociations\tingress_rules\tegress_rules\ttype\n"
    output += f"{id}\t{name}\t{description}\t{project_id}\t{created_at}\t{updated_at}\t{admin_state_up}\t{status}\t{enterprise_project_id}\t{tags}\t{len(associations) if associations else 0}\t{len(ingress_rules) if ingress_rules else 0}\t{len(egress_rules) if egress_rules else 0}\t{fw_type}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_firewall 查询失败: {e}")
    exit(1)
