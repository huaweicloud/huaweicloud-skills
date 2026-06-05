import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ListTrafficMirrorSessionsRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询流量镜像会话列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, help="会话 ID 过滤")
parser.add_argument("--name", type=str, help="会话名称过滤")
parser.add_argument("--traffic_mirror_filter_id", type=str, help="过滤器 ID 过滤，可通过 list_traffic_mirror_filters.py 获取")
parser.add_argument("--traffic_mirror_target_id", type=str, help="镜像目的 ID 过滤")
parser.add_argument("--enabled", type=str, help="是否启用过滤(true/false)")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: virtual_network_id, priority；方向可选: asc(升序), desc(降序)。例如 priority:asc 表示按优先级升序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by priority:asc --top 5 查找优先级最高的 5 个会话")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by priority:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('virtual_network_id', 'priority') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: virtual_network_id, priority；方向可选: asc, desc。例如 priority:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染流量镜像会话列表
    :param items: 会话列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到流量镜像会话")
        return

    output = f"id\tname\ttraffic_mirror_filter_id\ttraffic_mirror_target_id\tvirtual_network_id\tpriority\tenabled\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        traffic_mirror_filter_id = getattr(item, 'traffic_mirror_filter_id', '')
        traffic_mirror_target_id = getattr(item, 'traffic_mirror_target_id', '')
        virtual_network_id = getattr(item, 'virtual_network_id', '')
        priority = getattr(item, 'priority', '')
        enabled = getattr(item, 'enabled', '')
        output += f"{id}\t{name}\t{traffic_mirror_filter_id}\t{traffic_mirror_target_id}\t{virtual_network_id}\t{priority}\t{enabled}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条流量镜像会话，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --traffic_mirror_filter_id 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --name / --traffic_mirror_filter_id 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --traffic_mirror_filter_id 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --name / --traffic_mirror_filter_id 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条流量镜像会话"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPC 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListTrafficMirrorSessionsRequest()
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.traffic_mirror_filter_id:
        request.traffic_mirror_filter_id = args.traffic_mirror_filter_id
    if args.traffic_mirror_target_id:
        request.traffic_mirror_target_id = args.traffic_mirror_target_id
    if args.enabled:
        request.enabled = args.enabled

    # --sort_by 需要全量拉取才能排序
    has_custom_filter = args.sort_by is not None

    if has_custom_filter:
        # 全量拉取 + 排序 + 截取
        all_items = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_traffic_mirror_sessions(request)
            items = response.traffic_mirror_sessions
            if not items:
                break
            # 检测重复数据
            if marker and all_items and getattr(items[0], 'id', None) == getattr(all_items[-1], 'id', None):
                break
            all_items.extend(items)
            page_info = getattr(response, 'page_info', None)
            next_marker_val = getattr(page_info, 'next_marker', None) if page_info else None
            if not next_marker_val:
                break
            marker = next_marker_val

        if not all_items:
            print(f"没有找到流量镜像会话 (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'virtual_network_id':
                all_items.sort(key=lambda s: int(getattr(s, 'virtual_network_id', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'priority':
                all_items.sort(key=lambda s: int(getattr(s, 'priority', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_items = all_items[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_items, total_count=len(all_items))
    else:
        # 正常逻辑：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        # 只做一次查询
        response = client.list_traffic_mirror_sessions(request)
        items = response.traffic_mirror_sessions

        if not items:
            print(f"没有找到流量镜像会话 (区域: {Region})")
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
    print(f"vpc.list_traffic_mirror_sessions 查询失败: {e}")
    exit(1)
