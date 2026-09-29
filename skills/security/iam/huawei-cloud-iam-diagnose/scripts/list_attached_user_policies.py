#!/usr/bin/env python3
"""list_attached_user_policies.py — 列出 IAM 用户直连策略 (v5)

huawei_list_attached_user_policies
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from iam_common import IamConfig, resolve_user_id, list_attached_user_policies


def main():
    parser = argparse.ArgumentParser(description="列出 IAM 用户直连策略 (v5)")
    parser.add_argument("--region", type=str, help="区域, 默认 cn-north-4")
    parser.add_argument("--user_id", type=str, help="IAM 用户 ID")
    parser.add_argument("--user_name", type=str, help="IAM 用户名")
    parser.add_argument("--domain_id", type=str, help="账号 ID (按用户名查询时使用)")
    args = parser.parse_args()
    if not args.user_id and not args.user_name:
        parser.error("必须提供 --user_id 或 --user_name")

    cfg = IamConfig(region=args.region)
    user_id = resolve_user_id(cfg, user_id=args.user_id, user_name=args.user_name,
                              domain_id=args.domain_id or cfg.domain_id)
    if not user_id:
        print(f"未找到用户: {args.user_name or args.user_id}")
        sys.exit(1)
    policies = list_attached_user_policies(cfg, user_id)
    if not policies:
        print("该用户没有直连策略。")
        return 0
    print(f"user_id         {user_id}")
    print(f"policy_count    {len(policies)}")
    for p in policies:
        print(f"{p['policy_id']}\t{p['policy_name']}\t{p['attached_at']}")
    return 0


if __name__ == "__main__":
    main()