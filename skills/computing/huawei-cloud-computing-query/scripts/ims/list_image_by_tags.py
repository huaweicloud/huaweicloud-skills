import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import ListImageByTagsRequest, ListImageByTagsRequestBody, Tags, TagKeyValue
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="按标签查询 IMS 镜像，支持通过标签键值对和资源属性进行过滤")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--action", type=str, choices=["filter", "count"], default="filter", help="操作类型: filter(分页查询)/count(仅返回总数)，默认 filter")
parser.add_argument("--tag", type=str, action="append", help="包含标签(与关系)，格式: key=value，可多次指定，最多10个key，每个key最多10个values")
parser.add_argument("--tag_any", type=str, action="append", help="包含任意标签(或关系)，格式: key=value，可多次指定，最多10个key，每个key最多10个values")
parser.add_argument("--not_tag", type=str, action="append", help="不包含标签，格式: key=value，可多次指定，最多10个key，每个key最多10个values")
parser.add_argument("--not_tag_any", type=str, action="append", help="不包含任意标签，格式: key=value，可多次指定，最多10个key，每个key最多10个values")
parser.add_argument("--match", type=str, action="append", help="搜索字段，格式: key=value，可多次指定，key为resource_name/resource_id，多个key不允许重复")
parser.add_argument("--without_any_tag", action="store_true", help="查询所有不带标签的资源，此时忽略tag/not_tag/tag_any/not_tag_any")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(resources, total_count=None, has_more=False, next_marker=None):
    """
    渲染镜像列表
    :param resources: 资源列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not resources:
        print(f"没有找到符合条件的 IMS 镜像 (区域: {Region})")
        return

    output = f"resource_id\tresource_name\tstatus\n"
    for r in resources:
        resource_id = getattr(r, 'resource_id', '')
        resource_name = getattr(r, 'resource_name', '')
        detail = getattr(r, 'resource_detail', None)
        status = getattr(detail, 'status', '') if detail else ''
        output += f"{resource_id}\t{resource_name}\t{status}\n"

    # 汇总信息
    showing_count = len(resources)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --tag / --match 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --tag / --match 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = ImsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ImsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 IMS 客户端")
        exit(-1)

    request = ListImageByTagsRequest()
    body = ListImageByTagsRequestBody()
    body.action = args.action

    # action=count 时不能传 limit 和 offset
    if args.action == "filter":
        # API 使用 offset 分页，marker 值为 offset 数值
        offset = 0
        if args.marker:
            try:
                offset = int(args.marker)
            except ValueError:
                print(f"marker 格式错误，应为数字: {args.marker}")
                exit(1)
        body.limit = str(FETCH_SIZE)
        body.offset = str(offset)

    # 解析标签过滤条件
    def parse_tags(tag_list):
        """将 ['key=value', 'key=value2'] 格式解析为 [Tags(key='k', values=['v1','v2'])]"""
        if not tag_list:
            return None
        tag_map = {}
        for item in tag_list:
            if '=' not in item:
                print(f"标签格式错误: '{item}'，应为 key=value 格式")
                exit(1)
            k, v = item.split('=', 1)
            if k not in tag_map:
                tag_map[k] = []
            tag_map[k].append(v)
        return [Tags(key=k, values=vs) for k, vs in tag_map.items()]

    if args.tag:
        body.tags = parse_tags(args.tag)
    if args.tag_any:
        body.tags_any = parse_tags(args.tag_any)
    if args.not_tag:
        body.not_tags = parse_tags(args.not_tag)
    if args.not_tag_any:
        body.not_tags_any = parse_tags(args.not_tag_any)
    if args.without_any_tag:
        body.without_any_tag = True

    # 解析资源属性匹配
    if args.match:
        matches_list = []
        for item in args.match:
            if '=' not in item:
                print(f"匹配格式错误: '{item}'，应为 key=value 格式，key 支持 resource_name/resource_id")
                exit(1)
            k, v = item.split('=', 1)
            matches_list.append(TagKeyValue(key=k, value=v))
        body.matches = matches_list

    request.body = body

    # 只做一次查询
    response = client.list_image_by_tags(request)

    if args.action == "count":
        print(f"镜像总数: {response.total_count}")
    else:
        resources = response.resources
        total_count = response.total_count

        if not resources:
            render([])
            exit(0)

        # Response 有 total_count，用它判断 has_more
        next_marker = None
        has_more = total_count > PAGE_SIZE if total_count is not None else len(resources) > PAGE_SIZE

        if has_more and len(resources) > PAGE_SIZE:
            # 多查的1条存在，用当前 offset + PAGE_SIZE 作为 next_marker
            current_offset = int(body.offset) if body.offset else 0
            next_marker = str(current_offset + PAGE_SIZE)

        # 只展示前 PAGE_SIZE 条
        display_resources = resources[:PAGE_SIZE]

        # 渲染结果
        render(display_resources, total_count=total_count, has_more=has_more, next_marker=next_marker)

except Exception as e:
    print(f"ims.list_image_by_tags 查询失败: {e}")
    exit(1)
