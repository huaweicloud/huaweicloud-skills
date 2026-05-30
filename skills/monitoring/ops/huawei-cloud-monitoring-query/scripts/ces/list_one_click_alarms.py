import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListOneClickAlarmsRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询一键告警列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListOneClickAlarmsRequest()

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_one_click_alarms(request)

    one_click_alarms = getattr(response, 'one_click_alarms', []) or []

    if not one_click_alarms:
        print("查询结果为空")
        exit(0)

    output = "一键告警列表:\n"
    output += "一键告警ID\t命名空间\t描述\t是否启用\n"
    
    for alarm in one_click_alarms:
        one_click_alarm_id = getattr(alarm, 'one_click_alarm_id', '')
        namespace = getattr(alarm, 'namespace', '')
        description = getattr(alarm, 'description', '')
        enabled = getattr(alarm, 'enabled', False)
        output += f"{one_click_alarm_id}\t{namespace}\t{description}\t{'启用' if enabled else '禁用'}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_one_click_alarms 查询失败: {e}")
    exit(1)
