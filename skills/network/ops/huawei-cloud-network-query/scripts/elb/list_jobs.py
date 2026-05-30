import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListJobsRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

parser = argparse.ArgumentParser(description="查询 ELB 任务列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--job_id", type=str, help="任务ID")
parser.add_argument("--job_type", type=str, help="任务类型，如create/delete/update")
parser.add_argument("--status", type=str, help="任务状态，如SUCCESS/FAIL/RUNNING")
parser.add_argument("--error_code", type=str, help="错误码")
parser.add_argument("--resource_id", type=str, help="资源ID")
parser.add_argument("--begin_time", type=str, help="任务开始时间，格式yyyy-MM-dd HH:mm:ss")
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

    request = ListJobsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.job_id:
        request.job_id = args.job_id
    if args.job_type:
        request.job_type = args.job_type
    if args.status:
        request.status = args.status
    if args.error_code:
        request.error_code = args.error_code
    if args.resource_id:
        request.resource_id = args.resource_id
    if args.begin_time:
        request.begin_time = args.begin_time

    response = client.list_jobs(request)
    jobs = response.jobs

    if not jobs:
        print(f"没有找到任务 (区域: {Region})")
        exit(0)

    # Response 有 page_info，使用 page_info.next_marker 判断分页
    next_marker = None
    page_info = getattr(response, 'page_info', None)
    if page_info:
        next_marker = getattr(page_info, 'next_marker', None)
        has_more = next_marker is not None
    else:
        has_more = len(jobs) > PAGE_SIZE
        if has_more:
            next_marker = str(getattr(jobs[PAGE_SIZE - 1], 'job_id', ''))

    display_jobs = jobs[:PAGE_SIZE]

    output = f"job_id\tjob_type\tstatus\tresource_id\tbegin_time\tend_time\terror_code\n"
    for item in display_jobs:
        job_id = getattr(item, 'job_id', '')
        job_type = getattr(item, 'job_type', '')
        status = getattr(item, 'status', '')
        resource_id = getattr(item, 'resource_id', '')
        begin_time = getattr(item, 'begin_time', '')
        end_time = getattr(item, 'end_time', '')
        error_code = getattr(item, 'error_code', '')
        output += f"{job_id}\t{job_type}\t{status}\t{resource_id}\t{begin_time}\t{end_time}\t{error_code}\n"

    if has_more:
        output += f"\n当前返回 {len(display_jobs)} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
    else:
        output += f"\n共 {len(display_jobs)} 条"

    print(output)
except Exception as e:
    print(f"elb.list_jobs 查询失败: {e}")
    exit(1)
