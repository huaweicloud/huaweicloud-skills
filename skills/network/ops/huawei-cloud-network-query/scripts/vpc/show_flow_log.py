import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient
from huaweicloudsdkvpc.v2.model import ShowFlowLogRequest
from huaweicloudsdkvpc.v2.region.vpc_region import VpcRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询VPC流日志详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--flowlog_id", type=str, required=True, help="流日志 ID（必填），可通过 list_flow_logs.py 获取")
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

    request = ShowFlowLogRequest()
    request.flowlog_id = args.flowlog_id
    response = client.show_flow_log(request)
    item = response.flow_log
    if not item:
        print(f"没有找到VPC流日志")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    tenant_id = getattr(item, 'tenant_id', '')
    description = getattr(item, 'description', '')
    resource_type = getattr(item, 'resource_type', '')
    resource_id = getattr(item, 'resource_id', '')
    traffic_type = getattr(item, 'traffic_type', '')
    log_group_id = getattr(item, 'log_group_id', '')
    log_topic_id = getattr(item, 'log_topic_id', '')
    log_store_type = getattr(item, 'log_store_type', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    admin_state = getattr(item, 'admin_state', '')
    status = getattr(item, 'status', '')
    output = f"id\tname\ttenant_id\tdescription\tresource_type\tresource_id\ttraffic_type\tlog_group_id\tlog_topic_id\tlog_store_type\tcreated_at\tupdated_at\tadmin_state\tstatus\n"
    output += f"{id}\t{name}\t{tenant_id}\t{description}\t{resource_type}\t{resource_id}\t{traffic_type}\t{log_group_id}\t{log_topic_id}\t{log_store_type}\t{created_at}\t{updated_at}\t{admin_state}\t{status}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_flow_log 查询失败: {e}")
    exit(1)
