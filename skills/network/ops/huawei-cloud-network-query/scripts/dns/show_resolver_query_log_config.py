import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowResolverQueryLogConfigRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询解析器访问日志")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--id", type=str, required=True, help="解析器访问日志配置ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    if not resp:
        print("没有找到解析器访问日志配置")
        return
    cid = getattr(resp, 'id', '')
    lts_group_id = getattr(resp, 'lts_group_id', '')
    lts_topic_id = getattr(resp, 'lts_topic_id', '')
    vpc_ids = getattr(resp, 'vpc_ids', []) or []
    output = f"id: {cid}\nlts_group_id: {lts_group_id}\nlts_topic_id: {lts_topic_id}\n"
    if vpc_ids:
        output += f"vpc_ids: {', '.join(vpc_ids)}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowResolverQueryLogConfigRequest()
    request.id = args.id

    response = client.show_resolver_query_log_config(request)

    config = getattr(response, 'resolver_query_log_config', None)

    if not config:
        print(f"没有找到解析器访问日志配置 (id: {args.id})")
        exit(0)

    render(config)
except Exception as e:
    print(f"dns.show_resolver_query_log_config 查询失败: {e}")
    exit(1)
