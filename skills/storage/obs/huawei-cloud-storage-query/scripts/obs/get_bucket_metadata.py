import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import GetBucketMetadataRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="获取桶元数据")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bucket_name", type=str, required=True, help="桶名称，可通过 list_buckets.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = GetBucketMetadataRequest()
    request.bucket_name = args.bucket_name

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.get_bucket_metadata(request)

    date = getattr(response, 'date', '')
    location = getattr(response, 'x_obs_bucket_location', '')
    storage_class = getattr(response, 'x_obs_storage_class', '')
    az_redundancy = getattr(response, 'x_obs_az_redundancy', '')
    version = getattr(response, 'x_obs_version', '')
    epid = getattr(response, 'x_obs_epid', '')
    ies_location = getattr(response, 'x_obs_ies_location', '')
    fs_file_interface = getattr(response, 'x_obs_fs_file_interface', '')

    output = "桶元数据:\n"
    output += f"日期: {date}\n"
    output += f"位置: {location}\n"
    output += f"存储类型: {storage_class}\n"
    output += f"可用区冗余: {az_redundancy}\n"
    output += f"版本: {version}\n"
    output += f"企业ID: {epid}\n"
    output += f"IES位置: {ies_location}\n"
    output += f"文件接口: {fs_file_interface}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.get_bucket_metadata 查询失败: {e}")
    exit(1)
