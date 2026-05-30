import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id, resolve_vpc_info

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListScalingGroupsRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description='查询弹性伸缩组列表')
parser.add_argument('--scaling_group_name', type=str, default=None,
                    help='伸缩组名称')
parser.add_argument('--scaling_configuration_id', type=str, default=None,
                    help='伸缩配置ID，通过查询弹性伸缩配置列表接口获取')
parser.add_argument('--scaling_group_status', type=str, default=None,
                    choices=['INSERVICE', 'PAUSED', 'ERROR', 'DELETING', 'FREEZED'],
                    help='伸缩组状态：INSERVICE-正常；PAUSED-停用；ERROR-异常；DELETING-删除中；FREEZED-已冻结')
parser.add_argument('--start_number', type=int, default=0,
                    help='查询的起始行号，默认为0')
parser.add_argument('--limit', type=int, default=100,
                    help='查询的记录条数，默认为20，最大100')
parser.add_argument('--enterprise_project_id', type=str, default=None,
                    help='企业项目ID，传入all_granted_eps表示查询所有授权企业项目下的伸缩组')
parser.add_argument('--project_id', type=str, default=None,
                    help='项目ID')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')
parser.add_argument('--offset', type=int,
                    help='客户端分页偏移量，从0开始')


def render(groups, vpc_info=None):
    if not groups:
        print(f"没有找到伸缩组 (区域: {Region})")
        return
    header = "scaling_group_id\tscaling_group_name\tstatus\tscaling_configuration_id\tcurrent_instance_number\tdesire_instance_number\tmin_instance_number\tmax_instance_number\tvpc_id\tvpc_name\tcreate_time"
    print(header)
    start = Offset
    end = min(Offset + 50, len(groups))
    for g in groups[start:end]:
        vid = getattr(g, 'vpc_id', '')
        vname = (vpc_info or {}).get(vid, {}).get('name', '')
        print(f"{getattr(g, 'scaling_group_id', '')}\t{getattr(g, 'scaling_group_name', '')}\t{getattr(g, 'scaling_group_status', '')}\t{getattr(g, 'scaling_configuration_id', '')}\t{getattr(g, 'current_instance_number', 0)}\t{getattr(g, 'desire_instance_number', 0)}\t{getattr(g, 'min_instance_number', 0)}\t{getattr(g, 'max_instance_number', 0)}\t{vid}\t{vname}\t{getattr(g, 'create_time', '')}")
    if len(groups) > end:
        print(f"可以使用 --offset={end} 参数继续获取后续数据")


def main():
    global Offset, Region
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

        all_groups = []
        start = args.start_number
        while True:
            request = ListScalingGroupsRequest()
            if args.scaling_group_name:
                request.scaling_group_name = args.scaling_group_name
            if args.scaling_configuration_id:
                request.scaling_configuration_id = args.scaling_configuration_id
            if args.scaling_group_status:
                request.scaling_group_status = args.scaling_group_status
            if args.enterprise_project_id:
                request.enterprise_project_id = args.enterprise_project_id
            request.start_number = start
            request.limit = args.limit

            response = client.list_scaling_groups(request)
            groups = getattr(response, 'scaling_groups', []) or []
            all_groups.extend(groups)

            total = getattr(response, 'total_number', 0)
            if total <= 0 or len(all_groups) >= total:
                break
            start = len(all_groups)

        vpc_ids = list(set(getattr(g, 'vpc_id', '') for g in all_groups if getattr(g, 'vpc_id', '')))
        vpc_info = resolve_vpc_info(Region, project_id, vpc_ids) if vpc_ids else {}
        render(all_groups, vpc_info)
    except Exception as e:
        print(f"as.list_scaling_groups 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
