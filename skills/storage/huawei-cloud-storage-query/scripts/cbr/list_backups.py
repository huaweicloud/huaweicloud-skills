import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListBackupsRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 CBR 备份列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--checkpoint_id", type=str, help="还原点ID")
parser.add_argument("--dec", type=bool, help="是否专属")
parser.add_argument("--end_time", type=str, help="结束时间")
parser.add_argument("--image_type", type=str, help="备份类型")
parser.add_argument("--limit", type=int, default=1000, help="返回结果个数限制，默认1000")
parser.add_argument("--marker", type=str, help="分页标记")
parser.add_argument("--name", type=str, help="备份名称")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
parser.add_argument("--resource_az", type=str, help="资源可用区")
parser.add_argument("--resource_id", type=str, help="资源ID")
parser.add_argument("--resource_name", type=str, help="资源名称")
parser.add_argument("--resource_type", type=str, help="资源类型")
parser.add_argument("--sort", type=str, help="排序")
parser.add_argument("--start_time", type=str, help="开始时间")
parser.add_argument("--status", type=str, help="状态")
parser.add_argument("--vault_id", type=str, help="存储库ID，可通过 list_vault.py 获取")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID")
parser.add_argument("--own_type", type=str, help="所属类型")
parser.add_argument("--member_status", type=str, help="成员状态")
parser.add_argument("--parent_id", type=str, help="父备份ID")
parser.add_argument("--used_percent", type=str, help="使用百分比")
parser.add_argument("--show_replication", type=bool, help="是否显示复制")
parser.add_argument("--incremental", type=bool, help="是否增量备份")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(backups):
    total = len(backups)
    if Offset >= total:
        print(f"查询结果为空\n\n备份列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"id\tname\tstatus\tresource_type\tresource_name\tresource_size(GB)\tvault_id\timage_type\tcreated_at\tincremental\n"
    for i in range(Offset, min(total, Offset + 50)):
        backup = backups[i]
        bid = getattr(backup, 'id', '')
        name = getattr(backup, 'name', '')
        status = getattr(backup, 'status', '')
        resource_type = getattr(backup, 'resource_type', '')
        resource_name = getattr(backup, 'resource_name', '')
        resource_size = getattr(backup, 'resource_size', '')
        vault_id = getattr(backup, 'vault_id', '')
        image_type = getattr(backup, 'image_type', '')
        created_at = getattr(backup, 'created_at', '')
        incremental = getattr(backup, 'incremental', '')
        output += f"{bid}\t{name}\t{status}\t{resource_type}\t{resource_name}\t{resource_size}\t{vault_id}\t{image_type}\t{created_at}\t{incremental}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n备份列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    request = ListBackupsRequest()
    request.limit = args.limit
    if args.checkpoint_id:
        request.checkpoint_id = args.checkpoint_id
    if args.dec:
        request.dec = args.dec
    if args.end_time:
        request.end_time = args.end_time
    if args.image_type:
        request.image_type = args.image_type
    if args.marker:
        request.marker = args.marker
    if args.name:
        request.name = args.name
    if args.resource_az:
        request.resource_az = args.resource_az
    if args.resource_id:
        request.resource_id = args.resource_id
    if args.resource_name:
        request.resource_name = args.resource_name
    if args.resource_type:
        request.resource_type = args.resource_type
    if args.sort:
        request.sort = args.sort
    if args.start_time:
        request.start_time = args.start_time
    if args.status:
        request.status = args.status
    if args.vault_id:
        request.vault_id = args.vault_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.own_type:
        request.own_type = args.own_type
    if args.member_status:
        request.member_status = args.member_status
    if args.parent_id:
        request.parent_id = args.parent_id
    if args.used_percent:
        request.used_percent = args.used_percent
    if args.show_replication:
        request.show_replication = args.show_replication
    if args.incremental:
        request.incremental = args.incremental

    response = client.list_backups(request)
    backups = getattr(response, 'backups', []) or []
    count = getattr(response, 'count', 0)

    if not backups:
        print(f"没有找到备份 (区域: {Region})")
        exit(0)

    render(backups)
except Exception as e:
    print(f"cbr.list_backups 查询失败: {e}")
    exit(1)
