import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ShowQuotaRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询文件系统配额")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowQuotaRequest()

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.show_quota(request)

    quotas = getattr(response, 'quotas', None)
    all_items = getattr(quotas, 'resources', []) if quotas else []

    if not all_items:
        print("查询结果为空")
        exit(0)

    output = "文件系统配额:\n"
    for item in all_items:
        q_type = getattr(item, 'type', '')
        used = getattr(item, 'used', 0)
        quota = getattr(item, 'quota', 0)
        unit = getattr(item, 'unit', '')
        output += f"{q_type}: 已使用 {used}, 配额 {quota} {unit}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.show_quota 查询失败: {e}")
    exit(1)
