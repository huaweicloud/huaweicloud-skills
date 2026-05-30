import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import GlanceShowImageRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 IMS 镜像详情，返回镜像的完整信息（包括元数据、大小、格式、OS信息等）")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--image_id", type=str, required=True, help="镜像 ID，可通过 list_images.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = ImsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ImsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 IMS 客户端")
        exit(-1)

    request = GlanceShowImageRequest()
    request.image_id = args.image_id
    response = client.glance_show_image(request)

    # 渲染结果 - 基本信息
    output = ""
    output += f"id: {getattr(response, 'id', '')}\n"
    output += f"name: {getattr(response, 'name', '')}\n"
    output += f"status: {getattr(response, 'status', '')}\n"
    output += f"visibility: {getattr(response, 'visibility', '')}\n"
    output += f"imagetype: {getattr(response, 'imagetype', '')}\n"
    output += f"protected: {getattr(response, 'protected', '')}\n"

    # OS 信息
    output += f"\n--- OS 信息 ---\n"
    output += f"os_type: {getattr(response, 'os_type', '')}\n"
    output += f"os_bit: {getattr(response, 'os_bit', '')}\n"
    output += f"os_version: {getattr(response, 'os_version', '')}\n"
    output += f"platform: {getattr(response, 'platform', '')}\n"
    hw_firmware_type = getattr(response, 'hw_firmware_type', '')
    if hw_firmware_type:
        output += f"hw_firmware_type: {hw_firmware_type}\n"

    # 镜像规格
    output += f"\n--- 镜像规格 ---\n"
    output += f"disk_format: {getattr(response, 'disk_format', '')}\n"
    output += f"container_format: {getattr(response, 'container_format', '')}\n"
    output += f"min_disk: {getattr(response, 'min_disk', '')} GB\n"
    output += f"min_ram: {getattr(response, 'min_ram', '')} MB\n"
    image_size = getattr(response, 'image_size', '')
    if image_size:
        size_gb = int(image_size) / (1024 ** 3) if image_size.isdigit() else image_size
        output += f"image_size: {image_size} bytes ({size_gb:.2f} GB)\n"
    virtual_env_type = getattr(response, 'virtual_env_type', '')
    if virtual_env_type:
        output += f"virtual_env_type: {virtual_env_type}\n"
    enterprise_project_id = getattr(response, 'enterprise_project_id', '')
    if enterprise_project_id:
        output += f"enterprise_project_id: {enterprise_project_id}\n"

    # 时间信息
    output += f"\n--- 时间信息 ---\n"
    output += f"created_at: {getattr(response, 'created_at', '')}\n"
    output += f"updated_at: {getattr(response, 'updated_at', '')}\n"

    # 虚拟化支持
    output += f"\n--- 虚拟化支持 ---\n"
    support_kvm = getattr(response, 'support_kvm', '')
    support_xen = getattr(response, 'support_xen', '')
    support_kvm_gpu_type = getattr(response, 'support_kvm_gpu_type', '')
    support_xen_gpu_type = getattr(response, 'support_xen_gpu_type', '')
    output += f"support_kvm: {support_kvm}\n"
    output += f"support_xen: {support_xen}\n"
    if support_kvm_gpu_type:
        output += f"support_kvm_gpu_type: {support_kvm_gpu_type}\n"
    if support_xen_gpu_type:
        output += f"support_xen_gpu_type: {support_xen_gpu_type}\n"

    # 标签
    tags = getattr(response, 'tags', [])
    if tags:
        output += f"\n--- 标签 ---\n"
        output += f"tags: {', '.join(tags)}\n"

    # 其他信息
    owner = getattr(response, 'owner', '')
    description = getattr(response, 'description', '')
    checksum = getattr(response, 'checksum', '')
    if owner or description or checksum:
        output += f"\n--- 其他信息 ---\n"
        if owner:
            output += f"owner: {owner}\n"
        if description:
            output += f"description: {description}\n"
        if checksum:
            output += f"checksum: {checksum}\n"

    print(output)
except Exception as e:
    print(f"ims.show_image 查询失败: {e}")
    exit(1)
