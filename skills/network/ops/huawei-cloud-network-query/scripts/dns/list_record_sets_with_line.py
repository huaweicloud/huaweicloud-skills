import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListRecordSetsWithLineRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询租户记录集列表（支持线路）")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--zone_type", type=str, choices=["public", "private"], help="域名类型: public/private")
parser.add_argument("--marker", type=str, help="分页查询的起始资源ID")
parser.add_argument("--limit", type=int, help="分页查询时配置每页返回的资源个数，取值范围 0~500，默认 500")
parser.add_argument("--offset", type=int, help="分页查询起始偏移量，取值范围 0~2147483647，默认 0")
parser.add_argument("--zone_id", type=str, help="域名ID")
parser.add_argument("--line_id", type=str, help="线路ID")
parser.add_argument("--tags", type=str, help="资源标签，格式 key1,value1|key2,value2")
parser.add_argument("--status", type=str, help="记录集状态: ACTIVE/ERROR/FREEZE/DISABLE")
parser.add_argument("--type", type=str, help="记录集类型，如 A/AAAA/MX/CNAME/TXT/NS/SRV/CAA/PTR 等")
parser.add_argument("--name", type=str, help="记录集名称")
parser.add_argument("--id", type=str, help="记录集ID")
parser.add_argument("--records", type=str, help="记录集的值")
parser.add_argument("--sort_key", type=str, choices=["name", "type", "created_at", "updated_at"], help="排序字段，默认 created_at")
parser.add_argument("--sort_dir", type=str, choices=["desc", "asc"], help="排序方式，默认 desc")
parser.add_argument("--health_check_id", type=str, help="健康检查ID")
parser.add_argument("--search_mode", type=str, choices=["like", "equal"], help="查询条件搜索模式: like(模糊搜索)/equal(精确搜索)")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(recordsets):
    total = len(recordsets)
    if Offset >= total:
        print(f"查询结果为空\n\n记录集列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    header = "id\tname\ttype\tstatus\tttl\tzone_id\tzone_name\tline\tweight"
    output = header + "\n"
    for i in range(Offset, min(total, Offset + 50)):
        rs = recordsets[i]
        rsid = getattr(rs, 'id', '')
        name = getattr(rs, 'name', '')
        rtype = getattr(rs, 'type', '')
        status = getattr(rs, 'status', '')
        ttl = str(getattr(rs, 'ttl', ''))
        zone_id = getattr(rs, 'zone_id', '')
        zone_name = getattr(rs, 'zone_name', '')
        line = getattr(rs, 'line', '')
        weight = str(getattr(rs, 'weight', ''))
        output += f"{rsid}\t{name}\t{rtype}\t{status}\t{ttl}\t{zone_id}\t{zone_name}\t{line}\t{weight}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n记录集列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    all_recordsets = []
    marker = ""
    limit = 500

    request = ListRecordSetsWithLineRequest()
    request.limit = limit
    if args.zone_type:
        request.zone_type = args.zone_type
    if args.zone_id:
        request.zone_id = args.zone_id
    if args.line_id:
        request.line_id = args.line_id
    if args.tags:
        request.tags = args.tags
    if args.status:
        request.status = args.status
    if args.type:
        request.type = args.type
    if args.name:
        request.name = args.name
    if args.id:
        request.id = args.id
    if args.records:
        request.records = args.records
    if args.sort_key:
        request.sort_key = args.sort_key
    if args.sort_dir:
        request.sort_dir = args.sort_dir
    if args.health_check_id:
        request.health_check_id = args.health_check_id
    if args.search_mode:
        request.search_mode = args.search_mode

    while True:
        if marker:
            request.marker = marker
        response = client.list_record_sets_with_line(request)
        recordsets = getattr(response, 'recordsets', []) or []
        if not recordsets:
            break
        all_recordsets.extend(recordsets)
        links = getattr(response, 'links', None)
        next_link = getattr(links, 'next', None) if links else None
        if not next_link:
            break
        marker = recordsets[-1].id if recordsets else ""

    if not all_recordsets:
        print(f"没有找到记录集 (区域: {Region})")
        exit(0)

    render(all_recordsets)
except Exception as e:
    print(f"dns.list_record_sets_with_line 查询失败: {e}")
    exit(1)
