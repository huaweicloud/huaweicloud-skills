import argparse
import sys
import os



sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ListFsTasksRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询文件系统任务列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--share_id", type=str, required=True, help="文件系统ID，可通过 list_shares.py 获取")
parser.add_argument("--feature", type=str, help="任务类型")
parser.add_argument("--marker", type=str, help="分页标记")
parser.add_argument("--limit", type=int, default=50, help="分页大小，默认50")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListFsTasksRequest()
    request.share_id = args.share_id
    if args.feature:
        request.feature = args.feature
    if args.marker:
        request.marker = args.marker
    if args.limit is not None:
        request.limit = args.limit

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.list_fs_tasks(request)

    tasks = getattr(response, 'tasks', []) or []

    if not tasks:
        print("查询结果为空")
        exit(0)

    output = f"文件系统 {args.share_id} 的任务列表:\n"
    output += "任务ID\t状态\t开始时间\t结束时间\n"
    
    for task in tasks:
        task_id = getattr(task, 'task_id', '')
        status = getattr(task, 'status', '')
        begin_time = getattr(task, 'begin_time', '')
        end_time = getattr(task, 'end_time', '')
        output += f"{task_id}\t{status}\t{begin_time}\t{end_time}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.list_fs_tasks 查询失败: {e}")
    exit(1)
