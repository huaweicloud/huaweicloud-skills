import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowServerAttachableNicNumRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器可挂载网卡数量")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_id", type=str, required=True, help="服务器 ID（UUID），可通过 list_servers_details.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ECS 客户端")
        exit(-1)

    request = ShowServerAttachableNicNumRequest()
    request.server_id = args.server_id
    response = client.show_server_attachable_nic_num(request)
    quantity = response.attachable_quantity

    if not quantity:
        print(f"没有找到 ECS 服务器可挂载网卡数量 (区域: {Region}, 服务器 ID: {args.server_id})")
        exit(0)

    # 渲染结果
    output = ""
    output += f"free_nic: {getattr(quantity, 'free_nic', '')}\n"
    output += f"free_efi_nic: {getattr(quantity, 'free_efi_nic', '')}\n"
    output += f"free_scsi: {getattr(quantity, 'free_scsi', '')}\n"
    output += f"free_blk: {getattr(quantity, 'free_blk', '')}\n"
    output += f"free_disk: {getattr(quantity, 'free_disk', '')}\n"
    print(output)
except Exception as e:
    print(f"ecs.server_attachable_nic_num 查询失败: {e}")
    exit(1)
