import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkbms.v1 import BmsClient
from huaweicloudsdkbms.v1.model import ListBareMetalServerDetailsRequest
from huaweicloudsdkbms.v1.region.bms_region import BmsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询裸金属服务器详情（按ID查询单个服务器详情）")
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
    request = ListBareMetalServerDetailsRequest()
    request.server_id = args.server_id

    response = client.list_bare_metal_server_details(request)
    server = response.server

    if not server:
        print(f"没有找到裸金属服务器 (区域: {Region}, 服务器ID: {args.server_id})")
        exit(0)

    # 渲染详情
    output = ""
    output += f"id: {getattr(server, 'id', '')}\n"
    output += f"name: {getattr(server, 'name', '')}\n"
    output += f"status: {getattr(server, 'status', '')}\n"

    flavor = getattr(server, 'flavor', None)
    if flavor:
        output += f"flavor_id: {getattr(flavor, 'id', '')}\n"
        output += f"flavor_name: {getattr(flavor, 'name', '')}\n"
        output += f"vcpus: {getattr(flavor, 'vcpus', '')}\n"
        output += f"ram(MiB): {getattr(flavor, 'ram', '')}\n"
        output += f"disk(GB): {getattr(flavor, 'disk', '')}\n"
        gpus = getattr(flavor, 'gpus', None) or []
        if gpus:
            gpu_info = ', '.join(f"{getattr(g, 'name', '')}x{getattr(g, 'count', 0)}" for g in gpus)
            output += f"gpus: {gpu_info}\n"
        asic_accelerators = getattr(flavor, 'asic_accelerators', None) or []
        if asic_accelerators:
            asic_info = ', '.join(f"{getattr(a, 'name', '')}x{getattr(a, 'count', 0)}" for a in asic_accelerators)
            output += f"asic_accelerators: {asic_info}\n"

    image = getattr(server, 'image', None)
    if image:
        output += f"image_id: {getattr(image, 'id', '')}\n"

    output += f"availability_zone: {getattr(server, 'os_ext_a_zavailability_zone', '')}\n"
    output += f"created: {getattr(server, 'created', '')}\n"
    output += f"updated: {getattr(server, 'updated', '')}\n"
    output += f"key_name: {getattr(server, 'key_name', '')}\n"
    output += f"host_id: {getattr(server, 'host_id', '')}\n"
    output += f"enterprise_project_id: {getattr(server, 'enterprise_project_id', '')}\n"
    output += f"description: {getattr(server, 'description', '')}\n"
    output += f"host_status: {getattr(server, 'host_status', '')}\n"
    output += f"locked: {getattr(server, 'locked', '')}\n"

    tags = getattr(server, 'tags', None) or []
    if tags:
        output += f"tags: {', '.join(tags)}\n"

    metadata = getattr(server, 'metadata', None)
    if metadata:
        output += f"charging_mode: {getattr(metadata, 'charging_mode', '')}\n"
        output += f"image_name: {getattr(metadata, 'image_name', '')}\n"
        output += f"os_type: {getattr(metadata, 'os_type', '')}\n"
        output += f"os_bit: {getattr(metadata, 'os_bit', '')}\n"
        output += f"vpc_id: {getattr(metadata, 'vpc_id', '')}\n"

    volumes = getattr(server, 'os_extended_volumesvolumes_attached', None) or []
    if volumes:
        output += f"volumes_attached:\n"
        for vol in volumes:
            output += f"  - id: {getattr(vol, 'id', '')}, device: {getattr(vol, 'device', '')}, boot_index: {getattr(vol, 'boot_index', '')}\n"

    print(output)
except Exception as e:
    print(f"bms.list_bare_metal_server_details 查询失败: {e}")
    exit(1)
