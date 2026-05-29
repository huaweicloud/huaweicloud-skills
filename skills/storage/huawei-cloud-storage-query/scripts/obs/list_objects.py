import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import ListObjectsRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="列出桶内对象")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bucket_name", type=str, required=True, help="桶名称，可通过 list_buckets.py 获取")
parser.add_argument("--prefix", type=str, help="对象键前缀")
parser.add_argument("--marker", type=str, help="分页标记")
parser.add_argument("--max_keys", type=int, default=50, help="每页最大数量，默认50")
parser.add_argument("--delimiter", type=str, help="分隔符")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListObjectsRequest()
    request.bucket_name = args.bucket_name
    if args.prefix:
        request.prefix = args.prefix
    if args.marker:
        request.marker = args.marker
    request.max_keys = args.max_keys
    if args.delimiter:
        request.delimiter = args.delimiter

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.list_objects(request)

    contents = getattr(response, 'contents', []) or []
    name = getattr(response, 'name', '')
    prefix = getattr(response, 'prefix', '')
    marker = getattr(response, 'marker', '')
    next_marker = getattr(response, 'next_marker', '')

    if not contents:
        print("查询结果为空")
        exit(0)

    output = f"桶 {name} 的对象列表:\n"
    output += f"前缀: {prefix}\n"
    output += f"标记: {marker}\n"
    output += f"下一标记: {next_marker}\n"
    output += "对象键\t大小\t最后修改时间\n"
    
    for content in contents:
        key = getattr(content, 'key', '')
        size = getattr(content, 'size', 0)
        last_modified = getattr(content, 'last_modified', '')
        output += f"{key}\t{size}\t{last_modified}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.list_objects 查询失败: {e}")
    exit(1)
