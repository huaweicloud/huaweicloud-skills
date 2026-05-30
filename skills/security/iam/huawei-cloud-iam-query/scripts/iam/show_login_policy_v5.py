import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import ShowLoginPolicyV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 登录策略 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
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

    request = ShowLoginPolicyV5Request()
    response = client.show_login_policy_v5(request)
    item = response.login_policy

    if not item:
        print(f"没有找到 IAM 登录策略 (区域: {Region})")
        exit(0)

    user_validity_period = getattr(item, 'user_validity_period', '')
    custom_info_for_login = getattr(item, 'custom_info_for_login', '')
    lockout_duration = getattr(item, 'lockout_duration', '')
    login_failed_times = getattr(item, 'login_failed_times', '')
    period_with_login_failures = getattr(item, 'period_with_login_failures', '')
    session_timeout = getattr(item, 'session_timeout', '')
    show_recent_login_info = getattr(item, 'show_recent_login_info', '')
    allow_address_netmasks = getattr(item, 'allow_address_netmasks', []) or []
    allow_ip_ranges = getattr(item, 'allow_ip_ranges', []) or []
    addr_str = '; '.join([str(x) for x in allow_address_netmasks]) if allow_address_netmasks else ''
    ip_str = '; '.join([str(x) for x in allow_ip_ranges]) if allow_ip_ranges else ''
    print(f"user_validity_period\tcustom_info_for_login\tlockout_duration\tlogin_failed_times\tperiod_with_login_failures\tsession_timeout\tshow_recent_login_info\tallow_address_netmasks\tallow_ip_ranges\n{user_validity_period}\t{custom_info_for_login}\t{lockout_duration}\t{login_failed_times}\t{period_with_login_failures}\t{session_timeout}\t{show_recent_login_info}\t{addr_str}\t{ip_str}")
except Exception as e:
    print(f"iam.show_login_policy_v5 查询失败: {e}")
    exit(1)
