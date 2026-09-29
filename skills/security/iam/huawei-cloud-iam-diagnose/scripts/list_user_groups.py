#!/usr/bin/env python3
"""list_user_groups.py — 列出 IAM 用户所在用户组 (v3 keystone)

huawei_list_user_groups
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from iam_common import IamConfig, resolve_user_id, list_user_groups


def _classify_error(exc):
    """从 SDK 异常提取 HTTP 状态码; 无状态码视为未知错误."""
    import re
    msg = str(exc)
    m = re.search(r"status_code[:=]?\s*(\d+)", msg)
    if m:
        return m.group(1), msg[:200]
    return "UNKNOWN", msg[:200]


def main():
    parser = argparse.ArgumentParser(description="列出 IAM 用户所在用户组 (v3)")
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
    try:
        groups = list_user_groups(cfg, user_id)
    except Exception as e:
        code, detail = _classify_error(e)
        print(f"查询用户组失败: HTTP {code}")
        print(f"  {detail}")
        if code == "403":
            print("  当前凭据缺少 IAM 查看权限 (403)，无法列出用户组。")
            print("  可尝试: 1) 使用具备 IAM 查看权限的凭据重试;"
                  " 2) 改用 diagnose_user_permission.py / trace_permission_chain.py 做降级分析。")
        else:
            print("  网络错误或服务异常，请重试。")
        sys.exit(1)
    if not groups:
        print("该用户不在任何用户组中。")
        return 0
    print(f"user_id         {user_id}")
    print(f"group_count     {len(groups)}")
    for g in groups:
        print(f"{g['id']}\t{g['name']}\t{g.get('domain_id','')}")
    return 0


if __name__ == "__main__":
    main()