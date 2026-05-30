import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListPtrRecordsRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询弹性公网IP的反向解析记录列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页查询的起始资源ID")
parser.add_argument("--limit", type=int, help="分页查询时配置每页返回的资源个数，取值范围 0~500，默认 500")
parser.add_argument("--offset", type=int, help="分页查询起始偏移量，取值范围 0~2147483647，默认 0")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID")
parser.add_argument("--tags", type=str, help="资源标签，格式 key1,value1|key2,value2")
parser.add_argument("--status", type=str, help="反向解析状态: ACTIVE/ERROR/FREEZE/DISABLE")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(floatingips):
    total = len(floatingips)
    if Offset >= total:
        print(f"查询结果为空\n\n反向解析列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    header = "id\taddress\tptrdname\tstatus\tttl"
    output = header + "\n"
    for i in range(Offset, min(total, Offset + 50)):
        fip = floatingips[i]
        fid = getattr(fip, 'id', '')
        address = getattr(fip, 'address', '')
        ptrdname = getattr(fip, 'ptrdname', '')
        status = getattr(fip, 'status', '')
        ttl = str(getattr(fip, 'ttl', ''))
        output += f"{fid}\t{address}\t{ptrdname}\t{status}\t{ttl}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n反向解析列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    all_floatingips = []
    marker = ""
    limit = 500

    request = ListPtrRecordsRequest()
    request.limit = limit
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.tags:
        request.tags = args.tags
    if args.status:
        request.status = args.status

    while True:
        if marker:
            request.marker = marker
        response = client.list_ptr_records(request)
        floatingips = getattr(response, 'floatingips', []) or []
        if not floatingips:
            break
        all_floatingips.extend(floatingips)
        links = getattr(response, 'links', None)
        next_link = getattr(links, 'next', None) if links else None
        if not next_link:
            break
        marker = floatingips[-1].id if floatingips else ""

    if not all_floatingips:
        print(f"没有找到反向解析记录 (区域: {Region})")
        exit(0)

    render(all_floatingips)
except Exception as e:
    print(f"dns.list_ptr_records 查询失败: {e}")
    exit(1)
