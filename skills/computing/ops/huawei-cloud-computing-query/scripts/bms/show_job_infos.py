import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkbms.v1 import BmsClient
from huaweicloudsdkbms.v1.model import ShowJobInfosRequest
from huaweicloudsdkbms.v1.region.bms_region import BmsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询异步任务状态")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--job_id", type=str, required=True, help="异步任务ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = BmsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)
    ).with_region(BmsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 BMS 客户端")
        exit(-1)

    # 构建请求
    request = ShowJobInfosRequest()
    request.job_id = args.job_id

    response = client.show_job_infos(request)

    # 渲染
    output = ""
    output += f"job_id: {getattr(response, 'job_id', '')}\n"
    output += f"status: {getattr(response, 'status', '')}\n"
    output += f"job_type: {getattr(response, 'job_type', '')}\n"
    output += f"begin_time: {getattr(response, 'begin_time', '')}\n"
    output += f"end_time: {getattr(response, 'end_time', '')}\n"
    output += f"error_code: {getattr(response, 'error_code', '')}\n"
    output += f"fail_reason: {getattr(response, 'fail_reason', '')}\n"
    output += f"message: {getattr(response, 'message', '')}\n"
    output += f"code: {getattr(response, 'code', '')}\n"

    entities = getattr(response, 'entities', None)
    if entities:
        output += f"sub_jobs_total: {getattr(entities, 'sub_jobs_total', 0)}\n"
        sub_jobs = getattr(entities, 'sub_jobs', None) or []
        if sub_jobs:
            output += f"sub_jobs:\n"
            for job in sub_jobs:
                output += f"  - job_id: {getattr(job, 'job_id', '')}, status: {getattr(job, 'status', '')}, job_type: {getattr(job, 'job_type', '')}, begin_time: {getattr(job, 'begin_time', '')}, end_time: {getattr(job, 'end_time', '')}\n"

    print(output)
except Exception as e:
    print(f"bms.show_job_infos 查询失败: {e}")
    exit(1)
