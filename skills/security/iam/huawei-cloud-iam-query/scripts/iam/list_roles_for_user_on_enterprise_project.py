import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ListRolesForUserOnEnterpriseProjectRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询用户在企业项目上的角色 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--enterprise_project_id", type=str, required=True, help="企业项目ID，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--user_id", type=str, required=True, help="用户 ID")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(roles, total_count=None, has_more=False, next_marker=None):
    """
    渲染角色列表
    :param roles: 角色列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not roles:
        print("没有找到用户在企业项目上的角色")
        return

    output = f"id\tname\tdisplay_name\ttype\tcatalog\tdescription\tflag\n"
    for item in roles:
        id_ = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        display_name = getattr(item, 'display_name', '')
        type_ = getattr(item, 'type', '')
        catalog = getattr(item, 'catalog', '')
        description = getattr(item, 'description', '')
        flag = getattr(item, 'flag', '')
        output += f"{id_}\t{name}\t{display_name}\t{type_}\t{catalog}\t{description}\t{flag}\n"

    # 汇总信息
    showing_count = len(roles)

    if total_count is not None:
        output += f"\n共 {total_count} 条用户在企业项目上的角色，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条用户在企业项目上的角色"

    print(output)


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListRolesForUserOnEnterpriseProjectRequest()
    request.enterprise_project_id = args.enterprise_project_id
    request.user_id = args.user_id
    response = client.list_roles_for_user_on_enterprise_project(request)
    items = response.roles or []

    if not items:
        print(f"没有找到数据 (区域: {Region})")
        exit(0)

    # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
    start_idx = 0
    if args.marker:
        for i, item in enumerate(items):
            if str(getattr(item, 'id', '')) == args.marker:
                start_idx = i + 1
                break

    remaining_items = items[start_idx:]
    if not remaining_items:
        print(f"没有更多数据")
        exit(0)

    # 判断是否还有更多数据
    has_more = len(remaining_items) > PAGE_SIZE
    next_marker = None
    if has_more:
        next_marker = str(getattr(remaining_items[PAGE_SIZE - 1], 'id', ''))
    display_items = remaining_items[:PAGE_SIZE]

    # 渲染结果
    render(display_items, total_count=len(items), has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"iam.list_roles_for_user_on_enterprise_project 查询失败: {e}")
    exit(1)
