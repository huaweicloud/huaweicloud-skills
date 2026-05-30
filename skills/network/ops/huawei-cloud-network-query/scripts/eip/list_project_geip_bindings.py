import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ListProjectGeipBindingsRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询全局弹性公网IP(GEIP)与实例的绑定关系列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--geip_id", type=str, help="全局弹性公网IP的 ID")
parser.add_argument("--geip_ip_address", type=str, help="全局弹性公网IP的 IP 地址")
parser.add_argument("--instance_type", type=str, help="绑定的实例类型，如 EIP/NATGW/ELB 等")
parser.add_argument("--instance_id", type=str, help="绑定的实例 ID")
parser.add_argument("--instance_vpc_id", type=str, help="绑定的实例所属 VPC ID，可通过 scripts/vpc/list_vpcs.py 获取")
parser.add_argument("--public_border_group", type=str, help="站点信息（中心/边缘），可通过 list_common_pools.py 获取")
parser.add_argument("--gcbandwidth_id", type=str, help="骨干带宽的 ID")
parser.add_argument("--gcbandwidth_sla_level", type=str, choices=["Pt", "Au", "Ag", "Cu"], help="网络等级: Pt(铂金)/Au(金)/Ag(银)/Cu(铜)")
parser.add_argument("--vnic_private_ip_address", type=str, help="绑定实例的私有 IP 地址")
parser.add_argument("--vnic_vpc_id", type=str, help="绑定实例所在的 VPC ID，可通过 scripts/vpc/list_vpcs.py 获取")
parser.add_argument("--vnic_port_id", type=str, help="绑定实例端口的 ID")
parser.add_argument("--vnic_device_id", type=str, help="绑定实例端口对应的实例 ID")
parser.add_argument("--vnic_instance_type", type=str, help="绑定实例端口对应的实例类型")
parser.add_argument("--vnic_instance_id", type=str, help="绑定实例端口对应的实例 ID")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(bindings, total_count=None, has_more=False, next_marker=None):
    if not bindings:
        print("没有找到GEIP绑定")
        return

    output = f"geip_id\tgeip_ip_address\tinstance_type\tinstance_id\n"
    for b in bindings:
        geip_id = getattr(b, 'geip_id', '')
        geip_ip_address = getattr(b, 'geip_ip_address', '')
        instance_type = getattr(b, 'instance_type', '')
        instance_id = getattr(b, 'instance_id', '')
        output += f"{geip_id}\t{geip_ip_address}\t{instance_type}\t{instance_id}\n"

    # 汇总信息
    showing_count = len(bindings)

    if total_count is not None:
        output += f"\n共 {total_count} 条GEIP绑定，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --geip_id / --instance_type / --instance_id 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --geip_id / --instance_type / --instance_id 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --geip_id / --instance_type / --instance_id 等参数缩小查询范围"
        else:
            output += f"\n可使用 --geip_id / --instance_type / --instance_id 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条GEIP绑定"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EipClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EipRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EIP 客户端")
        exit(-1)

    # 构建请求
    request = ListProjectGeipBindingsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.geip_id:
        request.geip_id = args.geip_id
    if args.geip_ip_address:
        request.geip_ip_address = args.geip_ip_address
    if args.instance_type:
        request.instance_type = args.instance_type
    if args.instance_id:
        request.instance_id = args.instance_id
    if args.instance_vpc_id:
        request.instance_vpc_id = args.instance_vpc_id
    if args.public_border_group:
        request.public_border_group = args.public_border_group
    if args.gcbandwidth_id:
        request.gcbandwidth_id = args.gcbandwidth_id
    if args.gcbandwidth_sla_level:
        request.gcbandwidth_sla_level = args.gcbandwidth_sla_level
    if args.vnic_private_ip_address:
        request.vnic_private_ip_address = args.vnic_private_ip_address
    if args.vnic_vpc_id:
        request.vnic_vpc_id = args.vnic_vpc_id
    if args.vnic_port_id:
        request.vnic_port_id = args.vnic_port_id
    if args.vnic_device_id:
        request.vnic_device_id = args.vnic_device_id
    if args.vnic_instance_type:
        request.vnic_instance_type = args.vnic_instance_type
    if args.vnic_instance_id:
        request.vnic_instance_id = args.vnic_instance_id

    # 只做一次查询
    response = client.list_project_geip_bindings(request)
    total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
    bindings = response.geip_bindings

    if not bindings:
        print(f"没有找到GEIP绑定 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    if total_count is not None:
        has_more = total_count > PAGE_SIZE
    else:
        # 无 count/total_count 字段时，通过多查的第 FETCH_SIZE 条判断
        has_more = len(bindings) > PAGE_SIZE

    if has_more and len(bindings) > PAGE_SIZE:
        next_marker = str(bindings[PAGE_SIZE - 1].geip_id)

    # 只展示前 PAGE_SIZE 条
    display_bindings = bindings[:PAGE_SIZE]

    # 渲染结果
    render(display_bindings, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eip.list_project_geip_bindings 查询失败: {e}")
    exit(1)
