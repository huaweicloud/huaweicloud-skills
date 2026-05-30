import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowMasterSlavePoolRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 主备后端服务器组详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--pool_id", type=str, required=True, help="后端服务器组 ID（必填），可通过 list_master_slave_pools.py 获取")
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

    request = ShowMasterSlavePoolRequest()
    request.pool_id = args.pool_id
    response = client.show_master_slave_pool(request)
    item = response.pool
    if not item:
        print(f"没有找到主备后端服务器组")
        exit(0)

    # 输出详情
    output = f"id\tname\tprotocol\tlb_algorithm\tvpc_id\ttype\tdescription\tip_version\tenterprise_project_id\n"
    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    protocol = getattr(item, 'protocol', '')
    lb_algorithm = getattr(item, 'lb_algorithm', '')
    vpc_id = getattr(item, 'vpc_id', '')
    type = getattr(item, 'type', '')
    description = getattr(item, 'description', '')
    ip_version = getattr(item, 'ip_version', '')
    enterprise_project_id = getattr(item, 'enterprise_project_id', '')
    output += f"{id}\t{name}\t{protocol}\t{lb_algorithm}\t{vpc_id}\t{type}\t{description}\t{ip_version}\t{enterprise_project_id}\n"
    print(output)
except Exception as e:
    print(f"elb.show_master_slave_pool 查询失败: {e}")
    exit(1)
