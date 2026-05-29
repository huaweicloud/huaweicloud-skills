import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListOpLogsRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 CBR 任务列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--end_time", type=str, help="结束时间")
parser.add_argument("--limit", type=int, default=1000, help="返回结果个数限制，默认1000")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
parser.add_argument("--operation_type", type=str, help="任务类型")
parser.add_argument("--provider_id", type=str, help="备份提供商ID")
parser.add_argument("--resource_id", type=str, help="资源ID")
parser.add_argument("--resource_name", type=str, help="资源名称")
parser.add_argument("--start_time", type=str, help="开始时间")
parser.add_argument("--status", type=str, help="状态")
parser.add_argument("--vault_id", type=str, help="存储库ID，可通过 list_vault.py 获取")
parser.add_argument("--vault_name", type=str, help="存储库名称")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(op_logs):
    total = len(op_logs)
    if Offset >= total:
        print(f"查询结果为空\n\n任务列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"id\toperation_type\tstatus\tprovider_id\tvault_id\tvault_name\tcreated_at\n"
    for i in range(Offset, min(total, Offset + 50)):
        log = op_logs[i]
        oid = getattr(log, 'id', '')
        operation_type = getattr(log, 'operation_type', '')
        status = getattr(log, 'status', '')
        provider_id = getattr(log, 'provider_id', '')
        vault_id = getattr(log, 'vault_id', '')
        vault_name = getattr(log, 'vault_name', '')
        created_at = getattr(log, 'created_at', '')
        output += f"{oid}\t{operation_type}\t{status}\t{provider_id}\t{vault_id}\t{vault_name}\t{created_at}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n任务列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
        if end + 1 < total:
            output += f"可以使用 --offset={end + 1} 参数继续获取后续数据"
    print(output)


try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ListOpLogsRequest()
    request.limit = args.limit
    if args.end_time:
        request.end_time = args.end_time
    if args.operation_type:
        request.operation_type = args.operation_type
    if args.provider_id:
        request.provider_id = args.provider_id
    if args.resource_id:
        request.resource_id = args.resource_id
    if args.resource_name:
        request.resource_name = args.resource_name
    if args.start_time:
        request.start_time = args.start_time
    if args.status:
        request.status = args.status
    if args.vault_id:
        request.vault_id = args.vault_id
    if args.vault_name:
        request.vault_name = args.vault_name
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    response = client.list_op_logs(request)
    op_logs = getattr(response, 'operation_logs', []) or []
    count = getattr(response, 'count', 0)

    if not op_logs:
        print(f"没有找到任务(区域: {Region})")
        exit(0)

    render(op_logs)
except Exception as e:
    print(f"cbr.list_op_logs 查询失败: {e}")
    exit(1)
