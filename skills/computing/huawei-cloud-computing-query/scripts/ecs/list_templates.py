import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListTemplatesRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 启动模板列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--name", type=str, help="模板名称，支持模糊匹配")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(templates, total_count=None, has_more=False, next_marker=None):
    if not templates:
        print("没有找到 ECS 启动模板")
        return

    output = f"id\tname\tcreated_at\n"
    for t in templates:
        tid = getattr(t, 'id', '')
        name = getattr(t, 'name', '')
        created_at = getattr(t, 'created_at', '')
        output += f"{tid}\t{name}\t{created_at}\n"

    # 汇总信息
    showing_count = len(templates)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS 启动模板，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name 参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --name 参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name 参数缩小查询范围"
        else:
            output += f"\n可使用 --name 参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 ECS 启动模板"

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
    request = ListTemplatesRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.name:
        request.name = [args.name]

    # 只做一次查询
    response = client.list_templates(request)
    total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
    templates = response.launch_templates

    if not templates:
        print(f"没有找到 ECS 启动模板 (区域: {Region})")
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
        has_more = len(templates) > PAGE_SIZE

    if has_more and not next_marker and len(templates) > PAGE_SIZE:
        next_marker = str(templates[PAGE_SIZE - 1].id)

    # 只展示前 PAGE_SIZE 条
    display_templates = templates[:PAGE_SIZE]

    # 渲染结果
    render(display_templates, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"ecs.templates 查询失败: {e}")
    exit(1)
