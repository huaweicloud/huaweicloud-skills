import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListAlarmTemplatesRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询告警模板列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--offset", type=int, help="分页偏移量，范围0-10000，默认0")
parser.add_argument("--limit", type=int, default=100, help="分页大小，范围1-100，默认100")
parser.add_argument("--namespace", type=str, help="服务命名空间，格式service.item，长度3-32")
parser.add_argument("--dim_name", type=str, help="资源维度名称，多维度用逗号分隔，每个维度最大长度32，总长度1-131")
parser.add_argument("--template_type", type=str, help="模板类型，枚举值：system/custom/system_event/custom_event/system_custom_event")
parser.add_argument("--template_name", type=str, help="告警模板名称，以字母或汉字开头，长度1-128，支持模糊匹配")
parser.add_argument("--product_name", type=str, help="产品层级跨维规则产品名称，如SYS.ECS,instance_id，长度0-128")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListAlarmTemplatesRequest()
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit
    if args.namespace:
        request.namespace = args.namespace
    if args.dim_name:
        request.dim_name = args.dim_name
    if args.template_type:
        request.template_type = args.template_type
    if args.template_name:
        request.template_name = args.template_name
    if args.product_name:
        request.product_name = args.product_name

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_alarm_templates(request)

    alarm_templates = getattr(response, 'alarm_templates', []) or []
    count = getattr(response, 'count', 0)

    if not alarm_templates:
        print("查询结果为空")
        exit(0)

    output = f"告警模板列表（共{count}个）:\n"
    output += "模板ID\t名称\t类型\t创建时间\t描述\n"
    
    for template in alarm_templates:
        template_id = getattr(template, 'template_id', '')
        template_name = getattr(template, 'template_name', '')
        template_type = getattr(template, 'template_type', '')
        create_time = getattr(template, 'create_time', '')
        template_description = getattr(template, 'template_description', '')
        output += f"{template_id}\t{template_name}\t{template_type}\t{create_time}\t{template_description}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_alarm_templates 查询失败: {e}")
    exit(1)
