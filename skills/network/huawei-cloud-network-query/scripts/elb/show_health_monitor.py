import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowHealthMonitorRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 健康检查详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--healthmonitor_id", type=str, required=True, help="健康检查 ID（必填），可通过 list_health_monitors.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ShowHealthMonitorRequest()
    request.healthmonitor_id = args.healthmonitor_id
    response = client.show_health_monitor(request)
    item = response.healthmonitor
    if not item:
        print(f"没有找到健康检查")
        exit(0)

    # 输出详情
    output = f"id\tname\ttype\tdelay\ttimeout\tmax_retries\tmax_retries_down\tadmin_state_up\tmonitor_port\tdomain_name\turl_path\thttp_method\texpected_codes\n"
    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    type = getattr(item, 'type', '')
    delay = getattr(item, 'delay', '')
    timeout = getattr(item, 'timeout', '')
    max_retries = getattr(item, 'max_retries', '')
    max_retries_down = getattr(item, 'max_retries_down', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    monitor_port = getattr(item, 'monitor_port', '')
    domain_name = getattr(item, 'domain_name', '')
    url_path = getattr(item, 'url_path', '')
    http_method = getattr(item, 'http_method', '')
    expected_codes = getattr(item, 'expected_codes', '')
    output += f"{id}\t{name}\t{type}\t{delay}\t{timeout}\t{max_retries}\t{max_retries_down}\t{admin_state_up}\t{monitor_port}\t{domain_name}\t{url_path}\t{http_method}\t{expected_codes}\n"
    print(output)
except Exception as e:
    print(f"elb.show_health_monitor 查询失败: {e}")
    exit(1)
