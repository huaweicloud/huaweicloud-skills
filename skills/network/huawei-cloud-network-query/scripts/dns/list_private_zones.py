import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListPrivateZonesRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询内网域名列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--type", type=str, required=True, default="private", help="待查询域名的类型，取值: private")
parser.add_argument("--limit", type=int, required=True, default=50, help="分页查询时配置每页返回的资源个数，取值范围 0~500，默认 500")
parser.add_argument("--marker", type=str, help="分页查询的起始资源ID")
parser.add_argument("--offset", type=int, help="分页查询起始偏移量，取值范围 0~2147483647，默认 0")
parser.add_argument("--tags", type=str, help="内网域名的标签，格式 key1,value1|key2,value2")
parser.add_argument("--name", type=str, help="域名名称，默认模糊搜索")
parser.add_argument("--id", type=str, help="域名ID")
parser.add_argument("--status", type=str, help="内网域名状态: ACTIVE/PENDING_CREATE/PENDING_UPDATE/PENDING_DELETE/FREEZE/DISABLE/ERROR 等")
parser.add_argument("--search_mode", type=str, choices=["like", "equal"], help="查询条件搜索模式: like(模糊搜索)/equal(精确搜索)")
parser.add_argument("--sort_key", type=str, choices=["name", "created_at", "updated_at"], help="排序字段，默认 created_at")
parser.add_argument("--sort_dir", type=str, choices=["desc", "asc"], help="排序方式，默认 desc")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID")
parser.add_argument("--router_id", type=str, help="关联VPC的ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(zones):
    total = len(zones)
    if Offset >= total:
        print(f"查询结果为空\n\n内网域名列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    header = "zone_id\tname\tstatus\tzone_type\tttl\trecord_num\tenterprise_project_id\tcreated_at"
    output = header + "\n"
    for i in range(Offset, min(total, Offset + 50)):
        z = zones[i]
        zid = getattr(z, 'id', '')
        name = getattr(z, 'name', '')
        status = getattr(z, 'status', '')
        zone_type = getattr(z, 'zone_type', '')
        ttl = str(getattr(z, 'ttl', ''))
        record_num = str(getattr(z, 'record_num', ''))
        ep_id = getattr(z, 'enterprise_project_id', '')
        created_at = getattr(z, 'created_at', '')
        output += f"{zid}\t{name}\t{status}\t{zone_type}\t{ttl}\t{record_num}\t{ep_id}\t{created_at}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n内网域名列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
        if end + 1 < total:
            output += f"可以使用 --offset={end + 1} 参数继续获取后续数据"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    all_zones = []
    marker = ""
    limit = 500

    request = ListPrivateZonesRequest()
    request.limit = limit
    if args.type:
        request.type = args.type
    if args.tags:
        request.tags = args.tags
    if args.name:
        request.name = args.name
    if args.id:
        request.id = args.id
    if args.status:
        request.status = args.status
    if args.search_mode:
        request.search_mode = args.search_mode
    if args.sort_key:
        request.sort_key = args.sort_key
    if args.sort_dir:
        request.sort_dir = args.sort_dir
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.router_id:
        request.router_id = args.router_id

    while True:
        if marker:
            request.marker = marker
        response = client.list_private_zones(request)
        zones = getattr(response, 'zones', []) or []
        if not zones:
            break
        all_zones.extend(zones)
        links = getattr(response, 'links', None)
        next_link = getattr(links, 'next', None) if links else None
        if not next_link:
            break
        marker = zones[-1].id if zones else ""

    if not all_zones:
        print(f"没有找到内网域名 (区域: {Region})")
        exit(0)

    render(all_zones)
except Exception as e:
    print(f"dns.list_private_zones 查询失败: {e}")
    exit(1)
