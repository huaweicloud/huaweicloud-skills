import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowDomainPasswordPolicyRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 域密码策略 (v3)")
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

    request = ShowDomainPasswordPolicyRequest()
    request.domain_id = args.domain_id
    response = client.show_domain_password_policy(request)
    item = response.password_policy

    if not item:
        print(f"没有找到 IAM 域密码策略 (区域: {Region}, 域 ID: {args.domain_id})")
        exit(0)

    minimum_password_length = getattr(item, 'minimum_password_length', '')
    maximum_password_length = getattr(item, 'maximum_password_length', '')
    minimum_password_age = getattr(item, 'minimum_password_age', '')
    password_validity_period = getattr(item, 'password_validity_period', '')
    password_char_combination = getattr(item, 'password_char_combination', '')
    maximum_consecutive_identical_chars = getattr(item, 'maximum_consecutive_identical_chars', '')
    number_of_recent_passwords_disallowed = getattr(item, 'number_of_recent_passwords_disallowed', '')
    password_not_username_or_invert = getattr(item, 'password_not_username_or_invert', '')
    password_requirements = getattr(item, 'password_requirements', '')
    print(f"minimum_password_length\tmaximum_password_length\tminimum_password_age\tpassword_validity_period\tpassword_char_combination\tmaximum_consecutive_identical_chars\tnumber_of_recent_passwords_disallowed\tpassword_not_username_or_invert\tpassword_requirements\n{minimum_password_length}\t{maximum_password_length}\t{minimum_password_age}\t{password_validity_period}\t{password_char_combination}\t{maximum_consecutive_identical_chars}\t{number_of_recent_passwords_disallowed}\t{password_not_username_or_invert}\t{password_requirements}")
except Exception as e:
    print(f"iam.show_domain_password_policy 查询失败: {e}")
    exit(1)
