import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListFlavorsRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 规格列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="规格ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="规格名称，支持多值查询")
parser.add_argument("--type", type=str, nargs="+", help="规格类型，L4网络型/L7应用型，支持多值查询")
parser.add_argument("--shared", type=bool, help="是否共享型规格，true共享型，false独享型")
parser.add_argument("--public_border_group", type=str, nargs="+", help="公网边界组，支持多值查询")
parser.add_argument("--category", type=int, nargs="+", help="可用区子类型编码，0中心/21homezone/41IES，支持多值查询")
parser.add_argument("--list_all", type=bool, help="是否查询所有规格，true查询所有，false不查询所有")
parser.add_argument("--flavor_sold_out", type=bool, help="规格是否售罄，true售罄，false未售罄")
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

    request = ListFlavorsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.type:
        request.type = args.type
    if args.shared is not None:
        request.shared = args.shared
    if args.public_border_group:
        request.public_border_group = args.public_border_group
    if args.category:
        request.category = args.category
    if args.list_all is not None:
        request.list_all = args.list_all
    if args.flavor_sold_out is not None:
        request.flavor_sold_out = args.flavor_sold_out

    response = client.list_flavors(request)
    flavors = response.flavors

    if not flavors:
        print(f"没有找到规格 (区域: {Region})")
        exit(0)

    # Response 有 page_info，使用 page_info.next_marker 判断分页
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(flavors) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(flavors[PAGE_SIZE - 1], 'id', ''))

    display_flavors = flavors[:PAGE_SIZE]

    output = f"id\tname\ttype\tshared\tflavor_sold_out\tpublic_border_group\tcategory\n"
    for item in display_flavors:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        type = getattr(item, 'type', '')
        shared = getattr(item, 'shared', '')
        flavor_sold_out = getattr(item, 'flavor_sold_out', '')
        public_border_group = getattr(item, 'public_border_group', '')
        category = getattr(item, 'category', '')
        output += f"{id}\t{name}\t{type}\t{shared}\t{flavor_sold_out}\t{public_border_group}\t{category}\n"

    if has_more:
        output += f"\n当前返回 {len(display_flavors)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_flavors)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_flavors 查询失败: {e}")
    exit(1)
