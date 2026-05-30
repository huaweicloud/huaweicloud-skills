import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import ShowSnapshotRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询云硬盘快照详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--snapshot_id", type=str, required=True, help="快照ID，可通过 list_snapshots.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowSnapshotRequest()
    request.snapshot_id = args.snapshot_id

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.show_snapshot(request)

    snapshot = getattr(response, 'snapshot', None)
    if not snapshot:
        print("查询结果为空")
        exit(0)

    output = "快照详情:\n"
    output += f"快照ID: {getattr(snapshot, 'id', '')}\n"
    output += f"名称: {getattr(snapshot, 'name', '')}\n"
    output += f"状态: {getattr(snapshot, 'status', '')}\n"
    output += f"云硬盘ID: {getattr(snapshot, 'volume_id', '')}\n"
    output += f"大小(GB): {getattr(snapshot, 'size', 0)}\n"
    output += f"描述: {getattr(snapshot, 'description', '')}\n"
    output += f"创建时间: {getattr(snapshot, 'created_at', '')}\n"
    output += f"更新时间: {getattr(snapshot, 'updated_at', '')}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.show_snapshot 查询失败: {e}")
    exit(1)
