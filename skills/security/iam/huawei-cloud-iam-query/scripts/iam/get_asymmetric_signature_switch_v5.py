import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import GetAsymmetricSignatureSwitchV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询非对称签名开关 (v5)")
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

    request = GetAsymmetricSignatureSwitchV5Request()

    response = client.get_asymmetric_signature_switch_v5(request)
    item = response.asymmetric_signature
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"domain_id	asymmetric_signature_switch\n"
    domain_id = getattr(item, 'domain_id', '')
    asymmetric_signature_switch = getattr(item, 'asymmetric_signature_switch', '')
    output += f"{domain_id}	{asymmetric_signature_switch}\n"
    print(output)
except Exception as e:
    print(f"iam.get_asymmetric_signature_switch_v5 查询失败: {e}")
    exit(1)
