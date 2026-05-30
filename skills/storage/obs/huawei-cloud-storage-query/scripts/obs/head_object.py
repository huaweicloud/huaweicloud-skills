import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import HeadObjectRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="获取对象元数据")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bucket_name", type=str, required=True, help="桶名称，可通过 list_buckets.py 获取")
parser.add_argument("--object_key", type=str, required=True, help="对象键，可通过 list_objects.py 获取")
parser.add_argument("--version_id", type=str, help="版本ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = HeadObjectRequest()
    request.bucket_name = args.bucket_name
    request.object_key = args.object_key
    if args.version_id:
        request.version_id = args.version_id

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.head_object(request)

    content_length = getattr(response, 'content_length', 0)
    e_tag = getattr(response, 'e_tag', '')
    storage_class = getattr(response, 'x_obs_storage_class', '')
    version_id = getattr(response, 'x_obs_version_id', '')
    object_type = getattr(response, 'x_obs_object_type', '')
    restore = getattr(response, 'x_obs_restore', '')

    output = "对象元数据:\n"
    output += f"内容长度: {content_length}\n"
    output += f"ETag: {e_tag}\n"
    output += f"存储类型: {storage_class}\n"
    output += f"版本ID: {version_id}\n"
    output += f"对象类型: {object_type}\n"
    output += f"恢复状态: {restore}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.head_object 查询失败: {e}")
    exit(1)
