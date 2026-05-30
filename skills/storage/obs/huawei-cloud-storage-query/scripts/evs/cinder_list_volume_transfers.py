import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import CinderListVolumeTransfersRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询云硬盘过户记录列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--limit", type=int, default=50, help="返回结果个数限制，默认50")
parser.add_argument("--offset", type=int, help="偏移量")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = CinderListVolumeTransfersRequest()
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

    response = client.cinder_list_volume_transfers(request)

    transfers = getattr(response, 'transfers', []) or []

    if not transfers:
        print("查询结果为空")
        exit(0)

    output = "云硬盘过户记录列表:\n"
    output += "过户记录ID\t名称\t云硬盘ID\n"
    
    for transfer in transfers:
        transfer_id = getattr(transfer, 'id', '')
        name = getattr(transfer, 'name', '')
        volume_id = getattr(transfer, 'volume_id', '')
        output += f"{transfer_id}\t{name}\t{volume_id}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.cinder_list_volume_transfers 查询失败: {e}")
    exit(1)
