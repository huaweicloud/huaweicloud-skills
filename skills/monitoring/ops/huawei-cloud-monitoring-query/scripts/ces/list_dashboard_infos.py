import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListDashboardInfosRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询仪表盘列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--enterprise_id", type=str, help="企业项目ID，长度36，也可为0(默认企业项目)或all_granted_eps(所有企业项目)")
parser.add_argument("--is_favorite", type=str, help="监控看板是否收藏，枚举值：true(收藏)/false(未收藏)。填此参数时enterprise_id必填")
parser.add_argument("--dashboard_name", type=str, help="监控看板名称(支持模糊匹配)，长度1-128，只允许中文、英文、数字0-9、_和-")
parser.add_argument("--dashboard_id", type=str, help="监控看板ID，以db开头，包含22个字母和数字，长度24")
parser.add_argument("--dashboard_type", type=str, help="监控看板类型，枚举值：monitor_dashboard(监控大盘)/other(自定义看板)")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListDashboardInfosRequest()
    if args.enterprise_id:
        request.enterprise_id = args.enterprise_id
    if args.is_favorite:
        request.is_favorite = args.is_favorite.lower() == 'true'
    if args.dashboard_name:
        request.dashboard_name = args.dashboard_name
    if args.dashboard_id:
        request.dashboard_id = args.dashboard_id
    if args.dashboard_type:
        request.dashboard_type = args.dashboard_type

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_dashboard_infos(request)

    dashboards = getattr(response, 'dashboards', []) or []

    if not dashboards:
        print("查询结果为空")
        exit(0)

    output = f"仪表盘列表（共{len(dashboards)}个）:\n"
    output += "仪表盘ID\t名称\t是否收藏\t企业项目ID\t创建时间\n"
    
    for dashboard in dashboards:
        dashboard_id = getattr(dashboard, 'dashboard_id', '')
        dashboard_name = getattr(dashboard, 'dashboard_name', '')
        is_favorite = getattr(dashboard, 'is_favorite', False)
        enterprise_id = getattr(dashboard, 'enterprise_id', '')
        create_time = getattr(dashboard, 'create_time', '')
        output += f"{dashboard_id}\t{dashboard_name}\t{'是' if is_favorite else '否'}\t{enterprise_id}\t{create_time}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_dashboard_infos 查询失败: {e}")
    exit(1)
