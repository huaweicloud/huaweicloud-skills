import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListMasterSlavePoolsRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 主备后端服务器组列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--description", type=str, nargs="+", help="后端服务器组描述，支持多值查询")
parser.add_argument("--healthmonitor_id", type=str, nargs="+", help="健康检查ID，支持多值查询")
parser.add_argument("--id", type=str, nargs="+", help="后端服务器组ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="后端服务器组名称，支持多值查询")
parser.add_argument("--loadbalancer_id", type=str, nargs="+", help="负载均衡器ID，支持多值查询")
parser.add_argument("--protocol", type=str, nargs="+", help="后端协议，支持多值查询")
parser.add_argument("--lb_algorithm", type=str, nargs="+", help="负载均衡算法，支持多值查询")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--ip_version", type=str, nargs="+", help="IP版本，支持多值查询")
parser.add_argument("--member_address", type=str, nargs="+", help="后端服务器地址，支持多值查询")
parser.add_argument("--member_device_id", type=str, nargs="+", help="后端服务器对应的ECS ID，支持多值查询")
parser.add_argument("--listener_id", type=str, nargs="+", help="监听器ID，支持多值查询")
parser.add_argument("--member_instance_id", type=str, nargs="+", help="后端服务器实例ID，支持多值查询")
parser.add_argument("--vpc_id", type=str, nargs="+", help="VPC ID，支持多值查询")
parser.add_argument("--type", type=str, nargs="+", help="后端服务器组类型，如Instance/Ip，支持多值查询")
parser.add_argument("--connection_drain", type=bool, help="是否开启延迟注销")
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

    request = ListMasterSlavePoolsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.description:
        request.description = args.description
    if args.healthmonitor_id:
        request.healthmonitor_id = args.healthmonitor_id
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.loadbalancer_id:
        request.loadbalancer_id = args.loadbalancer_id
    if args.protocol:
        request.protocol = args.protocol
    if args.lb_algorithm:
        request.lb_algorithm = args.lb_algorithm
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.ip_version:
        request.ip_version = args.ip_version
    if args.member_address:
        request.member_address = args.member_address
    if args.member_device_id:
        request.member_device_id = args.member_device_id
    if args.listener_id:
        request.listener_id = args.listener_id
    if args.member_instance_id:
        request.member_instance_id = args.member_instance_id
    if args.vpc_id:
        request.vpc_id = args.vpc_id
    if args.type:
        request.type = args.type
    if args.connection_drain is not None:
        request.connection_drain = args.connection_drain

    response = client.list_master_slave_pools(request)
    pools = response.pools

    if not pools:
        print(f"没有找到主备后端服务器组 (区域: {Region})")
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

    output = f"id\tname\tprotocol\tlb_algorithm\tvpc_id\ttype\n"
    for item in display_pools:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        protocol = getattr(item, 'protocol', '')
        lb_algorithm = getattr(item, 'lb_algorithm', '')
        vpc_id = getattr(item, 'vpc_id', '')
        type = getattr(item, 'type', '')
        output += f"{id}\t{name}\t{protocol}\t{lb_algorithm}\t{vpc_id}\t{type}\n"

    if has_more:
        output += f"\n当前返回 {len(display_pools)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_pools)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_master_slave_pools 查询失败: {e}")
    exit(1)
