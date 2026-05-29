import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListPoolsRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限

parser = argparse.ArgumentParser(description="查询 ELB 后端服务器组列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: member_count；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by member_count:desc --top 5 查找后端服务器数最多的 5 个服务器组")
parser.add_argument("--id", type=str, nargs="+", help="后端服务器组的ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="后端服务器组的名称，支持多值查询")
parser.add_argument("--description", type=str, nargs="+", help="后端服务器组的描述信息，支持多值查询")
parser.add_argument("--loadbalancer_id", type=str, nargs="+", help="后端服务器组绑定的负载均衡器ID，支持多值查询，可通过 list_load_balancers.py 获取")
parser.add_argument("--listener_id", type=str, nargs="+", help="关联的监听器ID（包括通过l7policy关联的），支持多值查询，可通过 list_listeners.py 获取")
parser.add_argument("--protocol", type=str, nargs="+", help="后端协议，支持多值查询，取值: TCP UDP IP TLS HTTP HTTPS QUIC GRPC")
parser.add_argument("--lb_algorithm", type=str, nargs="+", help="负载均衡算法，支持多值查询，取值: ROUND_ROBIN LEAST_CONNECTIONS SOURCE_IP QUIC_CID 2_TUPLE_HASH 3_TUPLE_HASH 5_TUPLE_HASH")
parser.add_argument("--healthmonitor_id", type=str, nargs="+", help="关联的健康检查ID，支持多值查询")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="资源所属的企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--vpc_id", type=str, nargs="+", help="后端服务器组关联的虚拟私有云的ID")
parser.add_argument("--ip_version", type=str, nargs="+", help="后端服务器组支持的IP版本，支持多值查询")
parser.add_argument("--type", type=str, nargs="+", help="后端服务器组的类型，支持多值查询，取值: instance ip")
parser.add_argument("--member_address", type=str, nargs="+", help="后端服务器的IP地址，仅用于查询条件，支持多值查询")
parser.add_argument("--member_device_id", type=str, nargs="+", help="后端服务器对应的弹性云服务器的ID，仅用于查询条件，支持多值查询")
parser.add_argument("--member_instance_id", type=str, nargs="+", help="后端服务器ID，仅用于查询条件，支持多值查询")
parser.add_argument("--member_deletion_protection_enable", type=bool, help="是否开启后端服务器移除保护，false不开启，true开启")
parser.add_argument("--protection_status", type=str, nargs="+", help="修改保护状态，nonProtection不保护，consoleProtection控制台修改保护，支持多值查询")
parser.add_argument("--connection_drain", type=bool, help="查询是否开启延迟注销的功能")
parser.add_argument("--pool_health", type=str, help="查询是否开启后端全下线转发功能")
parser.add_argument("--any_port_enable", type=bool, help="后端是否开启全端口转发，false不开启，true开启")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by member_count:desc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('member_count',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: member_count；方向可选: asc, desc。例如 member_count:desc")
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

    request = ListPoolsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.description:
        request.description = args.description
    if args.loadbalancer_id:
        request.loadbalancer_id = args.loadbalancer_id
    if args.listener_id:
        request.listener_id = args.listener_id
    if args.protocol:
        request.protocol = args.protocol
    if args.lb_algorithm:
        request.lb_algorithm = args.lb_algorithm
    if args.healthmonitor_id:
        request.healthmonitor_id = args.healthmonitor_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.vpc_id:
        request.vpc_id = args.vpc_id
    if args.ip_version:
        request.ip_version = args.ip_version
    if args.type:
        request.type = args.type
    if args.member_address:
        request.member_address = args.member_address
    if args.member_device_id:
        request.member_device_id = args.member_device_id
    if args.member_instance_id:
        request.member_instance_id = args.member_instance_id
    if args.member_deletion_protection_enable is not None:
        request.member_deletion_protection_enable = args.member_deletion_protection_enable
    if args.protection_status:
        request.protection_status = args.protection_status
    if args.connection_drain is not None:
        request.connection_drain = args.connection_drain
    if args.pool_health:
        request.pool_health = args.pool_health
    if args.any_port_enable is not None:
        request.any_port_enable = args.any_port_enable

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地排序
        all_pools = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_pools(request)
            pools = response.pools
            if not pools:
                break
            if marker and all_pools and getattr(pools[0], 'id', None) == getattr(all_pools[-1], 'id', None):
                break
            all_pools.extend(pools)
            if len(pools) < API_LIMIT:
                break
            marker = pools[-1].id
            if not marker:
                break

        if not all_pools:
            print("没有找到后端服务器组")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'member_count':
                all_pools.sort(key=lambda f: len(getattr(f, 'members', []) or []), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_pools = all_pools[:args.top]

        # 渲染
        output = f"name\tid\tprotocol\tlb_algorithm\thealthmonitor_id\tvpc_id\ttype\tmember_count\tcreated_at\n"
        for item in all_pools:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            protocol = getattr(item, 'protocol', '')
            lb_algorithm = getattr(item, 'lb_algorithm', '')
            healthmonitor_id = getattr(item, 'healthmonitor_id', '')
            vpc_id = getattr(item, 'vpc_id', '')
            pool_type = getattr(item, 'type', '')
            members = getattr(item, 'members', [])
            member_count = len(members) if members else 0
            created_at = getattr(item, 'created_at', '')
            output += f"{name}\t{id}\t{protocol}\t{lb_algorithm}\t{healthmonitor_id}\t{vpc_id}\t{pool_type}\t{member_count}\t{created_at}\n"
        output += f"\n共 {len(all_pools)} 条"
        print(output)
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_pools(request)
        pools = response.pools

        if not pools:
            print(f"没有找到后端服务器组 (区域: {Region})")
            exit(0)

        # Response 有 page_info，使用 page_info.next_marker 判断分页
        next_marker = None
        page_info = getattr(response, 'page_info', None)
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        else:
            has_more = len(pools) > PAGE_SIZE
            if has_more:
                next_marker = str(getattr(pools[PAGE_SIZE - 1], 'id', ''))

        display_pools = pools[:PAGE_SIZE]

        output = f"name\tid\tprotocol\tlb_algorithm\thealthmonitor_id\tvpc_id\ttype\tmember_count\tcreated_at\n"
        for item in display_pools:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            protocol = getattr(item, 'protocol', '')
            lb_algorithm = getattr(item, 'lb_algorithm', '')
            healthmonitor_id = getattr(item, 'healthmonitor_id', '')
            vpc_id = getattr(item, 'vpc_id', '')
            pool_type = getattr(item, 'type', '')
            members = getattr(item, 'members', [])
            member_count = len(members) if members else 0
            created_at = getattr(item, 'created_at', '')
            output += f"{name}\t{id}\t{protocol}\t{lb_algorithm}\t{healthmonitor_id}\t{vpc_id}\t{pool_type}\t{member_count}\t{created_at}\n"

        if has_more:
            output += f"\n当前返回 {len(display_pools)} 条，还有更多数据"
            if next_marker:
                output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
        else:
            output += f"\n共 {len(display_pools)} 条"

        print(output)
except Exception as e:
    print(f"elb.list_pools 查询失败: {e}")
    exit(1)
