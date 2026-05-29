import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ShowActiveDirectoryDomainRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询文件系统AD域信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--share_id", type=str, required=True, help="文件系统ID，可通过 list_shares.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowActiveDirectoryDomainRequest()
    request.share_id = args.share_id

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.show_active_directory_domain(request)

    domain_name = getattr(response, 'domain_name', '')
    status = getattr(response, 'status', '')

    output = "文件系统AD域信息:\n"
    output += f"域名: {domain_name}\n"
    output += f"状态: {status}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.show_active_directory_domain 查询失败: {e}")
    exit(1)
