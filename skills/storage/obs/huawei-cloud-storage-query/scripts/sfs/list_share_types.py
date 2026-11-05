import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ListShareTypesRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询文件系统类型列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--limit", type=int, help="查询列表返回元素个数")
parser.add_argument("--offset", type=int, help="查询偏移量")
parser.add_argument("--format", type=str, choices=["text", "json"], default="text", help="输出格式，默认 text")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListShareTypesRequest()
    if args.limit is not None:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.list_share_types(request)

    share_types = getattr(response, 'share_types', []) or []

    if not share_types:
        print("查询结果为空")
        exit(0)

    # 对 share_type 去重，避免 API 原始返回中的重复条目 (standard/performance 各出现多次)
    seen = set()
    deduped = []
    for share_type in share_types:
        st = getattr(share_type, 'share_type', '')
        if st in seen:
            continue
        seen.add(st)
        deduped.append({
            "share_type": st,
            "spec_code": getattr(share_type, 'spec_code', ''),
            "storage_media": getattr(share_type, 'storage_media', ''),
            "support_period": getattr(share_type, 'support_period', '')
        })

    if not deduped:
        print("查询结果为空")
        exit(0)

    if args.format == "json":
        print(json.dumps({"total": len(deduped), "share_types": deduped}, ensure_ascii=False))
        exit(0)

    output = f"文件系统类型列表共 {len(deduped)} 个:\n"
    output += "share_type\tspec_code\tstorage_media\tsupport_period\n"

    for item in deduped:
        output += f"{item['share_type']}\t{item['spec_code']}\t{item['storage_media']}\t{item['support_period']}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.list_share_types 查询失败: {e}")
    exit(1)