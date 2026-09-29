#!/usr/bin/env python3
"""trace_permission_chain.py — 权限链路追踪 (直连策略 + 组 + 委托逐层展开)

不带 action 过滤, 把用户的所有权限链路完整列出来, 供排查「用户在哪些链路
上有哪些权限来源」。
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
)


def _emit_policy_doc(doc, indent=8):
    """打印策略文档的 statement 摘要."""
    if not doc:
        print(" " * indent + "- (策略文档拉取失败/无权限)")
        return
    statements = doc.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    for st in statements:
        effect = st.get("Effect", "")
        actions = st.get("Action") or []
        if isinstance(actions, str):
            actions = [actions]
        action_str = ", ".join(str(a) for a in actions[:5])
        if len(actions) > 5:
            action_str += f", ... (共{len(actions)}个)"
        cond = "  含Condition" if st.get("Condition") else ""
        print(f" " * indent + f"- [{effect}]{cond} {action_str}")


def main():
    parser = argparse.ArgumentParser(description="华为云 IAM 权限链路追踪")
    parser.add_argument("--region", type=str, help="区域, 默认 cn-north-4")
    parser.add_argument("--user_id", type=str, help="IAM 用户 ID (与 --user_name 二选一)")
    parser.add_argument("--user_name", type=str, help="IAM 用户名")
    parser.add_argument("--domain_id", type=str, help="账号 ID, 默认从凭据获取")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    if not args.user_id and not args.user_name:
        parser.error("必须提供 --user_id 或 --user_name")

    cfg = IamConfig(region=args.region)
    domain_id = args.domain_id or cfg.domain_id

    user_id = resolve_user_id(cfg, user_id=args.user_id, user_name=args.user_name, domain_id=domain_id)
    if not user_id:
        print(f"未找到用户: {args.user_name or args.user_id}")
        sys.exit(1)

    result = {"user_id": user_id, "user_name": args.user_name, "domain_id": domain_id,
              "chains": []}

    # ---- 漏1: 直连策略 ----
    direct = {"kind": "direct", "policies": []}
    try:
        u_policies = list_attached_user_policies(cfg, user_id)
    except Exception as e:
        u_policies = []
        direct["error"] = str(e)
    for p in u_policies:
        entry = {"policy_id": p["policy_id"], "policy_name": p.get("policy_name", ""),
                 "document": get_policy_document(cfg, p["policy_id"])}
        direct["policies"].append(entry)
    result["chains"].append(direct)

    # ---- 漏3: 组链路 ----
    group_chain = {"kind": "group", "groups": []}
    try:
        groups = list_user_groups(cfg, user_id)
    except Exception as e:
        groups = []
        group_chain["error"] = str(e)
    for g in groups:
        gitem = {"group_id": g["id"], "group_name": g["name"], "group_policies": [],
                 "domain_roles": [], "all_project_roles": []}
        try:
            for p in list_attached_group_policies(cfg, g["id"]):
                gitem["group_policies"].append(
                    {"policy_id": p["policy_id"], "policy_name": p.get("policy_name", ""),
                     "document": get_policy_document(cfg, p["policy_id"])})
        except Exception as e:
            gitem["group_policies_error"] = str(e)
        gitem["domain_roles"] = group_domain_roles(cfg, g["id"], domain_id)["roles"] if domain_id else []
        gitem["all_project_roles"] = group_all_project_roles(cfg, g["id"], domain_id)["roles"] if domain_id else []
        group_chain["groups"].append(gitem)
    result["chains"].append(group_chain)

    # ---- 漏4: 委托链路 ----
    agency_chain = {"kind": "agency", "agencies": []}
    try:
        agencies = list_agencies(cfg, domain_id)
    except Exception as e:
        agencies = []
        agency_chain["error"] = str(e)
    for a in agencies:
        aitem = {"agency_id": a["agency_id"], "agency_name": a["agency_name"],
                 "trust_domain_name": a.get("trust_domain_name", ""), "policies": [],
                 "domain_roles": [], "all_project_roles": []}
        try:
            for p in list_attached_agency_policies(cfg, a["agency_id"]):
                aitem["policies"].append(
                    {"policy_id": p["policy_id"], "policy_name": p.get("policy_name", ""),
                     "document": get_policy_document(cfg, p["policy_id"])})
        except Exception as e:
            aitem["policies_error"] = str(e)
        aitem["domain_roles"] = agency_domain_roles(cfg, a["agency_id"], domain_id)["roles"] if domain_id else []
        aitem["all_project_roles"] = agency_all_project_roles(cfg, a["agency_id"], domain_id)["roles"] if domain_id else []
        agency_chain["agencies"].append(aitem)
    result["chains"].append(agency_chain)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0

    # ---- 文本输出 ----
    print(f"== 权限链路追踪: user={result['user_name'] or user_id} (id={user_id})")
    print("== 输出为参考性链路图, 非权威授权结果")
    print()
    print("### 链路 1: 直连策略")
    for p in direct.get("policies", []):
        print(f"- 直连策略: {p['policy_name'] or p['policy_id']}")
        _emit_policy_doc(p.get("document"))
    if not direct.get("policies"):
        print("  (无)")

    print()
    print("### 链路 2: 用户组继承")
    for g in group_chain.get("groups", []):
        print(f"- 用户组: {g['group_name']} (id={g['group_id']})")
        for p in g.get("group_policies", []):
            print(f"   组策略: {p['policy_name'] or p['policy_id']}")
            _emit_policy_doc(p.get("document"), 8)
        for r in g.get("domain_roles", []):
            print(f"   域级 role: {r.get('display_name') or r.get('name')} (id={r.get('id')})")
            _emit_policy_doc(r.get("policy"), 8)
        for r in g.get("all_project_roles", []):
            print(f"   所有项目 role: {r.get('display_name') or r.get('name')} (id={r.get('id')})")
            _emit_policy_doc(r.get("policy"), 8)
    if not group_chain.get("groups"):
        print("  (无)")

    print()
    print("### 链路 3: 委托 (仅列出, 需结合角色扮演场景判断)")
    for a in agency_chain.get("agencies", []):
        print(f"- 委托: {a['agency_name']} (id={a['agency_id']}, trust_domain={a.get('trust_domain_name')})")
        for p in a.get("policies", []):
            print(f"   委托策略: {p['policy_name'] or p['policy_id']}")
            _emit_policy_doc(p.get("document"), 8)
        for r in a.get("domain_roles", []):
            print(f"   域级 role: {r.get('display_name') or r.get('name')} (id={r.get('id')})")
        for r in a.get("all_project_roles", []):
            print(f"   所有项目 role: {r.get('display_name') or r.get('name')} (id={r.get('id')})")
    if not agency_chain.get("agencies"):
        print("  (无)")

    print()
    print("注意: 委托链路通常需要用户具有 sts:agencies:assumeAgency 权限并通过角色转换"
          " (AssumeRole) 才能真正使用, 此处仅列出账号下委托及其授权关系, 供判断参考。")

    return 0


if __name__ == "__main__":
    main()