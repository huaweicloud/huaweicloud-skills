import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import CinderListQuotasRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询配额列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--target_project_id", type=str, help="目标项目ID")
parser.add_argument("--usage", type=str, default="true", help="是否查询配额详细信息，默认true")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = CinderListQuotasRequest()
    request.target_project_id = args.target_project_id if args.target_project_id else args.project_id
    request.usage = args.usage

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.cinder_list_quotas(request)

    quota_set = getattr(response, 'quota_set', None)
    if not quota_set:
        print("查询结果为空")
        exit(0)

    output = "配额信息:\n"
    
    # 处理 volumes 配额
    volumes = getattr(quota_set, 'volumes', None)
    if volumes:
        output += "\n云硬盘配额:\n"
        output += f"类型\t已用\t配额\n"
        output += f"volumes\t{getattr(volumes, 'used', 0)}\t{getattr(volumes, 'limit', 0)}\n"
    
    # 处理 snapshots 配额
    snapshots = getattr(quota_set, 'snapshots', None)
    if snapshots:
        output += f"snapshots\t{getattr(snapshots, 'used', 0)}\t{getattr(snapshots, 'limit', 0)}\n"
    
    # 处理 gigabytes 配额
    gigabytes = getattr(quota_set, 'gigabytes', None)
    if gigabytes:
        output += f"gigabytes\t{getattr(gigabytes, 'used', 0)}\t{getattr(gigabytes, 'limit', 0)}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.cinder_list_quotas 查询失败: {e}")
    exit(1)
