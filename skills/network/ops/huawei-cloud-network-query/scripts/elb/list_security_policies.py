import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListSecurityPoliciesRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 安全策略列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="安全策略ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="安全策略名称，支持多值查询")
parser.add_argument("--description", type=str, nargs="+", help="安全策略描述，支持多值查询")
parser.add_argument("--protocols", type=str, nargs="+", help="TLS协议版本，支持多值查询")
parser.add_argument("--ciphers", type=str, nargs="+", help="加密套件，支持多值查询")
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

    request = ListSecurityPoliciesRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.description:
        request.description = args.description
    if args.protocols:
        request.protocols = args.protocols
    if args.ciphers:
        request.ciphers = args.ciphers

    response = client.list_security_policies(request)
    security_policies = response.security_policies

    if not security_policies:
        print(f"没有找到安全策略 (区域: {Region})")
        exit(0)

    # Response 有 page_info，使用 page_info.next_marker 判断分页
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(security_policies) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(security_policies[PAGE_SIZE - 1], 'id', ''))

    display_policies = security_policies[:PAGE_SIZE]

    output = f"id\tname\tdescription\tprotocols\tciphers\n"
    for item in display_policies:
        id = getattr(item, 'id', '')
        name = getattr(item, 'name', '')
        description = getattr(item, 'description', '')
        protocols = getattr(item, 'protocols', [])
        protocols_str = ','.join(protocols) if protocols else ''
        ciphers = getattr(item, 'ciphers', [])
        ciphers_str = ','.join(ciphers) if ciphers else ''
        output += f"{id}\t{name}\t{description}\t{protocols_str}\t{ciphers_str}\n"

    if has_more:
        output += f"\n当前返回 {len(display_policies)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_policies)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_security_policies 查询失败: {e}")
    exit(1)
