import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListAlarmRulesRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询告警规则列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--alarm_id", type=str, help="告警规则ID，以al开头，后跟22位字母或数字，长度24")
parser.add_argument("--name", type=str, help="告警规则名称(支持模糊匹配)，长度1-128")
parser.add_argument("--namespace", type=str, help="服务命名空间，格式service.item")
parser.add_argument("--resource_id", type=str, help="告警资源ID，多维度按字母升序逗号分隔，长度0-700")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID，长度36，也可为0或all_granted_eps，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--product_name", type=str, help="云产品名称，如SYS.ECS,instance_id，长度0-128")
parser.add_argument("--resource_level", type=str, help="资源层级，枚举值：product(云产品)/dimension(子维度)")
parser.add_argument("--offset", type=int, help="分页偏移量，范围0-10000，默认0")
parser.add_argument("--limit", type=int, default=50, help="分页大小，范围1-100，默认50")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListAlarmRulesRequest()
    if args.alarm_id:
        request.alarm_id = args.alarm_id
    if args.name:
        request.name = args.name
    if args.namespace:
        request.namespace = args.namespace
    if args.resource_id:
        request.resource_id = args.resource_id
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.product_name:
        request.product_name = args.product_name
    if args.resource_level:
        request.resource_level = args.resource_level
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

    response = client.list_alarm_rules(request)

    alarms = getattr(response, 'alarms', []) or []
    count = getattr(response, 'count', 0)

    if not alarms:
        print("查询结果为空")
        exit(0)

    output = f"告警规则列表（共{count}个）:\n"
    output += "告警ID\t名称\t是否启用\t是否通知\t命名空间\t告警类型\n"
    
    for alarm in alarms:
        alarm_id = getattr(alarm, 'alarm_id', '')
        name = getattr(alarm, 'name', '')
        enabled = getattr(alarm, 'enabled', False)
        notification_enabled = getattr(alarm, 'notification_enabled', False)
        namespace = getattr(alarm, 'namespace', '')
        alarm_type = getattr(alarm, 'type', '')
        output += f"{alarm_id}\t{name}\t{'启用' if enabled else '禁用'}\t{'启用' if notification_enabled else '禁用'}\t{namespace}\t{alarm_type}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_alarm_rules 查询失败: {e}")
    exit(1)
