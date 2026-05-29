import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import ShowRecyclePolicyRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询回收站策略")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowRecyclePolicyRequest()

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.show_recycle_policy(request)

    switch = getattr(response, 'switch', False)
    threshold_time = getattr(response, 'threshold_time', 0)
    keep_time = getattr(response, 'keep_time', 0)

    output = "回收站策略:\n"
    output += f"回收站开关: {'开启' if switch else '关闭'}\n"
    output += f"门槛时间(天): {threshold_time}\n"
    output += f"保存期限(天): {keep_time}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.show_recycle_policy 查询失败: {e}")
    exit(1)
