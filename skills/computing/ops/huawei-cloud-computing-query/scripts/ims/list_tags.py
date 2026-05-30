import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import ListTagsRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询租户 IMS 镜像标签列表（仅用户标签），可按镜像属性过滤")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--imagetype", type=str, choices=["gold", "private", "shared", "market"], help="镜像类型过滤: gold(公共)/private(私有)/shared(共享)/market(市场)")
parser.add_argument("--os_type", type=str, choices=["Linux", "Windows", "Other"], help="操作系统类型过滤: Linux/Windows/Other")
parser.add_argument("--architecture", type=str, choices=["x86", "arm"], help="镜像架构过滤: x86/arm")
parser.add_argument("--status", type=str, choices=["queued", "saving", "deleted", "killed", "active"], help="镜像状态过滤: queued/saving/deleted/killed/active")
parser.add_argument("--id", type=str, help="镜像 ID 过滤")
parser.add_argument("--name", type=str, help="镜像名称过滤")
parser.add_argument("--platform", type=str, help="镜像平台分类过滤，如 Ubuntu/CentOS/Windows")
parser.add_argument("--virtual_env_type", type=str, choices=["FusionCompute", "Ironic", "DataImage"], help="使用环境类型过滤: FusionCompute/Ironic/DataImage")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID过滤，0表示default企业项目，UUID表示指定企业项目，all_granted_eps表示所有企业项目，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--min_disk", type=int, help="镜像运行需要的最小磁盘，单位为GB")
parser.add_argument("--member_status", type=str, choices=["accepted", "rejected", "pending"], help="成员状态: accepted(已接受)/rejected(已拒绝)/pending(待定)")
parser.add_argument("--created_at", type=str, help="镜像创建时间过滤，格式: 操作符:UTC时间，操作符支持gt/gte/lt/lte/eq/neq，如 'gte:2023-01-01T00:00:00Z'")
parser.add_argument("--updated_at", type=str, help="镜像修改时间过滤，格式同created_at")
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
        print(f"没有找到镜像标签 (区域: {Region})")
        return

    output = f"tag\n"
    for t in tags:
        output += f"{t}\n"

    # 汇总信息
    showing_count = len(tags)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --imagetype / --os_type 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --imagetype / --os_type 等参数缩小查询范围"
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

    # 构建请求，设置过滤参数
    request = ListTagsRequest()
    request.limit = FETCH_SIZE
    # API 使用 page 页码分页，marker 值为页码数值
    page = 1
    if args.marker:
        try:
            page = int(args.marker)
        except ValueError:
            print(f"marker 格式错误，应为数字: {args.marker}")
            exit(1)
    request.page = page
    if args.imagetype:
        request.imagetype = args.imagetype
    if args.os_type:
        request.os_type = args.os_type
    if args.architecture:
        request.architecture = args.architecture
    if args.status:
        request.status = args.status
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.platform:
        request.platform = args.platform
    if args.virtual_env_type:
        request.virtual_env_type = args.virtual_env_type
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.min_disk is not None:
        request.min_disk = args.min_disk
    if args.member_status:
        request.member_status = args.member_status
    if args.created_at:
        request.created_at = args.created_at
    if args.updated_at:
        request.updated_at = args.updated_at

    # 只做一次查询
    response = client.list_tags(request)
    tags = response.tags

    if not tags:
        render([])
        exit(0)

    # Response 无分页信息（无 page_info / count / total_count），通过多查的第 FETCH_SIZE 条判断
    next_marker = None
    has_more = len(tags) > PAGE_SIZE
    if has_more:
        next_marker = str(page + 1)

    # 只展示前 PAGE_SIZE 条
    display_tags = tags[:PAGE_SIZE]

    # 渲染结果
    render(display_tags, has_more=has_more, next_marker=next_marker)

except Exception as e:
    print(f"ims.list_tags 查询失败: {e}")
    exit(1)
