import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowDomainApiAclPolicyRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 域 API ACL 策略 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_id", type=str, required=True, help="域 ID")
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

    request = ShowDomainApiAclPolicyRequest()
    request.domain_id = args.domain_id
    response = client.show_domain_api_acl_policy(request)
    item = response.api_acl_policy

    if not item:
        print(f"没有找到 IAM 域 API ACL 策略 (区域: {Region}, 域 ID: {args.domain_id})")
        exit(0)

    allow_address_netmasks = getattr(item, 'allow_address_netmasks', []) or []
    allow_ip_ranges = getattr(item, 'allow_ip_ranges', []) or []
    allow_vpc_endpoints = getattr(item, 'allow_vpc_endpoints', []) or []
    addr_str = '; '.join([str(x) for x in allow_address_netmasks]) if allow_address_netmasks else ''
    ip_str = '; '.join([str(x) for x in allow_ip_ranges]) if allow_ip_ranges else ''
    vpc_str = '; '.join([str(x) for x in allow_vpc_endpoints]) if allow_vpc_endpoints else ''
    print(f"allow_address_netmasks\tallow_ip_ranges\tallow_vpc_endpoints\n{addr_str}\t{ip_str}\t{vpc_str}")
except Exception as e:
    print(f"iam.show_domain_api_acl_policy 查询失败: {e}")
    exit(1)
