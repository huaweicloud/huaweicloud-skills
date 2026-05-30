import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListResolverRulesRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询解析器转发规则列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_name", type=str, help="转发规则域名")
parser.add_argument("--name", type=str, help="转发规则名称")
parser.add_argument("--endpoint_id", type=str, help="终端节点ID")
parser.add_argument("--id", type=str, help="转发规则ID")
parser.add_argument("--limit", type=int, help="分页查询时配置每页返回的资源个数，取值范围 0~500，默认 500")
parser.add_argument("--offset", type=int, help="分页查询起始偏移量，取值范围 0~2147483647，默认 0")
parser.add_argument("--marker", type=str, help="分页查询的起始资源ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(resolver_rules):
    total = len(resolver_rules)
    if Offset >= total:
        print(f"查询结果为空\n\n转发规则列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    header = "id\tname\tdomain_name\tendpoint_id\tstatus\tcreated_at\tupdated_at"
    output = header + "\n"
    for i in range(Offset, min(total, Offset + 50)):
        rule = resolver_rules[i]
        rid = getattr(rule, 'id', '')
        name = getattr(rule, 'name', '')
        domain_name = getattr(rule, 'domain_name', '')
        endpoint_id = getattr(rule, 'endpoint_id', '')
        status = getattr(rule, 'status', '')
        created_at = getattr(rule, 'created_at', '')
        updated_at = getattr(rule, 'updated_at', '')
        output += f"{rid}\t{name}\t{domain_name}\t{endpoint_id}\t{status}\t{created_at}\t{updated_at}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n转发规则列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    request = ListResolverRulesRequest()
    if args.domain_name:
        request.domain_name = args.domain_name
    if args.name:
        request.name = args.name
    if args.endpoint_id:
        request.endpoint_id = args.endpoint_id
    if args.id:
        request.id = args.id
    if args.limit:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset
    if args.marker:
        request.marker = args.marker

    response = client.list_resolver_rules(request)

    resolver_rules = getattr(response, 'resolver_rules', []) or []

    if not resolver_rules:
        print("没有找到解析器转发规则")
        exit(0)

    render(resolver_rules)
except Exception as e:
    print(f"dns.list_resolver_rules 查询失败: {e}")
    exit(1)
