import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowTrafficMirrorSessionRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询流量镜像会话详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--traffic_mirror_session_id", type=str, required=True, help="流量镜像会话 ID（必填），可通过 list_traffic_mirror_sessions.py 获取")
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

    request = ShowTrafficMirrorSessionRequest()
    request.traffic_mirror_session_id = args.traffic_mirror_session_id
    response = client.show_traffic_mirror_session(request)
    item = response.traffic_mirror_session
    if not item:
        print(f"没有找到流量镜像会话")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    project_id = getattr(item, 'project_id', '')
    traffic_mirror_filter_id = getattr(item, 'traffic_mirror_filter_id', '')
    traffic_mirror_sources = getattr(item, 'traffic_mirror_sources', [])
    traffic_mirror_target_id = getattr(item, 'traffic_mirror_target_id', '')
    traffic_mirror_target_type = getattr(item, 'traffic_mirror_target_type', '')
    virtual_network_id = getattr(item, 'virtual_network_id', '')
    packet_length = getattr(item, 'packet_length', '')
    priority = getattr(item, 'priority', '')
    enabled = getattr(item, 'enabled', '')
    session_type = getattr(item, 'type', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output = f"id\tname\tdescription\tproject_id\ttraffic_mirror_filter_id\ttraffic_mirror_sources\ttraffic_mirror_target_id\ttraffic_mirror_target_type\tvirtual_network_id\tpacket_length\tpriority\tenabled\ttype\tcreated_at\tupdated_at\n"
    output += f"{id}\t{name}\t{description}\t{project_id}\t{traffic_mirror_filter_id}\t{traffic_mirror_sources}\t{traffic_mirror_target_id}\t{traffic_mirror_target_type}\t{virtual_network_id}\t{packet_length}\t{priority}\t{enabled}\t{session_type}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_traffic_mirror_session 查询失败: {e}")
    exit(1)
