import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import CinderListAvailabilityZonesRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询可用区列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = CinderListAvailabilityZonesRequest()

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.cinder_list_availability_zones(request)

    availability_zone_info = getattr(response, 'availability_zone_info', []) or []

    if not availability_zone_info:
        print("查询结果为空")
        exit(0)

    output = "可用区列表:\n"
    output += "可用区名称\t状态\n"
    
    for az in availability_zone_info:
        zone_name = getattr(az, 'zone_name', '')
        zone_state = getattr(az, 'zone_state', None)
        state = getattr(zone_state, 'available', False) if zone_state else False
        output += f"{zone_name}\t{state}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.cinder_list_availability_zones 查询失败: {e}")
    exit(1)
