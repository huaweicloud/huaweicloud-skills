import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListScalingPolicyExecuteLogsRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description='查询弹性伸缩策略执行日志列表')
parser.add_argument('--scaling_policy_id', type=str, required=True,
                    help='伸缩策略ID，可通过 list_scaling_policies.py 获取')
parser.add_argument('--log_id', type=str, default=None,
                    help='日志ID')
parser.add_argument('--scaling_resource_type', type=str, default=None,
                    choices=['SCALING_GROUP', 'BANDWIDTH'],
                    help='伸缩资源类型：SCALING_GROUP-伸缩组；BANDWIDTH-带宽')
parser.add_argument('--scaling_resource_id', type=str, default=None,
                    help='伸缩资源ID')
parser.add_argument('--execute_type', type=str, default=None,
                    choices=['SCHEDULED', 'RECURRENCE', 'ALARM', 'MANUAL'],
                    help='策略执行类型：SCHEDULED-自动触发(定时)；RECURRENCE-自动触发(周期)；ALARM-自动触发(告警)；MANUAL-手动触发')
parser.add_argument('--start_time', type=str, default=None,
                    help='查询的起始时间，格式为yyyy-MM-ddThh:mm:ssZ')
parser.add_argument('--end_time', type=str, default=None,
                    help='查询的截止时间，格式为yyyy-MM-ddThh:mm:ssZ')
parser.add_argument('--start_number', type=int, default=0,
                    help='查询的起始行号，默认为0')
parser.add_argument('--limit', type=int, default=100,
                    help='查询记录数，默认20，最大100')
parser.add_argument('--project_id', type=str, default=None,
                    help='项目ID')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')
parser.add_argument('--offset', type=int,
                    help='客户端分页偏移量，从0开始')


def render(logs):
    if not logs:
        print(f"没有找到策略执行日志 (区域: {Region})")
        return
    header = "id\tstatus\texecute_type\texecute_time\told_value\tdesire_value\tlimit_value\ttype\tfailed_reason"
    print(header)
    start = Offset
    end = min(Offset + 50, len(logs))
    for l in logs[start:end]:
        print(f"{getattr(l, 'id', '')}\t{getattr(l, 'status', '')}\t{getattr(l, 'execute_type', '')}\t{getattr(l, 'execute_time', '')}\t{getattr(l, 'old_value', '')}\t{getattr(l, 'desire_value', '')}\t{getattr(l, 'limit_value', '')}\t{getattr(l, 'type', '')}\t{getattr(l, 'failed_reason', '')}")
    if len(logs) > end:
        print(f"可以使用 --offset={end} 参数继续获取后续数据")


def main():
    global Region, Offset
    args = parser.parse_args()

    if args.region is not None:
        Region = args.region

    if args.offset is not None:
        Offset = args.offset

    if Offset < 0:
        Offset = 0

    # 使用 sdk
    try:
        project_id = resolve_project_id(Region, args.project_id)
        credentials = BasicCredentials(AK, SK, project_id)
        if SecurityToken:
            credentials = credentials.with_security_token(SecurityToken)
        http_config = build_http_config()

        client = AsClient.new_builder().with_http_config(http_config).with_credentials(credentials).with_region(AsRegion.value_of(Region)).build()

        all_logs = []
        start = args.start_number
        while True:
            request = ListScalingPolicyExecuteLogsRequest()
            request.scaling_policy_id = args.scaling_policy_id
            if args.log_id:
                request.log_id = args.log_id
            if args.scaling_resource_type:
                request.scaling_resource_type = args.scaling_resource_type
            if args.scaling_resource_id:
                request.scaling_resource_id = args.scaling_resource_id
            if args.execute_type:
                request.execute_type = args.execute_type
            if args.start_time:
                request.start_time = args.start_time
            if args.end_time:
                request.end_time = args.end_time
            request.start_number = start
            request.limit = args.limit

            response = client.list_scaling_policy_execute_logs(request)
            logs = getattr(response, 'scaling_policy_execute_log', []) or []
            all_logs.extend(logs)

            total = getattr(response, 'total_number', 0)
            if total <= 0 or len(all_logs) >= total:
                break
            start = len(all_logs)

        render(all_logs)
    except Exception as e:
        print(f"as.list_scaling_policy_execute_logs 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
