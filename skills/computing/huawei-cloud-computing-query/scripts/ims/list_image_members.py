import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import ListImageMembersRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 IMS 镜像成员列表（共享镜像的接受者信息），需要指定镜像 ID")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--image_id", type=str, required=True, help="镜像 ID，可通过 list_images.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(members, total_count=None, has_more=False, next_marker=None):
    """
    渲染镜像成员列表
    :param members: 成员列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not members:
        print(f"没有找到镜像成员 (镜像 ID: {args.image_id})")
        return

    output = f"member_id\tstatus\tmember_type\tcreated_at\n"
    for m in members:
        member_id = getattr(m, 'member_id', '')
        status = getattr(m, 'status', '')
        member_type = getattr(m, 'member_type', '')
        created_at = getattr(m, 'created_at', '')
        output += f"{member_id}\t{status}\t{member_type}\t{created_at}\n"

    # 汇总信息
    showing_count = len(members)

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

    # 构建请求
    request = ListImageMembersRequest()
    request.image_id = args.image_id
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker

    # 只做一次查询
    response = client.list_image_members(request)
    members = response.members

    if not members:
        render([])
        exit(0)

    # Response 有 page_info，必须用 page_info.next_marker
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        # 无 page_info 时，通过多查的第 FETCH_SIZE 条判断
        has_more = len(members) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(members[PAGE_SIZE - 1], 'member_id', ''))

    # 只展示前 PAGE_SIZE 条
    display_members = members[:PAGE_SIZE]

    # 渲染结果
    render(display_members, has_more=has_more, next_marker=next_marker)

except Exception as e:
    print(f"ims.list_image_members 查询失败: {e}")
    exit(1)
