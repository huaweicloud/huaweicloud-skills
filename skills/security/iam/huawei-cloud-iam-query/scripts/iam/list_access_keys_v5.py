import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import ListAccessKeysV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM AK/SK 列表 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--user_id", type=str, required=True, help="用户 ID（必填），可通过 list_users_v5.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    # 构建请求，只查1次
    request = ListAccessKeysV5Request()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.user_id:
        request.user_id = args.user_id

    # 只做一次查询
    response = client.list_access_keys_v5(request)
    items = response.access_keys
    if not items:
        print(f"没有找到 IAM AK/SK (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # 优先使用 API 返回的 page_info.next_marker
    page_info = getattr(response, 'page_info', None)
    next_marker = None
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(items) > PAGE_SIZE

    # 只展示前 PAGE_SIZE 条
    display_items = items[:PAGE_SIZE]

    output = f"user_id\taccess_key_id\tstatus\tcreated_at\n"
    for item in display_items:
        user_id = getattr(item, 'user_id', '')
        access_key_id = getattr(item, 'access_key_id', '')
        status = getattr(item, 'status', '')
        created_at = getattr(item, 'created_at', '')
        output += f"{user_id}\t{access_key_id}\t{status}\t{created_at}\n"

    # 汇总信息
    showing_count = len(display_items)
    if has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --user_id 等参数缩小查询范围"
        else:
            output += f"\n可使用 --user_id 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条"

    print(output)
except Exception as e:
    print(f"iam.list_access_keys_v5 查询失败: {e}")
    exit(1)
