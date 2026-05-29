import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListAvailabilityZonesRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 可用区列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--public_border_group", type=str, help="公网边界组，center表示中心站点，边缘站点名称表示边缘站点")
parser.add_argument("--loadbalancer_id", type=str, help="负载均衡器ID，查询该LB可用的可用区")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    # API 不支持分页（无 marker/limit/offset），一次返回所有数据，本地 marker 翻页
    request = ListAvailabilityZonesRequest()
    if args.public_border_group is not None:
        request.public_border_group = args.public_border_group
    if args.loadbalancer_id is not None:
        request.loadbalancer_id = args.loadbalancer_id

    response = client.list_availability_zones(request)
    az_list = response.availability_zones
    if not az_list:
        print(f"没有找到可用区 (区域: {Region})")
        exit(0)

    # response.availability_zones 是 list[list[AvailabilityZone]]，需要展平
    all_items = []
    for az_group in az_list:
        if az_group:
            all_items.extend(az_group)

    if not all_items:
        print(f"没有找到可用区 (区域: {Region})")
        exit(0)

    # 本地 marker 翻页：找到 marker 对应的位置，从该位置之后开始展示
    start_idx = 0
    if args.marker:
        for i, item in enumerate(all_items):
            if str(getattr(item, 'code', '')) == args.marker:
                start_idx = i + 1
                break

    remaining_items = all_items[start_idx:]
    if not remaining_items:
        print(f"没有更多数据")
        exit(0)

    # 判断是否还有更多数据
    has_more = len(remaining_items) > PAGE_SIZE
    next_marker = None
    if has_more:
        next_marker = str(getattr(remaining_items[PAGE_SIZE - 1], 'code', ''))
    display_items = remaining_items[:PAGE_SIZE]

    output = f"code\tstate\tprotocol\tpublic_border_group\tcategory\tspec_code\n"
    for item in display_items:
        code = getattr(item, 'code', '')
        state = getattr(item, 'state', '')
        protocol = getattr(item, 'protocol', [])
        protocol_str = ','.join(protocol) if protocol else ''
        public_border_group = getattr(item, 'public_border_group', '')
        category = getattr(item, 'category', '')
        spec_code = getattr(item, 'spec_code', '')
        output += f"{code}\t{state}\t{protocol_str}\t{public_border_group}\t{category}\t{spec_code}\n"

    if has_more:
        output += f"\n当前返回 {len(display_items)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_items)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_availability_zones 查询失败: {e}")
    exit(1)
