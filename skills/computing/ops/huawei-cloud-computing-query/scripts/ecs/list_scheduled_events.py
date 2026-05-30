import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListScheduledEventsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 计划事件列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--id", type=str, help="事件 ID")
parser.add_argument("--instance_id", type=str, nargs="+", help="实例 ID，可指定多个")
parser.add_argument("--type", type=str, nargs="+", help="事件类型，可指定多个")
parser.add_argument("--state", type=str, nargs="+", help="事件状态，可指定多个")
parser.add_argument("--publish_since", type=str, help="事件发布开始时间，ISO8601 格式")
parser.add_argument("--publish_until", type=str, help="事件发布截至时间，ISO8601 格式")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(events, total_count=None, has_more=False, next_marker=None):
    if not events:
        print("没有找到 ECS 计划事件")
        return

    output = f"id\tinstance_id\ttype\tstate\tpublish_time\tstart_time\tnot_before\tdescription\n"
    for event in events:
        eid = getattr(event, 'id', '')
        instance_id = getattr(event, 'instance_id', '')
        type_ = getattr(event, 'type', '')
        state = getattr(event, 'state', '')
        publish_time = getattr(event, 'publish_time', '')
        start_time = getattr(event, 'start_time', '')
        not_before = getattr(event, 'not_before', '')
        description = getattr(event, 'description', '')
        output += f"{eid}\t{instance_id}\t{type_}\t{state}\t{publish_time}\t{start_time}\t{not_before}\t{description}\n"

    # 汇总信息
    showing_count = len(events)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS 计划事件，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --instance_id / --type / --state 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --instance_id / --type / --state 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --instance_id / --type / --state 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --instance_id / --type / --state 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 ECS 计划事件"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListScheduledEventsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.instance_id:
        request.instance_id = args.instance_id
    if args.type:
        request.type = args.type
    if args.state:
        request.state = args.state
    if args.publish_since:
        request.publish_since = args.publish_since
    if args.publish_until:
        request.publish_until = args.publish_until

    # 只做一次查询
    response = client.list_scheduled_events(request)
    total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
    events = response.events

    if not events:
        print(f"没有找到 ECS 计划事件 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # 此 API 的 marker 来自 response.page_info.next_marker
    page_info = getattr(response, 'page_info', None)
    next_marker = None
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    elif total_count is not None:
        has_more = total_count > PAGE_SIZE
    else:
        # 无 count/total_count 字段时，通过多查的第 FETCH_SIZE 条判断
        has_more = len(events) > PAGE_SIZE

    if has_more and not next_marker and len(events) > PAGE_SIZE:
        next_marker = str(events[PAGE_SIZE - 1].id)

    # 只展示前 PAGE_SIZE 条
    display_events = events[:PAGE_SIZE]

    # 渲染结果
    render(display_events, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"ecs.scheduled_events 查询失败: {e}")
    exit(1)
