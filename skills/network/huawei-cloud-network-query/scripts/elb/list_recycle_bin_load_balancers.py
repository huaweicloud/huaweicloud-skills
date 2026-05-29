import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListRecycleBinLoadBalancersRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 回收站负载均衡器列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="负载均衡器ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="负载均衡器名称，支持多值查询")
parser.add_argument("--description", type=str, nargs="+", help="负载均衡器描述，支持多值查询")
parser.add_argument("--admin_state_up", type=bool, help="负载均衡器的启用状态")
parser.add_argument("--operating_status", type=str, nargs="+", help="操作状态，支持多值查询")
parser.add_argument("--guaranteed", type=bool, help="是否独享型LB，false共享型，true独享型")
parser.add_argument("--vpc_id", type=str, nargs="+", help="VPC ID，支持多值查询")
parser.add_argument("--vip_address", type=str, nargs="+", help="IPv4私网IP地址，支持多值查询")
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

    request = ListRecycleBinLoadBalancersRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.description:
        request.description = args.description
    if args.admin_state_up is not None:
        request.admin_state_up = args.admin_state_up
    if args.operating_status:
        request.operating_status = args.operating_status
    if args.guaranteed is not None:
        request.guaranteed = args.guaranteed
    if args.vpc_id:
        request.vpc_id = args.vpc_id
    if args.vip_address:
        request.vip_address = args.vip_address
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    response = client.list_recycle_bin_load_balancers(request)
    loadbalancers = response.loadbalancers

    if not loadbalancers:
        print(f"没有找到回收站负载均衡器 (区域: {Region})")
        exit(0)

    # Response 有 page_info，使用 page_info.next_marker 判断分页
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(loadbalancers) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(loadbalancers[PAGE_SIZE - 1], 'id', ''))

    display_loadbalancers = loadbalancers[:PAGE_SIZE]

    output = f"id\tname\tvip_address\tprovisioning_status\toperating_status\tvpc_id\n"
    for item in display_loadbalancers:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        vip_address = getattr(item, 'vip_address', '')
        provisioning_status = getattr(item, 'provisioning_status', '')
        operating_status = getattr(item, 'operating_status', '')
        vpc_id = getattr(item, 'vpc_id', '')
        output += f"{id}\t{name}\t{vip_address}\t{provisioning_status}\t{operating_status}\t{vpc_id}\n"

    if has_more:
        output += f"\n当前返回 {len(display_loadbalancers)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_loadbalancers)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_recycle_bin_load_balancers 查询失败: {e}")
    exit(1)
