import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListAllScalingV2PoliciesRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description='查询全量弹性伸缩策略列表(v2)')
parser.add_argument('--scaling_resource_id', type=str, default=None,
                    help='伸缩组ID')
parser.add_argument('--scaling_resource_type', type=str, default=None,
                    choices=['SCALING_GROUP', 'BANDWIDTH'],
                    help='伸缩资源类型：SCALING_GROUP-伸缩组；BANDWIDTH-带宽')
parser.add_argument('--scaling_policy_name', type=str, default=None,
                    help='伸缩策略名称')
parser.add_argument('--scaling_policy_type', type=str, default=None,
                    choices=['ALARM', 'SCHEDULED', 'RECURRENCE'],
                    help='策略类型：ALARM-告警策略；SCHEDULED-定时策略；RECURRENCE-周期策略')
parser.add_argument('--scaling_policy_id', type=str, default=None,
                    help='伸缩策略ID')
parser.add_argument('--start_number', type=int, default=0,
                    help='查询的起始行号，默认为0')
parser.add_argument('--limit', type=int, default=100,
                    help='查询记录数，默认20，最大100')
parser.add_argument('--sort_by', type=str, default=None,
                    choices=['POLICY_NAME', 'TRIGGER_CONDITION', 'CREATE_TIME'],
                    help='排序方法：POLICY_NAME-策略名称；TRIGGER_CONDITION-触发条件；CREATE_TIME-创建时间')
parser.add_argument('--order', type=str, default=None,
                    choices=['ASC', 'DESC'],
                    help='排序顺序：ASC-升序；DESC-降序')
parser.add_argument('--enterprise_project_id', type=str, default=None,
                    help='企业项目ID，传入all_granted_eps表示查询所有授权企业项目')
parser.add_argument('--alarm_id', type=str, default=None,
                    help='告警ID，即告警规则的ID')
parser.add_argument('--project_id', type=str, default=None,
                    help='项目ID')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')
parser.add_argument('--offset', type=int,
                    help='客户端分页偏移量，从0开始')


def render(policies):
    if not policies:
        print(f"没有找到伸缩策略 (区域: {Region})")
        return
    header = "scaling_policy_id\tscaling_policy_name\tpolicy_status\tscaling_policy_type\tscaling_resource_id\talarm_id\tcool_down_time\tcreate_time"
    print(header)
    start = Offset
    end = min(Offset + 50, len(policies))
    for p in policies[start:end]:
        print(f"{getattr(p, 'scaling_policy_id', '')}\t{getattr(p, 'scaling_policy_name', '')}\t{getattr(p, 'policy_status', '')}\t{getattr(p, 'scaling_policy_type', '')}\t{getattr(p, 'scaling_resource_id', '')}\t{getattr(p, 'alarm_id', '')}\t{getattr(p, 'cool_down_time', 0)}\t{getattr(p, 'create_time', '')}")
    if len(policies) > end:
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

        all_policies = []
        start = args.start_number
        while True:
            request = ListAllScalingV2PoliciesRequest()
            if args.scaling_resource_id:
                request.scaling_resource_id = args.scaling_resource_id
            if args.scaling_resource_type:
                request.scaling_resource_type = args.scaling_resource_type
            if args.scaling_policy_name:
                request.scaling_policy_name = args.scaling_policy_name
            if args.scaling_policy_type:
                request.scaling_policy_type = args.scaling_policy_type
            if args.scaling_policy_id:
                request.scaling_policy_id = args.scaling_policy_id
            if args.sort_by:
                request.sort_by = args.sort_by
            if args.order:
                request.order = args.order
            if args.enterprise_project_id:
                request.enterprise_project_id = args.enterprise_project_id
            if args.alarm_id:
                request.alarm_id = args.alarm_id
            request.start_number = start
            request.limit = args.limit

            response = client.list_all_scaling_v2_policies(request)
            policies = getattr(response, 'scaling_policies', []) or []
            all_policies.extend(policies)

            total = getattr(response, 'total_number', 0)
            if total <= 0 or len(all_policies) >= total:
                break
            start = len(all_policies)

        render(all_policies)
    except Exception as e:
        print(f"as.list_all_scaling_v2_policies 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
