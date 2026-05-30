import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ShowAlarmTemplateRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询告警模板详情")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--alarm_template_id", type=str, required=True, help="告警模板ID，以at开头，可通过 list_alarm_templates.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowAlarmTemplateRequest()
    request.template_id = args.alarm_template_id

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.show_alarm_template(request)

    template_id = getattr(response, 'template_id', '')
    template_name = getattr(response, 'template_name', '')
    template_type = getattr(response, 'template_type', '')
    create_time = getattr(response, 'create_time', '')
    template_description = getattr(response, 'template_description', '')
    policies = getattr(response, 'policies', []) or []

    output = "告警模板详情:\n"
    output += f"模板ID: {template_id}\n"
    output += f"名称: {template_name}\n"
    output += f"类型: {template_type}\n"
    output += f"创建时间: {create_time}\n"
    output += f"描述: {template_description}\n"
    
    if policies:
        output += "策略列表:\n"
        for idx, policy in enumerate(policies, 1):
            metric_name = getattr(policy, 'metric_name', '')
            alarm_level = getattr(policy, 'alarm_level', '')
            namespace = getattr(policy, 'namespace', '')
            output += f"  {idx}. {namespace} - {metric_name} - 级别: {alarm_level}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.show_alarm_template 查询失败: {e}")
    exit(1)
