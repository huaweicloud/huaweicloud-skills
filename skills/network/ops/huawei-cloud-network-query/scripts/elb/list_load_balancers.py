import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListLoadBalancersRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 负载均衡器列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="负载均衡器ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="负载均衡器名称，支持多值查询")
parser.add_argument("--description", type=str, nargs="+", help="负载均衡器的描述信息，支持多值查询")
parser.add_argument("--admin_state_up", type=bool, help="负载均衡器的启用状态，true启用，false停用")
parser.add_argument("--provisioning_status", type=str, nargs="+", help="负载均衡器的配置状态，支持多值查询，如 ACTIVE PENDING_DELETE")
parser.add_argument("--operating_status", type=str, nargs="+", help="负载均衡器的操作状态，支持多值查询，如 ONLINE FROZEN")
parser.add_argument("--guaranteed", type=bool, help="是否独享型LB，false共享型，true独享型")
parser.add_argument("--vpc_id", type=str, nargs="+", help="负载均衡器所在的VPC ID，支持多值查询")
parser.add_argument("--vip_port_id", type=str, nargs="+", help="负载均衡器的IPv4对应的port ID，支持多值查询")
parser.add_argument("--vip_address", type=str, nargs="+", help="负载均衡器的IPv4私网IP地址，支持多值查询")
parser.add_argument("--vip_subnet_cidr_id", type=str, nargs="+", help="负载均衡器所在子网的IPv4子网ID（前端子网），支持多值查询")
parser.add_argument("--ipv6_vip_port_id", type=str, nargs="+", help="双栈类型负载均衡器的IPv6对应的port ID")
parser.add_argument("--ipv6_vip_address", type=str, nargs="+", help="双栈类型负载均衡器的IPv6地址")
parser.add_argument("--ipv6_vip_virsubnet_id", type=str, nargs="+", help="双栈类型负载均衡器所在的子网IPv6网络ID（前端子网）")
parser.add_argument("--eips", type=str, nargs="+", help="负载均衡器绑定的EIP，支持按eip_id/eip_address/ip_version多值查询")
parser.add_argument("--publicips", type=str, nargs="+", help="负载均衡器绑定的公网IP，支持按publicip_id/publicip_address/ip_version多值查询")
parser.add_argument("--global_eips", type=str, nargs="+", help="负载均衡器绑定的全局EIP，支持按global_eip_id/global_eip_address/ip_version多值查询")
parser.add_argument("--availability_zone_list", type=str, nargs="+", help="负载均衡器所在可用区列表，支持多值查询")
parser.add_argument("--l4_flavor_id", type=str, nargs="+", help="网络型规格ID，支持多值查询")
parser.add_argument("--l7_flavor_id", type=str, nargs="+", help="应用型规格ID，支持多值查询")
parser.add_argument("--billing_info", type=str, nargs="+", help="资源账单信息，支持多值查询")
parser.add_argument("--member_device_id", type=str, nargs="+", help="后端服务器对应的弹性云服务器的ID，仅用于查询条件")
parser.add_argument("--member_address", type=str, nargs="+", help="后端服务器对应的弹性云服务器的IP地址，仅用于查询条件")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="资源所属的企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--ip_version", type=int, nargs="+", help="IP版本信息，4代表IPv4，6代表IPv6")
parser.add_argument("--deletion_protection_enable", type=bool, help="是否开启删除保护，false不开启，true开启")
parser.add_argument("--elb_virsubnet_type", type=str, nargs="+", help="下联面子网类型，ipv4或dualstack")
parser.add_argument("--autoscaling", type=str, nargs="+", help="是否开启弹性扩缩容，支持按enable=true/false多值查询")
parser.add_argument("--protection_status", type=str, nargs="+", help="修改保护状态，nonProtection不保护，consoleProtection控制台修改保护")
parser.add_argument("--log_topic_id", type=str, help="LB实例绑定的logtank的topic id信息")
parser.add_argument("--log_group_id", type=str, help="LB所关联的云日志服务（LTS）的日志组ID")
parser.add_argument("--include_recycle_bin", type=bool, help="查询结果是否包含回收站负载均衡器，true包含，false不包含")
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

    request = ListLoadBalancersRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.name:
        request.name = args.name
    if args.id:
        request.id = args.id
    if args.description:
        request.description = args.description
    if args.admin_state_up is not None:
        request.admin_state_up = args.admin_state_up
    if args.provisioning_status:
        request.provisioning_status = args.provisioning_status
    if args.operating_status:
        request.operating_status = args.operating_status
    if args.guaranteed is not None:
        request.guaranteed = args.guaranteed
    if args.vpc_id:
        request.vpc_id = args.vpc_id
    if args.vip_port_id:
        request.vip_port_id = args.vip_port_id
    if args.vip_address:
        request.vip_address = args.vip_address
    if args.vip_subnet_cidr_id:
        request.vip_subnet_cidr_id = args.vip_subnet_cidr_id
    if args.ipv6_vip_port_id:
        request.ipv6_vip_port_id = args.ipv6_vip_port_id
    if args.ipv6_vip_address:
        request.ipv6_vip_address = args.ipv6_vip_address
    if args.ipv6_vip_virsubnet_id:
        request.ipv6_vip_virsubnet_id = args.ipv6_vip_virsubnet_id
    if args.eips:
        request.eips = args.eips
    if args.publicips:
        request.publicips = args.publicips
    if args.global_eips:
        request.global_eips = args.global_eips
    if args.availability_zone_list:
        request.availability_zone_list = args.availability_zone_list
    if args.l4_flavor_id:
        request.l4_flavor_id = args.l4_flavor_id
    if args.l7_flavor_id:
        request.l7_flavor_id = args.l7_flavor_id
    if args.billing_info:
        request.billing_info = args.billing_info
    if args.member_device_id:
        request.member_device_id = args.member_device_id
    if args.member_address:
        request.member_address = args.member_address
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.ip_version is not None:
        request.ip_version = args.ip_version
    if args.deletion_protection_enable is not None:
        request.deletion_protection_enable = args.deletion_protection_enable
    if args.elb_virsubnet_type:
        request.elb_virsubnet_type = args.elb_virsubnet_type
    if args.autoscaling:
        request.autoscaling = args.autoscaling
    if args.protection_status:
        request.protection_status = args.protection_status
    if args.log_topic_id:
        request.log_topic_id = args.log_topic_id
    if args.log_group_id:
        request.log_group_id = args.log_group_id
    if args.include_recycle_bin is not None:
        request.include_recycle_bin = args.include_recycle_bin

    response = client.list_load_balancers(request)
    loadbalancers = response.loadbalancers

    if not loadbalancers:
        print(f"没有找到 ELB 负载均衡器 (区域: {Region})")
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

    output = f"name\tid\tvip_address\tpublic_ip\ttype\tprovisioning_status\toperating_status\tvpc_id\tavailability_zones\tcharge_mode\tenterprise_project_id\tcreated_at\n"
    for lb in display_loadbalancers:
        name = getattr(lb, 'name', '')
        id = getattr(lb, 'id', '')
        vip_address = getattr(lb, 'vip_address', '')
        # 获取公网IP
        publicips = getattr(lb, 'publicips', None)
        if publicips:
            public_ip = ','.join([getattr(p, 'publicip_address', '') for p in publicips if getattr(p, 'publicip_address', '')])
        else:
            eips = getattr(lb, 'eips', None)
            if eips:
                public_ip = ','.join([getattr(e, 'eip_address', '') for e in eips if getattr(e, 'eip_address', '')])
            else:
                public_ip = ''
        guaranteed = getattr(lb, 'guaranteed', None)
        type_str = '独享' if guaranteed else '共享'
        provisioning_status = getattr(lb, 'provisioning_status', '')
        operating_status = getattr(lb, 'operating_status', '')
        vpc_id = getattr(lb, 'vpc_id', '')
        availability_zone_list = getattr(lb, 'availability_zone_list', [])
        availability_zones = ','.join(availability_zone_list) if availability_zone_list else ''
        charge_mode = getattr(lb, 'charge_mode', '')
        enterprise_project_id = getattr(lb, 'enterprise_project_id', '')
        created_at = getattr(lb, 'created_at', '')
        output += f"{name}\t{id}\t{vip_address}\t{public_ip}\t{type_str}\t{provisioning_status}\t{operating_status}\t{vpc_id}\t{availability_zones}\t{charge_mode}\t{enterprise_project_id}\t{created_at}\n"

    if has_more:
        output += f"\n当前返回 {len(display_loadbalancers)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_loadbalancers)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_load_balancers 查询失败: {e}")
    exit(1)
