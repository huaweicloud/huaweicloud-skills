import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowDomainProtectPolicyRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 域保护策略 (v3)")
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

    request = ShowDomainProtectPolicyRequest()
    request.domain_id = args.domain_id
    response = client.show_domain_protect_policy(request)
    item = response.protect_policy

    if not item:
        print(f"没有找到 IAM 域保护策略 (区域: {Region}, 域 ID: {args.domain_id})")
        exit(0)

    operation_protection = getattr(item, 'operation_protection', '')
    allow_user = getattr(item, 'allow_user', None)
    allow_user_str = f"manage_accesskey={getattr(allow_user, 'manage_accesskey', '')};manage_email={getattr(allow_user, 'manage_email', '')};manage_mobile={getattr(allow_user, 'manage_mobile', '')};manage_password={getattr(allow_user, 'manage_password', '')}" if allow_user else ''
    mobile = getattr(item, 'mobile', '')
    email = getattr(item, 'email', '')
    admin_check = getattr(item, 'admin_check', '')
    scene = getattr(item, 'scene', '')
    print(f"operation_protection\tallow_user\tmobile\temail\tadmin_check\tscene\n{operation_protection}\t{allow_user_str}\t{mobile}\t{email}\t{admin_check}\t{scene}")
except Exception as e:
    print(f"iam.show_domain_protect_policy 查询失败: {e}")
    exit(1)
