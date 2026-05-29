import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListLogtanksRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 云日志列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="云日志ID，支持多值查询")
parser.add_argument("--loadbalancer_id", type=str, nargs="+", help="负载均衡器ID，支持多值查询")
parser.add_argument("--log_group_id", type=str, nargs="+", help="日志组ID，支持多值查询")
parser.add_argument("--log_topic_id", type=str, nargs="+", help="日志主题ID，支持多值查询")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ListLogtanksRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.loadbalancer_id:
        request.loadbalancer_id = args.loadbalancer_id
    if args.log_group_id:
        request.log_group_id = args.log_group_id
    if args.log_topic_id:
        request.log_topic_id = args.log_topic_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    response = client.list_logtanks(request)
    logtanks = response.logtanks

    if not logtanks:
        print(f"没有找到云日志 (区域: {Region})")
        exit(0)

    # Response 有 page_info，使用 page_info.next_marker 判断分页
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(logtanks) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(logtanks[PAGE_SIZE - 1], 'id', ''))

    display_logtanks = logtanks[:PAGE_SIZE]

    output = f"id\tloadbalancer_id\tlog_group_id\tlog_topic_id\n"
    for item in display_logtanks:
        id = getattr(item, 'id', '')
        loadbalancer_id = getattr(item, 'loadbalancer_id', '')
        log_group_id = getattr(item, 'log_group_id', '')
        log_topic_id = getattr(item, 'log_topic_id', '')
        output += f"{id}\t{loadbalancer_id}\t{log_group_id}\t{log_topic_id}\n"

    if has_more:
        output += f"\n当前返回 {len(display_logtanks)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_logtanks)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_logtanks 查询失败: {e}")
    exit(1)
