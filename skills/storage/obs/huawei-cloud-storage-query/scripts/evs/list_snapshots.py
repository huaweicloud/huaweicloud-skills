import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import ListSnapshotsRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询云硬盘快照列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--name", type=str, help="快照名称(支持模糊匹配)")
parser.add_argument("--status", type=str, help="快照状态")
parser.add_argument("--volume_id", type=str, help="所属云硬盘ID")
parser.add_argument("--limit", type=int, default=50, help="返回结果个数限制，默认50")
parser.add_argument("--offset", type=int, help="偏移量")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListSnapshotsRequest()
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status
    if args.volume_id:
        request.volume_id = args.volume_id
    if args.limit is not None:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.list_snapshots(request)

    snapshots = getattr(response, 'snapshots', []) or []
    count = getattr(response, 'count', 0)

    if not snapshots:
        print("查询结果为空")
        exit(0)

    output = f"云硬盘快照列表（共{count}个）:\n"
    output += "快照ID\t名称\t状态\t云硬盘ID\t大小(GB)\t创建时间\n"
    
    for snapshot in snapshots:
        snap_id = getattr(snapshot, 'id', '')
        name = getattr(snapshot, 'name', '')
        status = getattr(snapshot, 'status', '')
        volume_id = getattr(snapshot, 'volume_id', '')
        size = getattr(snapshot, 'size', 0)
        created_at = getattr(snapshot, 'created_at', '')
        output += f"{snap_id}\t{name}\t{status}\t{volume_id}\t{size}\t{created_at}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.list_snapshots 查询失败: {e}")
    exit(1)
