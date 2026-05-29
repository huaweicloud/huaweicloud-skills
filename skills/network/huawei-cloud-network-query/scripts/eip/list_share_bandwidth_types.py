import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ListShareBandwidthTypesRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询共享带宽类型列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--id", type=str, help="共享带宽类型 ID，精确匹配")
parser.add_argument("--bandwidth_type", type=str, help="带宽类型，如 bgp/sbgp 等")
parser.add_argument("--name_en", type=str, help="带宽类型英文名称")
parser.add_argument("--name_zh", type=str, help="带宽类型中文名称")
parser.add_argument("--public_border_group", type=str, help="站点信息，可通过 list_common_pools.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(types, total_count=None, has_more=False, next_marker=None):
    if not types:
        print("没有找到共享带宽类型")
        return

    output = f"id\tbandwidth_type\tname_zh\tname_en\tpublic_border_group\n"
    for t in types:
        t_id = getattr(t, 'id', '')
        bandwidth_type = getattr(t, 'bandwidth_type', '')
        name_zh = getattr(t, 'name_zh', '')
        name_en = getattr(t, 'name_en', '')
        public_border_group = getattr(t, 'public_border_group', '')
        output += f"{t_id}\t{bandwidth_type}\t{name_zh}\t{name_en}\t{public_border_group}\n"

    # 汇总信息
    showing_count = len(types)

    if total_count is not None:
        output += f"\n共 {total_count} 个共享带宽类型，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --bandwidth_type / --public_border_group 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --id / --bandwidth_type / --public_border_group 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --bandwidth_type / --public_border_group 等参数缩小查询范围"
        else:
            output += f"\n可使用 --id / --bandwidth_type / --public_border_group 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个共享带宽类型"

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
    request = ListShareBandwidthTypesRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.bandwidth_type:
        request.bandwidth_type = args.bandwidth_type
    if args.name_en:
        request.name_en = args.name_en
    if args.name_zh:
        request.name_zh = args.name_zh
    if args.public_border_group:
        request.public_border_group = args.public_border_group

    # 只做一次查询
    response = client.list_share_bandwidth_types(request)
    total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
    types = response.share_bandwidth_types

    if not types:
        print(f"没有找到共享带宽类型 (区域: {Region})")
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
        has_more = len(types) > PAGE_SIZE

    if has_more and not next_marker and len(types) > PAGE_SIZE:
        next_marker = str(types[PAGE_SIZE - 1].id)

    # 只展示前 PAGE_SIZE 条
    display_types = types[:PAGE_SIZE]

    # 渲染结果
    render(display_types, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eip.list_share_bandwidth_types 查询失败: {e}")
    exit(1)
