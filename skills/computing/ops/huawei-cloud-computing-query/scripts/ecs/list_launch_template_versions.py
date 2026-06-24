import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListLaunchTemplateVersionsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 100  # 服务端单次请求上限（此 API 上限为 100）

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 启动模板版本列表")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--launch_template_id", type=str, required=True, help="启动模板 ID，可通过 list_templates.py 获取")
parser.add_argument("--image_id", type=str, help="镜像 ID 过滤")
parser.add_argument("--flavor_id", type=str, help="规格 ID 过滤，可通过 list_flavors.py 获取")
parser.add_argument("--version", type=int, nargs="+", help="版本号过滤，可指定多个，如 --version 1 2 3")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: version_number；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by version_number:desc --top 3 查找最新的 3 个版本")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by version_number:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('version_number',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: version_number；方向可选: asc, desc。例如 version_number:desc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数（排序需要全量拉取）
has_custom_filter = args.sort_by is not None


# 渲染
def render(versions, total_count=None, has_more=False, next_marker=None):
    if not versions:
        print("没有找到 ECS 启动模板版本")
        return

    output = f"version_number\tversion_id\tlaunch_template_id\tversion_description\tcreated_at\n"
    for v in versions:
        version_number = getattr(v, 'version_number', '')
        version_id = getattr(v, 'version_id', '')
        launch_template_id = getattr(v, 'launch_template_id', '')
        version_description = getattr(v, 'version_description', '')
        created_at = getattr(v, 'created_at', '')
        output += f"{version_number}\t{version_id}\t{launch_template_id}\t{version_description}\t{created_at}\n"

    # 汇总信息
    showing_count = len(versions)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS 启动模板版本，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --image_id / --flavor_id / --version 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --image_id / --flavor_id / --version 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --image_id / --flavor_id / --version 等参数缩小查询范围"
        else:
            output += f"\n可使用 --image_id / --flavor_id / --version 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 ECS 启动模板版本"

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


    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListLaunchTemplateVersionsRequest()
    request.launch_template_id = args.launch_template_id
    if args.image_id:
        request.image_id = args.image_id
    if args.flavor_id:
        request.flavor_id = args.flavor_id
    if args.version is not None:
        request.version = args.version

    if has_custom_filter:
        # 有自定义过滤参数（排序）：全量拉取 + 本地排序
        all_versions = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_launch_template_versions(request)
            versions = response.launch_template_versions
            if not versions:
                break
            if marker and all_versions and getattr(versions[0], 'version_id', None) == getattr(all_versions[-1], 'version_id', None):
                break
            all_versions.extend(versions)
            if len(versions) < API_LIMIT:
                break
            page_info = getattr(response, 'page_info', None)
            marker = getattr(page_info, 'next_marker', None) if page_info else None
            if not marker:
                break

        if not all_versions:
            print("没有找到 ECS 启动模板版本")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'version_number':
                all_versions.sort(key=lambda v: int(getattr(v, 'version_number', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_versions = all_versions[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_versions, total_count=len(all_versions))
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        # 只做一次查询
        response = client.list_launch_template_versions(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        versions = response.launch_template_versions

        if not versions:
            print(f"没有找到 ECS 启动模板版本 (区域: {Region}, 模板 ID: {args.launch_template_id})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        # 此 API 的 marker 来自 response.page_info.next_marker
        page_info = getattr(response, 'page_info', None)
        next_marker = None
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        elif total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            # 无 count/total_count 字段时，通过多查的第 FETCH_SIZE 条判断
            has_more = len(versions) > PAGE_SIZE

        if has_more and not next_marker and len(versions) > PAGE_SIZE:
            next_marker = str(versions[PAGE_SIZE - 1].id)

        # 只展示前 PAGE_SIZE 条
        display_versions = versions[:PAGE_SIZE]

        # 渲染结果
        render(display_versions, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"ecs.launch_template_versions 查询失败: {e}")
    exit(1)
