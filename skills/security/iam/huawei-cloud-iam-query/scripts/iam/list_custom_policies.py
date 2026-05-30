import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ListCustomPoliciesRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 自定义策略列表 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(policies, total_count=None, has_more=False, next_marker=None):
    """
    渲染策略列表
    :param policies: 策略列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not policies:
        print("没有找到 IAM 自定义策略")
        return

    output = f"id\tname\tdisplay_name\ttype\tcatalog\tdescription\tdomain_id\tupdated_time\tcreated_time\n"
    for item in policies:
        id_ = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        display_name = getattr(item, 'display_name', '')
        type_ = getattr(item, 'type', '')
        catalog = getattr(item, 'catalog', '')
        description = getattr(item, 'description', '')
        domain_id = getattr(item, 'domain_id', '')
        updated_time = getattr(item, 'updated_time', '')
        created_time = getattr(item, 'created_time', '')
        output += f"{id_}\t{name}\t{display_name}\t{type_}\t{catalog}\t{description}\t{domain_id}\t{updated_time}\t{created_time}\n"

    # 汇总信息
    showing_count = len(policies)

    if total_count is not None:
        output += f"\n共 {total_count} 条 IAM 自定义策略，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 IAM 自定义策略"

    print(output)


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    # 构建请求，page/per_page 分页，marker 存储页码
    request = ListCustomPoliciesRequest()
    page = int(args.marker) if args.marker else 1
    request.page = page
    request.per_page = FETCH_SIZE

    # 只做一次查询
    response = client.list_custom_policies(request)
    total_count = getattr(response, 'total_number', None) or getattr(response, 'count', None) or getattr(response, 'total_count', None)
    policies = response.roles or []

    if not policies:
        print(f"没有找到 IAM 自定义策略 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    if total_count is not None:
        has_more = total_count > (page * PAGE_SIZE)
    else:
        # 无 count 字段时，通过多查的第 FETCH_SIZE 条判断
        has_more = len(policies) > PAGE_SIZE

    if has_more and len(policies) > PAGE_SIZE:
        # page/per_page 分页，next_marker 为下一页页码
        next_marker = str(page + 1)

    # 只展示前 PAGE_SIZE 条
    display_policies = policies[:PAGE_SIZE]

    # 渲染结果
    render(display_policies, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"iam.list_custom_policies 查询失败: {e}")
    exit(1)
