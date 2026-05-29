import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ListFlowLogsRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询VPC流日志列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, help="流日志 ID 过滤")
parser.add_argument("--name", type=str, help="流日志名称过滤")
parser.add_argument("--resource_type", type=str, help="资源类型过滤(port/network/vpc)")
parser.add_argument("--resource_id", type=str, help="资源 ID 过滤")
parser.add_argument("--traffic_type", type=str, help="采集类型过滤(all/accept/reject)")
parser.add_argument("--status", type=str, help="状态过滤(ACTIVE/DOWN/ERROR)")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染VPC流日志列表
    :param items: 流日志列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到VPC流日志")
        return

    output = f"id\tname\tresource_type\tresource_id\ttraffic_type\tlog_group_id\tlog_topic_id\tadmin_state\tstatus\n"
    for item in items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        resource_type = getattr(item, 'resource_type', '')
        resource_id = getattr(item, 'resource_id', '')
        traffic_type = getattr(item, 'traffic_type', '')
        log_group_id = getattr(item, 'log_group_id', '')
        log_topic_id = getattr(item, 'log_topic_id', '')
        admin_state = getattr(item, 'admin_state', '')
        status = getattr(item, 'status', '')
        output += f"{id}\t{name}\t{resource_type}\t{resource_id}\t{traffic_type}\t{log_group_id}\t{log_topic_id}\t{admin_state}\t{status}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条VPC流日志，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --resource_type 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --name / --resource_type 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --resource_type 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --name / --resource_type 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条VPC流日志"

    print(output)


try:
    http_config = build_http_config()
    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPC 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListFlowLogsRequest()
    request.limit = str(FETCH_SIZE)
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.resource_type:
        request.resource_type = args.resource_type
    if args.resource_id:
        request.resource_id = args.resource_id
    if args.traffic_type:
        request.traffic_type = args.traffic_type
    if args.status:
        request.status = args.status

    # 只做一次查询
    response = client.list_flow_logs(request)
    items = response.flow_logs

    if not items:
        print(f"没有找到VPC流日志 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # Response 无 page_info 和 count，通过多查的第 FETCH_SIZE 条判断
    next_marker = None
    has_more = len(items) > PAGE_SIZE
    if has_more:
        next_marker = str(getattr(items[PAGE_SIZE - 1], 'id', ''))

    # 只展示前 PAGE_SIZE 条
    display_items = items[:PAGE_SIZE]

    # 渲染结果
    render(display_items, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpc.list_flow_logs 查询失败: {e}")
    exit(1)
