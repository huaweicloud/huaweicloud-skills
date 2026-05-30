import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import ShowJobProgressRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 IMS 异步任务进度（含子任务进度），比 show_job.py 返回更详细的进度信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--job_id", type=str, required=True, help="异步任务 ID，创建镜像/导出镜像等异步操作返回的 job_id")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = ImsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ImsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 IMS 客户端")
        exit(-1)

    request = ShowJobProgressRequest()
    request.job_id = args.job_id
    response = client.show_job_progress(request)

    # 渲染结果
    output = ""
    output += f"job_id: {getattr(response, 'job_id', '')}\n"
    output += f"job_type: {getattr(response, 'job_type', '')}\n"
    output += f"status: {getattr(response, 'status', '')}\n"
    output += f"begin_time: {getattr(response, 'begin_time', '')}\n"
    output += f"end_time: {getattr(response, 'end_time', '')}\n"
    output += f"error_code: {getattr(response, 'error_code', '')}\n"
    output += f"fail_reason: {getattr(response, 'fail_reason', '')}\n"
    entities = getattr(response, 'entities', None)
    if entities:
        output += f"entities.image_id: {getattr(entities, 'image_id', '')}\n"
        output += f"entities.image_name: {getattr(entities, 'image_name', '')}\n"
        output += f"entities.current_task: {getattr(entities, 'current_task', '')}\n"
        process_percent = getattr(entities, 'process_percent', None)
        output += f"entities.process_percent: {process_percent}\n"
        sub_job_id = getattr(entities, 'sub_job_id', '')
        if sub_job_id:
            output += f"entities.sub_job_id: {sub_job_id}\n"
    print(output)
except Exception as e:
    print(f"ims.show_job_progress 查询失败: {e}")
    exit(1)
