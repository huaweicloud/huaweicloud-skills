import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowLoadBalancerTopologyRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 负载均衡器拓扑")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--loadbalancer_id", type=str, required=True, help="负载均衡器 ID（必填），可通过 list_load_balancers.py 获取")
parser.add_argument("--listener_id", type=str, help="监听器 ID（可选）")
parser.add_argument("--pool_id", type=str, help="后端服务器组 ID（可选）")
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

    request = ShowLoadBalancerTopologyRequest()
    request.loadbalancer_id = args.loadbalancer_id
    if args.listener_id is not None:
        request.listener_id = args.listener_id
    if args.pool_id is not None:
        request.pool_id = args.pool_id
    response = client.show_load_balancer_topology(request)
    if not response.topology:
        print(f"没有找到负载均衡器拓扑")
        exit(0)

    print(f"loadbalancer 拓扑:\n{response.topology}")
except Exception as e:
    print(f"elb.show_load_balancer_topology 查询失败: {e}")
    exit(1)
