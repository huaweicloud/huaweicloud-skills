import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowVpnGatewayRoutingTableRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 VPN 网关路由表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vgw_id", type=str, required=True, help="VPN 网关 ID，可通过 list_vgws.py 获取")
parser.add_argument("--is_include_nexthop_resource", type=str, help="是否包含下一跳资源信息，true/false")
parser.add_argument("--offset", type=int, help="分页偏移量，从 0 开始")
args = parser.parse_args()

if args.region is not None:
    Region = args.region
if args.offset is not None:
    Offset = args.offset
if Offset < 0:
    Offset = 0


def render(all_items):
    total = len(all_items)
    if Offset >= total:
        print(f"查询结果为空\n\n路由表条目共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"destination\tnexthop\toutbound_interface_ip\torigin\tas_path\tmed\tnexthop_resource\n"
    for i in range(Offset, min(total, Offset + 50)):
        item = all_items[i]
        destination = getattr(item, 'destination', '')
        nexthop = getattr(item, 'nexthop', '')
        outbound_interface_ip = getattr(item, 'outbound_interface_ip', '')
        origin = getattr(item, 'origin', '')
        as_path = getattr(item, 'as_path', '')
        med = getattr(item, 'med', '')
        nexthop_resource = getattr(item, 'nexthop_resource', None)
        if nexthop_resource:
            nr_id = getattr(nexthop_resource, 'id', '')
            nr_type = getattr(nexthop_resource, 'type', '')
            nexthop_resource_str = f"{nr_id}({nr_type})"
        else:
            nexthop_resource_str = ''
        output += f"{destination}\t{nexthop}\t{outbound_interface_ip}\t{origin}\t{as_path}\t{med}\t{nexthop_resource_str}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n路由表条目共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
        if end + 1 < total:
            output += f"可以使用 --offset={end + 1} 参数继续获取后续数据"
    print(output)


try:
    http_config = build_http_config()
    client = VpnClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpnRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPN 客户端")
        exit(-1)

    all_items = []
    marker = ""
    limit = 2000

    while True:
        request = ShowVpnGatewayRoutingTableRequest()
        request.vgw_id = args.vgw_id
        request.limit = limit
        if args.is_include_nexthop_resource:
            request.is_include_nexthop_resource = args.is_include_nexthop_resource.lower() == 'true'
        if marker:
            request.marker = marker
        response = client.show_vpn_gateway_routing_table(request)
        items = response.routing_table
        if not items:
            break
        all_items.extend(items)
        page_info = getattr(response, 'page_info', None)
        next_marker = getattr(page_info, 'next_marker', '') if page_info else ''
        if not next_marker:
            break
        marker = next_marker

    if not all_items:
        print(f"没有找到路由表条目 (区域: {Region})")
        exit(0)

    render(all_items)
except Exception as e:
    print(f"vpn.show_vpn_gateway_routing_table 查询失败: {e}")
    exit(1)
