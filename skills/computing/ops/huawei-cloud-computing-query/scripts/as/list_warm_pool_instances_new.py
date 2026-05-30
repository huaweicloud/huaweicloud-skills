import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListWarmPoolInstancesNewRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description='查询暖池实例列表(新)')
parser.add_argument('--scaling_group_id', type=str, required=True,
                    help='伸缩组ID，可通过 list_scaling_groups.py 获取')
parser.add_argument('--limit', type=int, default=100,
                    help='查询的记录条数，默认20，最大100')
parser.add_argument('--marker', type=str, default=None,
                    help='查询暖池实例的分页marker')
parser.add_argument('--project_id', type=str, default=None,
                    help='项目ID')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')
parser.add_argument('--offset', type=int,
                    help='客户端分页偏移量，从0开始')


def render(instances):
    if not instances:
        print(f"没有找到暖池实例 (区域: {Region})")
        return
    header = "id\tinstance_id\tname\tstatus"
    print(header)
    start = Offset
    end = min(Offset + 50, len(instances))
    for i in instances[start:end]:
        print(f"{getattr(i, 'id', '')}\t{getattr(i, 'instance_id', '')}\t{getattr(i, 'name', '')}\t{getattr(i, 'status', '')}")
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
        marker = args.marker

        while True:
            request = ListWarmPoolInstancesNewRequest()
            request.scaling_group_id = args.scaling_group_id
            request.limit = args.limit
            if marker:
                request.marker = marker

            response = client.list_warm_pool_instances_new(request)
            instances = getattr(response, 'warm_pool_instances', []) or []
            all_instances.extend(instances)

            page_info = getattr(response, 'page_info', None)
            next_marker = getattr(page_info, 'next_marker', '') if page_info else ''
            if not next_marker:
                break
            marker = next_marker

        render(all_instances)
    except Exception as e:
        print(f"as.list_warm_pool_instances_new 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
