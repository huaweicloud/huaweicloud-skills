import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowDomainRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询租户信息")
parser.add_argument("--project_id", type=str, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--source_project_id", type=str, required=True, help="源项目ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ShowDomainRequest()
    request.source_project_id = args.source_project_id
    response = client.show_domain(request)

    output = ""
    output += f"project_name: {getattr(response, 'project_name', '')}\n"
    output += f"project_id: {getattr(response, 'project_id', '')}\n"
    output += f"domain_id: {getattr(response, 'domain_id', '')}\n"
    output += f"domain_name: {getattr(response, 'domain_name', '')}\n"
    print(output)
except Exception as e:
    print(f"cbr.show_domain 查询失败: {e}")
    exit(1)
