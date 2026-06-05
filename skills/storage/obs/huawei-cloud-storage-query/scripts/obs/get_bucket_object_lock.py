import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import GetBucketObjectLockRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="获取桶对象锁配置")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bucket_name", type=str, required=True, help="桶名称，可通过 list_buckets.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = GetBucketObjectLockRequest()
    request.bucket_name = args.bucket_name

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.get_bucket_object_lock(request)

    object_lock_config = getattr(response, 'object_lock_configuration', None)

    output = "桶对象锁配置:\n"
    if object_lock_config:
        object_lock_enabled = getattr(object_lock_config, 'object_lock_enabled', '')
        rule = getattr(object_lock_config, 'rule', None)
        output += f"是否启用对象锁: {object_lock_enabled}\n"
        if rule:
            default_retention = getattr(rule, 'default_retention', None)
            if default_retention:
                mode = getattr(default_retention, 'mode', '')
                days = getattr(default_retention, 'days', '')
                years = getattr(default_retention, 'years', '')
                output += f"默认保留模式: {mode}\n"
                output += f"默认保留天数: {days}\n"
                output += f"默认保留年数: {years}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.get_bucket_object_lock 查询失败: {e}")
    exit(1)
