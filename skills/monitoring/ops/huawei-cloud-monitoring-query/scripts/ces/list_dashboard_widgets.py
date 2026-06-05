import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListDashboardWidgetsRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询仪表盘组件列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--dashboard_id", type=str, required=True, help="监控看板ID，以db开头，包含22个字母和数字，长度24，可通过 list_dashboard_infos.py 获取")
parser.add_argument("--group_id", type=str, help="视图分组ID，以dg开头包含22个字母和数字长度24，或default(不分组)")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListDashboardWidgetsRequest()
    request.dashboard_id = args.dashboard_id
    if args.group_id:
        request.group_id = args.group_id

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_dashboard_widgets(request)

    widgets = getattr(response, 'widgets', []) or []

    if not widgets:
        print("查询结果为空")
        exit(0)

    output = f"监控看板 {args.dashboard_id} 的视图列表:\n"
    output += "视图ID\t标题\t图表类型\t分组ID\t单位\n"
    
    for widget in widgets:
        widget_id = getattr(widget, 'widget_id', '')
        title = getattr(widget, 'title', '')
        view = getattr(widget, 'view', '')
        group_id = getattr(widget, 'group_id', '')
        unit = getattr(widget, 'unit', '')
        output += f"{widget_id}\t{title}\t{view}\t{group_id}\t{unit}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_dashboard_widgets 查询失败: {e}")
    exit(1)
