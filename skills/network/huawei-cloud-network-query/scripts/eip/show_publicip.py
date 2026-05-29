import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkeip.v3 import EipClient
from huaweicloudsdkeip.v3.model import ShowPublicipRequest
from huaweicloudsdkeip.v3.region.eip_region import EipRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询弹性公网IP详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认取环境变量 HW_REGION_NAME（未设置则 cn-north-4）")
parser.add_argument("--publicip_id", type=str, required=True, help="弹性公网IP ID，可通过 list_publicips.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EipClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EipRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EIP 客户端")
        exit(-1)

    request = ShowPublicipRequest()
    request.publicip_id = args.publicip_id
    response = client.show_publicip(request)

    eip = response.publicip
    if not eip:
        print(f"没有找到弹性公网IP (ID: {args.publicip_id})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"id: {getattr(eip, 'id', '')}\n"
    output += f"public_ip_address: {getattr(eip, 'public_ip_address', '')}\n"
    output += f"public_ipv6_address: {getattr(eip, 'public_ipv6_address', '')}\n"
    output += f"status: {getattr(eip, 'status', '')}\n"
    output += f"type: {getattr(eip, 'type', '')}\n"
    output += f"network_type: {getattr(eip, 'network_type', '')}\n"
    output += f"ip_version: {getattr(eip, 'ip_version', '')}\n"
    output += f"description: {getattr(eip, 'description', '')}\n"
    output += f"alias: {getattr(eip, 'alias', '')}\n"
    output += f"project_id: {getattr(eip, 'project_id', '')}\n"
    output += f"enterprise_project_id: {getattr(eip, 'enterprise_project_id', '')}\n"
    output += f"public_border_group: {getattr(eip, 'public_border_group', '')}\n"
    output += f"publicip_pool_id: {getattr(eip, 'publicip_pool_id', '')}\n"
    output += f"publicip_pool_name: {getattr(eip, 'publicip_pool_name', '')}\n"
    output += f"associate_instance_type: {getattr(eip, 'associate_instance_type', '')}\n"
    output += f"associate_instance_id: {getattr(eip, 'associate_instance_id', '')}\n"
    output += f"billing_info: {getattr(eip, 'billing_info', '')}\n"
    output += f"lock_status: {getattr(eip, 'lock_status', '')}\n"
    output += f"created_at: {getattr(eip, 'created_at', '')}\n"
    output += f"updated_at: {getattr(eip, 'updated_at', '')}\n"
    bandwidth = getattr(eip, 'bandwidth', None)
    if bandwidth:
        output += f"bandwidth.id: {getattr(bandwidth, 'id', '')}\n"
        output += f"bandwidth.name: {getattr(bandwidth, 'name', '')}\n"
        output += f"bandwidth.size: {getattr(bandwidth, 'size', '')}\n"
        output += f"bandwidth.share_type: {getattr(bandwidth, 'share_type', '')}\n"
        output += f"bandwidth.charge_mode: {getattr(bandwidth, 'charge_mode', '')}\n"
    vnic = getattr(eip, 'vnic', None)
    if vnic:
        output += f"vnic.private_ip_address: {getattr(vnic, 'private_ip_address', '')}\n"
        output += f"vnic.device_id: {getattr(vnic, 'device_id', '')}\n"
        output += f"vnic.vpc_id: {getattr(vnic, 'vpc_id', '')}\n"
        output += f"vnic.port_id: {getattr(vnic, 'port_id', '')}\n"
        output += f"vnic.instance_type: {getattr(vnic, 'instance_type', '')}\n"
        output += f"vnic.instance_id: {getattr(vnic, 'instance_id', '')}\n"
    print(output)
except Exception as e:
    print(f"eip.show_publicip 查询失败: {e}")
    exit(1)
