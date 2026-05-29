import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListPoliciesRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 策略列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--operation_type", type=str, help="策略类型：备份（backup）、复制(replication)")
parser.add_argument("--vault_id", type=str, help="存储库ID，可通过 list_vault.py 获取")
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

    request = ListPoliciesRequest()
    if args.operation_type:
        request.operation_type = args.operation_type
    if args.vault_id:
        request.vault_id = args.vault_id

    response = client.list_policies(request)
    policies = getattr(response, 'policies', []) or []
    count = getattr(response, 'count', 0)

    if not policies:
        print(f"没有找到策略 (区域: {Region})")
        exit(0)

    output = f"id\tname\tenabled\toperation_type\tassociated_vaults_count\n"
    for policy in policies:
        pid = getattr(policy, 'id', '')
        name = getattr(policy, 'name', '')
        enabled = getattr(policy, 'enabled', '')
        operation_type = getattr(policy, 'operation_type', '')
        associated_vaults = getattr(policy, 'associated_vaults', []) or []
        output += f"{pid}\t{name}\t{enabled}\t{operation_type}\t{len(associated_vaults)}\n"
    print(output)
except Exception as e:
    print(f"cbr.list_policies 查询失败: {e}")
    exit(1)
