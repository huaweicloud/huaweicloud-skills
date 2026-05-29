import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ListPublicipsRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限（此 API 上限为 2000）

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询弹性公网IP列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--id", type=str, nargs="+", help="弹性公网IP ID，支持多个")
parser.add_argument("--status", type=str, choices=["FREEZED", "DOWN", "ACTIVE", "ERROR"], help="状态过滤: FREEZED(冻结)/DOWN(未绑定)/ACTIVE(已绑定)/ERROR(异常)")
parser.add_argument("--type", type=str, choices=["EIP", "DUALSTACK", "DUALSTACK_SUBNET"], help="类型过滤: EIP(独享)/DUALSTACK(双栈)/DUALSTACK_SUBNET(双栈子网)")
parser.add_argument("--public_ip_address", type=str, nargs="+", help="公网IP地址，精确匹配，支持多个")
parser.add_argument("--public_ip_address_like", type=str, help="公网IP地址，模糊匹配")
parser.add_argument("--public_ipv6_address", type=str, nargs="+", help="公网IPv6地址，精确匹配，支持多个")
parser.add_argument("--ip_version", type=int, choices=[4, 6], help="IP版本: 4(IPv4)/6(IPv6)")
parser.add_argument("--alias_like", type=str, help="别名，模糊匹配")
parser.add_argument("--network_type", type=str, choices=["5_telcom", "5_union", "5_bgp", "5_sbgp", "5_ipv6", "5_graybgp"], help="网络类型: 5_telcom(联通)/5_union(联合)/5_bgp(动态BGP)/5_sbgp(静态BGP)/5_ipv6(IPv6)/5_graybgp(灰度BGP)")
parser.add_argument("--publicip_pool_name", type=str, nargs="+", help="公网IP池名称，支持多个")
parser.add_argument("--vnic_private_ip_address", type=str, nargs="+", help="关联实例的私有IP地址，支持多个")
parser.add_argument("--vnic_vpc_id", type=str, nargs="+", help="关联实例所属 VPC ID，可通过 scripts/vpc/list_vpcs.py 获取，支持多个")
parser.add_argument("--vnic_device_id", type=str, nargs="+", help="关联实例的设备 ID，支持多个")
parser.add_argument("--vnic_port_id", type=str, nargs="+", help="关联实例的端口 ID，支持多个")
parser.add_argument("--bandwidth_id", type=str, nargs="+", help="关联带宽 ID，可通过 list_bandwidth.py 获取，支持多个")
parser.add_argument("--bandwidth_share_type", type=str, choices=["PER", "WHOLE"], help="带宽共享类型: PER(独享)/WHOLE(共享)")
parser.add_argument("--bandwidth_charge_mode", type=str, choices=["bandwidth", "traffic", "95peak_plus"], help="带宽计费模式: bandwidth(按带宽)/traffic(按流量)/95peak_plus(按增强型95)")
parser.add_argument("--associate_instance_type", type=str, choices=["PORT", "NATGW", "ELB", "VPN", "ELBV1"], help="关联实例类型: PORT(端口)/NATGW(NAT网关)/ELB(弹性负载均衡)/VPN(VPN网关)/ELBV1(弹性负载均衡V1)")
parser.add_argument("--associate_instance_id", type=str, nargs="+", help="关联实例 ID，支持多个")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="企业项目 ID，支持多个，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--public_border_group", type=str, nargs="+", help="站点信息，可通过 list_common_pools.py 获取，支持多个")
parser.add_argument("--billing_mode", type=str, choices=["YEARLY_MONTHLY", "PAY_PER_USE"], help="计费模式: YEARLY_MONTHLY(包年包月)/PAY_PER_USE(按需)")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: bandwidth_size；方向可选: asc(升序), desc(降序)。例如 bandwidth_size:asc 表示按带宽升序，bandwidth_size:desc 表示按带宽降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by bandwidth_size:asc --top 5 查找带宽最小的 5 个公网IP，--sort_by bandwidth_size:desc --top 3 查找带宽最大的 3 个公网IP")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by bandwidth_size:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('bandwidth_size',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: bandwidth_size；方向可选: asc, desc。例如 bandwidth_size:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数
has_custom_filter = args.sort_by is not None


# 渲染
def render(publicips, total_count=None, has_more=False, next_marker=None):
    if not publicips:
        print("没有找到弹性公网IP")
        return

    output = f"id\tpublic_ip_address\tstatus\ttype\talias\tbandwidth_size\n"
    for eip in publicips:
        eip_id = getattr(eip, 'id', '')
        public_ip_address = getattr(eip, 'public_ip_address', '')
        status = getattr(eip, 'status', '')
        eip_type = getattr(eip, 'type', '')
        alias = getattr(eip, 'alias', '')
        bandwidth = getattr(eip, 'bandwidth', None)
        bandwidth_size = str(getattr(bandwidth, 'size', '')) if bandwidth else ''
        output += f"{eip_id}\t{public_ip_address}\t{status}\t{eip_type}\t{alias}\t{bandwidth_size}\n"

    # 汇总信息
    showing_count = len(publicips)

    if total_count is not None:
        output += f"\n共 {total_count} 个弹性公网IP，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --status / --type / --public_ip_address 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --status / --type / --public_ip_address 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --status / --type / --public_ip_address 等参数缩小查询范围"
        else:
            output += f"\n可使用 --status / --type / --public_ip_address 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个弹性公网IP"

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
    request = ListPublicipsRequest()
    if args.id:
        request.id = args.id
    if args.status:
        request.status = [args.status]
    if args.type:
        request.type = [args.type]
    if args.public_ip_address:
        request.public_ip_address = args.public_ip_address
    if args.public_ip_address_like:
        request.public_ip_address_like = args.public_ip_address_like
    if args.public_ipv6_address:
        request.public_ipv6_address = args.public_ipv6_address
    if args.ip_version is not None:
        request.ip_version = [args.ip_version]
    if args.alias_like:
        request.alias_like = args.alias_like
    if args.network_type:
        request.network_type = [args.network_type]
    if args.publicip_pool_name:
        request.publicip_pool_name = args.publicip_pool_name
    if args.vnic_private_ip_address:
        request.vnic_private_ip_address = args.vnic_private_ip_address
    if args.vnic_vpc_id:
        request.vnic_vpc_id = args.vnic_vpc_id
    if args.vnic_device_id:
        request.vnic_device_id = args.vnic_device_id
    if args.vnic_port_id:
        request.vnic_port_id = args.vnic_port_id
    if args.bandwidth_id:
        request.bandwidth_id = args.bandwidth_id
    if args.bandwidth_share_type:
        request.bandwidth_share_type = [args.bandwidth_share_type]
    if args.bandwidth_charge_mode:
        request.bandwidth_charge_mode = [args.bandwidth_charge_mode]
    if args.associate_instance_type:
        request.associate_instance_type = [args.associate_instance_type]
    if args.associate_instance_id:
        request.associate_instance_id = args.associate_instance_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.public_border_group:
        request.public_border_group = args.public_border_group
    if args.billing_mode:
        request.billing_mode = args.billing_mode

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 排序 + 截取
        all_publicips = []
        marker = args.marker or ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_publicips(request)
            publicips = response.publicips
            if not publicips:
                break
            # 检测重复数据：如果本页第一条的 id 跟上一页最后一条相同，说明 marker 没生效，退出
            if marker and all_publicips and getattr(publicips[0], 'id', None) == getattr(all_publicips[-1], 'id', None):
                break
            all_publicips.extend(publicips)
            if len(publicips) < API_LIMIT:
                break
            page_info = getattr(response, 'page_info', None)
            next_marker = getattr(page_info, 'next_marker', None) if page_info else None
            if next_marker:
                marker = next_marker
            else:
                marker = publicips[-1].id
                if not marker:
                    break

        if not all_publicips:
            print(f"没有找到弹性公网IP (区域: {Region})")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'bandwidth_size':
                all_publicips.sort(key=lambda f: int(getattr(getattr(f, 'bandwidth', None), 'size', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_publicips = all_publicips[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_publicips, total_count=len(all_publicips))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_publicips(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        publicips = response.publicips

        if not publicips:
            print(f"没有找到弹性公网IP (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        page_info = getattr(response, 'page_info', None)
        next_marker = None
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        elif total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            has_more = len(publicips) > PAGE_SIZE

        if has_more and not next_marker and len(publicips) > PAGE_SIZE:
            next_marker = str(publicips[PAGE_SIZE - 1].id)

        # 只展示前 PAGE_SIZE 条
        display_publicips = publicips[:PAGE_SIZE]

        # 渲染结果
        render(display_publicips, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eip.list_publicips 查询失败: {e}")
    exit(1)
