import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id, handle_not_found_error

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ShowScalingConfigRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询弹性伸缩配置详情')
parser.add_argument('--scaling_configuration_id', type=str, required=True,
                    help='伸缩配置ID，可通过 list_scaling_configs.py 获取')
parser.add_argument('--project_id', type=str, default=None,
                    help='项目ID')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')


def main():
    global Region
    args = parser.parse_args()

    if args.region is not None:
        Region = args.region

    # 使用 sdk
    try:
        project_id = resolve_project_id(Region, args.project_id)
        credentials = BasicCredentials(AK, SK, project_id)
        if SecurityToken:
            credentials = credentials.with_security_token(SecurityToken)
        http_config = build_http_config()

        client = AsClient.new_builder().with_http_config(http_config).with_credentials(credentials).with_region(AsRegion.value_of(Region)).build()

        request = ShowScalingConfigRequest()
        request.scaling_configuration_id = args.scaling_configuration_id

        response = client.show_scaling_config(request)
        config = getattr(response, 'scaling_configuration', None)
        if not config:
            print("未找到伸缩配置")
            return

        print(f"scaling_configuration_id:\t{getattr(config, 'scaling_configuration_id', '')}")
        print(f"scaling_configuration_name:\t{getattr(config, 'scaling_configuration_name', '')}")
        print(f"scaling_group_id:\t{getattr(config, 'scaling_group_id', '')}")
        print(f"create_time:\t{getattr(config, 'create_time', '')}")

        instance_config = getattr(config, 'instance_config', None)
        if instance_config:
            print(f"\ninstance_config:")
            print(f"  flavor_ref:\t{getattr(instance_config, 'flavor_ref', '')}")
            print(f"  image_ref:\t{getattr(instance_config, 'image_ref', '')}")
            print(f"  key_name:\t{getattr(instance_config, 'key_name', '')}")
            print(f"  instance_name:\t{getattr(instance_config, 'instance_name', '')}")
            print(f"  instance_id:\t{getattr(instance_config, 'instance_id', '')}")
            print(f"  server_group_id:\t{getattr(instance_config, 'server_group_id', '')}")

            disks = getattr(instance_config, 'disk', []) or []
            if disks:
                print("  disks:")
                for d in disks:
                    print(f"    size={getattr(d, 'size', 0)}, volume_type={getattr(d, 'volume_type', '')}, disk_type={getattr(d, 'disk_type', '')}")

            public_ip = getattr(instance_config, 'public_ip', None)
            if public_ip:
                print(f"  public_ip: eip_id={getattr(public_ip, 'eip_id', '')}, ip_type={getattr(public_ip, 'ip_type', '')}")

            security_groups = getattr(instance_config, 'security_groups', []) or []
            if security_groups:
                print("  security_groups:")
                for sg in security_groups:
                    print(f"    id={getattr(sg, 'id', '')}")

    except Exception as e:
        handle_not_found_error(e, "scalingConfiguration", args.scaling_configuration_id)


if __name__ == '__main__':
    main()
