import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListExtendedAvailabilityZonesRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 扩展可用区列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(rows, total_count=None, has_more=False, next_marker=None):
    """
    渲染扩展可用区列表
    :param rows: 行列表，每行为 (name, public_border_group, spec_flavor, spec_attachment_type, spec_ip_version) 元组
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not rows:
        print("没有找到扩展可用区")
        return

    output = f"name\tpublic_border_group\tspec_flavor\tspec_attachment_type\tspec_ip_version\n"
    for name, public_border_group, spec_flavor, spec_attachment_type, spec_ip_version in rows:
        output += f"{name}\t{public_border_group}\t{spec_flavor}\t{spec_attachment_type}\t{spec_ip_version}\n"

    # 汇总信息
    showing_count = len(rows)

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
    request = ListExtendedAvailabilityZonesRequest()
    response = client.list_extended_availability_zones(request)
    items = response.availability_zones

    if not items:
        print(f"没有找到扩展可用区 (区域: {Region})")
        exit(0)

    # 将嵌套的可用区数据展平为行列表
    rows = []
    for item in items:
        name = getattr(item, 'name', '')
        public_border_group = getattr(item, 'public_border_group', '')
        available_specs = getattr(item, 'available_specs', None) or []
        if available_specs:
            for spec in available_specs:
                spec_flavor = getattr(spec, 'flavor', '')
                spec_attachment_type = getattr(spec, 'attachment_type', '')
                spec_ip_version = getattr(spec, 'ip_version', '')
                rows.append((name, public_border_group, spec_flavor, spec_attachment_type, spec_ip_version))
        else:
            rows.append((name, public_border_group, '', '', ''))

    if not rows:
        print(f"没有找到扩展可用区 (区域: {Region})")
        exit(0)

    # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
    # 用 name:spec_flavor:spec_attachment_type:spec_ip_version 作为唯一标识
    start_idx = 0
    if args.marker:
        for i, row in enumerate(rows):
            row_key = f"{row[0]}:{row[2]}:{row[3]}:{row[4]}"
            if row_key == args.marker:
                start_idx = i + 1
                break

    remaining_rows = rows[start_idx:]
    if not remaining_rows:
        print("没有更多数据")
        exit(0)

    # 判断是否还有更多数据
    has_more = len(remaining_rows) > PAGE_SIZE
    next_marker = None
    if has_more:
        row = remaining_rows[PAGE_SIZE - 1]
        next_marker = f"{row[0]}:{row[2]}:{row[3]}:{row[4]}"
    display_rows = remaining_rows[:PAGE_SIZE]

    # 渲染结果
    render(display_rows, total_count=len(rows), has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpn.list_extended_availability_zones 查询失败: {e}")
    exit(1)
