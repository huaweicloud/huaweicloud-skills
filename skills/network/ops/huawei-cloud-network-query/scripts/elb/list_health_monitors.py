import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListHealthMonitorsRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限

parser = argparse.ArgumentParser(description="查询 ELB 健康检查列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: delay, timeout, max_retries, max_retries_down, monitor_port；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by delay:asc --top 5 查找间隔最短的 5 个健康检查")
parser.add_argument("--id", type=str, nargs="+", help="健康检查ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="健康检查名称，支持多值查询")
parser.add_argument("--type", type=str, nargs="+", help="健康检查请求协议，支持多值查询，取值: TCP UDP_CONNECT HTTP HTTPS TLS GRPC GRPCS")
parser.add_argument("--delay", type=int, nargs="+", help="健康检查间隔(秒)，支持多值查询，取值1-50")
parser.add_argument("--timeout", type=int, help="一次健康检查请求的超时时间")
parser.add_argument("--max_retries", type=int, nargs="+", help="健康检查连续成功次数判定为ONLINE，支持多值查询，取值1-10")
parser.add_argument("--max_retries_down", type=int, nargs="+", help="健康检查连续失败次数判定为OFFLINE，支持多值查询，取值1-10")
parser.add_argument("--monitor_port", type=int, nargs="+", help="健康检查端口号，支持多值查询")
parser.add_argument("--domain_name", type=str, nargs="+", help="发送健康检查请求的域名，支持多值查询")
parser.add_argument("--url_path", type=str, nargs="+", help="健康检查请求的请求路径，支持多值查询")
parser.add_argument("--http_method", type=str, nargs="+", help="HTTP请求方法，支持多值查询，取值: GET HEAD POST")
parser.add_argument("--expected_codes", type=str, nargs="+", help="期望响应状态码，支持多值查询，如200或200,202或200-204")
parser.add_argument("--admin_state_up", type=bool, help="健康检查的管理状态，true开启，false关闭")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="资源所属的企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by delay:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('delay', 'timeout', 'max_retries', 'max_retries_down', 'monitor_port') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: delay, timeout, max_retries, max_retries_down, monitor_port；方向可选: asc, desc。例如 delay:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数
has_custom_filter = args.sort_by is not None

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ListHealthMonitorsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.type:
        request.type = args.type
    if args.delay is not None:
        request.delay = args.delay
    if args.timeout is not None:
        request.timeout = args.timeout
    if args.max_retries is not None:
        request.max_retries = args.max_retries
    if args.max_retries_down is not None:
        request.max_retries_down = args.max_retries_down
    if args.monitor_port is not None:
        request.monitor_port = args.monitor_port
    if args.domain_name:
        request.domain_name = args.domain_name
    if args.url_path:
        request.url_path = args.url_path
    if args.http_method:
        request.http_method = args.http_method
    if args.expected_codes:
        request.expected_codes = args.expected_codes
    if args.admin_state_up is not None:
        request.admin_state_up = args.admin_state_up
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地排序
        all_healthmonitors = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_health_monitors(request)
            healthmonitors = response.healthmonitors
            if not healthmonitors:
                break
            if marker and all_healthmonitors and getattr(healthmonitors[0], 'id', None) == getattr(all_healthmonitors[-1], 'id', None):
                break
            all_healthmonitors.extend(healthmonitors)
            if len(healthmonitors) < API_LIMIT:
                break
            marker = healthmonitors[-1].id
            if not marker:
                break

        if not all_healthmonitors:
            print("没有找到健康检查")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'delay':
                all_healthmonitors.sort(key=lambda f: int(getattr(f, 'delay', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'timeout':
                all_healthmonitors.sort(key=lambda f: int(getattr(f, 'timeout', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'max_retries':
                all_healthmonitors.sort(key=lambda f: int(getattr(f, 'max_retries', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'max_retries_down':
                all_healthmonitors.sort(key=lambda f: int(getattr(f, 'max_retries_down', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'monitor_port':
                all_healthmonitors.sort(key=lambda f: int(getattr(f, 'monitor_port', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_healthmonitors = all_healthmonitors[:args.top]

        # 渲染
        output = f"name\tid\ttype\tdelay\ttimeout\tmax_retries\tmax_retries_down\tmonitor_port\tadmin_state_up\tpool_id\n"
        for item in all_healthmonitors:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            hm_type = getattr(item, 'type', '')
            delay = getattr(item, 'delay', '')
            timeout = getattr(item, 'timeout', '')
            max_retries = getattr(item, 'max_retries', '')
            max_retries_down = getattr(item, 'max_retries_down', '')
            monitor_port = getattr(item, 'monitor_port', '')
            admin_state_up = getattr(item, 'admin_state_up', '')
            pools = getattr(item, 'pools', [])
            pool_id = ','.join([getattr(p, 'id', '') for p in pools]) if pools else ''
            output += f"{name}\t{id}\t{hm_type}\t{delay}\t{timeout}\t{max_retries}\t{max_retries_down}\t{monitor_port}\t{admin_state_up}\t{pool_id}\n"
        output += f"\n共 {len(all_healthmonitors)} 条"
        print(output)
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_health_monitors(request)
        healthmonitors = response.healthmonitors

        if not healthmonitors:
            print(f"没有找到健康检查 (区域: {Region})")
            exit(0)

        # Response 有 page_info，使用 page_info.next_marker 判断分页
        next_marker = None
        page_info = getattr(response, 'page_info', None)
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        else:
            has_more = len(healthmonitors) > PAGE_SIZE
            if has_more:
                next_marker = str(getattr(healthmonitors[PAGE_SIZE - 1], 'id', ''))

        display_healthmonitors = healthmonitors[:PAGE_SIZE]

        output = f"name\tid\ttype\tdelay\ttimeout\tmax_retries\tmax_retries_down\tmonitor_port\tadmin_state_up\tpool_id\n"
        for item in display_healthmonitors:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            hm_type = getattr(item, 'type', '')
            delay = getattr(item, 'delay', '')
            timeout = getattr(item, 'timeout', '')
            max_retries = getattr(item, 'max_retries', '')
            max_retries_down = getattr(item, 'max_retries_down', '')
            monitor_port = getattr(item, 'monitor_port', '')
            admin_state_up = getattr(item, 'admin_state_up', '')
            pools = getattr(item, 'pools', [])
            pool_id = ','.join([getattr(p, 'id', '') for p in pools]) if pools else ''
            output += f"{name}\t{id}\t{hm_type}\t{delay}\t{timeout}\t{max_retries}\t{max_retries_down}\t{monitor_port}\t{admin_state_up}\t{pool_id}\n"

        if has_more:
            output += f"\n当前返回 {len(display_healthmonitors)} 条，还有更多数据"
            if next_marker:
                output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
        else:
            output += f"\n共 {len(display_healthmonitors)} 条"

        print(output)
except Exception as e:
    print(f"elb.list_health_monitors 查询失败: {e}")
    exit(1)
