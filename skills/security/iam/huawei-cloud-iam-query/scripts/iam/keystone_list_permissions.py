import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneListPermissionsRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询权限列表 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--name", type=str, help="权限名称")
parser.add_argument("--domain_id", type=str, help="域 ID")
parser.add_argument("--permission_type", type=str, choices=["policy", "role"], help="权限类型过滤，policy: 系统策略，role: 系统角色（需配合 domain_id 使用）")
parser.add_argument("--display_name", type=str, help="权限展示名称，模糊匹配")
parser.add_argument("--type", type=str, choices=["domain", "project", "all"], help="权限的显示模式，domain: 域级显示，project: 项目级显示，all: 全部显示")
parser.add_argument("--catalog", type=str, help="权限所属目录，精确匹配")
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
    request = KeystoneListPermissionsRequest()
    if args.name:
        request.name = args.name
    if args.domain_id:
        request.domain_id = args.domain_id
    if args.permission_type:
        request.permission_type = args.permission_type
    if args.display_name:
        request.display_name = args.display_name
    if args.type:
        request.type = args.type
    if args.catalog:
        request.catalog = args.catalog

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
    response = client.keystone_list_permissions(request)
    total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
    items = response.roles
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

    output = f"id	name	display_name	type	catalog\n"
    for item in display_items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        display_name = getattr(item, 'display_name', '')
        type = getattr(item, 'type', '')
        catalog = getattr(item, 'catalog', '')
        output += f"{id}	{name}	{display_name}	{type}	{catalog}\n"

    # 汇总信息
    showing_count = len(display_items)
    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --domain_id / --permission_type 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --name / --domain_id / --permission_type 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --domain_id / --permission_type 等参数缩小查询范围"
        else:
            output += f"\n可使用 --name / --domain_id / --permission_type 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条"

    print(output)
except Exception as e:
    print(f"iam.keystone_list_permissions 查询失败: {e}")
    exit(1)
