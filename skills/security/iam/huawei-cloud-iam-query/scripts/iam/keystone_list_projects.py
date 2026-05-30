import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneListProjectsRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询项目列表 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_id", type=str, help="域 ID")
parser.add_argument("--name", type=str, help="项目名称")
parser.add_argument("--parent_id", type=str, help="父项目 ID")
parser.add_argument("--enabled", type=bool, help="是否启用")
parser.add_argument("--is_domain", type=bool, help="是否为域")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    # API 使用 page/per_page 分页，不暴露给 agent，脚本内部控制
    request = KeystoneListProjectsRequest()
    if args.domain_id:
        request.domain_id = args.domain_id
    if args.name:
        request.name = args.name
    if args.parent_id:
        request.parent_id = args.parent_id
    if args.enabled is not None:
        request.enabled = args.enabled
    if args.is_domain is not None:
        request.is_domain = args.is_domain

    # 解析 marker 为 page（marker 存储的是页码）
    if args.marker:
        try:
            request.page = int(args.marker)
        except ValueError:
            request.page = 1
    else:
        request.page = 1
    request.per_page = FETCH_SIZE

    # 只做一次查询
    response = client.keystone_list_projects(request)
    total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
    items = response.projects
    if not items:
        print(f"没有找到数据 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    if total_count is not None:
        has_more = total_count > (request.page * PAGE_SIZE)
    else:
        has_more = len(items) > PAGE_SIZE

    if has_more and len(items) > PAGE_SIZE:
        next_marker = str(request.page + 1)

    # 只展示前 PAGE_SIZE 条
    display_items = items[:PAGE_SIZE]

    output = f"id	name	domain_id	enabled	description\n"
    for item in display_items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        domain_id = getattr(item, 'domain_id', '')
        enabled = getattr(item, 'enabled', '')
        description = getattr(item, 'description', '')
        output += f"{id}	{name}	{domain_id}	{enabled}	{description}\n"

    # 汇总信息
    showing_count = len(display_items)
    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --domain_id / --name 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --domain_id / --name 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --domain_id / --name 等参数缩小查询范围"
        else:
            output += f"\n可使用 --domain_id / --name 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条"

    print(output)
except Exception as e:
    print(f"iam.keystone_list_projects 查询失败: {e}")
    exit(1)
