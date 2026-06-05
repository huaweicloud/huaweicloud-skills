import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import GetAccountSummaryV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询账号摘要 (v5)")
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

    request = GetAccountSummaryV5Request()

    response = client.get_account_summary_v5(request)
    item = response
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"users	users_quota	groups	groups_quota	agencies	agencies_quota	policies	policies_quota	policy_size_quota	versions_per_policy_quota	attached_policies_per_user_quota	attached_policies_per_group_quota	attached_policies_per_agency_quota	root_user_mfa_enabled\n"
    users = getattr(item, 'users', '')
    users_quota = getattr(item, 'users_quota', '')
    groups = getattr(item, 'groups', '')
    groups_quota = getattr(item, 'groups_quota', '')
    agencies = getattr(item, 'agencies', '')
    agencies_quota = getattr(item, 'agencies_quota', '')
    policies = getattr(item, 'policies', '')
    policies_quota = getattr(item, 'policies_quota', '')
    policy_size_quota = getattr(item, 'policy_size_quota', '')
    versions_per_policy_quota = getattr(item, 'versions_per_policy_quota', '')
    attached_policies_per_user_quota = getattr(item, 'attached_policies_per_user_quota', '')
    attached_policies_per_group_quota = getattr(item, 'attached_policies_per_group_quota', '')
    attached_policies_per_agency_quota = getattr(item, 'attached_policies_per_agency_quota', '')
    root_user_mfa_enabled = getattr(item, 'root_user_mfa_enabled', '')
    output += f"{users}	{users_quota}	{groups}	{groups_quota}	{agencies}	{agencies_quota}	{policies}	{policies_quota}	{policy_size_quota}	{versions_per_policy_quota}	{attached_policies_per_user_quota}	{attached_policies_per_group_quota}	{attached_policies_per_agency_quota}	{root_user_mfa_enabled}\n"
    print(output)
except Exception as e:
    print(f"iam.get_account_summary_v5 查询失败: {e}")
    exit(1)
