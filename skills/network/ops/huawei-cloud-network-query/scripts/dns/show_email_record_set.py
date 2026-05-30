import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowEmailRecordSetRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询公网域名的邮箱域名")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--zone_id", type=str, required=True, help="公网域名ID")
parser.add_argument("--limit", type=int, help="分页查询时配置每页返回的资源个数，取值范围 0~500，默认 500")
parser.add_argument("--offset", type=int, help="分页查询起始偏移量，取值范围 0~2147483647，默认 0")
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
        print(f"查询结果为空\n\n邮箱记录集列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    header = "id\tname\ttype\tstatus\tttl\trecords"
    output = header + "\n"
    for i in range(Offset, min(total, Offset + 50)):
        rs = recordsets[i]
        rsid = getattr(rs, 'id', '')
        name = getattr(rs, 'name', '')
        rtype = getattr(rs, 'type', '')
        status = getattr(rs, 'status', '')
        ttl = str(getattr(rs, 'ttl', ''))
        records = getattr(rs, 'records', []) or []
        records_str = '; '.join(records) if records else ''
        output += f"{rsid}\t{name}\t{rtype}\t{status}\t{ttl}\t{records_str}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n邮箱记录集列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    request = ShowEmailRecordSetRequest()
    request.zone_id = args.zone_id
    if args.limit:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset

    response = client.show_email_record_set(request)

    recordsets = getattr(response, 'recordsets', []) or []

    if not recordsets:
        print(f"没有找到邮箱域名记录集 (zone_id: {args.zone_id})")
        exit(0)

    render(recordsets)
except Exception as e:
    print(f"dns.show_email_record_set 查询失败: {e}")
    exit(1)
