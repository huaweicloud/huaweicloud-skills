import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListOneClickAlarmRulesRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询一键告警规则列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--one_click_alarm_id", type=str, required=True, help="一键告警ID，以服务名+OneClickAlarm命名，可通过 list_one_click_alarms.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListOneClickAlarmRulesRequest()
    request.one_click_alarm_id = args.one_click_alarm_id

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_one_click_alarm_rules(request)

    alarms = getattr(response, 'alarms', []) or []

    if not alarms:
        print("查询结果为空")
        exit(0)

    output = f"一键告警 {args.one_click_alarm_id} 的告警规则列表:\n"
    output += "告警ID\t名称\t是否启用\n"
    
    for alarm in alarms:
        alarm_id = getattr(alarm, 'alarm_id', '')
        name = getattr(alarm, 'name', '')
        enabled = getattr(alarm, 'enabled', False)
        output += f"{alarm_id}\t{name}\t{'启用' if enabled else '禁用'}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_one_click_alarm_rules 查询失败: {e}")
    exit(1)
