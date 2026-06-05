import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import ListVolumesRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询云硬盘列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--name", type=str, help="磁盘名称(支持模糊匹配)")
parser.add_argument("--status", type=str, help="云硬盘状态")
parser.add_argument("--limit", type=int, default=50, help="返回结果个数限制，默认50")
parser.add_argument("--offset", type=int, help="偏移量")
parser.add_argument("--sort_key", type=str, help="排序关键字")
parser.add_argument("--sort_dir", type=str, help="排序方向：asc/desc")
parser.add_argument("--availability_zone", type=str, help="可用区")
parser.add_argument("--volume_type_id", type=str, help="云硬盘类型ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListVolumesRequest()
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status
    if args.limit is not None:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset
    if args.sort_key:
        request.sort_key = args.sort_key
    if args.sort_dir:
        request.sort_dir = args.sort_dir
    if args.availability_zone:
        request.availability_zone = args.availability_zone
    if args.volume_type_id:
        request.volume_type_id = args.volume_type_id

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.list_volumes(request)

    volumes = getattr(response, 'volumes', []) or []
    count = getattr(response, 'count', 0)

    if not volumes:
        print("查询结果为空")
        exit(0)

    output = f"云硬盘列表（共{count}个）:\n"
    output += "云硬盘ID\t名称\t状态\t大小(GB)\t类型\t可用区\t加密\t创建时间\n"
    
    for volume in volumes:
        vol_id = getattr(volume, 'id', '')
        name = getattr(volume, 'name', '')
        status = getattr(volume, 'status', '')
        size = getattr(volume, 'size', 0)
        volume_type = getattr(volume, 'volume_type', '')
        az = getattr(volume, 'availability_zone', '')
        encrypted = getattr(volume, 'encrypted', False)
        created_at = getattr(volume, 'created_at', '')
        output += f"{vol_id}\t{name}\t{status}\t{size}\t{volume_type}\t{az}\t{encrypted}\t{created_at}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.list_volumes 查询失败: {e}")
    exit(1)
