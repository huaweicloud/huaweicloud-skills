#!/usr/bin/env python3
"""list_attached_group_policies.py — 列出 IAM 用户组关联策略 (v5)

huawei_list_attached_group_policies
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from iam_common import IamConfig, list_attached_group_policies


def main():
    parser = argparse.ArgumentParser(description="列出 IAM 用户组关联策略 (v5)")
    parser.add_argument("--region", type=str, help="区域, 默认 cn-north-4")
    parser.add_argument("--group_id", type=str, required=True, help="用户组 ID (ListGroupsV5 返回的这个组ID格式)")
    args = parser.parse_args()

    cfg = IamConfig(region=args.region)
    policies = list_attached_group_policies(cfg, args.group_id)
    if not policies:
        print("该用户组没有关联策略。")
        return 0
    print(f"group_id        {args.group_id}")
    print(f"policy_count    {len(policies)}")
    for p in policies:
        print(f"{p['policy_id']}\t{p['policy_name']}\t{p['attached_at']}")
    return 0


if __name__ == "__main__":
    main()