import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ListSharesByTagRequest, ListSharesByTagRequestBody
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="根据标签查询SFS Turbo文件系统列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--action", type=str, default="filter", help="操作类型：filter 或 count")
parser.add_argument("--limit", type=int, default=50, help="返回的文件系统个数的最大值，默认50")
parser.add_argument("--offset", type=str, help="返回的文件系统的偏移量")
parser.add_argument("--without_any_tag", action="store_true", help="查询所有不带标签的资源")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    body = ListSharesByTagRequestBody()
    body.action = args.action
    if args.action != "count":
        if args.limit:
            body.limit = str(args.limit)
        if args.offset:
            body.offset = args.offset
    body.without_any_tag = args.without_any_tag

    request = ListSharesByTagRequest()
    request.body = body

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.list_shares_by_tag(request)

    resources = getattr(response, 'resources', []) or []
    total_count = getattr(response, 'total_count', 0)

    if args.action == "count":
        print(f"文件系统数量: {total_count}")
    else:
        if not resources:
            print("查询结果为空")
            exit(0)

        output = f"根据标签查询的文件系统列表（共{total_count}个）:\n"
        output += "文件系统ID\t名称\n"
        
        for resource in resources:
            resource_id = getattr(resource, 'resource_id', '')
            resource_name = getattr(resource, 'resource_name', '')
            output += f"{resource_id}\t{resource_name}\n"

        print(output.strip())
    
    exit(0)
except Exception as e:
    print(f"sfs.list_shares_by_tag 查询失败: {e}")
    exit(1)
