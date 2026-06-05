import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowOpenIdConnectConfigRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM OpenID Connect 配置 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--idp_id", type=str, required=True, help="身份提供商 ID")
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

    request = ShowOpenIdConnectConfigRequest()
    request.idp_id = args.idp_id
    response = client.show_open_id_connect_config(request)
    item = response.openid_connect_config

    if not item:
        print(f"没有找到 IAM OpenID Connect 配置 (区域: {Region}, 身份提供商 ID: {args.idp_id})")
        exit(0)

    access_mode = getattr(item, 'access_mode', '')
    idp_url = getattr(item, 'idp_url', '')
    client_id = getattr(item, 'client_id', '')
    authorization_endpoint = getattr(item, 'authorization_endpoint', '')
    scope = getattr(item, 'scope', '')
    response_type = getattr(item, 'response_type', '')
    response_mode = getattr(item, 'response_mode', '')
    signing_key = getattr(item, 'signing_key', '')
    print(f"access_mode\tidp_url\tclient_id\tauthorization_endpoint\tscope\tresponse_type\tresponse_mode\tsigning_key\n{access_mode}\t{idp_url}\t{client_id}\t{authorization_endpoint}\t{scope}\t{response_type}\t{response_mode}\t{signing_key}")
except Exception as e:
    print(f"iam.show_open_id_connect_config 查询失败: {e}")
    exit(1)
