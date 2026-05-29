import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowDomainLoginPolicyRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 域登录策略 (v3)")
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

    request = ShowDomainLoginPolicyRequest()
    request.domain_id = args.domain_id
    response = client.show_domain_login_policy(request)
    item = response.login_policy

    if not item:
        print(f"没有找到 IAM 域登录策略 (区域: {Region}, 域 ID: {args.domain_id})")
        exit(0)

    account_validity_period = getattr(item, 'account_validity_period', '')
    custom_info_for_login = getattr(item, 'custom_info_for_login', '')
    lockout_duration = getattr(item, 'lockout_duration', '')
    login_failed_times = getattr(item, 'login_failed_times', '')
    period_with_login_failures = getattr(item, 'period_with_login_failures', '')
    session_timeout = getattr(item, 'session_timeout', '')
    show_recent_login_info = getattr(item, 'show_recent_login_info', '')
    print(f"account_validity_period\tcustom_info_for_login\tlockout_duration\tlogin_failed_times\tperiod_with_login_failures\tsession_timeout\tshow_recent_login_info\n{account_validity_period}\t{custom_info_for_login}\t{lockout_duration}\t{login_failed_times}\t{period_with_login_failures}\t{session_timeout}\t{show_recent_login_info}")
except Exception as e:
    print(f"iam.show_domain_login_policy 查询失败: {e}")
    exit(1)
