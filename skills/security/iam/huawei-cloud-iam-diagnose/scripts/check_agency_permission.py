#!/usr/bin/env python3
"""check_agency_permission.py — 委托级权限真实 check 验证

huawei_check_agency_permission
使用 v3 真实 check 接口交叉验证:
  - check_project_permission_for_agency          (项目级)
  - check_domain_permission_for_agency           (域/全局级)
  - check_all_projects_permission_for_agency     (所有项目级)
说明: 与组级 check 相同, hcloud CLI 无法区分 204/404, 本脚本使用 SDK
以 HTTP 状态码作为可靠判据。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from iam_common import IamConfig

from huaweicloudsdkiam.v3.model import (
    CheckProjectPermissionForAgencyRequest,
    CheckDomainPermissionForAgencyRequest,
    CheckAllProjectsPermissionForAgencyRequest,
)


def _do_check(client, req, desc=""):
    try:
        if isinstance(req, CheckProjectPermissionForAgencyRequest):
            client.check_project_permission_for_agency(req)
        elif isinstance(req, CheckDomainPermissionForAgencyRequest):
            client.check_domain_permission_for_agency(req)
        else:
            client.check_all_projects_permission_for_agency(req)
        return "HAS", "204"
    except Exception as e:
        msg = str(e)
        m = re.search(r"status_code[:=]?\s*(\d+)", msg)
        if m and m.group(1) == "404":
            return "NO", "404"
        return "ERROR", (m.group(1) if m else msg[:200])


def main():
    parser = argparse.ArgumentParser(description="委托级权限真实 check 验证 (v3)")
    parser.add_argument("--region", type=str, help="区域, 默认 cn-north-4")
    parser.add_argument("--agency_id", type=str, required=True, help="委托 ID")
    parser.add_argument("--role_id", type=str, required=True, help="权限 ID (Role ID)")
    parser.add_argument("--scope", type=str, required=True, choices=["project", "domain", "all_projects"],
                        help="检查作用域")
    parser.add_argument("--domain_id", type=str, help="账号/委托方账号 ID (domain/all_projects 必填)")
    parser.add_argument("--project_id", type=str, help="委托方项目 ID (project 必填)")
    args = parser.parse_args()

    if args.scope == "project" and not args.project_id:
        parser.error("scope=project 时必须提供 --project_id")
    if args.scope in ("domain", "all_projects") and not args.domain_id:
        parser.error(f"scope={args.scope} 时必须提供 --domain_id")

    cfg = IamConfig(region=args.region)
    client = cfg.v3

    if args.scope == "project":
        req = CheckProjectPermissionForAgencyRequest()
        req.project_id = args.project_id
        req.agency_id = args.agency_id
        req.role_id = args.role_id
        desc = f"项目级 (project={args.project_id})"
    elif args.scope == "domain":
        req = CheckDomainPermissionForAgencyRequest()
        req.domain_id = args.domain_id
        req.agency_id = args.agency_id
        req.role_id = args.role_id
        desc = f"域/全局 (domain={args.domain_id})"
    else:
        req = CheckAllProjectsPermissionForAgencyRequest()
        req.domain_id = args.domain_id
        req.agency_id = args.agency_id
        req.role_id = args.role_id
        desc = "所有项目"

    status, http = _do_check(client, req, desc)
    print(f"scope      {desc}")
    print(f"agency_id  {args.agency_id}")
    print(f"role_id    {args.role_id}")
    print(f"result     {status}   (HTTP {http})")
    if status == "HAS":
        print("说明: 该委托确实拥有该权限。")
    elif status == "NO":
        print("说明: 该委托未拥有该权限 (HTTP 404)。")
    else:
        print("说明: check 接口调用失败(通常为当前凭据缺少 IAM 管理权限), 无法通过真实接口验证。")
        sys.exit(1)
    return 0


if __name__ == "__main__":
    main()