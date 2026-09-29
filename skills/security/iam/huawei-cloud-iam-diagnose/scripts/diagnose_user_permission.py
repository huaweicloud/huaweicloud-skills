#!/usr/bin/env python3
"""diagnose_user_permission.py — 华为云 IAM 参考性权限分析 (核心) 

对指定 IAM 用户 + 目标 action/资源 展开权限链路
(直连策略 + 用户组继承 + 委托), 解析策略文档的 Allow/Deny 语句,
输出「大概率有/无权限」+ 置信度分级 + 完整权限链路追踪。

输出为「参考性」结论, 非权威鉴权结果。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from iam_common import (
    IamConfig,
    resolve_user_id,
    list_user_groups,
    list_attached_user_policies,
    list_attached_group_policies,
    get_policy_document,
    group_domain_roles,
    group_all_project_roles,
    list_agencies,
    list_attached_agency_policies,
    agency_domain_roles,
    agency_all_project_roles,
    evaluate_policy_document,
    grade_confidence,
    is_system_role,
)


def _render_actions(role, action, resource):
    """从单个 role/policy 记录提取可评估实例并做效果评估."""
    policy = role.get("policy")
    if isinstance(policy, str):
        try:
            policy = json.loads(policy)
        except Exception:
            policy = None
    if not policy:
        return {"effect": "no_match", "matched": "", "has_condition": False}
    return evaluate_policy_document(policy, action, resource)


def _emit_node(node):
    print(f"- {node['kind']}: {node.get('name', '')} (id={node.get('id', '')})")
    if node.get("detail"):
        print(f"    {node['detail']}")


def _collect_direct(cfg, user_id, action, resource):
    """直连策略链路"""
    nodes = []
    matches = []
    try:
        u_policies = list_attached_user_policies(cfg, user_id)
    except Exception as e:
        u_policies = []
        nodes.append({"kind": "直连策略", "name": "", "id": "", "detail": f"查询失败: {e}"})
    for p in u_policies:
        try:
            doc = get_policy_document(cfg, p["policy_id"])
        except Exception as exc:
            doc = None
            nodes.append({"kind": "直连策略", "name": p.get("policy_name", ""),
                          "id": p["policy_id"],
                          "detail": f"策略文档拉取失败: {exc}"})
            continue
        is_sys = True
        if doc is None:
            detail = f"policy_id={p['policy_id']} (策略文档拉取失败/无权限)"
        else:
            result = evaluate_policy_document(doc, action, resource)
            level, reason = grade_confidence(source_kind="system", is_system_preset=is_sys,
                                             has_condition=result["has_condition"],
                                             is_agency=False, is_eps=False)
            detail = f"策略文档评估: {result['effect']} ({result.get('matched', '')}) | 置信度: {level} ({reason})"
            if result["effect"] in ("allow", "deny"):
                matches.append({"kind": "user", "policy_id": p["policy_id"], "policy_name": p["policy_name"],
                                "effect": result["effect"], "confidence": level, "reason": reason})
        nodes.append({"kind": "直连策略", "name": p.get("policy_name", ""),
                      "id": p["policy_id"], "detail": detail})
    return nodes, matches


def _collect_groups(cfg, user_id, action, resource, domain_id=None):
    """用户组链路: 组继承的策略 + 组级 role(域/所有项目)"""
    nodes = []
    matches = []
    try:
        groups = list_user_groups(cfg, user_id)
    except Exception as e:
        groups = []
        nodes.append({"kind": "用户组", "name": "", "id": "", "detail": f"查询失败: {e}"})
    for g in groups:
        gid = g["id"]
        detail_bits = []
        # 1. 组直连 v5 策略
        try:
            g_policies = list_attached_group_policies(cfg, gid)
        except Exception:
            g_policies = []
        for p in g_policies:
            try:
                doc = get_policy_document(cfg, p["policy_id"])
            except Exception as exc:
                detail_bits.append(f"组策略 {p['policy_name'] or p['policy_id']}: 文档拉取失败: {exc}")
                continue
            if doc is None:
                detail_bits.append(f"组策略 {p['policy_name'] or p['policy_id']}: 文档拉取失败/无权限")
                continue
            result = evaluate_policy_document(doc, action, resource)
            level, reason = grade_confidence(source_kind="group", is_system_preset=True,
                                             has_condition=result["has_condition"],
                                             is_agency=False, is_eps=False)
            detail_bits.append(f"组策略 {p.get('policy_name','')}: {result['effect']} ({result.get('matched','')}) | 置信度 {level} ({reason})")
            if result["effect"] in ("allow", "deny"):
                matches.append({"kind": "group", "group_id": gid, "group_name": g["name"],
                                "policy_id": p["policy_id"], "effect": result["effect"],
                                "confidence": level, "reason": reason})
        # 2. 域范围 role (组在域的权限)
        dom_res = group_domain_roles(cfg, gid, domain_id) if domain_id else {"roles": [], "error": None}
        if dom_res.get("error"):
            detail_bits.append(f"域级 role 查询失败: {dom_res['error']} (当前凭据可能缺少 IAM 查看权限)")
        for r in dom_res["roles"]:
            result = _render_actions(r, action, resource)
            sys_preset = is_system_role(r.get("catalog"))
            level, reason = grade_confidence(source_kind="group", is_system_preset=sys_preset,
                                             has_condition=result["has_condition"],
                                             is_agency=False, is_eps=False)
            detail_bits.append(f"域级 role {r.get('display_name') or r.get('name')}: {result['effect']} ({result.get('matched','')}) | 置信度 {level} ({reason})")
            if result["effect"] in ("allow", "deny"):
                matches.append({"kind": "group", "group_id": gid, "group_name": g["name"],
                                "role_id": r.get("id"), "effect": result["effect"],
                                "confidence": level, "reason": reason,
                                "display_name": r.get("display_name") or r.get("name")})
        # 3. 所有项目范围 role
        ap_res = group_all_project_roles(cfg, gid, domain_id) if domain_id else {"roles": [], "error": None}
        if ap_res.get("error"):
            detail_bits.append(f"所有项目 role 查询失败: {ap_res['error']}")
        for r in ap_res["roles"]:
            result = _render_actions(r, action, resource)
            sys_preset = is_system_role(r.get("catalog"))
            level, reason = grade_confidence(source_kind="group", is_system_preset=sys_preset,
                                             has_condition=result["has_condition"],
                                             is_agency=False, is_eps=False)
            detail_bits.append(f"所有项目 role {r.get('display_name') or r.get('name')}: {result['effect']} ({result.get('matched','')}) | 置信度 {level} ({reason})")
            if result["effect"] in ("allow", "deny"):
                matches.append({"kind": "group", "group_id": gid, "group_name": g["name"],
                                "role_id": r.get("id"), "effect": result["effect"],
                                "confidence": level, "reason": reason,
                                "display_name": r.get("display_name") or r.get("name")})
        nodes.append({"kind": "用户组", "name": g.get("name", ""), "id": gid,
                      "detail": "; ".join(detail_bits) if detail_bits else "无匹配的策略/role"})
    return nodes, matches


def _collect_agencies(cfg, action, resource, domain_id=None):
    """委托链路: 账号下所有委托 + 委托附加策略/role."""
    nodes = []
    matches = []
    try:
        agencies = list_agencies(cfg, domain_id)
    except Exception as e:
        agencies = []
        nodes.append({"kind": "委托", "name": "", "id": "", "detail": f"查询失败: {e}"})
    for a in agencies:
        aid = a["agency_id"]
        detail_bits = ["仅供判断参考"]
        # 1. 委托附加 v5 策略
        try:
            a_policies = list_attached_agency_policies(cfg, aid)
        except Exception:
            a_policies = []
        for p in a_policies:
            try:
                doc = get_policy_document(cfg, p["policy_id"])
            except Exception as exc:
                detail_bits.append(f"委托策略 {p.get('policy_name','')}: 文档拉取失败: {exc}")
                continue
            if doc is None:
                detail_bits.append(f"委托策略 {p.get('policy_name','')}: 文档拉取失败/无权限")
                continue
            result = evaluate_policy_document(doc, action, resource)
            level, reason = grade_confidence(source_kind="agency", is_system_preset=True,
                                             has_condition=result["has_condition"],
                                             is_agency=True, is_eps=False)
            detail_bits.append(f"委托策略 {p.get('policy_name','')}: {result['effect']} ({result.get('matched','')}) | 置信度 {level} ({reason})")
            if result["effect"] in ("allow", "deny"):
                matches.append({"kind": "agency", "agency_id": aid, "agency_name": a["agency_name"],
                                "policy_id": p["policy_id"], "effect": result["effect"],
                                "confidence": level, "reason": reason})
        # 2. 委托 role (域 + 所有项目)
        for fn in (agency_domain_roles, agency_all_project_roles):
            res = fn(cfg, aid, domain_id) if domain_id else {"roles": [], "error": None}
            if res.get("error"):
                detail_bits.append(f"委托 role 查询失败: {res['error']}")
                continue
            for r in res["roles"]:
                result = _render_actions(r, action, resource)
                sys_preset = is_system_role(r.get("catalog"))
                level, reason = grade_confidence(source_kind="agency", is_system_preset=sys_preset,
                                                 has_condition=result["has_condition"],
                                                 is_agency=True, is_eps=False)
                detail_bits.append(f"委托 role {r.get('display_name') or r.get('name')}: {result['effect']} ({result.get('matched','')}) | 置信度 {level} ({reason})")
                if result["effect"] in ("allow", "deny"):
                    matches.append({"kind": "agency", "agency_id": aid, "agency_name": a["agency_name"],
                                    "role_id": r.get("id"), "effect": result["effect"],
                                    "confidence": level, "reason": reason,
                                    "display_name": r.get("display_name") or r.get("name")})
        nodes.append({"kind": "委托", "name": a.get("agency_name", ""), "id": aid,
                      "detail": "; ".join(detail_bits)})
    return nodes, matches


def _final_verdict(matches):
    """汇总各链路匹配结果, 生成最终「大概率有/无权限」结论.

    IAM 语义(与 SKILL.md 判定规则一致):
    - 显式 Deny 优先级最高 -> 大概率无权限。
    - 命中任意 Allow -> 大概率有权限。
    - 未命中任何 Allow/Deny 语句 -> 隐式拒绝 -> 大概率无权限。
    命中语句含 Condition、资源匹配模糊等无法静态判定时, 置信度降级为「低」,
    结论按「仅供参考」处理, 但判定仍归属 大概率有/无权限。
    """
    denies = [m for m in matches if m["effect"] == "deny"]
    allows = [m for m in matches if m["effect"] == "allow"]
    if denies:
        return "大概率无权限 (存在显式 Deny 语句)", denies, allows
    if allows:
        return "大概率有权限", [], allows
    return "大概率无权限 (隐式拒绝: 链路中未匹配到该 action 的 Allow/Deny 语句)", [], []


def main():
    parser = argparse.ArgumentParser(description="华为云 IAM 参考性权限分析 (核心)")
    parser.add_argument("--region", type=str, help="区域, 默认 cn-north-4")
    parser.add_argument("--user_id", type=str, help="IAM 用户 ID (与 --user_name 二选一)")
    parser.add_argument("--user_name", type=str, help="IAM 用户名")
    parser.add_argument("--domain_id", type=str, help="账号 ID, 用于域级/所有项目 role 查询, 默认从凭据获取")
    parser.add_argument("--action", type=str, required=True,
                        help="目标 action, 例如 ecs:servers:list / obs:bucket:CreateBucket")
    parser.add_argument("--resource", type=str, default="", help="目标资源, 例如 OBS bucket 名; 默认 '*'")
    parser.add_argument("--only", type=str, default="all",
                        choices=["all", "direct", "group", "agency"], help="只分析指定链路")
    args = parser.parse_args()

    if not args.user_id and not args.user_name:
        parser.error("必须提供 --user_id 或 --user_name")

    cfg = IamConfig(region=args.region)
    domain_id = args.domain_id or cfg.domain_id

    # 1. 解析用户
    user_id = resolve_user_id(cfg, user_id=args.user_id, user_name=args.user_name, domain_id=domain_id)
    if not user_id:
        print(f"未找到用户: {args.user_name or args.user_id}")
        sys.exit(1)
    print(f"== 目标用户: {args.user_name or user_id} (id={user_id})")
    print(f"== 目标操作: {args.action}  目标资源: {args.resource or '*'}")
    print(f"== 输出说明: 本工具为「参考性权限分析」, 结论为大概率推断, 非权威鉴权结果")
    print()

    all_nodes = []
    all_matches = []

    print("### 1) 直连策略链路")
    if args.only in ("all", "direct"):
        nodes, matches = _collect_direct(cfg, user_id, args.action, args.resource)
        for n in nodes:
            _emit_node(n)
        all_nodes.extend(nodes)
        all_matches.extend(matches)
    print()

    print("### 2) 用户组链路 (组继承)")
    if args.only in ("all", "group"):
        nodes, matches = _collect_groups(cfg, user_id, args.action, args.resource, domain_id)
        for n in nodes:
            _emit_node(n)
        all_nodes.extend(nodes)
        all_matches.extend(matches)
    print()

    print("### 3) 委托链路 (仅供判断参考)")
    if args.only in ("all", "agency"):
        nodes, matches = _collect_agencies(cfg, args.action, args.resource, domain_id)
        for n in nodes:
            _emit_node(n)
        all_nodes.extend(nodes)
        all_matches.extend(matches)
    print()

    # 4. 最终结论
    verdict, denies, allows = _final_verdict(all_matches)
    print("=" * 72)
    print(f"[最终结论] {verdict}")
    if denies:
        print("\n根据 Deny 语句的来源:")
        for m in denies:
            print(f"  - {m.get('kind')} 链路: {m.get('display_name') or m.get('policy_name') or m.get('group_name') or m.get('agency_name')} (置信度 {m.get('confidence')}, {m.get('reason')})")
    if allows:
        print("\n根据 Allow 语句的来源:")
        for m in allows:
            print(f"  - {m.get('kind')} 链路: {m.get('display_name') or m.get('policy_name') or m.get('group_name') or m.get('agency_name')} (置信度 {m.get('confidence')}, {m.get('reason')})")
    print("=" * 72)
    print("注意事项:")
    print("1. 本结论为「参考性」评估, 仅依据策略文档静态匹配, 不代表真实可执行鉴权结果。")
    print("2. 含 Condition / 委托叠加 / EPS 授权场景结论可能不准确, 一律按「仅供参考」处理。")
    print("3. 如需 100% 确定, 请: a) 登录 IAM 控制台核对授权; b) 使用实际 API 试调用; c) 查询 CTS 审计日志。")
    print("4. 若部分接口返回 403 (当前凭据缺少 IAM 管理权限), 对应链路将标记为查询失败, 结论可用于参考。")
    return 0


if __name__ == "__main__":
    main()