import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id, handle_not_found_error

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ShowScalingV2PolicyRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询弹性伸缩策略详情(v2)')
parser.add_argument('--scaling_policy_id', type=str, required=True,
                    help='伸缩策略ID，可通过 list_scaling_v2_policies.py 获取')
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

        request = ShowScalingV2PolicyRequest()
        request.scaling_policy_id = args.scaling_policy_id

        response = client.show_scaling_v2_policy(request)
        policy = getattr(response, 'scaling_policy', None)
        if not policy:
            print("未找到伸缩策略")
            return

        print(f"scaling_policy_id:\t{getattr(policy, 'scaling_policy_id', '')}")
        print(f"scaling_policy_name:\t{getattr(policy, 'scaling_policy_name', '')}")
        print(f"scaling_resource_id:\t{getattr(policy, 'scaling_resource_id', '')}")
        print(f"scaling_resource_type:\t{getattr(policy, 'scaling_resource_type', '')}")
        print(f"policy_status:\t{getattr(policy, 'policy_status', '')}")
        print(f"scaling_policy_type:\t{getattr(policy, 'scaling_policy_type', '')}")
        print(f"alarm_id:\t{getattr(policy, 'alarm_id', '')}")
        print(f"cool_down_time:\t{getattr(policy, 'cool_down_time', 0)}")
        print(f"create_time:\t{getattr(policy, 'create_time', '')}")
        print(f"description:\t{getattr(policy, 'description', '')}")

        action = getattr(policy, 'scaling_policy_action', None)
        if action:
            print(f"\nscaling_policy_action:")
            print(f"  operation:\t{getattr(action, 'operation', '')}")
            print(f"  size:\t{getattr(action, 'size', 0)}")
            print(f"  percentage:\t{getattr(action, 'percentage', 0)}")
            print(f"  limits:\t{getattr(action, 'limits', 0)}")

        scheduled = getattr(policy, 'scheduled_policy', None)
        if scheduled:
            print(f"\nscheduled_policy:")
            print(f"  launch_time:\t{getattr(scheduled, 'launch_time', '')}")
            print(f"  recurrence_type:\t{getattr(scheduled, 'recurrence_type', '')}")
            print(f"  recurrence_value:\t{getattr(scheduled, 'recurrence_value', '')}")
            print(f"  start_time:\t{getattr(scheduled, 'start_time', '')}")
            print(f"  end_time:\t{getattr(scheduled, 'end_time', '')}")

        interval_actions = getattr(policy, 'interval_alarm_actions', []) or []
        if interval_actions:
            print(f"\ninterval_alarm_actions:")
            for ia in interval_actions:
                print(f"  operation={getattr(ia, 'operation', '')}, size={getattr(ia, 'size', 0)}, lower_bound={getattr(ia, 'lower_bound', 0)}, upper_bound={getattr(ia, 'upper_bound', 0)}")

        meta = getattr(policy, 'meta_data', None)
        if meta:
            print(f"\nmeta_data:")
            print(f"  metadata_bandwidth_share_type:\t{getattr(meta, 'metadata_bandwidth_share_type', '')}")
            print(f"  metadata_eip_id:\t{getattr(meta, 'metadata_eip_id', '')}")
            print(f"  metadata_eip_address:\t{getattr(meta, 'metadata_eip_address', '')}")

    except Exception as e:
        handle_not_found_error(e, "scalingPolicy", args.scaling_policy_id)


if __name__ == '__main__':
    main()
