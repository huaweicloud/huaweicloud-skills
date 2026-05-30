import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowMemberDetailRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 备份成员详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--backup_id", type=str, required=True, help="备份ID")
parser.add_argument("--member_id", type=str, required=True, help="成员id，为接收方的project_id")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ShowMemberDetailRequest()
    request.backup_id = args.backup_id
    request.member_id = args.member_id
    response = client.show_member_detail(request)
    member = getattr(response, 'member', None)

    if not member:
        print(f"没有找到备份成员 (区域: {Region}, 备份 ID: {args.backup_id}, 成员 ID: {args.member_id})")
        exit(0)

    output = ""
    output += f"id: {getattr(member, 'id', '')}\n"
    output += f"status: {getattr(member, 'status', '')}\n"
    output += f"backup_id: {getattr(member, 'backup_id', '')}\n"
    output += f"image_id: {getattr(member, 'image_id', '')}\n"
    output += f"dest_project_id: {getattr(member, 'dest_project_id', '')}\n"
    output += f"vault_id: {getattr(member, 'vault_id', '')}\n"
    output += f"created_at: {getattr(member, 'created_at', '')}\n"
    output += f"updated_at: {getattr(member, 'updated_at', '')}\n"
    print(output)
except Exception as e:
    print(f"cbr.show_member_detail 查询失败: {e}")
    exit(1)
