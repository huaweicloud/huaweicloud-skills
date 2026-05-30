import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import GetBucketPolicyPublicStatusRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="获取桶策略公共状态")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bucket_name", type=str, required=True, help="桶名称，可通过 list_buckets.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = GetBucketPolicyPublicStatusRequest()
    request.bucket_name = args.bucket_name

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.get_bucket_policy_public_status(request)

    is_public = getattr(response, 'is_public', '')
    bucket_type = getattr(response, 'x_obs_bucket_type', '')

    output = "桶策略公共状态:\n"
    output += f"是否公共访问: {is_public}\n"
    output += f"桶类型: {bucket_type}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.get_bucket_policy_public_status 查询失败: {e}")
    exit(1)
