import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowFeatureRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 特性详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--feature_key", type=str, required=True, help="特性key,当前支持：replication.enable、replication.source_region、replication.destination_regions、replication.destination_dgw_regions、features.backup_double_az")
parser.add_argument("--limit", type=int, help="返回结果个数限制")
parser.add_argument("--offset", type=int, help="偏移量")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ShowFeatureRequest()
    request.feature_key = args.feature_key
    if args.limit:
        request.limit = args.limit
    if args.offset:
        request.offset = args.offset

    response = client.show_feature(request)

    body = getattr(response, 'body', {})
    print(body)
except Exception as e:
    print(f"cbr.show_feature 查询失败: {e}")
    exit(1)
