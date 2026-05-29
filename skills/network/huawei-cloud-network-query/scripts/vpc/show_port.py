import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v3 import VpcClient
from huaweicloudsdkvpc.v3.model import ShowPortRequest
from huaweicloudsdkvpc.v3.region.vpc_region import VpcRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询端口详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--port_id", type=str, required=True, help="端口 ID（必填），可通过 list_ports.py 获取")
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

    request = ShowPortRequest()
    request.port_id = args.port_id
    response = client.show_port(request)
    item = response.port
    if not item:
        print(f"没有找到端口")
        exit(0)

    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    description = getattr(item, 'description', '')
    device_id = getattr(item, 'device_id', '')
    device_owner = getattr(item, 'device_owner', '')
    mac_address = getattr(item, 'mac_address', '')
    status = getattr(item, 'status', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    vpc_id = getattr(item, 'vpc_id', '')
    virsubnet_id = getattr(item, 'virsubnet_id', '')
    private_ips = getattr(item, 'private_ips', [])
    security_groups = getattr(item, 'security_groups', [])
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    project_id = getattr(item, 'project_id', '')
    bindingvnic_type = getattr(item, 'bindingvnic_type', '')
    output = f"id\tname\tdescription\tdevice_id\tdevice_owner\tmac_address\tstatus\tadmin_state_up\tvpc_id\tvirsubnet_id\tprivate_ips\tsecurity_groups\tcreated_at\tupdated_at\tproject_id\tbindingvnic_type\n"
    output += f"{id}\t{name}\t{description}\t{device_id}\t{device_owner}\t{mac_address}\t{status}\t{admin_state_up}\t{vpc_id}\t{virsubnet_id}\t{private_ips}\t{security_groups}\t{created_at}\t{updated_at}\t{project_id}\t{bindingvnic_type}\n"
    print(output)
except Exception as e:
    print(f"vpc.show_port 查询失败: {e}")
    exit(1)
