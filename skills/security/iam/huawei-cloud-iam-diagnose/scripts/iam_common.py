#!/usr/bin/env python3
"""iam_common.py — 华为云 IAM 参考性权限分析共享工具库

提供:
1. 客户端构造 (v3 + v5)
2. 用户解析 / 组解析 / 策略文档拉取
3. 权限评估 (Allow/Deny 语句匹配, 置信度分级)

本模块是 huawei-cloud-iam-diagnose 技能的内部实现, 被各 action 脚本调用。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from config import load_credentials, build_http_config

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient as IamClientV3
from huaweicloudsdkiam.v3.region.iam_region import IamRegion as IamRegionV3
from huaweicloudsdkiam.v5 import IamClient as IamClientV5
from huaweicloudsdkiam.v5.region.iam_region import IamRegion as IamRegionV5


class IamConfig:
    """IAM 客户端 + 账户上下文"""

    def __init__(self, region=None, security_token_extra=None):
        ak, sk, region_, security_token, domain_id = load_credentials()
        self.region = region or region_
        self.security_token = security_token
        self.domain_id = domain_id
        self.ak = ak
        self.sk = sk
        http_config = build_http_config()
        creds = BasicCredentials(ak, sk)
        if security_token:
            creds = creds.with_security_token(security_token)
        self.v3 = IamClientV3.new_builder().with_http_config(http_config).with_credentials(
            creds).with_region(IamRegionV3.value_of(self.region)).build()
        self.v5 = IamClientV5.new_builder().with_http_config(http_config).with_credentials(
            creds).with_region(IamRegionV5.value_of(self.region)).build()


def _resolve_user_v3(cfg, user_name, domain_id):
    """v3 keystone 按用户名精确匹配 (需要 IAM 管理权限)."""
    from huaweicloudsdkiam.v3.model import KeystoneListUsersRequest
    req = KeystoneListUsersRequest()
    req.name = user_name
    if domain_id:
        req.domain_id = domain_id
    resp = cfg.v3.keystone_list_users(req)
    users = resp.users or []
    if not users:
        return None
    return users[0].id


def _resolve_user_v5(cfg, user_name, domain_id):
    """v5 分页列出全部用户, 按 user_name 精确匹配 (无需 IAM 管理权限)."""
    from huaweicloudsdkiam.v5.model import ListUsersV5Request
    marker = None
    while True:
        req = ListUsersV5Request()
        req.limit = 200
        if marker:
            req.marker = marker
        resp = cfg.v5.list_users_v5(req)
        for u in (resp.users or []):
            if getattr(u, "user_name", "") == user_name:
                return getattr(u, "user_id", None)
        page_info = getattr(resp, "page_info", None)
        if not page_info:
            return None
        next_marker = getattr(page_info, "next_marker", None)
        if not next_marker:
            return None
        marker = next_marker


def resolve_user_id(cfg, user_id=None, user_name=None, domain_id=None):
    """解析用户 ID: 优先 user_id, 否则按 user_name 精确匹配.

    v3 keystone 优先 (带 name 过滤), 失败/被拒时回退 v5 全量扫描。
    返回 user_id; 找不到返回 None.
    """
    if user_id:
        return user_id
    if not user_name:
        raise ValueError("必须提供 user_id 或 user_name")
    try:
        uid = _resolve_user_v3(cfg, user_name, domain_id)
        if uid:
            return uid
    except Exception:
        pass
    try:
        uid = _resolve_user_v5(cfg, user_name, domain_id)
        if uid:
            return uid
    except Exception:
        pass
    return None


def list_user_groups(cfg, user_id):
    """查询用户所在组列表, 返回 [{'id','name','domain_id'}]"""
    from huaweicloudsdkiam.v3.model import KeystoneListGroupsForUserRequest
    req = KeystoneListGroupsForUserRequest()
    req.user_id = user_id
    resp = cfg.v3.keystone_list_groups_for_user(req)
    out = []
    for g in (resp.groups or []):
        out.append({"id": g.id, "name": g.name, "domain_id": g.domain_id})
    return out


def list_attached_user_policies(cfg, user_id):
    """v5: 列出用户直连策略, 返回 [{'policy_id','policy_name','attached_at'}]"""
    from huaweicloudsdkiam.v5.model import ListAttachedUserPoliciesV5Request
    req = ListAttachedUserPoliciesV5Request()
    req.user_id = user_id
    resp = cfg.v5.list_attached_user_policies_v5(req)
    out = []
    for p in (resp.attached_policies or []):
        out.append({"policy_id": p.policy_id, "policy_name": p.policy_name,
                    "attached_at": getattr(p, "attached_at", "")})
    return out


def list_attached_group_policies(cfg, group_id):
    """v5: 列出组关联策略, 返回 [{'policy_id','policy_name','attached_at'}]"""
    from huaweicloudsdkiam.v5.model import ListAttachedGroupPoliciesV5Request
    req = ListAttachedGroupPoliciesV5Request()
    req.group_id = group_id
    resp = cfg.v5.list_attached_group_policies_v5(req)
    out = []
    for p in (resp.attached_policies or []):
        out.append({"policy_id": p.policy_id, "policy_name": p.policy_name,
                    "attached_at": getattr(p, "attached_at", "")})
    return out


def list_attached_agency_policies(cfg, agency_id):
    """v5: 列出委托关联策略"""
    from huaweicloudsdkiam.v5.model import ListAttachedAgencyPoliciesV5Request
    req = ListAttachedAgencyPoliciesV5Request()
    req.agency_id = agency_id
    resp = cfg.v5.list_attached_agency_policies_v5(req)
    out = []
    for p in (resp.attached_policies or []):
        out.append({"policy_id": p.policy_id, "policy_name": p.policy_name,
                    "attached_at": getattr(p, "attached_at", "")})
    return out


def list_agencies(cfg, domain_id=None):
    """v5: 列出账号下所有委托"""
    from huaweicloudsdkiam.v5.model import ListAgenciesV5Request
    req = ListAgenciesV5Request()
    resp = cfg.v5.list_agencies_v5(req)
    out = []
    for a in (resp.agencies or []):
        out.append({
            "agency_id": a.agency_id,
            "agency_name": a.agency_name,
            "trust_domain_id": getattr(a, "trust_domain_id", ""),
            "trust_domain_name": getattr(a, "trust_domain_name", ""),
            "description": getattr(a, "description", ""),
        })
    return out


def get_policy_document(cfg, policy_id):
    """v5: 获取策略默认版本文档(JSON 字符串). 返回 dict 或 None"""
    from huaweicloudsdkiam.v5.model import ListPolicyVersionsV5Request, GetPolicyVersionV5Request
    try:
        req = ListPolicyVersionsV5Request()
        req.policy_id = policy_id
        resp = cfg.v5.list_policy_versions_v5(req)
        versions = resp.policy_versions or []
        target = None
        for v in versions:
            if getattr(v, "is_default", False):
                target = v
                break
        if target is None and versions:
            target = versions[0]
        if target is None:
            return None
        req2 = GetPolicyVersionV5Request()
        req2.policy_id = policy_id
        req2.version_id = target.version_id
        resp2 = cfg.v5.get_policy_version_v5(req2)
        doc = resp2.policy_version.document
        return json.loads(doc) if isinstance(doc, str) else doc
    except Exception:
        return None


def get_role_policy(cfg, role_id, is_custom=False):
    """v3: 获取单条权限(role)的 policy 文档. 返回 dict 或 None"""
    try:
        if is_custom:
            from huaweicloudsdkiam.v3.model import ShowCustomPolicyRequest
            req = ShowCustomPolicyRequest()
            req.role_id = role_id
            resp = cfg.v3.show_custom_policy(req)
            return json.loads(resp.role.policy) if isinstance(resp.role.policy, str) else resp.role.policy
        else:
            from huaweicloudsdkiam.v3.model import KeystoneShowPermissionRequest
            req = KeystoneShowPermissionRequest()
            req.role_id = role_id
            resp = cfg.v3.keystone_show_permission(req)
            return json.loads(resp.role.policy) if isinstance(resp.role.policy, str) else resp.role.policy
    except Exception:
        return None


def group_domain_roles(cfg, group_id, domain_id):
    """v3: 组在全局(域)范围的权限列表.

    返回 {'roles': [...], 'error': str|None}
    """
    from huaweicloudsdkiam.v3.model import KeystoneListDomainPermissionsForGroupRequest
    req = KeystoneListDomainPermissionsForGroupRequest()
    req.domain_id = domain_id
    req.group_id = group_id
    try:
        resp = cfg.v3.keystone_list_domain_permissions_for_group(req)
    except Exception as e:
        err = _short_err(e)
        return {"roles": [], "error": err}
    out = []
    for r in (resp.roles or []):
        out.append({"id": r.id, "name": r.name, "display_name": r.display_name,
                    "catalog": r.catalog, "policy": r.policy, "type": getattr(r, "type", "")})
    return {"roles": out, "error": None}


def group_all_project_roles(cfg, group_id, domain_id):
    """v3: 组在所有项目范围(基于所有项目授权)的权限列表"""
    from huaweicloudsdkiam.v3.model import KeystoneListAllProjectPermissionsForGroupRequest
    req = KeystoneListAllProjectPermissionsForGroupRequest()
    req.domain_id = domain_id
    req.group_id = group_id
    try:
        resp = cfg.v3.keystone_list_all_project_permissions_for_group(req)
    except Exception as e:
        err = _short_err(e)
        return {"roles": [], "error": err}
    out = []
    for r in (resp.roles or []):
        out.append({"id": r.id, "name": r.name, "display_name": r.display_name,
                    "catalog": r.catalog, "policy": r.policy, "type": getattr(r, "type", "")})
    return {"roles": out, "error": None}


def agency_domain_roles(cfg, agency_id, domain_id):
    """v3: 委托在全局范围的权限列表"""
    from huaweicloudsdkiam.v3.model import ListDomainPermissionsForAgencyRequest
    req = ListDomainPermissionsForAgencyRequest()
    req.agency_id = agency_id
    req.domain_id = domain_id
    try:
        resp = cfg.v3.list_domain_permissions_for_agency(req)
    except Exception as e:
        err = _short_err(e)
        return {"roles": [], "error": err}
    out = []
    for r in (resp.roles or []):
        out.append({"id": r.id, "name": r.name, "display_name": r.display_name,
                    "catalog": r.catalog, "policy": r.policy, "type": getattr(r, "type", "")})
    return {"roles": out, "error": None}


def agency_all_project_roles(cfg, agency_id, domain_id):
    """v3: 委托在所有项目范围的权限列表"""
    from huaweicloudsdkiam.v3.model import ListAllProjectsPermissionsForAgencyRequest
    req = ListAllProjectsPermissionsForAgencyRequest()
    req.agency_id = agency_id
    req.domain_id = domain_id
    try:
        resp = cfg.v3.list_all_projects_permissions_for_agency(req)
    except Exception as e:
        err = _short_err(e)
        return {"roles": [], "error": err}
    out = []
    for r in (resp.roles or []):
        out.append({"id": r.id, "name": r.name, "display_name": r.display_name,
                    "catalog": r.catalog, "policy": r.policy, "type": getattr(r, "type", "")})
    return {"roles": out, "error": None}


def _short_err(exc):
    """从 SDK 异常中提取短错误描述(404/403/错误码)."""
    import re
    msg = str(exc)
    m = re.search(r"status_code[:=]?\s*(\d+)", msg)
    if m:
        code = m.group(1)
        nm = re.search(r"error_msg[:=]?[^\w]*([^,\]}]{0,80})", msg)
        return f"HTTP {code}{' ' + nm.group(1) if nm else ''}"
    return msg[:120]


# ---------------------------------------------------------------------------
# 权限评估逻辑
# ---------------------------------------------------------------------------

def _action_match(pattern, action):
    """通配匹配 action。华为云 action 形如 service:type:verb, 支持 * 通配。"""
    pattern = pattern.strip()
    if pattern in ("*", action):
        return True
    pattern_parts = pattern.split(":")
    action_parts = action.split(":")
    if len(pattern_parts) > len(action_parts):
        return False
    for pp, ap in zip(pattern_parts, action_parts):
        if pp == "*":
            continue
        if re.fullmatch(pp.replace("*", ".*"), ap) is None:
            return False
    if len(pattern_parts) < len(action_parts) and pattern_parts[-1] != "*":
        return len(pattern_parts) == len(action_parts)
    return True


def _resource_match(pattern, resource):
    """资源匹配。pattern='*' 或 resource 以 pattern 前缀匹配 / 完全匹配。"""
    pattern = pattern.strip()
    if not pattern or pattern == "*":
        return True
    if not resource:
        return True
    if pattern == resource:
        return True
    if resource.startswith(pattern):
        return True
    return re.fullmatch(pattern.replace("*", ".*"), resource) is not None


def evaluate_policy_document(doc, action, resource=""):
    """对单个策略文档执行 Allow/Deny 语句评估.

    返回: {'effect': 'allow'|'deny'|'no_match', 'matched': str 描述, 'has_condition': bool}
    华为云 IAM 语义: 显式 Deny 优先级高于 Allow。
    """
    if not doc:
        return {"effect": "no_match", "matched": "", "has_condition": False}
    statements = doc.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    denied = None
    allowed = None
    has_condition = False
    for st in statements:
        effect = (st.get("Effect") or "").strip()
        actions = st.get("Action") or []
        if isinstance(actions, str):
            actions = [actions]
        resources = st.get("Resource") or []
        if isinstance(resources, str):
            resources = [resources]
        if st.get("Condition"):
            has_condition = True
        for a in actions:
            if not _action_match(str(a), action):
                continue
            for r in resources or [""]:
                if not _resource_match(str(r), resource):
                    continue
                if effect.lower() == "deny":
                    denied = {"effect": "deny", "matched": f"Action={a}, Resource={r}", "has_condition": has_condition}
                else:
                    allowed = {"effect": "allow", "matched": f"Action={a}, Resource={r}", "has_condition": has_condition}
                break
    if denied:
        return denied
    if allowed:
        return allowed
    return {"effect": "no_match", "matched": "", "has_condition": has_condition}


def grade_confidence(source_kind, is_system_preset, has_condition, is_agency, is_eps):
    """评估置信度分级.

    返回: (级别, 参考性标注)
    - 预置系统策略 + 组继承 = 高
    - 自定义策略无 Condition = 中
    - 含 Condition = 低
    - 委托叠加 = 中 (仅供判断参考)
    - EPS 授权 = 中
    """
    if is_eps:
        return "中", "EPS 授权"
    if is_agency:
        return "中", "委托叠加"
    if has_condition:
        return "低", "包含 Condition"
    if is_system_preset:
        return "高", "预置系统策略"
    return "中", "自定义策略" if source_kind == "custom" else "中"


def is_system_role(catalog):
    """catalog == 'CUSTOMED' / 'Custom' 视为自定义"""
    if not catalog:
        return True
    return str(catalog).upper() != "CUSTOMED"