import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ListTenantVpcIgwsRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询租户下的虚拟IGW（Internet网关）列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--id", type=str, help="虚拟IGW的 ID，精确匹配")
parser.add_argument("--vpc_id", type=str, help="虚拟IGW所属 VPC ID，可通过 scripts/vpc/list_vpcs.py 获取")
parser.add_argument("--name", type=str, help="虚拟IGW名称，精确匹配")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(igws, total_count=None, has_more=False, next_marker=None):
    if not igws:
        print("没有找到虚拟IGW")
        return

    output = f"id\tname\tvpc_id\tenable_ipv6\n"
    for igw in igws:
        igw_id = getattr(igw, 'id', '')
        name = getattr(igw, 'name', '')
        vpc_id = getattr(igw, 'vpc_id', '')
        enable_ipv6 = str(getattr(igw, 'enable_ipv6', ''))
        output += f"{igw_id}\t{name}\t{vpc_id}\t{enable_ipv6}\n"

    # 汇总信息
    showing_count = len(igws)

    if total_count is not None:
        output += f"\n共 {total_count} 个虚拟IGW，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --vpc_id / --name 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --vpc_id / --name 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --vpc_id / --name 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --vpc_id / --name 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个虚拟IGW"

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
    request = ListTenantVpcIgwsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.vpc_id:
        request.vpc_id = args.vpc_id
    if args.name:
        request.name = args.name

    # 只做一次查询
    response = client.list_tenant_vpc_igws(request)
    total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
    igws = response.vpc_igws

    if not igws:
        print(f"没有找到虚拟IGW (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    if total_count is not None:
        has_more = total_count > PAGE_SIZE
    else:
        # 无 count/total_count 字段时，通过多查的第 FETCH_SIZE 条判断
        has_more = len(igws) > PAGE_SIZE

    if has_more and len(igws) > PAGE_SIZE:
        next_marker = str(igws[PAGE_SIZE - 1].id)

    # 只展示前 PAGE_SIZE 条
    display_igws = igws[:PAGE_SIZE]

    # 渲染结果
    render(display_igws, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eip.list_tenant_vpc_igws 查询失败: {e}")
    exit(1)
