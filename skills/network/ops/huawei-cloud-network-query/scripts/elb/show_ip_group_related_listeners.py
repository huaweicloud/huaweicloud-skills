import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowIpGroupRelatedListenersRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB IP 地址组关联的监听器列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--ipgroup_id", type=str, required=True, help="IP 地址组ID，可通过 list_ip_groups.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ShowIpGroupRelatedListenersRequest()
    request.ipgroup_id = args.ipgroup_id
    response = client.show_ip_group_related_listeners(request)
    items = response.listeners
    if not items:
        print(f"没有找到 IP 地址组关联的监听器 (区域: {Region})")
        exit(0)

    output = f"id\n"
    for item in items:
        id = getattr(item, 'id', '')
        output += f"{id}\n"
    print(output)
except Exception as e:
    print(f"elb.show_ip_group_related_listeners 查询失败: {e}")
    exit(1)
