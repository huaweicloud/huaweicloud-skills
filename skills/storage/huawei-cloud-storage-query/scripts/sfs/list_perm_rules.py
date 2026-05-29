import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdksfsturbo.v1 import SFSTurboClient
from huaweicloudsdksfsturbo.v1.model import ListPermRulesRequest
from huaweicloudsdksfsturbo.v1.region.sfsturbo_region import SFSTurboRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询文件系统权限规则列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--share_id", type=str, required=True, help="文件系统ID，可通过 list_shares.py 获取")
parser.add_argument("--limit", type=int, help="查询列表返回元素个数")
parser.add_argument("--offset", type=int, help="查询偏移量")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListPermRulesRequest()
    request.share_id = args.share_id
    if args.limit is not None:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset

    http_config = build_http_config()
    client = SFSTurboClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(SFSTurboRegion.value_of(Region)).build()
    if not client:
        print("无法获取 SFS Turbo 客户端")
        exit(-1)

    response = client.list_perm_rules(request)

    rules = getattr(response, 'rules', []) or []

    if not rules:
        print("查询结果为空")
        exit(0)

    output = f"文件系统 {args.share_id} 的权限规则列表:\n"
    output += "规则ID\tIP CIDR\t读写类型\t用户类型\n"
    
    for rule in rules:
        rule_id = getattr(rule, 'id', '')
        ip_cidr = getattr(rule, 'ip_cidr', '')
        rw_type = getattr(rule, 'rw_type', '')
        user_type = getattr(rule, 'user_type', '')
        output += f"{rule_id}\t{ip_cidr}\t{rw_type}\t{user_type}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"sfs.list_perm_rules 查询失败: {e}")
    exit(1)
