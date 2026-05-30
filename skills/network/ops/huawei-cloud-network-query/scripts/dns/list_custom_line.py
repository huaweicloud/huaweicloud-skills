import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListCustomLineRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询自定义线路")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--line_id", type=str, help="自定义线路ID")
parser.add_argument("--name", type=str, help="自定义线路名称")
parser.add_argument("--limit", type=int, help="分页查询时配置每页返回的资源个数，取值范围 0~500，默认 500")
parser.add_argument("--offset", type=int, help="分页查询起始偏移量，取值范围 0~2147483647，默认 0")
parser.add_argument("--show_detail", type=bool, help="是否显示详细信息，默认 false")
parser.add_argument("--status", type=str, help="自定义线路状态: ACTIVE/ERROR")
parser.add_argument("--ip", type=str, help="自定义线路的IP地址")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(lines):
    total = len(lines)
    if Offset >= total:
        print(f"查询结果为空\n\n自定义线路列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    header = "line_id\tname\tstatus\tcreated_at\tupdated_at"
    output = header + "\n"
    for i in range(Offset, min(total, Offset + 50)):
        line = lines[i]
        line_id = getattr(line, 'line_id', '')
        name = getattr(line, 'name', '')
        status = getattr(line, 'status', '')
        created_at = getattr(line, 'created_at', '')
        updated_at = getattr(line, 'updated_at', '')
        output += f"{line_id}\t{name}\t{status}\t{created_at}\t{updated_at}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n自定义线路列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    request = ListCustomLineRequest()
    if args.line_id:
        request.line_id = args.line_id
    if args.name:
        request.name = args.name
    if args.limit:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset
    if args.show_detail is not None:
        request.show_detail = args.show_detail
    if args.status:
        request.status = args.status
    if args.ip:
        request.ip = args.ip

    response = client.list_custom_line(request)

    lines = getattr(response, 'lines', []) or []

    if not lines:
        print("没有找到自定义线路")
        exit(0)

    render(lines)
except Exception as e:
    print(f"dns.list_custom_line 查询失败: {e}")
    exit(1)
