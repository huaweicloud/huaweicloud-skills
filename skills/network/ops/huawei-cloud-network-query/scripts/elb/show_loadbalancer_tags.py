import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowLoadbalancerTagsRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 ELB 负载均衡器标签列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--loadbalancer_id", type=str, required=True, help="负载均衡器 ID（必填），可通过 list_load_balancers.py 获取")
parser.add_argument("--offset", type=int, help="分页偏移量，从 0 开始")
args = parser.parse_args()

if args.region is not None:
    Region = args.region
if args.offset is not None:
    Offset = args.offset
if Offset < 0:
    Offset = 0

def render(items):
    total = len(items)
    if Offset >= total:
        print(f"查询结果为空\n\n负载均衡器标签列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)
    output = f"key\tvalue\n"
    for i in range(Offset, min(total, Offset + 50)):
        item = items[i]
        key = getattr(item, 'key', '')
        value = getattr(item, 'value', '')
        output += f"{key}\t{value}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n负载均衡器标签列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
        if end + 1 < total:
            output += f"可以使用 --offset={end + 1} 参数继续获取后续数据"
    print(output)

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ShowLoadbalancerTagsRequest()
    request.loadbalancer_id = args.loadbalancer_id
    response = client.show_loadbalancer_tags(request)
    items = response.tags
    if not items:
        print(f"没有找到负载均衡器标签 (区域: {Region})")
        exit(0)
    render(items)
except Exception as e:
    print(f"elb.show_loadbalancer_tags 查询失败: {e}")
    exit(1)
