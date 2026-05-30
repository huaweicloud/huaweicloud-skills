import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkbms.v1 import BmsClient
from huaweicloudsdkbms.v1.model import ShowBaremetalServerInterfaceAttachmentsRequest
from huaweicloudsdkbms.v1.region.bms_region import BmsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询裸金属服务器网卡信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_id", type=str, required=True, help="裸金属服务器ID，可通过 list_bare_metal_servers.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = BmsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)
    ).with_region(BmsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 BMS 客户端")
        exit(-1)

    # 构建请求
    request = ShowBaremetalServerInterfaceAttachmentsRequest()
    request.server_id = args.server_id

    response = client.show_baremetal_server_interface_attachments(request)
    interface_attachments = response.interface_attachments

    if not interface_attachments:
        print(f"没有找到网卡信息 (区域: {Region}, 服务器ID: {args.server_id})")
        exit(0)

    # 渲染
    output = f"port_id\tnet_id\tmac_addr\tport_state\tdriver_mode\tpci_address\tip_addresses\n"
    for iface in interface_attachments:
        port_id = getattr(iface, 'port_id', '')
        net_id = getattr(iface, 'net_id', '')
        mac_addr = getattr(iface, 'mac_addr', '')
        port_state = getattr(iface, 'port_state', '')
        driver_mode = getattr(iface, 'driver_mode', '')
        pci_address = getattr(iface, 'pci_address', '')
        fixed_ips = getattr(iface, 'fixed_ips', None) or []
        ip_addrs = ', '.join(getattr(ip, 'ip_address', '') for ip in fixed_ips if getattr(ip, 'ip_address', ''))
        output += f"{port_id}\t{net_id}\t{mac_addr}\t{port_state}\t{driver_mode}\t{pci_address}\t{ip_addrs}\n"

    print(output)
except Exception as e:
    print(f"bms.show_baremetal_server_interface_attachments 查询失败: {e}")
    exit(1)
