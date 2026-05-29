import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import CountPreoccupyIpNumRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="计算LB预占IP数量")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--ip_version", type=int, required=True, help="IP地址类型，4表示IPv4，6表示IPv6（必填）")
parser.add_argument("--l7_flavor_id", type=str, help="七层规格ID，传入表示计算创建该规格LB的预占IP数量，或变更LB规格到该规格所需新增预占IP数量")
parser.add_argument("--ip_target_enable", type=bool, help="IP类型后端转发开关，true开启，false不开启，默认false")
parser.add_argument("--loadbalancer_id", type=str, help="负载均衡器ID，计算LB变更或创建LB中第一个七层监听器的新增预占IP")
parser.add_argument("--availability_zone_id", type=str, nargs="+", help="可用区ID列表，计算创建AZ列表为该值的LB实例的预占IP，仅创建LB场景有效")
parser.add_argument("--scene", type=str, help="场景，UPGRADE表示共享型升级为独享型ELB场景，需同时传入loadbalancer_id")
parser.add_argument("--nat64_enable", type=bool, help="是否开启地址转换(NAT64)，true开启，false不开启，默认false")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 使用 sdk
try:
    http_config = build_http_config()

    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = CountPreoccupyIpNumRequest()
    request.ip_version = args.ip_version
    if args.l7_flavor_id is not None:
        request.l7_flavor_id = args.l7_flavor_id
    if args.ip_target_enable is not None:
        request.ip_target_enable = args.ip_target_enable
    if args.loadbalancer_id is not None:
        request.loadbalancer_id = args.loadbalancer_id
    if args.availability_zone_id is not None:
        request.availability_zone_id = args.availability_zone_id
    if args.scene is not None:
        request.scene = args.scene
    if args.nat64_enable is not None:
        request.nat64_enable = args.nat64_enable

    response = client.count_preoccupy_ip_num(request)
    preoccupy_ip = response.preoccupy_ip
    if not preoccupy_ip:
        print(f"未获取到预占IP信息")
        exit(-1)

    total = getattr(preoccupy_ip, 'total', 0)
    print(f"预占IP总数: {total}")
except Exception as e:
    print(f"elb.count_preoccupy_ip_num 查询失败: {e}")
    exit(1)
