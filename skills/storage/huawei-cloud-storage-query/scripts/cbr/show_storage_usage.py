import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowStorageUsageRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 CBR 存储使用情况")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--limit", type=int, help="返回结果个数限制")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
parser.add_argument("--resource_id", type=str, help="资源ID")
parser.add_argument("--resource_type", type=str, help="资源类型")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(storage_usage, resource_count):
    total = len(storage_usage)
    if Offset >= total:
        print(f"查询结果为空\n\n存储使用列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"resource_count: {resource_count}\n\n"
    output += f"resource_id\tresource_name\tresource_type\tbackup_count\tbackup_size(GB)\tbackup_size_multiaz\n"
    for i in range(Offset, min(total, Offset + 50)):
        su = storage_usage[i]
        resource_id = getattr(su, 'resource_id', '')
        resource_name = getattr(su, 'resource_name', '')
        resource_type = getattr(su, 'resource_type', '')
        backup_count = getattr(su, 'backup_count', 0)
        backup_size = getattr(su, 'backup_size', 0)
        backup_size_multiaz = getattr(su, 'backup_size_multiaz', 0)
        output += f"{resource_id}\t{resource_name}\t{resource_type}\t{backup_count}\t{backup_size}\t{backup_size_multiaz}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n存储使用列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    request = ShowStorageUsageRequest()
    if args.limit:
        request.limit = args.limit
    if args.resource_id:
        request.resource_id = args.resource_id
    if args.resource_type:
        request.resource_type = args.resource_type

    response = client.show_storage_usage(request)
    resource_count = getattr(response, 'resource_count', 0)
    storage_usage = getattr(response, 'storage_usage', []) or []

    if not storage_usage:
        print(f"没有找到存储使用信息 (区域: {Region})")
        exit(0)

    render(storage_usage, resource_count)
except Exception as e:
    print(f"cbr.show_storage_usage 查询失败: {e}")
    exit(1)
