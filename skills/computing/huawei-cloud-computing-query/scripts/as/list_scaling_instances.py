import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListScalingInstancesRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description='查询弹性伸缩组实例列表')
parser.add_argument('--scaling_group_id', type=str, required=True,
                    help='伸缩组ID，可通过 list_scaling_groups.py 获取')
parser.add_argument('--life_cycle_state', type=str, default=None,
                    choices=['INSERVICE', 'PENDING', 'REMOVING', 'PENDING_WAIT', 'REMOVING_WAIT'],
                    help='实例生命周期状态：INSERVICE-正在使用；PENDING-正在加入；REMOVING-正在移出；PENDING_WAIT-正在加入等待；REMOVING_WAIT-正在移出等待')
parser.add_argument('--health_status', type=str, default=None,
                    choices=['INITIALIZING', 'NORMAL', 'ERROR'],
                    help='实例健康状态：INITIALIZING-初始化；NORMAL-正常；ERROR-异常')
parser.add_argument('--protect_from_scaling_down', type=str, default=None,
                    choices=['true', 'false'],
                    help='实例保护状态：true-已设置实例保护；false-未设置实例保护')
parser.add_argument('--start_number', type=int, default=0,
                    help='查询的起始行号，默认为0')
parser.add_argument('--limit', type=int, default=100,
                    help='查询的记录条数，默认为20')
parser.add_argument('--project_id', type=str, default=None,
                    help='项目ID')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')
parser.add_argument('--offset', type=int,
                    help='客户端分页偏移量，从0开始')


def render(instances):
    if not instances:
        print(f"没有找到伸缩组实例 (区域: {Region})")
        return
    header = "instance_id\tinstance_name\tlife_cycle_state\thealth_status\tscaling_configuration_id\tprotect_from_scaling_down\tcreate_time"
    print(header)
    start = Offset
    end = min(Offset + 50, len(instances))
    for i in instances[start:end]:
        print(f"{getattr(i, 'instance_id', '')}\t{getattr(i, 'instance_name', '')}\t{getattr(i, 'life_cycle_state', '')}\t{getattr(i, 'health_status', '')}\t{getattr(i, 'scaling_configuration_id', '')}\t{getattr(i, 'protect_from_scaling_down', False)}\t{getattr(i, 'create_time', '')}")
    if len(instances) > end:
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

        all_instances = []
        start = args.start_number
        while True:
            request = ListScalingInstancesRequest()
            request.scaling_group_id = args.scaling_group_id
            if args.life_cycle_state:
                request.life_cycle_state = args.life_cycle_state
            if args.health_status:
                request.health_status = args.health_status
            if args.protect_from_scaling_down:
                request.protect_from_scaling_down = args.protect_from_scaling_down
            request.start_number = start
            request.limit = args.limit

            response = client.list_scaling_instances(request)
            instances = getattr(response, 'scaling_group_instances', []) or []
            all_instances.extend(instances)

            total = getattr(response, 'total_number', 0)
            if total <= 0 or len(all_instances) >= total:
                break
            start = len(all_instances)

        render(all_instances)
    except Exception as e:
        print(f"as.list_scaling_instances 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
