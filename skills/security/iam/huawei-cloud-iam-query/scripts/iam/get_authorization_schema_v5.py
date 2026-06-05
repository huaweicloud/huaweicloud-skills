import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import GetAuthorizationSchemaV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询授权方案 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--service_code", type=str, required=True, help="服务名称缩写，如 ECS/VPC/IAM 等，可通过 list_registered_services_for_auth_schema_v5.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    request = GetAuthorizationSchemaV5Request()
    request.service_code = args.service_code
    response = client.get_authorization_schema_v5(request)
    item = response
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"version\n"
    version = getattr(item, 'version', '')
    output += f"{version}\n"

    actions = getattr(item, 'actions', None)
    if actions:
        output += f"\nactions ({len(actions)}):\n"
        output += f"name\taccess_level\tpermission_only\n"
        for a in actions:
            name = getattr(a, 'name', '')
            access_level = getattr(a, 'access_level', '')
            permission_only = getattr(a, 'permission_only', '')
            output += f"{name}\t{access_level}\t{permission_only}\n"

    resources = getattr(item, 'resources', None)
    if resources:
        output += f"\nresources ({len(resources)}):\n"
        output += f"type_name\turn_template\n"
        for r in resources:
            type_name = getattr(r, 'type_name', '')
            urn_template = getattr(r, 'urn_template', '')
            output += f"{type_name}\t{urn_template}\n"

    conditions = getattr(item, 'conditions', None)
    if conditions:
        output += f"\nconditions ({len(conditions)}):\n"
        output += f"key\tvalue_type\tmulti_valued\n"
        for c in conditions:
            key = getattr(c, 'key', '')
            value_type = getattr(c, 'value_type', '')
            multi_valued = getattr(c, 'multi_valued', '')
            output += f"{key}\t{value_type}\t{multi_valued}\n"

    operations = getattr(item, 'operations', None)
    if operations:
        output += f"\noperations ({len(operations)}):\n"
        output += f"operation_id\toperation_action\tdependent_actions\n"
        for o in operations:
            operation_id = getattr(o, 'operation_id', '')
            operation_action = getattr(o, 'operation_action', '')
            dependent_actions = getattr(o, 'dependent_actions', [])
            dep_str = ';'.join(dependent_actions) if dependent_actions else ''
            output += f"{operation_id}\t{operation_action}\t{dep_str}\n"
    print(output)
except Exception as e:
    print(f"iam.get_authorization_schema_v5 查询失败: {e}")
    exit(1)
