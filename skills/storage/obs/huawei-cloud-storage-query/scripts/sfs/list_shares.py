import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ListSharesRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询SFS Turbo文件系统列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--limit", type=int, default=50, help="返回的文件系统个数的最大值，默认50")
parser.add_argument("--offset", type=int, help="返回的文件系统的偏移量")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListSharesRequest()
    if args.limit is not None:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.list_shares(request)

    shares = getattr(response, 'shares', []) or []
    count = getattr(response, 'count', 0)

    if not shares:
        print("查询结果为空")
        exit(0)

    output = f"SFS Turbo文件系统列表（共{count}个）:\n"
    output += "文件系统ID\t名称\t状态\t容量(GB)\n"
    
    for share in shares:
        share_id = getattr(share, 'id', '')
        name = getattr(share, 'name', '')
        status = getattr(share, 'status', '')
        size = getattr(share, 'size', 0)
        output += f"{share_id}\t{name}\t{status}\t{size}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.list_shares 查询失败: {e}")
    exit(1)
