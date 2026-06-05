import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ListResourcesByTagsRequest, QueryResourcesRequestBody, Tag as QueryTag, Match
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="按标签查询资源实例列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--resource_type", type=str, required=True, help="资源类型 (必填)，如 vpn-gateway, vpn-connection, customer-gateway, p2c-vpn-gateway")
parser.add_argument("--without_any_tag", type=str, help="是否查询不带标签的资源，true/false")
parser.add_argument("--tags", type=str, help="标签过滤，格式: key1=value1,value2;key2=value3（多个标签用分号分隔）")
parser.add_argument("--match_resource_name", type=str, help="按资源名称匹配过滤")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(items, total_count=None, has_more=False, next_marker=None):
    """
    渲染资源实例列表
    :param items: 资源列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not items:
        print("没有找到资源")
        return

    output = f"resource_id\tresource_name\ttags\n"
    for r in items:
        resource_id = getattr(r, 'resource_id', '')
        resource_name = getattr(r, 'resource_name', '')
        tags = getattr(r, 'tags', None) or []
        tags_str = '; '.join(f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags)
        output += f"{resource_id}\t{resource_name}\t{tags_str}\n"

    # 汇总信息
    showing_count = len(items)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --tags / --match_resource_name 参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --tags / --match_resource_name 参数缩小查询范围"
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

    # API 使用 offset 分页（无 marker），用 offset 实现服务端分页，对外暴露 --marker
    # marker 值为 offset 数值（字符串形式）
    sdk_offset = 0
    if args.marker:
        try:
            sdk_offset = int(args.marker)
        except ValueError:
            sdk_offset = 0

    request = ListResourcesByTagsRequest()
    request.resource_type = args.resource_type
    request.limit = str(FETCH_SIZE)
    request.offset = str(sdk_offset)

    body = QueryResourcesRequestBody()
    if args.without_any_tag:
        body.without_any_tag = args.without_any_tag.lower() == 'true'
    if args.tags:
        tag_list = []
        for tag_part in args.tags.split(';'):
            if '=' in tag_part:
                key, values_str = tag_part.split('=', 1)
                values = values_str.split(',')
                tag_list.append(QueryTag(key=key, values=values))
        if tag_list:
            body.tags = tag_list
    if args.match_resource_name:
        body.matches = [Match(key='resource_name', value=args.match_resource_name)]
    request.body = body

    response = client.list_resources_by_tags(request)
    resources = response.resources
    total_count = getattr(response, 'total_count', None)

    if not resources:
        print(f"没有找到资源 (区域: {Region}, 资源类型: {args.resource_type})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    if total_count is not None:
        has_more = total_count > sdk_offset + PAGE_SIZE
    else:
        has_more = len(resources) > PAGE_SIZE

    if has_more:
        next_marker = str(sdk_offset + PAGE_SIZE)

    # 只展示前 PAGE_SIZE 条
    display_items = resources[:PAGE_SIZE]

    # 渲染结果
    render(display_items, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"vpn.list_resources_by_tags 查询失败: {e}")
    exit(1)
