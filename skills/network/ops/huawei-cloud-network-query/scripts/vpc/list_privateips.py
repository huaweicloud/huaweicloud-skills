import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ListPrivateipsRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询私有IP列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--subnet_id", type=str, required=True, help="子网 ID（必填），可通过 list_subnets.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染私有IP列表
    :param items: 私有IP列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到私有IP")
        return

    output = f"id\tsubnet_id\tip_address\tstatus\tdevice_owner\ttenant_id\n"
    for item in items:
        id = getattr(item, 'id', '')
        subnet_id = getattr(item, 'subnet_id', '')
        ip_address = getattr(item, 'ip_address', '')
        status = getattr(item, 'status', '')
        device_owner = getattr(item, 'device_owner', '')
        tenant_id = getattr(item, 'tenant_id', '')
        output += f"{id}\t{subnet_id}\t{ip_address}\t{status}\t{device_owner}\t{tenant_id}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条私有IP，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --subnet_id 参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --subnet_id 参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --subnet_id 参数缩小查询范围"
        else:
            output += f"\n可使用 --subnet_id 参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条私有IP"

    print(output)


try:
    http_config = build_http_config()
    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPC 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListPrivateipsRequest()
    request.limit = FETCH_SIZE
    if args.subnet_id:
        request.subnet_id = args.subnet_id
    if args.marker:
        request.marker = args.marker

    # 只做一次查询
    response = client.list_privateips(request)
    items = response.privateips

    if not items:
        print(f"没有找到私有IP (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # Response 无 page_info 和 count，通过多查的第 FETCH_SIZE 条判断
    next_marker = None
    has_more = len(items) > PAGE_SIZE
    if has_more:
        next_marker = str(getattr(items[PAGE_SIZE - 1], 'id', ''))

    # 只展示前 PAGE_SIZE 条
    display_items = items[:PAGE_SIZE]

    # 渲染结果
    render(display_items, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpc.list_privateips 查询失败: {e}")
    exit(1)
