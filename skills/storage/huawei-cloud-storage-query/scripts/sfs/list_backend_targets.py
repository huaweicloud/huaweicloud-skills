import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ListBackendTargetsRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询后端存储目标列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--share_id", type=str, required=True, help="文件系统ID，可通过 list_shares.py 获取")
parser.add_argument("--limit", type=int, default=50, help="查询列表返回元素个数，默认50")
parser.add_argument("--marker", type=str, help="查询列表偏移量")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListBackendTargetsRequest()
    request.share_id = args.share_id
    if args.limit is not None:
        request.limit = args.limit
    if args.marker:
        request.marker = args.marker

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.list_backend_targets(request)

    targets = getattr(response, 'targets', []) or []

    if not targets:
        print("查询结果为空")
        exit(0)

    output = f"文件系统 {args.share_id} 的后端存储目标列表:\n"
    output += "目标ID\t联动目录\t绑定状态\n"
    
    for target in targets:
        target_id = getattr(target, 'target_id', '')
        file_system_path = getattr(target, 'file_system_path', '')
        lifecycle = getattr(target, 'lifecycle', '')
        output += f"{target_id}\t{file_system_path}\t{lifecycle}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.list_backend_targets 查询失败: {e}")
    exit(1)
