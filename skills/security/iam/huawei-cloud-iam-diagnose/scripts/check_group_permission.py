#!/usr/bin/env python3
"""check_group_permission.py — 组级权限真实 check 验证

huawei_check_group_permission
使用 v3 真实 check 接口交叉验证:
  - keystone_check_project_permission_for_group   (项目级)
  - keystone_check_domain_permission_for_group    (域/全局级)
  - keystone_checkrole_for_group                  (所有项目级/全部项目授权)
说明: hcloud CLI 对这三个接口无论 204/404 都返回 exit code 0 且无输出,
无法区分「有权限」与「无权限」, 因此本脚本使用 Python SDK, 以 HTTP 状态码
(204=有权限, 404=无权限) 作为可靠判据。SDK 对该接口存在两种历史命名
(KeystoneCheckRoleForGroupRequest / KeystoneCheckroleForGroupRequest),
脚本对两者均做兼容。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from iam_common import IamConfig

from huaweicloudsdkiam.v3.model import (
    KeystoneCheckProjectPermissionForGroupRequest,
    KeystoneCheckDomainPermissionForGroupRequest,
)
try:
    # 不同 SDK 版本对「所有项目」接口的命名存在差异:
    # 官方 SDK (>=3.1.x) 实际类名为 KeystoneCheckroleForGroupRequest，
    # 但部分历史/网关文档使用 KeystoneCheckRoleForGroupRequest。此处两种拼写都兼容。
    from huaweicloudsdkiam.v3.model import (
        KeystoneCheckRoleForGroupRequest as _KeystoneCheckRoleForGroupRequest,
    )
    KeystoneCheckRoleForGroupRequest = _KeystoneCheckRoleForGroupRequest
except ImportError:
    from huaweicloudsdkiam.v3.model import (
        KeystoneCheckroleForGroupRequest as KeystoneCheckRoleForGroupRequest,
    )


def _check_role_for_group(client, req):
    """兼容 SDK 两种方法名的组级「所有项目」check 调用"""
    method = getattr(client, "keystone_check_role_for_group", None)
    if method is None:
        method = getattr(client, "keystone_checkrole_for_group")
    try:
        method(req)
        return "HAS", "204"
    except Exception as e:
        msg = str(e)
        import re
        m = re.search(r"status_code[:=]?\s*(\d+)", msg)
        if m and m.group(1) == "404":
            return "NO", "404"
        return "ERROR", (m.group(1) if m else msg[:200])


def _do_check(client, req):
    """执行 check, 返回 ('HAS'|'NO'|'ERROR', http_status_or_msg)"""
    try:
        if isinstance(req, KeystoneCheckProjectPermissionForGroupRequest):
            client.keystone_check_project_permission_for_group(req)
        elif isinstance(req, KeystoneCheckDomainPermissionForGroupRequest):
            client.keystone_check_domain_permission_for_group(req)
        else:
            return _check_role_for_group(client, req)
        return "HAS", "204"
    except Exception as e:
        msg = str(e)
        import re
        m = re.search(r"status_code[:=]?\s*(\d+)", msg)
        if m and m.group(1) == "404":
            return "NO", "404"
        return "ERROR", (m.group(1) if m else msg[:200])


def main():
    parser = argparse.ArgumentParser(description="组级权限真实 check 验证 (v3)")
    parser.add_argument("--region", type=str, help="区域, 默认 cn-north-4")
    parser.add_argument("--group_id", type=str, required=True, help="用户组 ID")
    parser.add_argument("--role_id", type=str, required=True, help="权限 ID (Role ID)")
    parser.add_argument("--scope", type=str, required=True, choices=["project", "domain", "all_projects"],
                        help="检查作用域: project=项目级, domain=域/全局, all_projects=所有项目(keystone_checkrole)")
    parser.add_argument("--domain_id", type=str, help="账号 ID (domain/all_projects 必填)")
    parser.add_argument("--project_id", type=str, help="项目 ID (project 必填)")
    args = parser.parse_args()

    if args.scope == "project" and not args.project_id:
        parser.error("scope=project 时必须提供 --project_id")
    if args.scope in ("domain", "all_projects") and not args.domain_id:
        parser.error(f"scope={args.scope} 时必须提供 --domain_id")

    cfg = IamConfig(region=args.region)
    client = cfg.v3

    if args.scope == "project":
        req = KeystoneCheckProjectPermissionForGroupRequest()
        req.project_id = args.project_id
        req.group_id = args.group_id
        req.role_id = args.role_id
        desc = f"项目级 (project={args.project_id})"
    elif args.scope == "domain":
        req = KeystoneCheckDomainPermissionForGroupRequest()
        req.domain_id = args.domain_id
        req.group_id = args.group_id
        req.role_id = args.role_id
        desc = f"域/全局 (domain={args.domain_id})"
    else:
        req = KeystoneCheckRoleForGroupRequest()
        req.domain_id = args.domain_id
        req.group_id = args.group_id
        req.role_id = args.role_id
        desc = "所有项目 (keystone_checkrole)"

    status, http = _do_check(client, req)
    print(f"scope      {desc}")
    print(f"group_id   {args.group_id}")
    print(f"role_id    {args.role_id}")
    print(f"result     {status}   (HTTP {http})")
    if status == "HAS":
        print("说明: 该用户组确实拥有该权限。")
    elif status == "NO":
        print("说明: 该用户组未拥有该权限 (HTTP 404)。")
    else:
        print("说明: check 接口调用失败(通常为当前凭据缺少 IAM 管理权限), 无法通过真实接口验证。")
        sys.exit(1)
    return 0


if __name__ == "__main__":
    main()