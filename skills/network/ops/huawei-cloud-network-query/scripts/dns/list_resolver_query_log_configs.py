import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListResolverQueryLogConfigsRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询解析器访问日志列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--limit", type=int, help="分页查询时配置每页返回的资源个数，取值范围 0~500，默认 500")
parser.add_argument("--marker", type=str, help="分页查询的起始资源ID")
parser.add_argument("--vpc_id", type=str, help="VPC ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(configs):
    total = len(configs)
    if Offset >= total:
        print(f"查询结果为空\n\n解析器访问日志列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    header = "id\tlts_group_id\tlts_topic_id\tvpc_ids"
    output = header + "\n"
    for i in range(Offset, min(total, Offset + 50)):
        cfg = configs[i]
        cid = getattr(cfg, 'id', '')
        lts_group_id = getattr(cfg, 'lts_group_id', '')
        lts_topic_id = getattr(cfg, 'lts_topic_id', '')
        vpc_ids = getattr(cfg, 'vpc_ids', []) or []
        vpc_str = '; '.join(vpc_ids) if vpc_ids else ''
        output += f"{cid}\t{lts_group_id}\t{lts_topic_id}\t{vpc_str}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n解析器访问日志列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    all_configs = []
    marker = ""
    limit = 500

    request = ListResolverQueryLogConfigsRequest()
    request.limit = limit
    if args.vpc_id:
        request.vpc_id = args.vpc_id

    while True:
        if marker:
            request.marker = marker
        response = client.list_resolver_query_log_configs(request)
        configs = getattr(response, 'resolver_query_log_configs', []) or []
        if not configs:
            break
        all_configs.extend(configs)
        page_info = getattr(response, 'page_info', None)
        next_marker = getattr(page_info, 'next_marker', None) if page_info else None
        if not next_marker:
            break
        marker = next_marker

    if not all_configs:
        print("没有找到解析器访问日志配置")
        exit(0)

    render(all_configs)
except Exception as e:
    print(f"dns.list_resolver_query_log_configs 查询失败: {e}")
    exit(1)
