import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowCheckpointRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 还原点详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--checkpoint_id", type=str, required=True, help="还原点ID，可通过 list_backups.py 获取")
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

    request = ShowCheckpointRequest()
    request.checkpoint_id = args.checkpoint_id
    response = client.show_checkpoint(request)
    checkpoint = getattr(response, 'checkpoint', None)

    if not checkpoint:
        print(f"没有找到还原点 (区域: {Region}, 还原点 ID: {args.checkpoint_id})")
        exit(0)

    output = ""
    output += f"id: {getattr(checkpoint, 'id', '')}\n"
    output += f"status: {getattr(checkpoint, 'status', '')}\n"
    output += f"project_id: {getattr(checkpoint, 'project_id', '')}\n"
    output += f"created_at: {getattr(checkpoint, 'created_at', '')}\n"

    extra_info = getattr(checkpoint, 'extra_info', None)
    if extra_info:
        output += f"\nextra_info:\n"
        output += f"  name: {getattr(extra_info, 'name', '')}\n"
        output += f"  description: {getattr(extra_info, 'description', '')}\n"
        output += f"  retention_duration: {getattr(extra_info, 'retention_duration', '')}\n"

    vault = getattr(checkpoint, 'vault', None)
    if vault:
        output += f"\nvault:\n"
        output += f"  id: {getattr(vault, 'id', '')}\n"
        output += f"  name: {getattr(vault, 'name', '')}\n"

        resources = getattr(vault, 'resources', []) or []
        if resources:
            output += f"  resources ({len(resources)}):\n"
            for res in resources:
                output += f"    id: {getattr(res, 'id', '')}\n"
                output += f"    name: {getattr(res, 'name', '')}\n"
                output += f"    type: {getattr(res, 'type', '')}\n"
                output += f"    protect_status: {getattr(res, 'protect_status', '')}\n"
                output += f"    resource_size: {getattr(res, 'resource_size', '')}\n"
                output += f"    backup_size: {getattr(res, 'backup_size', '')}\n"
                output += f"    backup_count: {getattr(res, 'backup_count', '')}\n"
                extra = getattr(res, 'extra_info', '')
                if extra:
                    output += f"    extra_info: {extra}\n"

        skipped_resources = getattr(vault, 'skipped_resources', []) or []
        if skipped_resources:
            output += f"  skipped_resources ({len(skipped_resources)}):\n"
            for sk in skipped_resources:
                output += f"    id: {getattr(sk, 'id', '')}\n"
                output += f"    name: {getattr(sk, 'name', '')}\n"
                output += f"    type: {getattr(sk, 'type', '')}\n"
                output += f"    code: {getattr(sk, 'code', '')}\n"
                output += f"    reason: {getattr(sk, 'reason', '')}\n"

    print(output)
except Exception as e:
    print(f"cbr.show_checkpoint 查询失败: {e}")
    exit(1)
