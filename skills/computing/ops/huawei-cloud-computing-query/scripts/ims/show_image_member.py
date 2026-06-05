import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import ShowImageMemberRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 IMS 镜像成员详情，获取指定共享镜像的某个成员的共享状态信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--image_id", type=str, required=True, help="镜像 ID，可通过 list_images.py 获取")
parser.add_argument("--member_id", type=str, required=True, help="成员 ID（接受共享的租户 ID），可通过 list_image_members.py 获取")
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

    request = ShowImageMemberRequest()
    request.image_id = args.image_id
    request.member_id = args.member_id
    response = client.show_image_member(request)

    # 渲染结果
    output = ""
    output += f"image_id: {getattr(response, 'image_id', '')}\n"
    output += f"member_id: {getattr(response, 'member_id', '')}\n"
    output += f"status: {getattr(response, 'status', '')}\n"
    output += f"member_type: {getattr(response, 'member_type', '')}\n"
    output += f"created_at: {getattr(response, 'created_at', '')}\n"
    output += f"updated_at: {getattr(response, 'updated_at', '')}\n"
    urn = getattr(response, 'urn', '')
    if urn:
        output += f"urn: {urn}\n"
    print(output)
except Exception as e:
    print(f"ims.show_image_member 查询失败: {e}")
    exit(1)
