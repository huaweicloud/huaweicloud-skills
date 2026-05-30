import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ShowFsTaskRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询文件系统任务详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--share_id", type=str, required=True, help="文件系统ID，可通过 list_shares.py 获取")
parser.add_argument("--feature", type=str, required=True, help="任务类型")
parser.add_argument("--task_id", type=str, required=True, help="任务ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowFsTaskRequest()
    request.share_id = args.share_id
    request.feature = args.feature
    request.task_id = args.task_id

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.show_fs_task(request)

    task_id = getattr(response, 'task_id', '')
    status = getattr(response, 'status', '')
    begin_time = getattr(response, 'begin_time', '')
    end_time = getattr(response, 'end_time', '')

    output = "文件系统任务详情:\n"
    output += f"任务ID: {task_id}\n"
    output += f"状态: {status}\n"
    output += f"开始时间: {begin_time}\n"
    output += f"结束时间: {end_time}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.show_fs_task 查询失败: {e}")
    exit(1)
