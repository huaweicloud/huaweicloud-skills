import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ListInstancesRequest, ListInstancesRequestBody
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="批量查询DNS解析量统计相关的资源")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_id", type=str, help="域名ID")
parser.add_argument("--domain_name", type=str, help="域名名称")
parser.add_argument("--start_time", type=str, help="查询开始时间，格式 YYYY-MM-DD")
parser.add_argument("--end_time", type=str, help="查询结束时间，格式 YYYY-MM-DD")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(instances):
    if not instances:
        print("没有找到DNS解析量统计资源")
        return
    header = "id\tname\tstatus\tregion\tenterprise_project_id"
    output = header + "\n"
    for inst in instances:
        iid = getattr(inst, 'id', '')
        name = getattr(inst, 'name', '')
        status = getattr(inst, 'status', '')
        region = getattr(inst, 'region', '')
        ep_id = getattr(inst, 'enterprise_project_id', '')
        output += f"{iid}\t{name}\t{status}\t{region}\t{ep_id}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ListInstancesRequest()
    body = ListInstancesRequestBody()
    if args.domain_id:
        body.domain_id = args.domain_id
    if args.domain_name:
        body.domain_name = args.domain_name
    if args.start_time:
        body.start_time = args.start_time
    if args.end_time:
        body.end_time = args.end_time
    request.body = body

    response = client.list_instances(request)

    instances = getattr(response, 'instances', []) or []

    if not instances:
        print("没有找到DNS解析量统计资源")
        exit(0)

    render(instances)
except Exception as e:
    print(f"dns.list_instances 查询失败: {e}")
    exit(1)
