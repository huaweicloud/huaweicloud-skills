import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowL7RuleRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 转发规则详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--l7policy_id", type=str, required=True, help="转发策略 ID（必填），可通过 list_l7_policies.py 获取")
parser.add_argument("--l7rule_id", type=str, required=True, help="转发规则 ID（必填），可通过 list_l7_rules.py 获取")
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

    request = ShowL7RuleRequest()
    request.l7policy_id = args.l7policy_id
    request.l7rule_id = args.l7rule_id
    response = client.show_l7_rule(request)
    item = response.rule
    if not item:
        print(f"没有找到转发规则")
        exit(0)

    # 输出详情
    output = f"id\ttype\tcompare_type\tvalue\tkey\tadmin_state_up\tprovisioning_status\tinvert\n"
    id = getattr(item, 'id', '')
    type = getattr(item, 'type', '')
    compare_type = getattr(item, 'compare_type', '')
    value = getattr(item, 'value', '')
    key = getattr(item, 'key', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    provisioning_status = getattr(item, 'provisioning_status', '')
    invert = getattr(item, 'invert', '')
    output += f"{id}\t{type}\t{compare_type}\t{value}\t{key}\t{admin_state_up}\t{provisioning_status}\t{invert}\n"
    print(output)
except Exception as e:
    print(f"elb.show_l7_rule 查询失败: {e}")
    exit(1)
