import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import CinderListVolumeTypesRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询云硬盘类型列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = CinderListVolumeTypesRequest()

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.cinder_list_volume_types(request)

    volume_types = getattr(response, 'volume_types', []) or []

    if not volume_types:
        print("查询结果为空")
        exit(0)

    output = "云硬盘类型列表:\n"
    output += "类型ID\t类型名称\t描述\n"
    
    for vt in volume_types:
        vt_id = getattr(vt, 'id', '')
        name = getattr(vt, 'name', '')
        description = getattr(vt, 'description', '')
        output += f"{vt_id}\t{name}\t{description}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.cinder_list_volume_types 查询失败: {e}")
    exit(1)
