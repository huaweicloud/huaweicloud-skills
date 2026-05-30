import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import ListImageTagsRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询指定 IMS 镜像的标签列表，需要指定镜像 ID")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--image_id", type=str, required=True, help="镜像 ID，可通过 list_images.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(tags, total_count=None, has_more=False, next_marker=None):
    """
    渲染标签列表
    :param tags: 标签列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not tags:
        print(f"镜像没有标签 (镜像 ID: {args.image_id})")
        return

    output = f"key\tvalue\n"
    for t in tags:
        key = getattr(t, 'key', '')
        value = getattr(t, 'value', '')
        output += f"{key}\t{value}\n"

    # 汇总信息
    showing_count = len(tags)

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

    client = ImsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ImsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 IMS 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListImageTagsRequest()
    request.image_id = args.image_id
    response = client.list_image_tags(request)

    tags = response.tags
    if not tags:
        render([])
        exit(0)

    # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
    start_idx = 0
    if args.marker:
        for i, t in enumerate(tags):
            if str(getattr(t, 'key', '')) == args.marker:
                start_idx = i + 1
                break

    remaining_tags = tags[start_idx:]
    if not remaining_tags:
        print("没有更多数据")
        exit(0)

    # 判断是否还有更多数据
    has_more = len(remaining_tags) > PAGE_SIZE
    next_marker = None
    if has_more:
        next_marker = str(getattr(remaining_tags[PAGE_SIZE - 1], 'key', ''))
    display_tags = remaining_tags[:PAGE_SIZE]

    # 渲染结果
    render(display_tags, total_count=len(tags), has_more=has_more, next_marker=next_marker)

except Exception as e:
    print(f"ims.list_image_tags 查询失败: {e}")
    exit(1)
