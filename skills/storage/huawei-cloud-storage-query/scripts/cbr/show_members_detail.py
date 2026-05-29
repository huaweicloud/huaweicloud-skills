import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowMembersDetailRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 CBR 备份成员列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--backup_id", type=str, required=True, help="备份ID，可通过 list_backups.py 获取")
parser.add_argument("--dest_project_id", type=str, help="接受备份恢复的目标项目ID")
parser.add_argument("--image_id", type=str, help="接受备份共享的镜像ID")
parser.add_argument("--status", type=str, help="状态")
parser.add_argument("--vault_id", type=str, help="存储库ID")
parser.add_argument("--limit", type=int, help="返回结果个数限制")
parser.add_argument("--marker", type=str, help="分页标记")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
parser.add_argument("--sort", type=str, help="排序")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(members):
    total = len(members)
    if Offset >= total:
        print(f"查询结果为空\n\n成员列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"id\tstatus\tbackup_id\tdest_project_id\tvault_id\tcreated_at\n"
    for i in range(Offset, min(total, Offset + 50)):
        member = members[i]
        mid = getattr(member, 'id', '')
        status = getattr(member, 'status', '')
        backup_id = getattr(member, 'backup_id', '')
        dest_project_id = getattr(member, 'dest_project_id', '')
        vault_id = getattr(member, 'vault_id', '')
        created_at = getattr(member, 'created_at', '')
        output += f"{mid}\t{status}\t{backup_id}\t{dest_project_id}\t{vault_id}\t{created_at}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n成员列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    request = ShowMembersDetailRequest()
    request.backup_id = args.backup_id
    if args.dest_project_id:
        request.dest_project_id = args.dest_project_id
    if args.image_id:
        request.image_id = args.image_id
    if args.status:
        request.status = args.status
    if args.vault_id:
        request.vault_id = args.vault_id
    if args.limit:
        request.limit = args.limit
    if args.marker:
        request.marker = args.marker
    if args.sort:
        request.sort = args.sort

    response = client.show_members_detail(request)
    members = getattr(response, 'members', []) or []
    count = getattr(response, 'count', 0)

    if not members:
        print(f"没有找到备份成员 (区域: {Region})")
        exit(0)

    render(members)
except Exception as e:
    print(f"cbr.show_members_detail 查询失败: {e}")
    exit(1)
