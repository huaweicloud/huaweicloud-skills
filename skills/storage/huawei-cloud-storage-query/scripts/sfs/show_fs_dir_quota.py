import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ShowFsDirQuotaRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询文件系统目录配额")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--share_id", type=str, required=True, help="文件系统ID，可通过 list_shares.py 获取")
parser.add_argument("--path", type=str, required=True, help="目录路径")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowFsDirQuotaRequest()
    request.share_id = args.share_id
    request.path = args.path

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.show_fs_dir_quota(request)

    path = getattr(response, 'path', '')
    capacity = getattr(response, 'capacity', 0)
    inode = getattr(response, 'inode', 0)
    used_capacity = getattr(response, 'used_capacity', 0)
    used_inode = getattr(response, 'used_inode', 0)

    output = "文件系统目录配额:\n"
    output += f"路径: {path}\n"
    output += f"容量配额: {capacity}\n"
    output += f"Inode配额: {inode}\n"
    output += f"已用容量: {used_capacity}\n"
    output += f"已用Inode: {used_inode}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.show_fs_dir_quota 查询失败: {e}")
    exit(1)
