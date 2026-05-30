import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListScalingConfigsRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description='查询弹性伸缩配置列表')
parser.add_argument('--scaling_configuration_name', type=str, default=None,
                    help='伸缩配置名称')
parser.add_argument('--image_id', type=str, default=None,
                    help='镜像ID，同imageRef')
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


def render(configs):
    if not configs:
        print(f"没有找到伸缩配置 (区域: {Region})")
        return
    header = "scaling_configuration_id\tscaling_configuration_name\tscaling_group_id\tcreate_time"
    print(header)
    start = Offset
    end = min(Offset + 50, len(configs))
    for c in configs[start:end]:
        print(f"{getattr(c, 'scaling_configuration_id', '')}\t{getattr(c, 'scaling_configuration_name', '')}\t{getattr(c, 'scaling_group_id', '')}\t{getattr(c, 'create_time', '')}")
    if len(configs) > end:
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

        all_configs = []
        start = args.start_number
        while True:
            request = ListScalingConfigsRequest()
            if args.scaling_configuration_name:
                request.scaling_configuration_name = args.scaling_configuration_name
            if args.image_id:
                request.image_id = args.image_id
            request.start_number = start
            request.limit = args.limit

            response = client.list_scaling_configs(request)
            configs = getattr(response, 'scaling_configurations', []) or []
            all_configs.extend(configs)

            total = getattr(response, 'total_number', 0)
            if total <= 0 or len(all_configs) >= total:
                break
            start = len(all_configs)

        render(all_configs)
    except Exception as e:
        print(f"as.list_scaling_configs 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
