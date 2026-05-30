import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowVaultRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 存储库详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vault_id", type=str, required=True, help="存储库ID，可通过 list_vault.py 获取")
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

    request = ShowVaultRequest()
    request.vault_id = args.vault_id
    response = client.show_vault(request)
    vault = getattr(response, 'vault', None)

    if not vault:
        print(f"没有找到存储库 (区域: {Region}, 存储库 ID: {args.vault_id})")
        exit(0)

    output = ""
    output += f"id: {getattr(vault, 'id', '')}\n"
    output += f"name: {getattr(vault, 'name', '')}\n"
    output += f"description: {getattr(vault, 'description', '')}\n"
    output += f"project_id: {getattr(vault, 'project_id', '')}\n"
    output += f"provider_id: {getattr(vault, 'provider_id', '')}\n"
    output += f"enterprise_project_id: {getattr(vault, 'enterprise_project_id', '')}\n"
    output += f"user_id: {getattr(vault, 'user_id', '')}\n"
    output += f"created_at: {getattr(vault, 'created_at', '')}\n"
    output += f"availability_zone: {getattr(vault, 'availability_zone', '')}\n"
    output += f"auto_bind: {getattr(vault, 'auto_bind', '')}\n"
    output += f"auto_expand: {getattr(vault, 'auto_expand', '')}\n"
    output += f"smn_notify: {getattr(vault, 'smn_notify', '')}\n"
    output += f"threshold: {getattr(vault, 'threshold', '')}\n"
    output += f"sys_lock_source_service: {getattr(vault, 'sys_lock_source_service', '')}\n"
    output += f"locked: {getattr(vault, 'locked', '')}\n"

    billing = getattr(vault, 'billing', None)
    if billing:
        output += f"\nbilling:\n"
        output += f"  charging_mode: {getattr(billing, 'charging_mode', '')}\n"
        output += f"  cloud_type: {getattr(billing, 'cloud_type', '')}\n"
        output += f"  consistent_level: {getattr(billing, 'consistent_level', '')}\n"
        output += f"  object_type: {getattr(billing, 'object_type', '')}\n"
        output += f"  protect_type: {getattr(billing, 'protect_type', '')}\n"
        output += f"  size: {getattr(billing, 'size', '')}\n"
        output += f"  used: {getattr(billing, 'used', '')}\n"
        output += f"  allocated: {getattr(billing, 'allocated', '')}\n"
        output += f"  status: {getattr(billing, 'status', '')}\n"
        output += f"  spec_code: {getattr(billing, 'spec_code', '')}\n"
        output += f"  order_id: {getattr(billing, 'order_id', '')}\n"
        output += f"  product_id: {getattr(billing, 'product_id', '')}\n"
        output += f"  storage_unit: {getattr(billing, 'storage_unit', '')}\n"
        output += f"  frozen_scene: {getattr(billing, 'frozen_scene', '')}\n"
        output += f"  is_multi_az: {getattr(billing, 'is_multi_az', '')}\n"

    bind_rules = getattr(vault, 'bind_rules', None)
    if bind_rules:
        rule_tags = getattr(bind_rules, 'tags', []) or []
        output += f"\nbind_rules:\n"
        if rule_tags:
            output += f"  tags ({len(rule_tags)}):\n"
            for rt in rule_tags:
                output += f"    key: {getattr(rt, 'key', '')}, value: {getattr(rt, 'value', '')}\n"
        else:
            output += f"  tags: []\n"

    resources = getattr(vault, 'resources', []) or []
    if resources:
        output += f"\nresources ({len(resources)}):\n"
        for res in resources:
            output += f"  id: {getattr(res, 'id', '')}\n"
            output += f"  name: {getattr(res, 'name', '')}\n"
            output += f"  type: {getattr(res, 'type', '')}\n"
            output += f"  protect_status: {getattr(res, 'protect_status', '')}\n"
            output += f"  size: {getattr(res, 'size', '')}\n"
            output += f"  backup_size: {getattr(res, 'backup_size', '')}\n"
            output += f"  backup_count: {getattr(res, 'backup_count', '')}\n"
            output += f"  auto_protect: {getattr(res, 'auto_protect', '')}\n"
            extra_info = getattr(res, 'extra_info', None)
            if extra_info:
                exclude_volumes = getattr(extra_info, 'exclude_volumes', []) or []
                include_volumes = getattr(extra_info, 'include_volumes', []) or []
                if exclude_volumes:
                    output += f"  extra_info.exclude_volumes: {', '.join(exclude_volumes)}\n"
                if include_volumes:
                    output += f"  extra_info.include_volumes ({len(include_volumes)}):\n"
                    for iv in include_volumes:
                        output += f"    id: {getattr(iv, 'id', '')}, os_version: {getattr(iv, 'os_version', '')}\n"

    tags = getattr(vault, 'tags', []) or []
    if tags:
        output += f"\ntags ({len(tags)}):\n"
        for tag in tags:
            output += f"  key: {getattr(tag, 'key', '')}, value: {getattr(tag, 'value', '')}\n"

    print(output)
except Exception as e:
    print(f"cbr.show_vault 查询失败: {e}")
    exit(1)
