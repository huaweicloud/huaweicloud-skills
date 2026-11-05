import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListFeaturesRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 特性列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--limit", type=int, help="返回结果个数限制")
parser.add_argument("--offset", type=int, help="偏移量")
parser.add_argument("--format", type=str, choices=["text", "json"], default="text", help="输出格式，默认 text")
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

    request = ListFeaturesRequest()
    if args.limit:
        request.limit = args.limit
    if args.offset:
        request.offset = args.offset

    response = client.list_features(request)

    body = getattr(response, 'body', {})

    if args.format == "json":
        print(json.dumps(body, ensure_ascii=False, default=str))
        exit(0)

    if not body:
        print("查询结果为空")
        exit(0)

    if isinstance(body, list):
        for item in body:
            if isinstance(item, dict):
                print("\t".join(f"{k}={v}" for k, v in item.items() if v is not None))
            else:
                print(item)
    elif isinstance(body, dict):
        for key, value in body.items():
            if isinstance(value, (list, dict)) and value:
                print(f"{key}:")
                for item in value if isinstance(value, list) else [value]:
                    if isinstance(item, dict):
                        print("\t" + "\t".join(f"{k}={v}" for k, v in item.items() if v is not None))
                    else:
                        print(f"\t{item}")
            else:
                print(f"{key}: {value}")
    else:
        print(body)
    exit(0)
except Exception as e:
    print(f"cbr.list_features 查询失败: {e}")
    exit(1)