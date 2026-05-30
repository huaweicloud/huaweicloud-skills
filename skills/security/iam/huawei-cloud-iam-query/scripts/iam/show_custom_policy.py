import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowCustomPolicyRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 自定义策略详情 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--role_id", type=str, required=True, help="策略 ID，可通过 list_custom_policies.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    request = ShowCustomPolicyRequest()
    request.role_id = args.role_id
    response = client.show_custom_policy(request)
    item = response.role

    if not item:
        print(f"没有找到 IAM 自定义策略 (区域: {Region}, 策略 ID: {args.role_id})")
        exit(0)

    id_ = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    display_name = getattr(item, 'display_name', '')
    type_ = getattr(item, 'type', '')
    catalog = getattr(item, 'catalog', '')
    description = getattr(item, 'description', '')
    description_cn = getattr(item, 'description_cn', '')
    domain_id = getattr(item, 'domain_id', '')
    references = getattr(item, 'references', '')
    created_time = getattr(item, 'created_time', '')
    updated_time = getattr(item, 'updated_time', '')
    links = getattr(item, 'links', None)
    links_str = str(links) if links else ''
    policy = getattr(item, 'policy', None)
    policy_str = str(policy) if policy else ''
    print(f"id\tname\tdisplay_name\ttype\tcatalog\tdescription\tdescription_cn\tdomain_id\treferences\tcreated_time\tupdated_time\tlinks\tpolicy\n{id_}\t{name}\t{display_name}\t{type_}\t{catalog}\t{description}\t{description_cn}\t{domain_id}\t{references}\t{created_time}\t{updated_time}\t{links_str}\t{policy_str}")
except Exception as e:
    print(f"iam.show_custom_policy 查询失败: {e}")
    exit(1)
