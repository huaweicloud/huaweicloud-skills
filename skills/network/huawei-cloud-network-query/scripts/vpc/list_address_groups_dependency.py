import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ListAddressGroupsDependencyRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询地址组依赖")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--id", type=str, required=True, help="地址组 ID（必填），可通过 list_address_group.py 获取")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目 ID 过滤，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染地址组依赖列表
    :param items: 依赖列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到地址组依赖")
        return

    for item in items:
        group_id = getattr(item, 'id', '')
        enterprise_project_id = getattr(item, 'enterprise_project_id', '')
        dependencies = getattr(item, 'dependency', []) or []

        print(f"地址组 ID: {group_id}")
        print(f"企业项目 ID: {enterprise_project_id}")
        if dependencies:
            print(f"  关联资源 (共 {len(dependencies)} 个):")
            output = f"  type\tinstance_id\tinstance_name\n"
            for dep in dependencies:
                dep_type = getattr(dep, 'type', '')
                instance_id = getattr(dep, 'instance_id', '')
                instance_name = getattr(dep, 'instance_name', '')
                output += f"  {dep_type}\t{instance_id}\t{instance_name}\n"
            print(output)
        else:
            print(f"  无关联资源")
        print()

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        summary = f"\n共 {total_count} 条地址组依赖，当前返回 {showing_count} 条"
        if has_more and next_marker:
            summary += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id 等参数缩小查询范围"
        print(summary)
    elif has_more:
        summary = f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            summary += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id 等参数缩小查询范围"
        print(summary)
    else:
        print(f"\n共 {showing_count} 条地址组依赖")


# 使用 sdk
try:
    http_config = build_http_config()

    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPC 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListAddressGroupsDependencyRequest()
    request.id = args.id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    response = client.list_address_groups_dependency(request)
    items = response.address_groups

    if not items:
        print(f"没有找到地址组依赖 (区域: {Region})")
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
        print("没有更多数据")
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
    print(f"vpc.list_address_groups_dependency 查询失败: {e}")
    exit(1)
