import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id, format_api_error, format_empty_result
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowServerRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器详情")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, help="区域，不传时回退环境变量 HW_REGION_NAME（默认 cn-north-4）")
parser.add_argument("--server_id", type=str, required=True, help="服务器 ID（UUID），可通过 list_servers_details.py 获取")
parser.add_argument("--with_related", "--with-related", dest="with_related", action="store_true", help="附带整机关联资源视图：内网 IP、弹性 IP、安全组、已挂载云硬盘")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


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
        print(f"无法获取 ECS 客户端")
        exit(-1)

    request = ShowServerRequest()
    request.server_id = args.server_id
    response = client.show_server(request)
    server = response.server

    if not server:
        print(format_empty_result(
            "ECS 服务器", Region, args.project_id, f"服务器 ID: {args.server_id}",
            hints=[
                "确认服务器 ID 正确（可由 list_servers_details.py 获取）",
                "确认服务器属于当前 --region 对应的项目（ECS 资源不跨区域）",
                "确认账号具备 ecs:servers:get 权限",
            ]))
        exit(0)

    # 渲染结果
    output = ""
    output += f"id: {getattr(server, 'id', '')}\n"
    output += f"name: {getattr(server, 'name', '')}\n"
    output += f"status: {getattr(server, 'status', '')}\n"
    flavor = getattr(server, 'flavor', None)
    if flavor:
        output += f"flavor: {getattr(flavor, 'id', '')}\n"
        output += f"flavor_name: {getattr(flavor, 'name', '')}\n"
        output += f"vcpus: {getattr(flavor, 'vcpus', '')}\n"
        ram_mb = getattr(flavor, 'ram', 0)
        ram_gib = str(int(ram_mb) // 1024) if ram_mb else ''
        output += f"ram(GiB): {ram_gib}\n"
        output += f"disk: {getattr(flavor, 'disk', '')}\n"
        gpus = getattr(flavor, 'gpus', None) or []
        output += "gpus: " + (';'.join(f"{getattr(g, 'name', '')}x{getattr(g, 'count', '')}" for g in gpus) if gpus else '') + "\n"
    else:
        output += "flavor: \n"
        output += "flavor_name: \n"
        output += "vcpus: \n"
        output += "ram(GiB): \n"
        output += "disk: \n"
        output += "gpus: \n"
    image = getattr(server, 'image', None)
    if image:
        output += f"image: {getattr(image, 'id', '')}\n"
    else:
        output += f"image: \n"
    output += f"created: {getattr(server, 'created', '')}\n"
    output += f"updated: {getattr(server, 'updated', '')}\n"

    if args.with_related:
        fixed_ips, floating_ips = [], []
        for entries in (getattr(server, 'addresses', None) or {}).values():
            for entry in entries or []:
                addr = getattr(entry, 'addr', '') or ''
                if not addr:
                    continue
                if str(getattr(entry, 'os_ext_ip_stype', '') or '').lower() == 'floating':
                    floating_ips.append(addr)
                else:
                    fixed_ips.append(addr)
        groups = [getattr(g, 'name', '') or getattr(g, 'id', '')
                  for g in (getattr(server, 'security_groups', None) or [])]
        volumes = [getattr(v, 'id', '') for v in (getattr(server, 'os_extended_volumesvolumes_attached', None) or [])]
        output += "\n关联资源:\n"
        output += f"  fixed_ips: {','.join(fixed_ips) or '-'}\n"
        output += f"  floating_ips: {','.join(floating_ips) or '-'}\n"
        output += f"  security_groups: {','.join(groups) or '-'}\n"
        output += f"  volumes: {','.join(volumes) or '-'}\n"
        output += "  提示: 云硬盘快照/磁盘类型等 EVS 详情请使用存储类查询技能（详见 SKILL.md Related Skills）\n"
    print(output)
except Exception as e:
    print(format_api_error(e, "ECS 服务器详情查询", Region, args.project_id, f"服务器 ID: {args.server_id}"))
    exit(1)
