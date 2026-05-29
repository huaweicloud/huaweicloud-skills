import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowMemberHealthCheckJobRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 成员健康检查任务详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--job_id", type=str, required=True, help="任务 ID（必填）")
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

    request = ShowMemberHealthCheckJobRequest()
    request.job_id = args.job_id
    response = client.show_member_health_check_job(request)
    item = response.member_check
    if not item:
        print(f"没有找到成员健康检查任务")
        exit(0)

    # 输出详情
    output = f"job_id\tstatus\tlistener_id\tmember_id\tcheck_item_total_num\tcheck_item_finished_num\tcreated_at\tupdated_at\n"
    job_id = getattr(item, 'job_id', '')
    status = getattr(item, 'status', '')
    listener_id = getattr(item, 'listener_id', '')
    member_id = getattr(item, 'member_id', '')
    check_item_total_num = getattr(item, 'check_item_total_num', '')
    check_item_finished_num = getattr(item, 'check_item_finished_num', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output += f"{job_id}\t{status}\t{listener_id}\t{member_id}\t{check_item_total_num}\t{check_item_finished_num}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"elb.show_member_health_check_job 查询失败: {e}")
    exit(1)
