import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import ShowVolumeTagsRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询指定云硬盘的标签信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--volume_id", type=str, required=True, help="云硬盘ID，可通过 list_volumes.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowVolumeTagsRequest()
    request.volume_id = args.volume_id

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.show_volume_tags(request)

    tags = getattr(response, 'tags', []) or []

    if not tags:
        print("查询结果为空")
        exit(0)

    output = f"云硬盘 {args.volume_id} 的标签信息:\n"
    output += "标签键\t标签值\n"
    
    for tag in tags:
        key = getattr(tag, 'key', '')
        value = getattr(tag, 'value', '')
        output += f"{key}\t{value}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.show_volume_tags 查询失败: {e}")
    exit(1)
