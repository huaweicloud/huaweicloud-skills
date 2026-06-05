import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListAlarmTemplateAssociationAlarmsRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询告警模板关联的告警规则列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--alarm_template_id", type=str, required=True, help="告警模板ID，以at开头，后跟字母、数字，长度2-64，可通过 list_alarm_templates.py 获取")
parser.add_argument("--offset", type=int, help="分页偏移量，范围0-10000，默认0")
parser.add_argument("--limit", type=int, default=100, help="分页大小，范围1-100，默认100")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListAlarmTemplateAssociationAlarmsRequest()
    request.template_id = args.alarm_template_id
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

    response = client.list_alarm_template_association_alarms(request)

    alarms = getattr(response, 'alarms', []) or []
    count = getattr(response, 'count', 0)

    if not alarms:
        print("查询结果为空")
        exit(0)

    output = f"告警模板 {args.alarm_template_id} 关联的告警规则列表（共{count}个）:\n"
    output += "告警ID\t名称\t描述\n"
    
    for alarm in alarms:
        alarm_id = getattr(alarm, 'alarm_id', '')
        name = getattr(alarm, 'name', '')
        description = getattr(alarm, 'description', '')
        output += f"{alarm_id}\t{name}\t{description}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_alarm_template_association_alarms 查询失败: {e}")
    exit(1)
