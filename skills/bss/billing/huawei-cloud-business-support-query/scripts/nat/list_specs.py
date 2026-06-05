import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdknat.v2 import NatClient
from huaweicloudsdknat.v2.model import ListSpecsRequest
from huaweicloudsdknat.v2.region.nat_region import NatRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询私网NAT网关规格列表(Small=小型 Medium=中型 Large=大型 Extra-large=超大型 Extra-xlarge=企业型)")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: rule_max, sess_max, bps_max, pps_max, qps_max；方向可选: asc(升序), desc(降序)。例如 rule_max:asc 表示按规则最大数升序，bps_max:desc 表示按带宽最大值降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by rule_max:asc --top 5 查找规则数最小的 5 个规格")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by rule_max:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('rule_max', 'sess_max', 'bps_max', 'pps_max', 'qps_max') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: rule_max, sess_max, bps_max, pps_max, qps_max；方向可选: asc, desc。例如 rule_max:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(specs, total_count=None, has_more=False, next_marker=None):
    """
    渲染规格列表
    :param specs: 规格列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not specs:
        print("没有找到私网 NAT 网关规格")
        return

    output = f"name\tcode\trule_max\tsess_max\tbps_max\tpps_max\tqps_max\n"
    for spec in specs:
        name = getattr(spec, 'name', '')
        code = getattr(spec, 'code', '')
        rule_max = getattr(spec, 'rule_max', '')
        sess_max = getattr(spec, 'sess_max', '')
        bps_max = getattr(spec, 'bps_max', '')
        pps_max = getattr(spec, 'pps_max', '')
        qps_max = getattr(spec, 'qps_max', '')
        output += f"{name}\t{code}\t{rule_max}\t{sess_max}\t{bps_max}\t{pps_max}\t{qps_max}\n"

    # 汇总信息
    showing_count = len(specs)

    if total_count is not None:
        output += f"\n共 {total_count} 个规格，当前返回 {showing_count} 个"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    elif has_more:
        output += f"\n当前返回 {showing_count} 个，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    else:
        output += f"\n共 {showing_count} 个规格"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = NatClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(NatRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 NAT 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListSpecsRequest()
    response = client.list_specs(request)
    specs = response.specs

    if not specs:
        print(f"没有找到私网 NAT 网关规格 (区域: {Region})")
        exit(0)

    # 客户端排序
    if args.sort_by:
        sort_field, sort_dir = args.sort_by.split(':')
        if sort_field == 'rule_max':
            specs.sort(key=lambda f: int(getattr(f, 'rule_max', 0) or 0), reverse=(sort_dir == 'desc'))
        elif sort_field == 'sess_max':
            specs.sort(key=lambda f: int(getattr(f, 'sess_max', 0) or 0), reverse=(sort_dir == 'desc'))
        elif sort_field == 'bps_max':
            specs.sort(key=lambda f: int(getattr(f, 'bps_max', 0) or 0), reverse=(sort_dir == 'desc'))
        elif sort_field == 'pps_max':
            specs.sort(key=lambda f: int(getattr(f, 'pps_max', 0) or 0), reverse=(sort_dir == 'desc'))
        elif sort_field == 'qps_max':
            specs.sort(key=lambda f: int(getattr(f, 'qps_max', 0) or 0), reverse=(sort_dir == 'desc'))

    # top 截取
    if args.top is not None:
        specs = specs[:args.top]
        render(specs, total_count=len(specs))
    else:
        # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
        start_idx = 0
        if args.marker:
            for i, spec in enumerate(specs):
                if str(getattr(spec, 'code', '')) == args.marker:
                    start_idx = i + 1
                    break

        remaining_specs = specs[start_idx:]
        if not remaining_specs:
            print("没有更多数据")
            exit(0)

        # 判断是否还有更多数据
        has_more = len(remaining_specs) > PAGE_SIZE
        next_marker = None
        if has_more:
            next_marker = str(getattr(remaining_specs[PAGE_SIZE - 1], 'code', ''))
        display_specs = remaining_specs[:PAGE_SIZE]

        # 渲染结果
        render(display_specs, total_count=len(specs), has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"nat.list_specs 查询失败: {e}")
    exit(1)
