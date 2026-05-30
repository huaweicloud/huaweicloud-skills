import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import ListOsVersionsRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 IMS 镜像支持的 OS 版本列表，用于创建镜像或云服务器时选择操作系统")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--tag", type=str, choices=["bms", "uefi", "arm", "x86"], help="OS标签过滤: bms(支持BMS的OS列表)/uefi(支持UEFI启动的OS列表)/arm(ARM架构OS列表)/x86(x86架构OS列表)，不指定则返回所有")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(flat_versions, total_count=None, has_more=False, next_marker=None):
    """
    渲染 OS 版本列表
    :param flat_versions: 展开后的版本列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not flat_versions:
        print(f"没有找到 OS 版本列表 (区域: {Region})")
        return

    output = f"platform\tos_version_key\tos_version\tos_bit\tos_type\n"
    for item in flat_versions:
        output += f"{item['platform']}\t{item['os_version_key']}\t{item['os_version']}\t{item['os_bit']}\t{item['os_type']}\n"

    # 汇总信息
    showing_count = len(flat_versions)

    if total_count is not None:
        output += f"\n共 {total_count} 条，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --tag 参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --tag 参数缩小查询范围"
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
    request = ListOsVersionsRequest()
    if args.tag:
        request.tag = args.tag
    response = client.list_os_versions(request)

    os_versions = response.body
    if not os_versions:
        render([])
        exit(0)

    # 将嵌套结构展开为扁平列表
    flat_versions = []
    for item in os_versions:
        platform = getattr(item, 'platform', '')
        version_list = getattr(item, 'version_list', [])
        for v in version_list:
            flat_versions.append({
                'platform': getattr(v, 'platform', platform),
                'os_version_key': getattr(v, 'os_version_key', ''),
                'os_version': getattr(v, 'os_version', ''),
                'os_bit': str(getattr(v, 'os_bit', '')),
                'os_type': getattr(v, 'os_type', ''),
            })

    if not flat_versions:
        print(f"没有找到 OS 版本列表 (区域: {Region})")
        exit(0)

    # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
    start_idx = 0
    if args.marker:
        for i, item in enumerate(flat_versions):
            if item['os_version_key'] == args.marker:
                start_idx = i + 1
                break

    remaining_versions = flat_versions[start_idx:]
    if not remaining_versions:
        print("没有更多数据")
        exit(0)

    # 判断是否还有更多数据
    has_more = len(remaining_versions) > PAGE_SIZE
    next_marker = None
    if has_more:
        next_marker = remaining_versions[PAGE_SIZE - 1]['os_version_key']
    display_versions = remaining_versions[:PAGE_SIZE]

    # 渲染结果
    render(display_versions, total_count=len(flat_versions), has_more=has_more, next_marker=next_marker)

except Exception as e:
    print(f"ims.list_os_versions 查询失败: {e}")
    exit(1)
