import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import ListBucketsRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="列出桶列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListBucketsRequest()

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.list_buckets(request)

    buckets_obj = getattr(response, 'buckets', None)

    if not buckets_obj:
        print("查询结果为空")
        exit(0)

    buckets = getattr(buckets_obj, 'bucket', []) or []

    if not buckets:
        print("查询结果为空")
        exit(0)

    output = "桶列表:\n"
    output += "桶名称\t创建时间\t位置\n"

    for bucket in buckets:
        name = getattr(bucket, 'name', '')
        creation_date = getattr(bucket, 'creation_date', '')
        location = getattr(bucket, 'location', '')
        output += f"{name}\t{creation_date}\t{location}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.list_buckets 查询失败: {e}")
    exit(1)
