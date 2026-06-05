import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListEndpointVpcsRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询终端节点VPC列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--limit", type=int, help="分页查询时配置每页返回的资源个数，取值范围 0~500，默认 500")
parser.add_argument("--offset", type=int, help="分页查询起始偏移量，取值范围 0~2147483647，默认 0")
parser.add_argument("--vpc_id", type=str, help="VPC ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(vpcs):
    total = len(vpcs)
    if Offset >= total:
        print(f"查询结果为空\n\nVPC列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    header = "vpc_id\tvpc_name\tregion"
    output = header + "\n"
    for i in range(Offset, min(total, Offset + 50)):
        vpc = vpcs[i]
        vpc_id = getattr(vpc, 'vpc_id', '')
        vpc_name = getattr(vpc, 'vpc_name', '')
        region = getattr(vpc, 'region', '')
        output += f"{vpc_id}\t{vpc_name}\t{region}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\nVPC列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    request = ListEndpointVpcsRequest()
    if args.limit:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset
    if args.vpc_id:
        request.vpc_id = args.vpc_id

    response = client.list_endpoint_vpcs(request)

    vpcs = getattr(response, 'vpcs', []) or []

    if not vpcs:
        print("没有找到终端节点VPC")
        exit(0)

    render(vpcs)
except Exception as e:
    print(f"dns.list_endpoint_vpcs 查询失败: {e}")
    exit(1)
