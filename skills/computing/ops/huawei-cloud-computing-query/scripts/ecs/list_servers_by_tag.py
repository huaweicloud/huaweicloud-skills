import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListServersByTagRequest, ListServersByTagRequestBody, ServerTags, ServerTagMatch
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="按标签查询 ECS 服务器列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--tag_key", type=str, help="标签键（包含该标签的服务器）")
parser.add_argument("--tag_value", type=str, help="标签值（与 tag_key 配合使用）")
parser.add_argument("--not_tag_key", type=str, help="排除标签键（不包含该标签的服务器）")
parser.add_argument("--not_tag_value", type=str, help="排除标签值（与 not_tag_key 配合使用）")
parser.add_argument("--resource_name", type=str, help="按资源名称搜索（模糊匹配）")
parser.add_argument("--offset", type=int, help="查询偏移量，从 0 开始，用于翻页")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(resources, total_count=None, has_more=False, next_offset=None):
    if not resources:
        print("没有找到按标签查询的 ECS 服务器")
        return

    output = f"resource_id\tresource_name\ttags\n"
    for res in resources:
        resource_id = getattr(res, 'resource_id', '')
        resource_name = getattr(res, 'resource_name', '')
        tags = getattr(res, 'tags', [])
        if tags:
            tag_str = ','.join(f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags)
        else:
            tag_str = ''
        output += f"{resource_id}\t{resource_name}\t{tag_str}\n"

    # 汇总信息
    showing_count = len(resources)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS 服务器，当前返回 {showing_count} 条"
        if has_more and next_offset is not None:
            output += f"\n可使用 --offset={next_offset} 继续查询下一页，或使用 --tag_key / --not_tag_key / --resource_name 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --tag_key / --not_tag_key / --resource_name 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_offset is not None:
            output += f"\n可使用 --offset={next_offset} 继续查询下一页，或使用 --tag_key / --not_tag_key / --resource_name 等参数缩小查询范围"
        else:
            output += f"\n可使用 --tag_key / --not_tag_key / --resource_name 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 ECS 服务器"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    # 构建请求
    request = ListServersByTagRequest()
    body = ListServersByTagRequestBody()
    body.action = "filter"
    body.limit = str(FETCH_SIZE)
    body.offset = str(args.offset if args.offset else 0)

    if args.tag_key:
        server_tag = ServerTags()
        server_tag.key = args.tag_key
        if args.tag_value:
            server_tag.value = args.tag_value
        if not body.tags:
            body.tags = []
        body.tags.append(server_tag)

    if args.not_tag_key:
        not_tag = ServerTags()
        not_tag.key = args.not_tag_key
        if args.not_tag_value:
            not_tag.value = args.not_tag_value
        if not body.not_tags:
            body.not_tags = []
        body.not_tags.append(not_tag)

    if args.resource_name:
        match = ServerTagMatch()
        match.key = "resource_name"
        match.value = args.resource_name
        if not body.matches:
            body.matches = []
        body.matches.append(match)

    request.body = body

    # 只做一次查询
    response = client.list_servers_by_tag(request)
    total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
    resources = response.resources

    if not resources:
        print(f"没有找到按标签查询的 ECS 服务器 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据
    next_offset = None
    if total_count is not None:
        has_more = total_count > (args.offset if args.offset else 0) + PAGE_SIZE
    else:
        has_more = len(resources) > PAGE_SIZE

    if has_more:
        next_offset = (args.offset if args.offset else 0) + PAGE_SIZE

    # 只展示前 PAGE_SIZE 条
    display_resources = resources[:PAGE_SIZE]

    # 渲染结果
    render(display_resources, total_count=total_count, has_more=has_more, next_offset=next_offset)
except Exception as e:
    print(f"ecs.servers_by_tag 查询失败: {e}")
    exit(1)
