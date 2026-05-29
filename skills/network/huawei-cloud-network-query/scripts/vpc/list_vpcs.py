import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ListVpcsRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 VPC 列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="VPC ID 过滤，支持多个")
parser.add_argument("--name", type=str, nargs="+", help="VPC 名称过滤，支持多个")
parser.add_argument("--description", type=str, nargs="+", help="VPC 描述过滤，支持多个")
parser.add_argument("--cidr", type=str, nargs="+", help="VPC CIDR 过滤，支持多个")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目 ID 过滤，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--name_contains", type=str, help="VPC名称模糊搜索(客户端过滤)")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染VPC列表
    :param items: VPC列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到 VPC")
        return

    output = f"id\tname\tcidr\tstatus\tdescription\tenterprise_project_id\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        cidr = getattr(item, 'cidr', '')
        status = getattr(item, 'status', '')
        description = getattr(item, 'description', '')
        enterprise_project_id = getattr(item, 'enterprise_project_id', '')
        output += f"{id}\t{name}\t{cidr}\t{status}\t{description}\t{enterprise_project_id}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条VPC，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --name_contains 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --name / --name_contains 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --name_contains 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --name / --name_contains 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条VPC"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPC 客户端")
        exit(-1)

    # name_contains 是自定义过滤参数（SDK 不支持），需要全量拉取 + 本地过滤
    has_custom_filter = args.name_contains is not None

    if has_custom_filter:
        # 全量拉取 + 本地过滤（因为 SDK 单次最多返回1000条，必须循环拉完）
        all_items = []
        marker = ""
        while True:
            request = ListVpcsRequest()
            request.limit = 1000
            if marker:
                request.marker = marker
            if args.id:
                request.id = args.id
            if args.name:
                request.name = args.name
            if args.description:
                request.description = args.description
            if args.cidr:
                request.cidr = args.cidr
            if args.enterprise_project_id:
                request.enterprise_project_id = args.enterprise_project_id
            response = client.list_vpcs(request)
            items = response.vpcs
            if not items:
                break
            # 检测重复数据：如果本页第一条的 id 跟上一页最后一条相同，说明 marker 没生效，退出
            if marker and all_items and getattr(items[0], 'id', None) == getattr(all_items[-1], 'id', None):
                break
            all_items.extend(items)
            page_info = getattr(response, 'page_info', None)
            next_marker_val = getattr(page_info, 'next_marker', None) if page_info else None
            if not next_marker_val:
                break
            marker = next_marker_val

        # 本地过滤
        filtered = [v for v in all_items if args.name_contains in (getattr(v, 'name', '') or '')]
        if not filtered:
            print(f"没有找到名称包含 '{args.name_contains}' 的 VPC (区域: {Region})")
            exit(0)

        # 本地 marker 翻页
        start_idx = 0
        if args.marker:
            for i, item in enumerate(filtered):
                if str(getattr(item, 'id', '')) == args.marker:
                    start_idx = i + 1
                    break

        remaining_items = filtered[start_idx:]
        if not remaining_items:
            print("没有更多数据")
            exit(0)

        has_more = len(remaining_items) > PAGE_SIZE
        next_marker = None
        if has_more:
            next_marker = str(getattr(remaining_items[PAGE_SIZE - 1], 'id', ''))
        display_items = remaining_items[:PAGE_SIZE]

        render(display_items, total_count=len(filtered), has_more=has_more, next_marker=next_marker)
    else:
        # 正常逻辑：只查1次
        request = ListVpcsRequest()
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker
        if args.id:
            request.id = args.id
        if args.name:
            request.name = args.name
        if args.description:
            request.description = args.description
        if args.cidr:
            request.cidr = args.cidr
        if args.enterprise_project_id:
            request.enterprise_project_id = args.enterprise_project_id

        # 只做一次查询
        response = client.list_vpcs(request)
        items = response.vpcs

        if not items:
            print(f"没有找到 VPC (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        # Response 有 page_info，必须用 page_info.next_marker
        next_marker = None
        page_info = getattr(response, 'page_info', None)
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        else:
            has_more = len(items) > PAGE_SIZE
            if has_more:
                next_marker = str(getattr(items[PAGE_SIZE - 1], 'id', ''))

        # 只展示前 PAGE_SIZE 条
        display_items = items[:PAGE_SIZE]

        # 渲染结果
        render(display_items, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpc.list_vpcs 查询失败: {e}")
    exit(1)
