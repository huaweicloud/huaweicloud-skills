import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import GetBucketCustomdomainRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="获取桶自定义域名")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bucket_name", type=str, required=True, help="桶名称，可通过 list_buckets.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = GetBucketCustomdomainRequest()
    request.bucket_name = args.bucket_name

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.get_bucket_customdomain(request)

    domains = getattr(response, 'domains', []) or []

    if not domains:
        print("查询结果为空")
        exit(0)

    output = f"桶 {args.bucket_name} 的自定义域名列表:\n"
    output += "域名\t创建时间\t证书ID\n"

    for domain in domains:
        domain_name = getattr(domain, 'domain_name', '')
        create_time = getattr(domain, 'create_time', '')
        certificate_id = getattr(domain, 'certificate_id', '')
        output += f"{domain_name}\t{create_time}\t{certificate_id}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.get_bucket_customdomain 查询失败: {e}")
    exit(1)
