import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowSecurityGroupRuleRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询安全组规则详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--security_group_rule_id", type=str, required=True, help="安全组规则 ID（必填），可通过 list_security_group_rules.py 获取")
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

    request = ShowSecurityGroupRuleRequest()
    request.security_group_rule_id = args.security_group_rule_id
    response = client.show_security_group_rule(request)
    item = response.security_group_rule
    if not item:
        print(f"没有找到安全组规则")
        exit(0)

    id = getattr(item, 'id', '')
    description = getattr(item, 'description', '')
    security_group_id = getattr(item, 'security_group_id', '')
    direction = getattr(item, 'direction', '')
    protocol = getattr(item, 'protocol', '')
    ethertype = getattr(item, 'ethertype', '')
    multiport = getattr(item, 'multiport', '')
    action = getattr(item, 'action', '')
    priority = getattr(item, 'priority', '')
    remote_group_id = getattr(item, 'remote_group_id', '')
    remote_ip_prefix = getattr(item, 'remote_ip_prefix', '')
    remote_address_group_id = getattr(item, 'remote_address_group_id', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    project_id = getattr(item, 'project_id', '')
    enabled = getattr(item, 'enabled', '')
    output = f"id\tdescription\tsecurity_group_id\tdirection\tprotocol\tethertype\tmultiport\taction\tpriority\tremote_group_id\tremote_ip_prefix\tremote_address_group_id\tcreated_at\tupdated_at\tproject_id\tenabled\n"
    output += f"{id}\t{description}\t{security_group_id}\t{direction}\t{protocol}\t{ethertype}\t{multiport}\t{action}\t{priority}\t{remote_group_id}\t{remote_ip_prefix}\t{remote_address_group_id}\t{created_at}\t{updated_at}\t{project_id}\t{enabled}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_security_group_rule 查询失败: {e}")
    exit(1)
