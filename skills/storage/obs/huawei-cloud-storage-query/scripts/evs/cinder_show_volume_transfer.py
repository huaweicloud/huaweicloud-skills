import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import CinderShowVolumeTransferRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询云硬盘过户记录详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--transfer_id", type=str, required=True, help="云硬盘过户记录ID，可通过 cinder_list_volume_transfers.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = CinderShowVolumeTransferRequest()
    request.transfer_id = args.transfer_id

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.cinder_show_volume_transfer(request)

    transfer = getattr(response, 'transfer', None)
    if not transfer:
        print("查询结果为空")
        exit(0)

    output = "云硬盘过户记录详情:\n"
    output += f"过户记录ID: {getattr(transfer, 'id', '')}\n"
    output += f"名称: {getattr(transfer, 'name', '')}\n"
    output += f"云硬盘ID: {getattr(transfer, 'volume_id', '')}\n"
    output += f"创建时间: {getattr(transfer, 'created_at', '')}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.cinder_show_volume_transfer 查询失败: {e}")
    exit(1)
