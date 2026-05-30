import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowTrafficMirrorFilterRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询流量镜像过滤器详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--traffic_mirror_filter_id", type=str, required=True, help="流量镜像过滤器 ID（必填），可通过 list_traffic_mirror_filters.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = VpcClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpcRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 VPC 客户端")
        exit(-1)

    request = ShowTrafficMirrorFilterRequest()
    request.traffic_mirror_filter_id = args.traffic_mirror_filter_id
    response = client.show_traffic_mirror_filter(request)
    item = response.traffic_mirror_filter
    if not item:
        print(f"没有找到流量镜像过滤器")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    project_id = getattr(item, 'project_id', '')
    ingress_rules = getattr(item, 'ingress_rules', [])
    egress_rules = getattr(item, 'egress_rules', [])
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    filter_type = getattr(item, 'type', '')
    output = f"id\tname\tdescription\tproject_id\tingress_rules\tegress_rules\tcreated_at\tupdated_at\ttype\n"
    output += f"{id}\t{name}\t{description}\t{project_id}\t{len(ingress_rules) if ingress_rules else 0}\t{len(egress_rules) if egress_rules else 0}\t{created_at}\t{updated_at}\t{filter_type}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_traffic_mirror_filter 查询失败: {e}")
    exit(1)
