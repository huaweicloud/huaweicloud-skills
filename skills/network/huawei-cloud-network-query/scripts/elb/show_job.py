import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowJobRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 任务详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--job_id", type=str, required=True, help="任务 ID（必填），可通过 list_jobs.py 获取")
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

    request = ShowJobRequest()
    request.job_id = args.job_id
    response = client.show_job(request)
    item = response.job
    if not item:
        print(f"没有找到任务")
        exit(0)

    # 输出详情
    output = f"job_id\tjob_type\tstatus\tresource_id\terror_code\terror_msg\tbegin_time\tend_time\n"
    job_id = getattr(item, 'job_id', '')
    job_type = getattr(item, 'job_type', '')
    status = getattr(item, 'status', '')
    resource_id = getattr(item, 'resource_id', '')
    error_code = getattr(item, 'error_code', '')
    error_msg = getattr(item, 'error_msg', '')
    begin_time = getattr(item, 'begin_time', '')
    end_time = getattr(item, 'end_time', '')
    output += f"{job_id}\t{job_type}\t{status}\t{resource_id}\t{error_code}\t{error_msg}\t{begin_time}\t{end_time}\n"
    print(output)
except Exception as e:
    print(f"elb.show_job 查询失败: {e}")
    exit(1)
