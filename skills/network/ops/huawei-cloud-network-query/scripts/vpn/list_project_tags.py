import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListProjectTagsRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询项目标签")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--resource_type", type=str, required=True, help="资源类型 (必填)，如 vpn-gateway, vpn-connection, customer-gateway, p2c-vpn-gateway")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染项目标签列表
    :param items: 标签列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到项目标签")
        return

    output = f"key\tvalues\n"
    for tag in items:
        key = getattr(tag, 'key', '')
        values = getattr(tag, 'values', []) or []
        output += f"{key}\t{', '.join(values)}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    else:
        output += f"\n共 {showing_count} 条"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()
    client = VpnClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpnRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPN 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListProjectTagsRequest()
    request.resource_type = args.resource_type
    response = client.list_project_tags(request)
    tags = response.tags

    if not tags:
        print(f"没有找到项目标签 (区域: {Region}, 资源类型: {args.resource_type})")
        exit(0)

    # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
    # 标签用 key 作为唯一标识
    start_idx = 0
    if args.marker:
        for i, tag in enumerate(tags):
            if str(getattr(tag, 'key', '')) == args.marker:
                start_idx = i + 1
                break

    remaining_items = tags[start_idx:]
    if not remaining_items:
        print("没有更多数据")
        exit(0)

    # 判断是否还有更多数据
    has_more = len(remaining_items) > PAGE_SIZE
    next_marker = None
    if has_more:
        next_marker = str(getattr(remaining_items[PAGE_SIZE - 1], 'key', ''))
    display_items = remaining_items[:PAGE_SIZE]

    # 渲染结果
    render(display_items, total_count=len(tags), has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpn.list_project_tags 查询失败: {e}")
    exit(1)
