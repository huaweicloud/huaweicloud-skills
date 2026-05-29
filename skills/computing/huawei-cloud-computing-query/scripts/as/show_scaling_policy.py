import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id, handle_not_found_error

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ShowScalingPolicyRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询弹性伸缩策略详情(v1)')
parser.add_argument('--scaling_policy_id', type=str, required=True,
                    help='伸缩策略ID，可通过 list_scaling_policies.py 获取')
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

        request = ShowScalingPolicyRequest()
        request.scaling_policy_id = args.scaling_policy_id

        response = client.show_scaling_policy(request)
        policy = getattr(response, 'scaling_policy', None)
        if not policy:
            print("未找到伸缩策略")
            return

        print(f"scaling_policy_id:\t{getattr(policy, 'scaling_policy_id', '')}")
        print(f"scaling_policy_name:\t{getattr(policy, 'scaling_policy_name', '')}")
        print(f"scaling_group_id:\t{getattr(policy, 'scaling_group_id', '')}")
        print(f"policy_status:\t{getattr(policy, 'policy_status', '')}")
        print(f"scaling_policy_type:\t{getattr(policy, 'scaling_policy_type', '')}")
        print(f"alarm_id:\t{getattr(policy, 'alarm_id', '')}")
        print(f"cool_down_time:\t{getattr(policy, 'cool_down_time', 0)}")
        print(f"create_time:\t{getattr(policy, 'create_time', '')}")

        action = getattr(policy, 'scaling_policy_action', None)
        if action:
            print(f"\nscaling_policy_action:")
            print(f"  operation:\t{getattr(action, 'operation', '')}")
            print(f"  instance_number:\t{getattr(action, 'instance_number', 0)}")
            print(f"  instance_percentage:\t{getattr(action, 'instance_percentage', 0)}")

        scheduled = getattr(policy, 'scheduled_policy', None)
        if scheduled:
            print(f"\nscheduled_policy:")
            print(f"  launch_time:\t{getattr(scheduled, 'launch_time', '')}")
            print(f"  recurrence_type:\t{getattr(scheduled, 'recurrence_type', '')}")
            print(f"  recurrence_value:\t{getattr(scheduled, 'recurrence_value', '')}")
            print(f"  start_time:\t{getattr(scheduled, 'start_time', '')}")
            print(f"  end_time:\t{getattr(scheduled, 'end_time', '')}")

    except Exception as e:
        handle_not_found_error(e, "scalingPolicy", args.scaling_policy_id)


if __name__ == '__main__':
    main()
