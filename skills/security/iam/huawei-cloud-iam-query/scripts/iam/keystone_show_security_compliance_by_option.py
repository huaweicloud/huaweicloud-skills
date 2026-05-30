import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneShowSecurityComplianceByOptionRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="按选项查询安全合规配置 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_id", type=str, required=True, help="待查询的账号 ID")
parser.add_argument("--option", type=str, required=True, choices=["password_regex", "password_regex_description"], help="查询条件：password_regex(密码强度正则表达式) 或 password_regex_description(密码强度描述)")
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

    request = KeystoneShowSecurityComplianceByOptionRequest()
    request.domain_id = args.domain_id
    request.option = args.option
    response = client.keystone_show_security_compliance_by_option(request)
    item = response.config
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"password_regex\tpassword_regex_description\n"
    password_regex = getattr(item, 'password_regex', '')
    password_regex_description = getattr(item, 'password_regex_description', '')
    output += f"{password_regex}\t{password_regex_description}\n"
    print(output)
except Exception as e:
    print(f"iam.keystone_show_security_compliance_by_option 查询失败: {e}")
    exit(1)
