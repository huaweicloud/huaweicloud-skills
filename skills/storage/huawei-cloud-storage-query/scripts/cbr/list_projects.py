import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListProjectsRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 项目列表")
parser.add_argument("--project_id", type=str, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ListProjectsRequest()
    response = client.list_projects(request)

    projects = getattr(response, 'projects', []) or []

    if not projects:
        print(f"没有找到项目 (区域: {Region})")
        exit(0)

    output = f"id\tname\tdomain_id\tenabled\n"
    for project in projects:
        pid = getattr(project, 'id', '')
        name = getattr(project, 'name', '')
        domain_id = getattr(project, 'domain_id', '')
        enabled = getattr(project, 'enabled', '')
        output += f"{pid}\t{name}\t{domain_id}\t{enabled}\n"
    print(output)
except Exception as e:
    print(f"cbr.list_projects 查询失败: {e}")
    exit(1)
