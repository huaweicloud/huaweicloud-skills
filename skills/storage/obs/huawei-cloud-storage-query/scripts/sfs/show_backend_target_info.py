import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ShowBackendTargetInfoRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询后端存储目标详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--share_id", type=str, required=True, help="文件系统ID，可通过 list_shares.py 获取")
parser.add_argument("--target_id", type=str, required=True, help="后端存储目标ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowBackendTargetInfoRequest()
    request.share_id = args.share_id
    request.target_id = args.target_id

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.show_backend_target_info(request)

    target_id = getattr(response, 'target_id', '')
    file_system_path = getattr(response, 'file_system_path', '')
    lifecycle = getattr(response, 'lifecycle', '')

    output = "后端存储目标详情:\n"
    output += f"目标ID: {target_id}\n"
    output += f"联动目录: {file_system_path}\n"
    output += f"绑定状态: {lifecycle}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.show_backend_target_info 查询失败: {e}")
    exit(1)
