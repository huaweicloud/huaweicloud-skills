import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ShowWidgetRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询仪表盘组件详情")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--widget_id", type=str, required=True, help="监控视图ID，以wg开头，长度24，可通过 list_dashboard_widgets.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowWidgetRequest()
    request.widget_id = args.widget_id

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.show_widget(request)

    widget_id = getattr(response, 'widget_id', '')
    title = getattr(response, 'title', '')
    view = getattr(response, 'view', '')
    unit = getattr(response, 'unit', '')

    output = "监控视图详情:\n"
    output += f"视图ID: {widget_id}\n"
    output += f"标题: {title}\n"
    output += f"图表类型: {view}\n"
    output += f"单位: {unit}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.show_widget 查询失败: {e}")
    exit(1)
