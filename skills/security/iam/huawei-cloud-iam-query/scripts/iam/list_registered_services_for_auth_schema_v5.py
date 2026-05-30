import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import ListRegisteredServicesForAuthSchemaV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 认证模式注册服务列表 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(services, total_count=None, has_more=False, next_marker=None):
    """
    渲染注册服务列表
    :param services: 服务列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not services:
        print("没有找到 IAM 认证模式注册服务")
        return

    output = f"service_code\n"
    for item in services:
        output += f"{item}\n"

    # 汇总信息
    showing_count = len(services)

    if total_count is not None:
        output += f"\n共 {total_count} 条 IAM 认证模式注册服务，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 IAM 认证模式注册服务"

    print(output)


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListRegisteredServicesForAuthSchemaV5Request()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker

    # 只做一次查询
    response = client.list_registered_services_for_auth_schema_v5(request)
    services = response.service_codes or []

    if not services:
        print(f"没有找到 IAM 认证模式注册服务 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # 优先使用 API 返回的 page_info.next_marker
    page_info = getattr(response, 'page_info', None)
    next_marker = None
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(services) > PAGE_SIZE

    # 只展示前 PAGE_SIZE 条
    display_services = services[:PAGE_SIZE]

    # 渲染结果
    render(display_services, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"iam.list_registered_services_for_auth_schema_v5 查询失败: {e}")
    exit(1)
