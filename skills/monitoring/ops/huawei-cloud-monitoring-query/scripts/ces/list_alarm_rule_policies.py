import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import ListAlarmRulePoliciesRequest, CesClient
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询告警规则绑定的告警策略列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--alarm_id", type=str, required=True, help="告警规则ID，以al开头，后跟22个数字或字母，长度24，可通过 list_alarm_rules.py 获取")
parser.add_argument("--offset", type=int, help="分页偏移量，范围0-10000，默认0")
parser.add_argument("--limit", type=int, default=50, help="分页大小，范围1-100，默认50")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListAlarmRulePoliciesRequest()
    request.alarm_id = args.alarm_id
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_alarm_rule_policies(request)

    policies = getattr(response, 'policies', []) or []
    count = getattr(response, 'count', 0)

    if not policies:
        print("查询结果为空")
        exit(0)

    output = f"告警规则 {args.alarm_id} 绑定的策略列表（共{count}个）:\n"
    output += "指标名称\t命名空间\t维度名称\t聚合方式\t比较运算符\t阈值\t单位\t触发次数\t告警级别\n"
    
    for policy in policies:
        metric_name = getattr(policy, 'metric_name', '')
        namespace = getattr(policy, 'namespace', '')
        dimension_name = getattr(policy, 'dimension_name', '')
        filter = getattr(policy, 'filter', '')
        comparison_operator = getattr(policy, 'comparison_operator', '')
        value = getattr(policy, 'value', '')
        unit = getattr(policy, 'unit', '')
        policy_count = getattr(policy, 'count', '')
        level = getattr(policy, 'level', '')
        output += f"{metric_name}\t{namespace}\t{dimension_name}\t{filter}\t{comparison_operator}\t{value}\t{unit}\t{policy_count}\t{level}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_alarm_rule_policies 查询失败: {e}")
    exit(1)
