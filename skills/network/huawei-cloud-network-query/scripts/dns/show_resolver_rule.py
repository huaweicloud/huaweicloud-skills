import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowResolverRuleRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询解析器转发规则")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--resolverrule_id", type=str, required=True, help="转发规则ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resolver_rule):
    if not resolver_rule:
        print("没有找到转发规则信息")
        return
    rid = getattr(resolver_rule, 'id', '')
    name = getattr(resolver_rule, 'name', '')
    domain_name = getattr(resolver_rule, 'domain_name', '')
    endpoint_id = getattr(resolver_rule, 'endpoint_id', '')
    status = getattr(resolver_rule, 'status', '')
    created_at = getattr(resolver_rule, 'created_at', '')
    updated_at = getattr(resolver_rule, 'updated_at', '')
    ip_addresses = getattr(resolver_rule, 'ip_addresses', []) or []
    output = f"id: {rid}\nname: {name}\ndomain_name: {domain_name}\nendpoint_id: {endpoint_id}\nstatus: {status}\ncreated_at: {created_at}\nupdated_at: {updated_at}\n"
    if ip_addresses:
        output += "ip_addresses:\n"
        for ip in ip_addresses:
            output += f"  {ip}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowResolverRuleRequest()
    request.resolverrule_id = args.resolverrule_id

    response = client.show_resolver_rule(request)

    resolver_rule = getattr(response, 'resolver_rule', None)

    if not resolver_rule:
        print(f"没有找到转发规则 (resolverrule_id: {args.resolverrule_id})")
        exit(0)

    render(resolver_rule)
except Exception as e:
    print(f"dns.show_resolver_rule 查询失败: {e}")
    exit(1)
