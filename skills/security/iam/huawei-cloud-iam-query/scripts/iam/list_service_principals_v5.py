import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import ListServicePrincipalsV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 服务主体列表 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, choices=["zh-cn", "en-us"], help="语言，zh-cn 或 en-us")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(principals, total_count=None, has_more=False, next_marker=None):
    """
    渲染服务主体列表
    :param principals: 服务主体列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not principals:
        print("没有找到 IAM 服务主体")
        return

    output = f"service_principal\tdisplay_name\tdescription\n"
    for item in principals:
        service_principal = getattr(item, 'service_principal', '')
        display_name = getattr(item, 'display_name', '')
        description = getattr(item, 'description', '')
        output += f"{service_principal}\t{display_name}\t{description}\n"

    # 汇总信息
    showing_count = len(principals)

    if total_count is not None:
        output += f"\n共 {total_count} 条 IAM 服务主体，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 IAM 服务主体"

    print(output)


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListServicePrincipalsV5Request()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.x_language:
        request.x_language = args.x_language

    # 只做一次查询
    response = client.list_service_principals_v5(request)
    principals = response.service_principals or []

    if not principals:
        print(f"没有找到 IAM 服务主体 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # 优先使用 API 返回的 page_info.next_marker
    page_info = getattr(response, 'page_info', None)
    next_marker = None
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(principals) > PAGE_SIZE

    # 只展示前 PAGE_SIZE 条
    display_principals = principals[:PAGE_SIZE]

    # 渲染结果
    render(display_principals, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"iam.list_service_principals_v5 查询失败: {e}")
    exit(1)
