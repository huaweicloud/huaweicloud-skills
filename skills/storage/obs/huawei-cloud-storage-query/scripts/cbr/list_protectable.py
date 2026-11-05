import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListProtectableRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

# protectable_type 白名单：无效类型在发送请求前直接拦截，返回参数错误而非服务端 500
VALID_PROTECTABLE_TYPES = ("server", "disk", "turbo", "workspace", "workspace_v2")

parser = argparse.ArgumentParser(description="查询 CBR 可保护资源列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--protectable_type", type=str, required=True, help=f"可保护资源类型，取值: {', '.join(VALID_PROTECTABLE_TYPES)}")
parser.add_argument("--limit", type=int, default=1000, help="返回结果个数限制，默认1000")
parser.add_argument("--marker", type=str, help="分页标记")
parser.add_argument("--name", type=str, help="资源名称")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
parser.add_argument("--status", type=str, help="状态")
parser.add_argument("--id", type=str, help="根据资源id过滤")
parser.add_argument("--server_id", type=str, help="云服务器ID")
parser.add_argument("--retries", type=int, default=3, help="服务端 500 时自动重试次数，默认 3")
parser.add_argument("--format", type=str, choices=["text", "json"], default="text", help="输出格式，默认 text")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数预校验：无效 protectable_type 立即报错（400 级参数错误），不进入 API 调用
if args.protectable_type not in VALID_PROTECTABLE_TYPES:
    print(f"参数错误: 无效的 protectable_type '{args.protectable_type}'，合法取值: {', '.join(VALID_PROTECTABLE_TYPES)}")
    exit(2)

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(instances):
    total = len(instances)
    if Offset >= total:
        print(f"查询结果为空\n\n可保护资源列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    if args.format == "json":
        items = []
        for i in range(Offset, min(total, Offset + 50)):
            inst = instances[i]
            items.append({
                "id": getattr(inst, 'id', ''),
                "name": getattr(inst, 'name', ''),
                "type": getattr(inst, 'type', ''),
                "size": getattr(inst, 'size', ''),
                "status": getattr(inst, 'status', '')
            })
        print(json.dumps({"total": total, "offset": Offset, "items": items}, ensure_ascii=False))
        exit(0)

    output = f"id\tname\ttype\tsize(GB)\tstatus\n"
    for i in range(Offset, min(total, Offset + 50)):
        inst = instances[i]
        iid = getattr(inst, 'id', '')
        name = getattr(inst, 'name', '')
        itype = getattr(inst, 'type', '')
        size = getattr(inst, 'size', '')
        status = getattr(inst, 'status', '')
        output += f"{iid}\t{name}\t{itype}\t{size}\t{status}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n可保护资源列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    request = ListProtectableRequest()
    request.protectable_type = args.protectable_type
    request.limit = args.limit
    if args.marker:
        request.marker = args.marker
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status
    if args.id:
        request.id = args.id
    if args.server_id:
        request.server_id = args.server_id

    # 服务端 500(The system is busy) 时自动重试
    response = None
    last_error = None
    for attempt in range(max(1, args.retries + 1)):
        try:
            response = client.list_protectable(request)
            last_error = None
            break
        except Exception as retry_e:
            last_error = retry_e
            if attempt < args.retries:
                time.sleep(2 * (attempt + 1))

    if last_error is not None:
        raise last_error

    instances = getattr(response, 'instances', []) or []

    if not instances:
        print(f"没有找到可保护资源 (区域: {Region})")
        exit(0)

    render(instances)
except Exception as e:
    print(f"cbr.list_protectable 查询失败: {e}")
    exit(1)