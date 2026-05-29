import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowMigrateStatusRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 迁移状态")
parser.add_argument("--project_id", type=str, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--all_regions", type=bool, help="是否查询所有区域")
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

    request = ShowMigrateStatusRequest()
    if args.all_regions:
        request.all_regions = args.all_regions
    response = client.show_migrate_status(request)

    output = ""
    status = getattr(response, 'status', '')
    output += f"status: {status}\n"

    project_status = getattr(response, 'project_status', []) or []
    if project_status:
        output += f"\nproject_status ({len(project_status)}):\n"
        for ps in project_status:
            output += f"  {ps}\n"

    print(output)
except Exception as e:
    print(f"cbr.show_migrate_status 查询失败: {e}")
    exit(1)
