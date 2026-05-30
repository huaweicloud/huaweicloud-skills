import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowDomainConsoleAclPolicyRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 域控制台 ACL 策略 (v3)")
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

    request = ShowDomainConsoleAclPolicyRequest()
    request.domain_id = args.domain_id
    response = client.show_domain_console_acl_policy(request)
    item = response.console_acl_policy

    if not item:
        print(f"没有找到 IAM 域控制台 ACL 策略 (区域: {Region}, 域 ID: {args.domain_id})")
        exit(0)

    allow_address_netmasks = getattr(item, 'allow_address_netmasks', []) or []
    allow_ip_ranges = getattr(item, 'allow_ip_ranges', []) or []
    allow_address_netmasks_ipv6 = getattr(item, 'allow_address_netmasks_ipv6', []) or []
    allow_ip_ranges_ipv6 = getattr(item, 'allow_ip_ranges_ipv6', []) or []
    addr_str = '; '.join([str(x) for x in allow_address_netmasks]) if allow_address_netmasks else ''
    ip_str = '; '.join([str(x) for x in allow_ip_ranges]) if allow_ip_ranges else ''
    addr_ipv6_str = '; '.join([str(x) for x in allow_address_netmasks_ipv6]) if allow_address_netmasks_ipv6 else ''
    ip_ipv6_str = '; '.join([str(x) for x in allow_ip_ranges_ipv6]) if allow_ip_ranges_ipv6 else ''
    print(f"allow_address_netmasks\tallow_ip_ranges\tallow_address_netmasks_ipv6\tallow_ip_ranges_ipv6\n{addr_str}\t{ip_str}\t{addr_ipv6_str}\t{ip_ipv6_str}")
except Exception as e:
    print(f"iam.show_domain_console_acl_policy 查询失败: {e}")
    exit(1)
