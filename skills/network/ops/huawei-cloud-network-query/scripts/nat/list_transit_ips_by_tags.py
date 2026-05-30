import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ListTransitIpsByTagsRequest, ListTagResourceInstancesRequestBody, Tags, Match
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="按标签过滤查询中转IP实例")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--action", type=str, required=True, choices=["filter", "count"], help="操作类型: filter=过滤查询 count=查询总条数")
parser.add_argument("--tags", type=str, help="包含标签，JSON格式，如: '[{\"key\":\"env\",\"values\":[\"prod\"]}]'")
parser.add_argument("--tags_any", type=str, help="包含任意标签，JSON格式，同tags")
parser.add_argument("--not_tags", type=str, help="不包含标签，JSON格式，同tags")
parser.add_argument("--not_tags_any", type=str, help="不包含任意标签，JSON格式，同tags")
parser.add_argument("--matches", type=str, help="搜索字段，JSON格式，如: '[{\"key\":\"resource_name\",\"value\":\"transit\"}]'")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def parse_tags(json_str):
    if not json_str:
        return None
    data = json.loads(json_str)
    result = []
    for item in data:
        tag = Tags()
        tag.key = item.get('key', '')
        tag.values = item.get('values', [])
        result.append(tag)
    return result


def parse_matches(json_str):
    if not json_str:
        return None
    data = json.loads(json_str)
    result = []
    for item in data:
        match = Match()
        match.key = item.get('key', '')
        match.value = item.get('value', '')
        result.append(match)
    return result


# 渲染
def render(resources, total_count=None, has_more=False, next_marker=None):
    """
    渲染资源列表
    :param resources: 资源列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not resources:
        print("没有找到匹配的中转IP")
        return

    output = f"resource_id\tresource_name\ttags\n"
    for res in resources:
        resource_id = getattr(res, 'resource_id', '')
        resource_name = getattr(res, 'resource_name', '')
        res_tags = getattr(res, 'tags', [])
        tag_str = ';'.join([f"{getattr(t,'key','')}={getattr(t,'value','')}" for t in res_tags]) if res_tags else ''
        output += f"{resource_id}\t{resource_name}\t{tag_str}\n"

    # 汇总信息
    showing_count = len(resources)

    if total_count is not None:
        output += f"\n共 {total_count} 个匹配的中转IP，当前返回 {showing_count} 个"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --tags / --matches 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --tags / --matches 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 个，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --tags / --matches 等参数缩小查询范围"
        else:
            output += f"\n可使用 --tags / --matches 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个匹配的中转IP"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = NatClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(NatRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 NAT 客户端")
        exit(-1)

    # count 模式直接查询总数
    if args.action == "count":
        body = ListTagResourceInstancesRequestBody()
        body.action = "count"
        tags = parse_tags(args.tags)
        if tags:
            body.tags = tags
        tags_any = parse_tags(args.tags_any)
        if tags_any:
            body.tags_any = tags_any
        not_tags = parse_tags(args.not_tags)
        if not_tags:
            body.not_tags = not_tags
        not_tags_any = parse_tags(args.not_tags_any)
        if not_tags_any:
            body.not_tags_any = not_tags_any
        matches = parse_matches(args.matches)
        if matches:
            body.matches = matches

        request = ListTransitIpsByTagsRequest()
        request.body = body
        response = client.list_transit_ips_by_tags(request)
        total = getattr(response, 'total_count', 0)
        print(f"匹配的中转IP总数: {total}")
        exit(0)

    # filter 模式
    # API 使用 offset 分页（无 marker），marker 值为下一页的 offset 数值
    offset = 0
    if args.marker:
        try:
            offset = int(args.marker)
        except ValueError:
            print(f"无效的 marker 值: {args.marker}，应为数字")
            exit(1)

    body = ListTagResourceInstancesRequestBody()
    body.action = "filter"
    body.limit = str(FETCH_SIZE)
    body.offset = str(offset)

    tags = parse_tags(args.tags)
    if tags:
        body.tags = tags
    tags_any = parse_tags(args.tags_any)
    if tags_any:
        body.tags_any = tags_any
    not_tags = parse_tags(args.not_tags)
    if not_tags:
        body.not_tags = not_tags
    not_tags_any = parse_tags(args.not_tags_any)
    if not_tags_any:
        body.not_tags_any = not_tags_any
    matches = parse_matches(args.matches)
    if matches:
        body.matches = matches

    request = ListTransitIpsByTagsRequest()
    request.body = body

    # 只做一次查询
    response = client.list_transit_ips_by_tags(request)
    resources = getattr(response, 'resources', [])
    total_count = getattr(response, 'total_count', None)

    if not resources:
        print(f"没有找到匹配的中转IP (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    if total_count is not None:
        has_more = total_count > (offset + PAGE_SIZE)
    else:
        has_more = len(resources) > PAGE_SIZE

    if has_more:
        next_marker = str(offset + PAGE_SIZE)

    # 只展示前 PAGE_SIZE 条
    display_resources = resources[:PAGE_SIZE]

    # 渲染结果
    render(display_resources, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"nat.list_transit_ips_by_tags 查询失败: {e}")
    exit(1)
