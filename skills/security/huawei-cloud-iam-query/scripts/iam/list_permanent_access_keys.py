import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ListPermanentAccessKeysRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 永久 AK/SK 列表 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--user_id", type=str, help="用户 ID")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(credentials, total_count=None, has_more=False, next_marker=None):
    """
    渲染 AK/SK 列表
    :param credentials: 凭据列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not credentials:
        print("没有找到 IAM 永久 AK/SK")
        return

    output = f"user_id\taccess\tstatus\tcreate_time\tdescription\n"
    for item in credentials:
        user_id = getattr(item, 'user_id', '')
        access = getattr(item, 'access', '')
        status = getattr(item, 'status', '')
        create_time = getattr(item, 'create_time', '')
        description = getattr(item, 'description', '')
        output += f"{user_id}\t{access}\t{status}\t{create_time}\t{description}\n"

    # 汇总信息
    showing_count = len(credentials)

    if total_count is not None:
        output += f"\n共 {total_count} 条 IAM 永久 AK/SK，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --user_id 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --user_id 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 IAM 永久 AK/SK"

    print(output)


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListPermanentAccessKeysRequest()
    if args.user_id:
        request.user_id = args.user_id
    response = client.list_permanent_access_keys(request)
    items = response.credentials or []

    if not items:
        print(f"没有找到 IAM 永久 AK/SK (区域: {Region})")
        exit(0)

    # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
    start_idx = 0
    if args.marker:
        for i, item in enumerate(items):
            if str(getattr(item, 'access', '')) == args.marker:
                start_idx = i + 1
                break

    remaining_items = items[start_idx:]
    if not remaining_items:
        print(f"没有更多数据")
        exit(0)

    # 判断是否还有更多数据
    has_more = len(remaining_items) > PAGE_SIZE
    next_marker = None
    if has_more:
        next_marker = str(getattr(remaining_items[PAGE_SIZE - 1], 'access', ''))
    display_items = remaining_items[:PAGE_SIZE]

    # 渲染结果
    render(display_items, total_count=len(items), has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"iam.list_permanent_access_keys 查询失败: {e}")
    exit(1)
