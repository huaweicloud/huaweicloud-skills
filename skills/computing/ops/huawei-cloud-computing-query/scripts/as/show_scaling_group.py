import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id, resolve_vpc_info, resolve_subnet_info, handle_not_found_error

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ShowScalingGroupRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询弹性伸缩组详情')
parser.add_argument('--scaling_group_id', type=str, required=True,
                    help='伸缩组ID，可通过 list_scaling_groups.py 获取')
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

        request = ShowScalingGroupRequest()
        request.scaling_group_id = args.scaling_group_id

        response = client.show_scaling_group(request)
        group = getattr(response, 'scaling_group', None)
        if not group:
            print("未找到伸缩组")
            return

        print(f"scaling_group_id:\t{getattr(group, 'scaling_group_id', '')}")
        print(f"scaling_group_name:\t{getattr(group, 'scaling_group_name', '')}")
        print(f"status:\t{getattr(group, 'scaling_group_status', '')}")
        print(f"scaling_configuration_id:\t{getattr(group, 'scaling_configuration_id', '')}")
        print(f"scaling_configuration_name:\t{getattr(group, 'scaling_configuration_name', '')}")
        print(f"current_instance_number:\t{getattr(group, 'current_instance_number', 0)}")
        print(f"desire_instance_number:\t{getattr(group, 'desire_instance_number', 0)}")
        print(f"min_instance_number:\t{getattr(group, 'min_instance_number', 0)}")
        print(f"max_instance_number:\t{getattr(group, 'max_instance_number', 0)}")
        print(f"cool_down_time:\t{getattr(group, 'cool_down_time', 0)}")
        vpc_id = getattr(group, 'vpc_id', '')
        vpc_info = resolve_vpc_info(Region, project_id, [vpc_id]) if vpc_id else {}
        vpc_detail = vpc_info.get(vpc_id, {})
        print(f"vpc_id:\t{vpc_id}")
        if vpc_detail.get("name"):
            print(f"vpc_name:\t{vpc_detail['name']}")
            print(f"vpc_cidr:\t{vpc_detail['cidr']}")
        print(f"health_periodic_audit_method:\t{getattr(group, 'health_periodic_audit_method', '')}")
        print(f"health_periodic_audit_time:\t{getattr(group, 'health_periodic_audit_time', 0)}")
        print(f"health_periodic_audit_grace_period:\t{getattr(group, 'health_periodic_audit_grace_period', 0)}")
        print(f"instance_terminate_policy:\t{getattr(group, 'instance_terminate_policy', '')}")
        print(f"delete_publicip:\t{getattr(group, 'delete_publicip', False)}")
        print(f"delete_volume:\t{getattr(group, 'delete_volume', False)}")
        print(f"enterprise_project_id:\t{getattr(group, 'enterprise_project_id', '')}")
        print(f"multi_az_priority_policy:\t{getattr(group, 'multi_az_priority_policy', '')}")
        print(f"description:\t{getattr(group, 'detail', '')}")
        print(f"create_time:\t{getattr(group, 'create_time', '')}")
        print(f"is_scaling:\t{getattr(group, 'is_scaling', False)}")

        networks = getattr(group, 'networks', []) or []
        if networks:
            subnet_ids = [getattr(n, 'id', '') for n in networks]
            subnet_info = resolve_subnet_info(Region, project_id, subnet_ids, vpc_id)
            print("\nnetworks:")
            for n in networks:
                nid = getattr(n, 'id', '')
                sd = subnet_info.get(nid, {})
                print(f"  subnet_id={nid}, subnet_name={sd.get('name', '')}, cidr={sd.get('cidr', '')}, gateway_ip={sd.get('gateway_ip', '')}, availability_zone={sd.get('availability_zone', '')}, available_ip_count={sd.get('available_ip_address_count', '')}, ipv6_enable={getattr(n, 'ipv6_enable', False)}")

        security_groups = getattr(group, 'security_groups', []) or []
        if security_groups:
            print("\nsecurity_groups:")
            for sg in security_groups:
                print(f"  security_group_id={getattr(sg, 'id', '')}")

        available_zones = getattr(group, 'available_zones', []) or []
        if available_zones:
            print(f"\navailable_zones:\t{', '.join(available_zones)}")

        notifications = getattr(group, 'notifications', []) or []
        if notifications:
            print(f"\nnotifications:\t{', '.join(notifications)}")

        lbaas_listeners = getattr(group, 'lbaas_listeners', []) or []
        if lbaas_listeners:
            print("\nlbaas_listeners:")
            for lb in lbaas_listeners:
                print(f"  listener_id={getattr(lb, 'listener_id', '')}, pool_id={getattr(lb, 'pool_id', '')}, protocol_port={getattr(lb, 'protocol_port', 0)}")

        tags = getattr(group, 'tags', []) or []
        if tags:
            print("\ntags:")
            for t in tags:
                print(f"  {getattr(t, 'key', '')}={getattr(t, 'value', '')}")

    except Exception as e:
        handle_not_found_error(e, "scalingGroup", args.scaling_group_id)


if __name__ == '__main__':
    main()
