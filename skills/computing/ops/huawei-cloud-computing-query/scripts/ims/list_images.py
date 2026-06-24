import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import ListImagesRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 IMS 镜像列表")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--imagetype", type=str, choices=["gold", "private", "shared", "market"], help="镜像类型: gold(公共镜像), private(私有镜像), shared(共享镜像), market(市场镜像)")
parser.add_argument("--os_type", type=str, choices=["Linux", "Windows", "Other"], help="操作系统类型: Linux/Windows/Other")
parser.add_argument("--os_bit", type=str, choices=["32", "64"], help="操作系统位数: 32 或 64")
parser.add_argument("--architecture", type=str, choices=["x86", "arm"], help="镜像架构类型: x86 或 arm")
parser.add_argument("--status", type=str, choices=["queued", "saving", "deleted", "killed", "active"], help="镜像状态: queued(排队中)/saving(保存中)/deleted(已删除)/killed(错误)/active(可用)")
parser.add_argument("--visibility", type=str, choices=["public", "private", "shared"], help="镜像可见性: public(公共)/private(私有)/shared(共享)")
parser.add_argument("--id", type=str, help="镜像 ID，精确查询指定镜像")
parser.add_argument("--name", type=str, help="镜像名称(精确匹配，需输入完整名称，如 'Ubuntu 22.04 server 64bit')")
parser.add_argument("--name_contains", type=str, help="镜像名称模糊搜索(客户端过滤，如 'Ubuntu' 可匹配所有名称包含Ubuntu的镜像)")
parser.add_argument("--disk_format", type=str, choices=["vhd", "zvhd", "raw", "qcow2", "zvhd2"], help="镜像格式: vhd/zvhd/raw/qcow2/zvhd2")
parser.add_argument("--tag", type=str, help="标签，用户为镜像增加自定义标签后可以通过该参数过滤查询")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID，0表示default企业项目，UUID表示指定企业项目，all_granted_eps表示所有企业项目，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--platform", type=str, help="镜像平台分类，如 Ubuntu/CentOS/Windows 等")
parser.add_argument("--virtual_env_type", type=str, choices=["FusionCompute", "Ironic", "DataImage"], help="使用环境类型: FusionCompute(云服务器)/Ironic(裸金属)/DataImage(数据盘)")
parser.add_argument("--flavor_id", type=str, help="云服务器规格ID，用于过滤出可用公共镜像")
parser.add_argument("--member_status", type=str, choices=["accepted", "rejected", "pending"], help="成员状态，需配合--visibility=shared使用: accepted(已接受)/rejected(已拒绝)/pending(待定)")
parser.add_argument("--created_at", type=str, help="镜像创建时间过滤，格式: 操作符:UTC时间，操作符支持gt/gte/lt/lte/eq/neq，如 'gte:2023-01-01T00:00:00Z'")
parser.add_argument("--updated_at", type=str, help="镜像修改时间过滤，格式同created_at")
parser.add_argument("--sort_key", type=str, help="排序字段，取值为镜像属性name/container_format/disk_format/status/id/size，默认为创建时间")
parser.add_argument("--sort_dir", type=str, choices=["asc", "desc"], help="排序方向: asc(升序)/desc(降序)，默认 desc")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: min_disk, min_ram, size；方向可选: asc(升序), desc(降序)。size 为综合资源需求大小(min_disk×min_ram_GiB)，适合查找整体资源需求最小或最大的镜像。例如 size:asc 表示按综合资源需求升序，min_disk:asc 表示按最小磁盘升序，min_ram:desc 表示按最小内存降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by size:asc --top 5 查找综合资源需求最小的 5 个镜像，--sort_by min_disk:desc --top 3 查找最小磁盘要求最大的 3 个镜像")
args = parser.parse_args()

Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by min_disk:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('min_disk', 'min_ram', 'size') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: min_disk, min_ram, size；方向可选: asc, desc。例如 size:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(images, total_count=None, has_more=False, next_marker=None):
    """
    渲染镜像列表
    :param images: 镜像列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not images:
        msg = f"没有找到 IMS 镜像（区域：{Region}）"
        if args.name:
            msg += (f"\n提示：--name 为精确匹配（名称='{args.name}'），"
                    f"需输入完整的镜像名称。如不确定完整名称，"
                    f"请改用 --name_contains 进行模糊搜索。")
        elif args.platform:
            msg += (f"\n提示：使用了 --platform='{args.platform}'过滤，"
                    f"可尝试不加 --platform 查看该区域下所有镜像。")
        elif args.imagetype or args.os_type or args.status or args.visibility:
            msg += f"\n提示：当前使用了过滤条件，可尝试去掉部分过滤参数扩大搜索范围。"
        else:
            msg += f"\n提示：可尝试添加 --imagetype=gold 查询公共镜像。"
        print(msg)
        return

    output = f"id\tname\tos_type\tos_version\tos_bit\tstatus\timagetype\tvisibility\tdisk_format\tmin_disk\tenterprise_project_id\tcreated_at\tupdated_at\ttags\n"
    for img in images:
        img_id = getattr(img, 'id', '')
        name = getattr(img, 'name', '')
        os_type = getattr(img, 'os_type', '')
        os_version = getattr(img, 'os_version', '')
        os_bit = getattr(img, 'os_bit', '')
        status = getattr(img, 'status', '')
        imagetype = getattr(img, 'imagetype', '')
        visibility = getattr(img, 'visibility', '')
        disk_format = getattr(img, 'disk_format', '')
        min_disk = getattr(img, 'min_disk', '')
        enterprise_project_id = getattr(img, 'enterprise_project_id', '')
        created_at = getattr(img, 'created_at', '')
        updated_at = getattr(img, 'updated_at', '')
        tags = getattr(img, 'tags', [])
        tag_str = ';'.join(tags) if tags else ''
        output += f"{img_id}\t{name}\t{os_type}\t{os_version}\t{os_bit}\t{status}\t{imagetype}\t{visibility}\t{disk_format}\t{min_disk}\t{enterprise_project_id}\t{created_at}\t{updated_at}\t{tag_str}\n"

    # 汇总信息
    showing_count = len(images)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --imagetype / --os_type / --name 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --imagetype / --os_type / --name 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    # 未指定 project_id 则自动获取
    if not args.project_id:
        args.project_id = get_project_id(Region, AK, SK, SecurityToken)
        if not args.project_id:
            print(f"无法获取项目 ID (region={Region})，请检查凭据或手动指定 --project_id")
            exit(-1)

    client = ImsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ImsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 IMS 客户端")
        exit(-1)

    # --name_contains 是自定义过滤参数（SDK 不支持），需要全量拉取+本地过滤
    has_custom_filter = args.name_contains is not None or args.sort_by is not None

    # 构建请求，设置过滤参数
    request = ListImagesRequest()
    if args.imagetype:
        request.imagetype = args.imagetype
    if args.os_type:
        request.os_type = args.os_type
    if args.os_bit:
        request.os_bit = args.os_bit
    if args.architecture:
        request.architecture = args.architecture
    if args.status:
        request.status = args.status
    if args.visibility:
        request.visibility = args.visibility
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.disk_format:
        request.disk_format = args.disk_format
    if args.tag:
        request.tag = args.tag
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.platform:
        request.platform = args.platform
    if args.virtual_env_type:
        request.virtual_env_type = args.virtual_env_type
    if args.flavor_id:
        request.flavor_id = args.flavor_id
    if args.member_status:
        request.member_status = args.member_status
    if args.created_at:
        request.created_at = args.created_at
    if args.updated_at:
        request.updated_at = args.updated_at
    if args.sort_key:
        request.sort_key = args.sort_key
    if args.sort_dir:
        request.sort_dir = args.sort_dir

    if has_custom_filter:
        # 全量拉取 + 本地过滤（因为SDK单次最多返回有限条数，必须循环拉完）
        all_images = []
        marker = ""

        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_images(request)
            images = response.images
            if not images:
                break
            # 检测重复数据：如果本页第一条的 id 跟上一页最后一条相同，说明 marker 没生效，退出
            if marker and all_images and getattr(images[0], 'id', None) == getattr(all_images[-1], 'id', None):
                break
            all_images.extend(images)
            if len(images) < API_LIMIT:
                break
            marker = images[-1].id
            if not marker:
                break

        # 本地过滤
        if args.name_contains:
            filtered_images = [img for img in all_images if args.name_contains in (getattr(img, 'name', '') or '')]
        else:
            filtered_images = all_images

        if not filtered_images:
            if args.name_contains:
                msg = f"没有找到名称包含 '{args.name_contains}' 的镜像"
                if len(args.name_contains) >= 4:
                    msg += (f"\n提示：关键词较长，可尝试改用更短的词汇重新搜索，"
                            f"如 'CentOS'、'Ubuntu'、'Windows' 等。")
                print(msg)
            else:
                print(f"没有找到 IMS 镜像（区域：{Region}）")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'min_disk':
                filtered_images.sort(key=lambda f: int(getattr(f, 'min_disk', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'min_ram':
                filtered_images.sort(key=lambda f: int(getattr(f, 'min_ram', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'size':
                filtered_images.sort(key=lambda f: int(getattr(f, 'min_disk', 0) or 0) * (int(getattr(f, 'min_ram', 0) or 0) / 1024), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            filtered_images = filtered_images[:args.top]

        # 渲染过滤结果（全量已拉取，无需翻页）
        render(filtered_images, total_count=len(filtered_images))
    else:
        # 正常逻辑：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_images(request)
        images = response.images

        if not images:
            render([])
            exit(0)

        # Response 无分页信息（无 page_info / count / total_count），通过多查的第 FETCH_SIZE 条判断
        next_marker = None
        has_more = len(images) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(images[PAGE_SIZE - 1], 'id', ''))

        # 只展示前 PAGE_SIZE 条
        display_images = images[:PAGE_SIZE]

        # 渲染结果
        render(display_images, has_more=has_more, next_marker=next_marker)

except Exception as e:
    print(f"ims.list_images 查询失败: {e}")
    exit(1)
