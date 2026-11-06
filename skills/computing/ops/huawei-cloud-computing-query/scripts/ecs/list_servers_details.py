import argparse
import sys
import os
import csv
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient, ListServersDetailsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 1000  # 服务端单次请求上限
SCRIPT_NAME = os.path.splitext(os.path.basename(__file__))[0]  # 导出文件默认前缀

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 实例详情列表")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--server_id", type=str, help="云服务器 ID（UUID），精确匹配，可逗号分隔多个，如 id1,id2。使用此参数时不能同时使用其他过滤条件")
parser.add_argument("--name", type=str, help="云服务器名称，模糊匹配")
parser.add_argument("--status", type=str, choices=["ACTIVE", "BUILD", "DELETED", "ERROR", "HARD_REBOOT", "MIGRATING", "REBOOT", "RESIZE", "REVERT_RESIZE", "SHELVED", "SHELVED_OFFLOADED", "SHUTOFF", "UNKNOWN", "VERIFY_RESIZE"], help="云服务器状态")
parser.add_argument("--flavor", type=str, help="规格 ID，可通过 list_flavors.py 获取")
parser.add_argument("--ip", type=str, help="IPv4 地址，模糊匹配")
parser.add_argument("--ip_eq", type=str, help="IPv4 地址，精确匹配")
parser.add_argument("--tags", type=str, help="查询 tag 字段中包含该值的云服务器")
parser.add_argument("--not_tags", type=str, help="查询 tag 字段中不包含该值的云服务器")
parser.add_argument("--tag", type=str, action="append", metavar="key=value", help="按标签过滤，格式 key=value，可重复指定，多个标签之间为 AND 关系，例如 --tag env=prod --tag group=web")
parser.add_argument("--not_tag", type=str, action="append", metavar="key=value", help="按标签排除，格式 key=value，可重复指定，多个标签之间为 AND 关系，例如 --not_tag env=test")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目 ID，查询所有可传 all_granted_eps，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--reservation_id", type=str, help="批量创建时返回的预留 ID，用于查询本次批量创建的云服务器")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: vcpus, ram, size；方向可选: asc(升序), desc(降序)。size 为综合规格大小(vCPU×内存GiB)，适合查找整体最小或最大的规格。例如 size:asc 表示按综合规格升序，vcpus:asc 表示按 vCPU 升序，ram:desc 表示按内存降序。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by size:asc --top 5 查找综合规格最小的 5 个 ECS，--sort_by size:desc --top 3 查找综合规格最大的 3 个 ECS")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--export", type=str, choices=["csv", "json"], help="把本次查询结果导出为文件，可选 csv（UTF-8-SIG 编码，Excel 可直接打开）或 json")
parser.add_argument("--export_path", type=str, help="导出文件路径，不传时默认写入当前目录 <脚本名>_<时间戳>.<格式>")
args = parser.parse_args()

Region = args.region


# 解析标签过滤参数（key=value，可重复，多个标签之间为 AND 关系）
def parse_tag_pairs(items, option):
    pairs = []
    for item in items or []:
        if '=' not in item or not item.split('=', 1)[0]:
            print(f"{option} 格式错误，应为 key=value，例如 {option} env=prod，可重复指定多个标签")
            exit(1)
        pairs.append(item)
    return ','.join(pairs)


# 参数校验
if args.tag and args.tags:
    print("--tag 与 --tags 不能同时使用：--tag 按 key=value 标签过滤（可重复），--tags 查询 tag 字段中包含该值的云服务器")
    exit(1)

if args.not_tag and args.not_tags:
    print("--not_tag 与 --not_tags 不能同时使用：--not_tag 按 key=value 标签排除（可重复），--not_tags 查询 tag 字段中不包含该值的云服务器")
    exit(1)

if args.export_path and not args.export:
    print("--export_path 需要与 --export 配合使用，例如 --export csv --export_path ./servers.csv")
    exit(1)

if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by vcpus:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('vcpus', 'ram', 'size') or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: vcpus, ram, size；方向可选: asc, desc。例如 size:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 标签过滤参数，多个标签拼成 key1=value1,key2=value2（对应 ECS API 的 tags / not_tags 查询参数）
tag_filter = parse_tag_pairs(args.tag, "--tag")
not_tag_filter = parse_tag_pairs(args.not_tag, "--not_tag")

# 判断是否有自定义过滤参数（排序需要全量拉取）
has_custom_filter = args.sort_by is not None


# 取云服务器第一个 IPv4 地址（优先 primary，用于导出）
def pick_ip(server):
    addresses = getattr(server, 'addresses', None)
    if not addresses:
        return ''
    fallback = ''
    for entries in addresses.values():
        for entry in entries or []:
            if str(getattr(entry, 'version', '')) != '4':
                continue
            addr = getattr(entry, 'addr', '') or ''
            if not addr:
                continue
            if getattr(entry, 'primary', False):
                return addr
            if not fallback:
                fallback = addr
    return fallback


# 计费模式取值映射：0-按需，1-包周期，2-竞价；空值渲染 '-'，未知值原样透出
CHARGING_MODE_LABELS = {
    '0': '按需',
    '1': '包周期',
    '2': '竞价',
}


def get_charging_mode(server):
    metadata = getattr(server, 'metadata', None)
    if not isinstance(metadata, dict):
        return '-'
    value = metadata.get('charging_mode')
    if value in (None, ''):
        return '-'
    return CHARGING_MODE_LABELS.get(str(value), str(value))


# 采集导出数据（字段与表格展示字段一致，另附 ip）
def collect_export_rows(servers):
    rows = []
    for server in servers:
        flavor = getattr(server, 'flavor', None)
        rows.append({
            "id": getattr(server, 'id', ''),
            "name": getattr(server, 'name', ''),
            "status": getattr(server, 'status', ''),
            "charging_mode": get_charging_mode(server),
            "flavor_id": getattr(flavor, 'id', '') if flavor else '',
            "vcpus": getattr(flavor, 'vcpus', '') if flavor else '',
            "memory(GiB)": str(int(getattr(flavor, 'ram', 0)) // 1024) if flavor and getattr(flavor, 'ram', 0) else '',
            "availability_zone": getattr(server, 'os_ext_a_zavailability_zone', ''),
            "created": getattr(server, 'created', ''),
            "ip": pick_ip(server),
        })
    return rows


# 导出查询结果到 CSV / JSON
def export_servers(servers, export_format, export_path):
    if not export_format or not servers:
        return

    if not export_path:
        export_path = f"{SCRIPT_NAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"

    rows = collect_export_rows(servers)
    if export_format == "csv":
        with open(export_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"已导出 {len(rows)} 条到 {export_path} (格式: {export_format})")


# 渲染
def render(servers, total_count=None, has_more=False, next_marker=None):
    if not servers:
        print("没有找到 ECS")
        return

    output = f"id\tname\tstatus\tcharging_mode\tflavor_id\tvcpus\tmemory(GiB)\tavailability_zone\tcreated\n"
    for server in servers:
        sid = getattr(server, 'id', '')
        name = getattr(server, 'name', '')
        status = getattr(server, 'status', '')
        charging_mode = get_charging_mode(server)
        flavor = getattr(server, 'flavor', None)
        flavor_id = getattr(flavor, 'id', '') if flavor else ''
        vcpus = getattr(flavor, 'vcpus', '') if flavor else ''
        ram_mb = getattr(flavor, 'ram', 0) if flavor else 0
        ram_gib = str(int(ram_mb) // 1024) if ram_mb else ''
        availability_zone = getattr(server, 'os_ext_a_zavailability_zone', '')
        created = getattr(server, 'created', '')
        output += f"{sid}\t{name}\t{status}\t{charging_mode}\t{flavor_id}\t{vcpus}\t{ram_gib}\t{availability_zone}\t{created}\n"

    # 汇总信息
    showing_count = len(servers)

    if total_count is not None:
        output += f"\n共 {total_count} 条 ECS，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --status / --flavor / --ip 等参数缩小查询范围"
        elif total_count > showing_count:
            output += f"\n可使用 --name / --status / --flavor / --ip 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --name / --status / --flavor / --ip 等参数缩小查询范围"
        else:
            output += f"\n可使用 --name / --status / --flavor / --ip 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条 ECS"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()
    # 未指定 project_id 则自动获取
    if not args.project_id:
        args.project_id = get_project_id(Region, AK, SK, SecurityToken)
        if not args.project_id:
            print(f"无法获取项目 ID (region={Region})，请检查凭据或手动指定 --project_id")
            exit(-1)


    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    # 构建请求
    request = ListServersDetailsRequest()
    if args.server_id:
        request.server_id = args.server_id
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status
    if args.flavor:
        request.flavor = args.flavor
    if args.ip:
        request.ip = args.ip
    if args.ip_eq:
        request.ip_eq = args.ip_eq
    if tag_filter:
        request.tags = tag_filter
    elif args.tags:
        request.tags = args.tags
    if not_tag_filter:
        request.not_tags = not_tag_filter
    elif args.not_tags:
        request.not_tags = args.not_tags
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.reservation_id:
        request.reservation_id = args.reservation_id

    if has_custom_filter:
        # 有自定义过滤参数（排序）：全量拉取 + 本地排序
        all_servers = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_servers_details(request)
            servers = response.servers
            if not servers:
                break
            if marker and all_servers and getattr(servers[0], 'id', None) == getattr(all_servers[-1], 'id', None):
                break
            all_servers.extend(servers)
            if len(servers) < API_LIMIT:
                break
            marker = servers[-1].id
            if not marker:
                break

        if not all_servers:
            print("没有找到 ECS")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'vcpus':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'vcpus', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'ram':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'ram', 0) or 0), reverse=(sort_dir == 'desc'))
            elif sort_field == 'size':
                all_servers.sort(key=lambda s: int(getattr(getattr(s, 'flavor', None), 'vcpus', 0) or 0) * (int(getattr(getattr(s, 'flavor', None), 'ram', 0) or 0) // 1024), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_servers = all_servers[:args.top]

        # 渲染结果（全量已拉取，无需翻页）
        render(all_servers, total_count=len(all_servers))

        # 导出结果（全量拉取时为本次拉取到的全部数据）
        export_servers(all_servers, args.export, args.export_path)
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        # 只做一次查询
        response = client.list_servers_details(request)
        total_count = getattr(response, 'count', None) or getattr(response, 'total_count', None)
        servers = response.servers

        if not servers:
            print(f"没有找到 ECS (区域: {Region})")
            exit(0)

        # 判断是否还有更多数据，计算 next_marker
        next_marker = None
        if total_count is not None:
            has_more = total_count > PAGE_SIZE
        else:
            has_more = len(servers) > PAGE_SIZE

        if has_more and len(servers) > PAGE_SIZE:
            next_marker = str(servers[PAGE_SIZE - 1].id)

        # 只展示前 PAGE_SIZE 条
        display_servers = servers[:PAGE_SIZE]

        # 渲染结果
        render(display_servers, total_count=total_count, has_more=has_more, next_marker=next_marker)

        # 导出结果（常规查询为当前页展示的数据，最多 PAGE_SIZE 条）
        export_servers(display_servers, args.export, args.export_path)
except Exception as e:
    print(f"ecs.list 查询失败: {e}")
    exit(1)
