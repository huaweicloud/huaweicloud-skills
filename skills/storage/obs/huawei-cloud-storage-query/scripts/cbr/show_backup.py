import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowBackupRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 备份详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--backup_id", type=str, required=True, help="备份ID，可通过 list_backups.py 获取")
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

    request = ShowBackupRequest()
    request.backup_id = args.backup_id
    response = client.show_backup(request)
    backup = getattr(response, 'backup', None)

    if not backup:
        print(f"没有找到备份 (区域: {Region}, 备份 ID: {args.backup_id})")
        exit(0)

    output = ""
    output += f"id: {getattr(backup, 'id', '')}\n"
    output += f"name: {getattr(backup, 'name', '')}\n"
    output += f"description: {getattr(backup, 'description', '')}\n"
    output += f"status: {getattr(backup, 'status', '')}\n"
    output += f"resource_id: {getattr(backup, 'resource_id', '')}\n"
    output += f"resource_name: {getattr(backup, 'resource_name', '')}\n"
    output += f"resource_type: {getattr(backup, 'resource_type', '')}\n"
    output += f"resource_size: {getattr(backup, 'resource_size', '')}\n"
    output += f"vault_id: {getattr(backup, 'vault_id', '')}\n"
    output += f"image_type: {getattr(backup, 'image_type', '')}\n"
    output += f"incremental: {getattr(backup, 'incremental', '')}\n"
    output += f"created_at: {getattr(backup, 'created_at', '')}\n"
    output += f"expired_at: {getattr(backup, 'expired_at', '')}\n"
    output += f"protected_at: {getattr(backup, 'protected_at', '')}\n"
    output += f"checkpoint_id: {getattr(backup, 'checkpoint_id', '')}\n"
    output += f"enterprise_project_id: {getattr(backup, 'enterprise_project_id', '')}\n"
    output += f"provider_id: {getattr(backup, 'provider_id', '')}\n"
    print(output)
except Exception as e:
    print(f"cbr.show_backup 查询失败: {e}")
    exit(1)
