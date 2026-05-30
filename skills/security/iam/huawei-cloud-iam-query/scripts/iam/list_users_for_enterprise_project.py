import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ListUsersForEnterpriseProjectRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询企业项目下用户列表 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--enterprise_project_id", type=str, required=True, help="企业项目ID，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: policy_num；方向可选: asc(升序), desc(降序)。例如 policy_num:asc 表示按策略数升序，policy_num:desc 表示按策略数降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by policy_num:asc --top 5 查找策略数最少的 5 个用户，--sort_by policy_num:desc --top 3 查找策略数最多的 3 个用户")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by policy_num:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('policy_num',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: policy_num；方向可选: asc, desc。例如 policy_num:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤/排序参数（触发全量数据处理）
has_custom_filter = args.sort_by is not None


def render(users, total_count=None, has_more=False, next_marker=None):
    """
    渲染用户列表
    :param users: 用户列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not users:
        print("没有找到企业项目下用户")
        return

    output = f"id\tname\tdomain_id\tenabled\tdescription\tpolicy_num\n"
    for item in users:
        id_ = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        domain_id = getattr(item, 'domain_id', '')
        enabled = getattr(item, 'enabled', '')
        description = getattr(item, 'description', '')
        policy_num = getattr(item, 'policy_num', '')
        output += f"{id_}\t{name}\t{domain_id}\t{enabled}\t{description}\t{policy_num}\n"

    # 汇总信息
    showing_count = len(users)

    if total_count is not None:
        output += f"\n共 {total_count} 条企业项目下用户，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条企业项目下用户"

    print(output)


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListUsersForEnterpriseProjectRequest()
    request.enterprise_project_id = args.enterprise_project_id
    response = client.list_users_for_enterprise_project(request)
    items = response.users or []

    if not items:
        print(f"没有找到数据 (区域: {Region})")
        exit(0)

    if has_custom_filter:
        # 有排序参数：在全量数据上排序再截取，无需翻页
        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'policy_num':
                items.sort(key=lambda f: int(getattr(f, 'policy_num', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            items = items[:args.top]

        # 渲染排序结果（全量已处理，无需翻页）
        render(items, total_count=len(items))
    else:
        # 无排序参数：本地 marker 翻页
        # 找到 marker 对应的位置，从该位置之后开始展示
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
    print(f"iam.list_users_for_enterprise_project 查询失败: {e}")
    exit(1)
