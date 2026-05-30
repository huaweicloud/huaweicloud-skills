import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkeps.v1 import EpsClient
from huaweicloudsdkeps.v1.model import ListProvidersRequest
from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询企业项目支持的云服务提供商列表")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--locale", type=str, help="指定显示语言，如 zh-cn/en-us")
parser.add_argument("--provider", type=str, help="云服务名称，用于精确过滤")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(providers, total_count=None, has_more=False, next_marker=None):
    """
    渲染云服务提供商列表
    :param providers: 提供商列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not providers:
        print("没有找到云服务提供商")
        return

    output = f"provider\tdisplay_name\tresource_types\n"
    for p in providers:
        provider = getattr(p, 'provider', '')
        display_name = getattr(p, 'provider_i18n_display_name', '')
        resource_types = getattr(p, 'resource_types', []) or []
        type_str = ';'.join([getattr(rt, 'type', '') for rt in resource_types])
        output += f"{provider}\t{display_name}\t{type_str}\n"

    # 汇总信息
    showing_count = len(providers)

    if total_count is not None:
        output += f"\n共 {total_count} 个云服务提供商，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --provider 参数精确过滤"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --provider 参数精确过滤"
    else:
        output += f"\n共 {showing_count} 个云服务提供商"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EpsClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(EpsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EPS 客户端")
        exit(-1)

    # API 使用 offset/limit 分页（无 marker），用 --marker 传递 offset 值实现翻页
    request = ListProvidersRequest()
    request.limit = FETCH_SIZE
    # marker 的值就是 offset（已跳过的条数）
    request.offset = int(args.marker) if args.marker else 0
    if args.locale:
        request.locale = args.locale
    if args.provider:
        request.provider = args.provider

    # 只做一次查询
    response = client.list_providers(request)
    total_count = getattr(response, 'total_count', None)
    providers = response.providers

    if not providers:
        print(f"没有找到云服务提供商 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    if total_count is not None:
        has_more = total_count > (request.offset + PAGE_SIZE)
    else:
        # 无 total_count 时，通过多查的第 FETCH_SIZE 条判断
        has_more = len(providers) > PAGE_SIZE

    if has_more and len(providers) > PAGE_SIZE:
        # 多查的1条存在，说明还有更多，next_marker 为当前 offset + PAGE_SIZE
        next_marker = str(request.offset + PAGE_SIZE)

    # 只展示前 PAGE_SIZE 条
    display_providers = providers[:PAGE_SIZE]

    # 渲染结果
    render(display_providers, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eps.list_providers 查询失败: {e}")
    exit(1)
