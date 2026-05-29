import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListQuotaDetailsRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 配额详情列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--quota_key", type=str, nargs="+", help="配额类型，支持多值查询，如 loadbalancer/listener/pool/member/healthmonitor/l7policy/certificate/security_policy 等")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: quota_limit, used；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by used:desc --top 5 查找已用量最多的 5 个配额")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by used:desc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('quota_limit', 'used') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: quota_limit, used；方向可选: asc, desc。例如 used:desc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数
has_custom_filter = args.sort_by is not None

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListQuotaDetailsRequest()
    if args.quota_key:
        request.quota_key = args.quota_key
    response = client.list_quota_details(request)
    items = response.quotas
    if not items:
        print(f"没有找到配额详情 (区域: {Region})")
        exit(0)

    # 客户端排序（API 一次返回全部数据，直接在全量数据上排序）
    if args.sort_by:
        sort_field, sort_dir = args.sort_by.split(':')
        if sort_field == 'quota_limit':
            items.sort(key=lambda f: int(getattr(f, 'quota_limit', 0) or 0), reverse=(sort_dir == 'desc'))
        elif sort_field == 'used':
            items.sort(key=lambda f: int(getattr(f, 'used', 0) or 0), reverse=(sort_dir == 'desc'))

    # top 截取
    if args.top is not None:
        items = items[:args.top]

    # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
    start_idx = 0
    if args.marker:
        for i, item in enumerate(items):
            if str(getattr(item, 'quota_key', '')) == args.marker:
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
        next_marker = str(getattr(remaining_items[PAGE_SIZE - 1], 'quota_key', ''))
    display_items = remaining_items[:PAGE_SIZE]

    output = f"quota_key\tquota_limit\tused\tunit\n"
    for item in display_items:
        quota_key = getattr(item, 'quota_key', '')
        quota_limit = getattr(item, 'quota_limit', '')
        used = getattr(item, 'used', '')
        unit = getattr(item, 'unit', '')
        output += f"{quota_key}\t{quota_limit}\t{used}\t{unit}\n"

    if has_more:
        output += f"\n当前返回 {len(display_items)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_items)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_quota_details 查询失败: {e}")
    exit(1)
