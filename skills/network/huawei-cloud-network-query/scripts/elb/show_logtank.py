import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowLogtankRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 云日志详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--logtank_id", type=str, required=True, help="云日志 ID（必填），可通过 list_logtanks.py 获取")
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

    request = ShowLogtankRequest()
    request.logtank_id = args.logtank_id
    response = client.show_logtank(request)
    item = response.logtank
    if not item:
        print(f"没有找到云日志")
        exit(0)

    # 输出详情
    output = f"id\tloadbalancer_id\tlog_group_id\tlog_topic_id\tproject_id\n"
    id = getattr(item, 'id', '')
    loadbalancer_id = getattr(item, 'loadbalancer_id', '')
    log_group_id = getattr(item, 'log_group_id', '')
    log_topic_id = getattr(item, 'log_topic_id', '')
    project_id = getattr(item, 'project_id', '')
    output += f"{id}\t{loadbalancer_id}\t{log_group_id}\t{log_topic_id}\t{project_id}\n"
    print(output)
except Exception as e:
    print(f"elb.show_logtank 查询失败: {e}")
    exit(1)
