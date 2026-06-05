import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowTrafficMirrorFilterRuleRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询流量镜像过滤规则详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--traffic_mirror_filter_rule_id", type=str, required=True, help="流量镜像过滤规则 ID（必填），可通过 list_traffic_mirror_filter_rules.py 获取")
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

    request = ShowTrafficMirrorFilterRuleRequest()
    request.traffic_mirror_filter_rule_id = args.traffic_mirror_filter_rule_id
    response = client.show_traffic_mirror_filter_rule(request)
    item = response.traffic_mirror_filter_rule
    if not item:
        print(f"没有找到流量镜像过滤规则")
        exit(0)

    id = getattr(item, 'id', '')
    project_id = getattr(item, 'project_id', '')
    description = getattr(item, 'description', '')
    traffic_mirror_filter_id = getattr(item, 'traffic_mirror_filter_id', '')
    direction = getattr(item, 'direction', '')
    source_cidr_block = getattr(item, 'source_cidr_block', '')
    destination_cidr_block = getattr(item, 'destination_cidr_block', '')
    source_port_range = getattr(item, 'source_port_range', '')
    destination_port_range = getattr(item, 'destination_port_range', '')
    ethertype = getattr(item, 'ethertype', '')
    protocol = getattr(item, 'protocol', '')
    action = getattr(item, 'action', '')
    priority = getattr(item, 'priority', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output = f"id\tproject_id\tdescription\ttraffic_mirror_filter_id\tdirection\tsource_cidr_block\tdestination_cidr_block\tsource_port_range\tdestination_port_range\tethertype\tprotocol\taction\tpriority\tcreated_at\tupdated_at\n"
    output += f"{id}\t{project_id}\t{description}\t{traffic_mirror_filter_id}\t{direction}\t{source_cidr_block}\t{destination_cidr_block}\t{source_port_range}\t{destination_port_range}\t{ethertype}\t{protocol}\t{action}\t{priority}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_traffic_mirror_filter_rule 查询失败: {e}")
    exit(1)
