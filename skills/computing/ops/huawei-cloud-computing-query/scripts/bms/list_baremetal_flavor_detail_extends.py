import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkbms.v1 import BmsClient
from huaweicloudsdkbms.v1.model import ListBaremetalFlavorDetailExtendsRequest
from huaweicloudsdkbms.v1.region.bms_region import BmsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询裸金属服务器规格详情列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--availability_zone", type=str, help="可用区名称，可通过 show_available_resource.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: vcpus, ram, disk, size；方向可选: asc(升序), desc(降序)。size 为综合规格大小(vCPU×内存GiB)，适合查找整体最小或最大的规格。例如 size:asc 表示按综合规格升序，vcpus:desc 表示按 vCPU 降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by size:asc --top 5 查找综合规格最小的 5 个规格")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by vcpus:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('vcpus', 'ram', 'disk', 'size') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: vcpus, ram, disk, size；方向可选: asc, desc。例如 size:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(flavors, total_count=None, has_more=False, next_marker=None):
    if not flavors:
        print("没有找到裸金属服务器规格")
        return

    output = f"id\tname\tvcpus\tram(MiB)\tdisk(GB)\tresource_type\tcpu_arch\tdisk_detail\n"
    for flavor in flavors:
        fid = getattr(flavor, 'id', '')
        name = getattr(flavor, 'name', '')
        vcpus = getattr(flavor, 'vcpus', '')
        ram = getattr(flavor, 'ram', '')
        disk = getattr(flavor, 'disk', '')
        os_extra_specs = getattr(flavor, 'os_extra_specs', None)
        resource_type = getattr(os_extra_specs, 'resource_type', '') if os_extra_specs else ''
        cpu_arch = getattr(os_extra_specs, 'capabilitiescpu_arch', '') if os_extra_specs else ''
        disk_detail = getattr(os_extra_specs, 'baremetaldisk_detail', '') if os_extra_specs else ''
        output += f"{fid}\t{name}\t{vcpus}\t{ram}\t{disk}\t{resource_type}\t{cpu_arch}\t{disk_detail}\n"

    # 汇总信息
    showing_count = len(flavors)

    if total_count is not None:
        output += f"\n共 {total_count} 条规格，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --availability_zone 参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --availability_zone 参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --availability_zone 参数缩小查询范围"
        else:
            output += f"\n可使用 --availability_zone 参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条规格"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = BmsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)
    ).with_region(BmsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 BMS 客户端")
        exit(-1)

    # 构建请求（此API不支持分页，一次返回所有数据）
    request = ListBaremetalFlavorDetailExtendsRequest()
    if args.availability_zone:
        request.availability_zone = args.availability_zone

    response = client.list_baremetal_flavor_detail_extends(request)
    flavors = response.flavors

    if not flavors:
        print(f"没有找到裸金属服务器规格 (区域: {Region})")
        exit(0)

    if args.sort_by:
        # 有排序参数：在全量数据上排序 + top 截取，不走本地 marker 翻页
        # 客户端排序
        sort_field, sort_dir = args.sort_by.split(':')
        if sort_field == 'vcpus':
            flavors.sort(key=lambda f: int(getattr(f, 'vcpus', 0) or 0), reverse=(sort_dir == 'desc'))
        elif sort_field == 'ram':
            flavors.sort(key=lambda f: int(getattr(f, 'ram', 0) or 0), reverse=(sort_dir == 'desc'))
        elif sort_field == 'disk':
            flavors.sort(key=lambda f: int(getattr(f, 'disk', 0) or 0), reverse=(sort_dir == 'desc'))
        elif sort_field == 'size':
            flavors.sort(key=lambda f: int(getattr(f, 'vcpus', 0) or 0) * (int(getattr(f, 'ram', 0) or 0) // 1024), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            flavors = flavors[:args.top]

        # 渲染结果
        render(flavors, total_count=len(flavors))
    else:
        # 无排序参数：本地 marker 翻页
        # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
        start_idx = 0
        if args.marker:
            for i, item in enumerate(flavors):
                if str(getattr(item, 'id', '')) == args.marker:
                    start_idx = i + 1
                    break

        remaining_flavors = flavors[start_idx:]
        if not remaining_flavors:
            print("没有更多数据")
            exit(0)

        has_more = len(remaining_flavors) > PAGE_SIZE
        next_marker = None
        if has_more:
            next_marker = str(getattr(remaining_flavors[PAGE_SIZE - 1], 'id', ''))
        display_flavors = remaining_flavors[:PAGE_SIZE]

        # 渲染结果
        render(display_flavors, total_count=len(flavors), has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"bms.list_baremetal_flavor_detail_extends 查询失败: {e}")
    exit(1)
