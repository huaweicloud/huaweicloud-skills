import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import ShowGroupSummaryRequest
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 IAM 用户组摘要 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--offset", type=int, help="客户端分页偏移量，从 0 开始，用于控制显示范围")
parser.add_argument("--limit", type=int, help="每页请求条目数，范围 1~200，默认 100")
parser.add_argument("--user_id", type=str, help="用户 ID，可通过 list_users_v5.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region
if args.offset is not None:
    Offset = args.offset
if Offset < 0:
    Offset = 0


def render(all_items):
    total = len(all_items)
    if Offset >= total:
        print(f"查询结果为空\n\nIAM 用户组摘要列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)
    output = f"group_id\tgroup_name\tdescription\tuser_count\n"
    for i in range(Offset, min(total, Offset + 50)):
        item = all_items[i]
        group_id = getattr(item, 'group_id', '')
        group_name = getattr(item, 'group_name', '')
        description = getattr(item, 'description', '')
        user_count = getattr(item, 'user_count', '')
        output += f"{group_id}\t{group_name}\t{description}\t{user_count}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\nIAM 用户组摘要列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
        if end + 1 < total:
            output += f"可以使用 --offset={end + 1} 参数继续获取后续数据"
    print(output)


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    all_items = []
    marker = ""
    while True:
        request = ShowGroupSummaryRequest()
        if marker:
            request.marker = marker
        if args.limit is not None:
            request.limit = args.limit
        if args.user_id:
            request.user_id = args.user_id
        response = client.show_group_summary(request)
        items = response.groups
        if not items:
            break
        all_items.extend(items)
        page_info = getattr(response, 'page_info', None)
        next_marker = getattr(page_info, 'next_marker', '') if page_info else ''
        if not next_marker:
            break
        marker = next_marker

    if not all_items:
        print(f"没有找到 IAM 用户组摘要 (区域: {Region})")
        exit(0)
    render(all_items)
except Exception as e:
    print(f"iam.show_group_summary 查询失败: {e}")
    exit(1)
