import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowOpLogRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 任务详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--operation_log_id", type=str, required=True, help="任务ID，可通过 list_op_logs.py 获取")
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

    request = ShowOpLogRequest()
    request.operation_log_id = args.operation_log_id
    response = client.show_op_log(request)
    op_log = getattr(response, 'operation_log', None)

    if not op_log:
        print(f"没有找到任务 (区域: {Region}, 任务 ID: {args.operation_log_id})")
        exit(0)

    output = ""
    output += f"id: {getattr(op_log, 'id', '')}\n"
    output += f"operation_type: {getattr(op_log, 'operation_type', '')}\n"
    output += f"status: {getattr(op_log, 'status', '')}\n"
    output += f"provider_id: {getattr(op_log, 'provider_id', '')}\n"
    output += f"vault_id: {getattr(op_log, 'vault_id', '')}\n"
    output += f"vault_name: {getattr(op_log, 'vault_name', '')}\n"
    output += f"project_id: {getattr(op_log, 'project_id', '')}\n"
    output += f"policy_id: {getattr(op_log, 'policy_id', '')}\n"
    output += f"checkpoint_id: {getattr(op_log, 'checkpoint_id', '')}\n"
    output += f"created_at: {getattr(op_log, 'created_at', '')}\n"
    output += f"started_at: {getattr(op_log, 'started_at', '')}\n"
    output += f"ended_at: {getattr(op_log, 'ended_at', '')}\n"
    output += f"updated_at: {getattr(op_log, 'updated_at', '')}\n"
    print(output)
except Exception as e:
    print(f"cbr.show_op_log 查询失败: {e}")
    exit(1)
