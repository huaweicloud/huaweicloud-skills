import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListL7RulesRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 七层转发规则列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--l7policy_id", type=str, required=True, help="七层转发策略ID，可通过 list_l7_policies.py 获取")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--id", type=str, nargs="+", help="转发规则ID，支持多值查询")
parser.add_argument("--type", type=str, nargs="+", help="匹配类别，支持多值查询，取值: HOST_NAME PATH METHOD HEADER QUERY_STRING SOURCE_IP COOKIE")
parser.add_argument("--compare_type", type=str, nargs="+", help="转发匹配方式，支持多值查询，取值: EQUAL_TO REGEX STARTS_WITH")
parser.add_argument("--value", type=str, nargs="+", help="匹配内容的值，支持多值查询")
parser.add_argument("--key", type=str, nargs="+", help="匹配内容的键值，支持多值查询")
parser.add_argument("--provisioning_status", type=str, nargs="+", help="转发规则的配置状态，支持多值查询，取值: ACTIVE PENDING_CREATE ERROR")
parser.add_argument("--invert", type=bool, help="是否反向匹配")
parser.add_argument("--admin_state_up", type=bool, help="转发规则的管理状态")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="资源所属的企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ListL7RulesRequest()
    request.l7policy_id = args.l7policy_id
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.type:
        request.type = args.type
    if args.compare_type:
        request.compare_type = args.compare_type
    if args.value:
        request.value = args.value
    if args.key:
        request.key = args.key
    if args.provisioning_status:
        request.provisioning_status = args.provisioning_status
    if args.invert is not None:
        request.invert = args.invert
    if args.admin_state_up is not None:
        request.admin_state_up = args.admin_state_up
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id

    response = client.list_l7_rules(request)
    rules = response.rules

    if not rules:
        print(f"没有找到七层规则 (区域: {Region})")
        exit(0)

    # Response 有 page_info，使用 page_info.next_marker 判断分页
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(rules) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(rules[PAGE_SIZE - 1], 'id', ''))

    display_rules = rules[:PAGE_SIZE]

    output = f"id\ttype\tcompare_type\tvalue\tkey\tinvert\tprovisioning_status\n"
    for item in display_rules:
        id = getattr(item, 'id', '')
        rule_type = getattr(item, 'type', '')
        compare_type = getattr(item, 'compare_type', '')
        value = getattr(item, 'value', '')
        key = getattr(item, 'key', '')
        invert = getattr(item, 'invert', '')
        provisioning_status = getattr(item, 'provisioning_status', '')
        output += f"{id}\t{rule_type}\t{compare_type}\t{value}\t{key}\t{invert}\t{provisioning_status}\n"

    if has_more:
        output += f"\n当前返回 {len(display_rules)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_rules)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_l7_rules 查询失败: {e}")
    exit(1)
