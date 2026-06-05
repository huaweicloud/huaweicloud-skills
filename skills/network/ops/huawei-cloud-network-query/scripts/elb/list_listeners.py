import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListListenersRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限

parser = argparse.ArgumentParser(description="查询 ELB 监听器列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: protocol_port, connection_limit；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by protocol_port:asc --top 5 查找监听端口最小的 5 个监听器")
parser.add_argument("--id", type=str, nargs="+", help="监听器ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="监听器名称，支持多值查询")
parser.add_argument("--description", type=str, nargs="+", help="监听器的描述信息，支持多值查询")
parser.add_argument("--loadbalancer_id", type=str, nargs="+", help="监听器所属的负载均衡器ID，支持多值查询，可通过 list_load_balancers.py 获取")
parser.add_argument("--protocol", type=str, nargs="+", help="监听协议，支持多值查询，取值: TCP UDP HTTP HTTPS TERMINATED_HTTPS QUIC TLS IP")
parser.add_argument("--protocol_port", type=str, nargs="+", help="监听器的前端监听端口，支持多值查询")
parser.add_argument("--default_pool_id", type=str, nargs="+", help="监听器的默认后端服务器组ID，支持多值查询")
parser.add_argument("--default_tls_container_ref", type=str, nargs="+", help="监听器的服务器证书ID，支持多值查询")
parser.add_argument("--client_ca_tls_container_ref", type=str, nargs="+", help="监听器的CA证书ID，支持多值查询")
parser.add_argument("--admin_state_up", type=bool, help="监听器的管理状态，true启用，false停用")
parser.add_argument("--http2_enable", type=bool, help="客户端与LB之间的HTTPS请求的HTTP2功能的开启状态")
parser.add_argument("--connection_limit", type=int, nargs="+", help="监听器的最大连接数，支持多值查询")
parser.add_argument("--tls_ciphers_policy", type=str, nargs="+", help="监听器使用的安全策略，支持多值查询")
parser.add_argument("--member_address", type=str, nargs="+", help="后端服务器的IP地址，仅用于查询条件，支持多值查询")
parser.add_argument("--member_device_id", type=str, nargs="+", help="后端服务器对应的弹性云服务器的ID，仅用于查询条件，支持多值查询")
parser.add_argument("--member_instance_id", type=str, nargs="+", help="后端服务器ID，仅用于查询条件，支持多值查询")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="资源所属的企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--enable_member_retry", type=bool, help="是否开启后端服务器的重试，true开启，false不开启")
parser.add_argument("--member_timeout", type=int, nargs="+", help="等待后端服务器响应超时时间，支持多值查询")
parser.add_argument("--client_timeout", type=int, nargs="+", help="等待客户端请求超时时间，支持多值查询")
parser.add_argument("--keepalive_timeout", type=int, nargs="+", help="客户端连接空闲超时时间，支持多值查询")
parser.add_argument("--transparent_client_ip_enable", type=bool, help="是否开启客户端IP地址透传到后端服务器")
parser.add_argument("--proxy_protocol_enable", type=bool, help="是否开启proxy_protocol")
parser.add_argument("--enhance_l7policy_enable", type=bool, help="是否开启高级转发策略功能")
parser.add_argument("--protection_status", type=str, nargs="+", help="修改保护状态，nonProtection不保护，consoleProtection控制台修改保护，支持多值查询")
parser.add_argument("--ssl_early_data_enable", type=bool, help="是否开启监听器0-RTT功能")
parser.add_argument("--nat64_enable", type=bool, help="是否开启nat64地址转换功能")
parser.add_argument("--include_recycle_bin", type=bool, help="查询结果是否包含回收站负载均衡器的监听器，true包含，false不包含")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by protocol_port:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('protocol_port', 'connection_limit') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: protocol_port, connection_limit；方向可选: asc, desc。例如 protocol_port:asc")
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

    request = ListListenersRequest()
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
    if args.protocol:
        request.protocol = args.protocol
    if args.protocol_port:
        request.protocol_port = args.protocol_port
    if args.default_pool_id:
        request.default_pool_id = args.default_pool_id
    if args.default_tls_container_ref:
        request.default_tls_container_ref = args.default_tls_container_ref
    if args.client_ca_tls_container_ref:
        request.client_ca_tls_container_ref = args.client_ca_tls_container_ref
    if args.admin_state_up is not None:
        request.admin_state_up = args.admin_state_up
    if args.http2_enable is not None:
        request.http2_enable = args.http2_enable
    if args.connection_limit is not None:
        request.connection_limit = args.connection_limit
    if args.tls_ciphers_policy:
        request.tls_ciphers_policy = args.tls_ciphers_policy
    if args.member_address:
        request.member_address = args.member_address
    if args.member_device_id:
        request.member_device_id = args.member_device_id
    if args.member_instance_id:
        request.member_instance_id = args.member_instance_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.enable_member_retry is not None:
        request.enable_member_retry = args.enable_member_retry
    if args.member_timeout is not None:
        request.member_timeout = args.member_timeout
    if args.client_timeout is not None:
        request.client_timeout = args.client_timeout
    if args.keepalive_timeout is not None:
        request.keepalive_timeout = args.keepalive_timeout
    if args.transparent_client_ip_enable is not None:
        request.transparent_client_ip_enable = args.transparent_client_ip_enable
    if args.proxy_protocol_enable is not None:
        request.proxy_protocol_enable = args.proxy_protocol_enable
    if args.enhance_l7policy_enable is not None:
        request.enhance_l7policy_enable = args.enhance_l7policy_enable
    if args.protection_status:
        request.protection_status = args.protection_status
    if args.ssl_early_data_enable is not None:
        request.ssl_early_data_enable = args.ssl_early_data_enable
    if args.nat64_enable is not None:
        request.nat64_enable = args.nat64_enable
    if args.include_recycle_bin is not None:
        request.include_recycle_bin = args.include_recycle_bin

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地排序
        all_listeners = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_listeners(request)
            listeners = response.listeners
            if not listeners:
                break
            # 检测重复数据
            if marker and all_listeners and getattr(listeners[0], 'id', None) == getattr(all_listeners[-1], 'id', None):
                break
            all_listeners.extend(listeners)
            if len(listeners) < API_LIMIT:
                break
            marker = listeners[-1].id
            if not marker:
                break

        if not all_listeners:
            print("没有找到监听器")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'protocol_port':
                all_listeners.sort(key=lambda f: int(getattr(f, 'protocol_port', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'connection_limit':
                all_listeners.sort(key=lambda f: int(getattr(f, 'connection_limit', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_listeners = all_listeners[:args.top]

        # 渲染
        output = f"name\tid\tprotocol\tprotocol_port\tloadbalancer_id\tdefault_pool_id\tadmin_state_up\tconnection_limit\tcreated_at\n"
        for item in all_listeners:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            protocol = getattr(item, 'protocol', '')
            protocol_port = getattr(item, 'protocol_port', '')
            loadbalancers = getattr(item, 'loadbalancers', [])
            loadbalancer_id = ','.join([getattr(lb, 'id', '') for lb in loadbalancers]) if loadbalancers else ''
            default_pool_id = getattr(item, 'default_pool_id', '')
            admin_state_up = getattr(item, 'admin_state_up', '')
            connection_limit = getattr(item, 'connection_limit', '')
            created_at = getattr(item, 'created_at', '')
            output += f"{name}\t{id}\t{protocol}\t{protocol_port}\t{loadbalancer_id}\t{default_pool_id}\t{admin_state_up}\t{connection_limit}\t{created_at}\n"
        output += f"\n共 {len(all_listeners)} 条"
        print(output)
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_listeners(request)
        listeners = response.listeners

        if not listeners:
            print(f"没有找到监听器 (区域: {Region})")
            exit(0)

        # Response 有 page_info，使用 page_info.next_marker 判断分页
        next_marker = None
        page_info = getattr(response, 'page_info', None)
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        else:
            has_more = len(listeners) > PAGE_SIZE
            if has_more:
                next_marker = str(getattr(listeners[PAGE_SIZE - 1], 'id', ''))

        display_listeners = listeners[:PAGE_SIZE]

        output = f"name\tid\tprotocol\tprotocol_port\tloadbalancer_id\tdefault_pool_id\tadmin_state_up\tconnection_limit\tcreated_at\n"
        for item in display_listeners:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            protocol = getattr(item, 'protocol', '')
            protocol_port = getattr(item, 'protocol_port', '')
            loadbalancers = getattr(item, 'loadbalancers', [])
            loadbalancer_id = ','.join([getattr(lb, 'id', '') for lb in loadbalancers]) if loadbalancers else ''
            default_pool_id = getattr(item, 'default_pool_id', '')
            admin_state_up = getattr(item, 'admin_state_up', '')
            connection_limit = getattr(item, 'connection_limit', '')
            created_at = getattr(item, 'created_at', '')
            output += f"{name}\t{id}\t{protocol}\t{protocol_port}\t{loadbalancer_id}\t{default_pool_id}\t{admin_state_up}\t{connection_limit}\t{created_at}\n"

        if has_more:
            output += f"\n当前返回 {len(display_listeners)} 条，还有更多数据"
            if next_marker:
                output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
        else:
            output += f"\n共 {len(display_listeners)} 条"

        print(output)
except Exception as e:
    print(f"elb.list_listeners 查询失败: {e}")
    exit(1)
