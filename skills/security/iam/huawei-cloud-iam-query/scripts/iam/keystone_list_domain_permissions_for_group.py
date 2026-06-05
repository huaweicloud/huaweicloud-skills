import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneListDomainPermissionsForGroupRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询用户组域权限 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_id", type=str, required=True, help="用户组所属账号 ID")
parser.add_argument("--group_id", type=str, required=True, help="用户组 ID，可通过 keystone_list_groups.py 获取")
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

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = KeystoneListDomainPermissionsForGroupRequest()
    request.domain_id = args.domain_id
    request.group_id = args.group_id
    response = client.keystone_list_domain_permissions_for_group(request)
    items = response.roles
    if not items:
        print(f"没有找到数据 (区域: {Region})")
        exit(0)

    # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
    start_idx = 0
    if args.marker:
        for i, item in enumerate(items):
            if str(getattr(item, 'id', '')) == args.marker:
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
        next_marker = str(getattr(remaining_items[PAGE_SIZE - 1], 'id', ''))
    display_items = remaining_items[:PAGE_SIZE]

    output = f"id	name	display_name	type	catalog	description	flag	domain_id\n"
    for item in display_items:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        display_name = getattr(item, 'display_name', '')
        type = getattr(item, 'type', '')
        catalog = getattr(item, 'catalog', '')
        description = getattr(item, 'description', '')
        flag = getattr(item, 'flag', '')
        domain_id = getattr(item, 'domain_id', '')
        output += f"{id}	{name}	{display_name}	{type}	{catalog}	{description}	{flag}	{domain_id}\n"

    # 汇总信息
    if has_more:
        output += f"\n当前返回 {len(display_items)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_items)} 条"

    print(output)
except Exception as e:
    print(f"iam.keystone_list_domain_permissions_for_group 查询失败: {e}")
    exit(1)
