"""Manage actions — create/update/delete security groups and rules.

All manage actions are write operations (R2/R1). They are gated at the tool
level: without `confirmed=true` the dispatcher only PREVIEWS the exact hcloud
command and its impact. The preview must be shown to the user and approved
before confirmed execution. SKILL.md additionally requires explicit user
confirmation — the tool gate is the last line of defence, not a replacement.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import (
    build_command,
    get_security_group,
    get_security_group_rule,
    list_security_group_rules,
    run_hcloud,
)

WRITE_WARNING = (
    "WRITE OPERATION — executing this command modifies live Huawei Cloud "
    "resources. It MUST only run after the user explicitly approved the preview."
)

def _cmd(
    operation: str,
    region: str,
    params: Dict[str, Any],
    project_id: Optional[str],
) -> str:
    """Render the exact hcloud command the runtime executes (credentials omitted)."""
    return " ".join(
        build_command("VPC", operation, region, params, project_id, include_credentials=False)
    )


def create_security_group(
    region: str,
    name: str,
    description: Optional[str] = None,
    enterprise_project_id: Optional[str] = None,
    confirmed: bool = False,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"security_group.name": name}
    if description:
        params["security_group.description"] = description
    if enterprise_project_id:
        params["security_group.enterprise_project_id"] = enterprise_project_id

    impact = {
        "action": "create security group",
        "name": name,
        "description": description or "",
        "enterprise_project_id": enterprise_project_id or "",
    }
    cmd = _cmd("CreateSecurityGroup/v3", region, params, project_id)
    if not confirmed:
        return {
            "success": True,
            "preview": True,
            "message": "PREVIEW ONLY — no resource was changed. Re-run with confirmed=true after user approval.",
            "command": cmd,
            "preconditions": [
                "User approved the name/description/enterprise_project_id shown above.",
                "The name is unique in this region + project (a duplicate name is allowed by the API but confuses operators).",
            ],
            "impact": impact,
            "rollback": (
                "Delete the group created by this call with its returned id: "
                f"hcloud VPC DeleteSecurityGroup/v3 --cli-region={region} --security_group_id=<created.security_group.id>"
            ),
            "warning": WRITE_WARNING,
        }
    data = run_hcloud("VPC", "CreateSecurityGroup/v3", region, params, project_id)
    return {
        "success": True,
        "preview": False,
        "command": cmd,
        "created": data,
    }


def create_security_group_rule(
    region: str,
    security_group_id: str,
    direction: str,
    protocol: Optional[str] = None,
    ethertype: Optional[str] = None,
    multiport: Optional[str] = None,
    remote_ip_prefix: Optional[str] = None,
    remote_group_id: Optional[str] = None,
    remote_address_group_id: Optional[str] = None,
    action: Optional[str] = None,
    priority: Optional[int] = None,
    enabled: Optional[bool] = None,
    description: Optional[str] = None,
    confirmed: bool = False,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "security_group_rule.security_group_id": security_group_id,
        "security_group_rule.direction": direction,
    }
    if protocol:
        params["security_group_rule.protocol"] = protocol
    if ethertype:
        params["security_group_rule.ethertype"] = ethertype
    if multiport:
        params["security_group_rule.multiport"] = multiport
    if remote_ip_prefix:
        params["security_group_rule.remote_ip_prefix"] = remote_ip_prefix
    if remote_group_id:
        params["security_group_rule.remote_group_id"] = remote_group_id
    if remote_address_group_id:
        params["security_group_rule.remote_address_group_id"] = remote_address_group_id
    if action:
        params["security_group_rule.action"] = action
    if priority is not None:
        params["security_group_rule.priority"] = priority
    if enabled is not None:
        params["security_group_rule.enabled"] = "true" if enabled else "false"
    if description:
        params["security_group_rule.description"] = description

    remote = remote_ip_prefix or remote_group_id or remote_address_group_id or "any"
    impact = {
        "action": "create security group rule",
        "security_group_id": security_group_id,
        "direction": direction,
        "protocol": protocol or "any",
        "ethertype": ethertype or "IPv4",
        "ports": multiport or "all",
        "remote": remote,
        "action": action or "allow",
        "priority": priority if priority is not None else "1",
        "enabled": "true" if enabled is None or enabled else "false",
    }
    cmd = _cmd("CreateSecurityGroupRule/v3", region, params, project_id)
    if not confirmed:
        return {
            "success": True,
            "preview": True,
            "message": "PREVIEW ONLY — no resource was changed. Re-run with confirmed=true after user approval.",
            "command": cmd,
            "preconditions": [
                "The target security group exists in this region and is the intended one.",
                "User approved direction/protocol/ports/remote/priority shown above.",
            ],
            "impact": impact,
            "rollback": (
                "Delete the rule created by this call with its returned id: "
                f"hcloud VPC DeleteSecurityGroupRule/v3 --cli-region={region} --security_group_rule_id=<created.security_group_rule.id>"
            ),
            "warning": WRITE_WARNING,
        }
    data = run_hcloud("VPC", "CreateSecurityGroupRule/v3", region, params, project_id)
    return {
        "success": True,
        "preview": False,
        "command": cmd,
        "created": data,
    }


def update_security_group(
    region: str,
    security_group_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    confirmed: bool = False,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"security_group_id": security_group_id}
    if name:
        params["security_group.name"] = name
    if description:
        params["security_group.description"] = description

    try:
        current = get_security_group(region, security_group_id, project_id)
        snapshot = {
            "name": current.get("name"),
            "description": current.get("description"),
        }
    except RuntimeError as exc:
        snapshot = {}
        snapshot_error = str(exc)
    else:
        snapshot_error = None

    impact = {
        "action": "update security group",
        "security_group_id": security_group_id,
        "new_name": name or "(unchanged)",
        "new_description": description or "(unchanged)",
    }
    cmd = _cmd("UpdateSecurityGroup/v3", region, params, project_id)
    if not confirmed:
        return {
            "success": True,
            "preview": True,
            "message": "PREVIEW ONLY — no resource was changed. Re-run with confirmed=true after user approval.",
            "command": cmd,
            "preconditions": [
                "The security group id was read from the target account/region, not guessed.",
                "User approved the new name/description shown above.",
            ],
            "current_values": snapshot,
            "preview_lookup_error": snapshot_error,
            "impact": impact,
            "rollback": (
                "Restore the captured values with: "
                f"hcloud VPC UpdateSecurityGroup/v3 --cli-region={region} --security_group_id={security_group_id} "
                f"--security_group.name={snapshot.get('name') or '<unset>'} "
                f"--security_group.description={snapshot.get('description') or '<unset>'}"
                if snapshot else
                f"Capture the previous name/description first with hcloud VPC ShowSecurityGroup/v3 "
                f"--cli-region={region} --security_group_id={security_group_id}, then restore them via UpdateSecurityGroup/v3."
            ),
            "warning": WRITE_WARNING,
        }
    data = run_hcloud("VPC", "UpdateSecurityGroup/v3", region, params, project_id)
    return {
        "success": True,
        "preview": False,
        "command": cmd,
        "updated": data,
    }


def delete_security_group(
    region: str,
    security_group_id: str,
    confirmed: bool = False,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    lookup_errors: List[str] = []
    try:
        sg = get_security_group(region, security_group_id, project_id)
    except RuntimeError as exc:
        sg = {}
        lookup_errors.append(str(exc))
    try:
        rules = list_security_group_rules(
            region, project_id, security_group_id=security_group_id
        )
    except RuntimeError as exc:
        rules = []
        lookup_errors.append(str(exc))

    params: Dict[str, Any] = {"security_group_id": security_group_id}
    cmd = _cmd("DeleteSecurityGroup/v3", region, params, project_id)
    impact = {
        "action": "delete security group",
        "security_group_id": security_group_id,
        "security_group_name": sg.get("name", "(unknown)"),
        "rules_to_delete_with_it": len(rules),
    }
    if not confirmed:
        return {
            "success": True,
            "preview": True,
            "message": "PREVIEW ONLY — no resource was changed. Re-run with confirmed=true after user approval.",
            "command": cmd,
            "preconditions": [
                "No instance/NIC is bound to this security group (detach it in ECS/NIC first).",
                "The rule snapshot below was exported and stored, so the group can be rebuilt.",
                "The user explicitly confirmed the irreversible deletion.",
            ],
            "impact": impact,
            "rules_snapshot": rules,
            "preview_lookup_error": "; ".join(lookup_errors) or None,
            "rollback": (
                "The deletion cannot be undone. To restore service, recreate the group and its rules from "
                f"`rules_snapshot`: hcloud VPC CreateSecurityGroup/v3 --cli-region={region} "
                f"--security_group.name={sg.get('name') or '<old-name>'} "
                f"--security_group.description={sg.get('description') or '<old-description>'}"
                ", then recreate each saved rule with CreateSecurityGroupRule/v3 and rebind the instances/NICs."
            ),
            "warning": (
                "DELETING A SECURITY GROUP is irreversible and removes ALL of "
                "its rules. Instances/ports still associated with this security "
                "group may lose network connectivity. Verify no running "
                "instance uses this security group before deleting."
            ),
        }
    data = run_hcloud("VPC", "DeleteSecurityGroup/v3", region, params, project_id)
    return {
        "success": True,
        "preview": False,
        "command": cmd,
        "deleted": True,
        "response": data,
    }


def delete_security_group_rule(
    region: str,
    security_group_rule_id: str,
    confirmed: bool = False,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        rule = get_security_group_rule(region, security_group_rule_id, project_id)
    except RuntimeError as exc:
        rule = {}
        rule_lookup_error = str(exc)
    else:
        rule_lookup_error = None

    params: Dict[str, Any] = {"security_group_rule_id": security_group_rule_id}
    cmd = _cmd("DeleteSecurityGroupRule/v3", region, params, project_id)
    impact = {
        "action": "delete security group rule",
        "security_group_rule_id": security_group_rule_id,
        "direction": rule.get("direction", "(unknown)"),
        "protocol": rule.get("protocol", "(unknown)"),
        "ports": rule.get("multiport") or rule.get("ports") or "all",
        "remote": rule.get("remote_ip_prefix")
        or rule.get("remote_group_id")
        or rule.get("remote_address_group_id")
        or "any",
    }
    if not confirmed:
        return {
            "success": True,
            "preview": True,
            "message": "PREVIEW ONLY — no resource was changed. Re-run with confirmed=true after user approval.",
            "command": cmd,
            "preconditions": [
                "The rule id came from ListSecurityGroupRules/v3 of the target security group.",
                "User confirmed the direction/protocol/ports/remote shown above.",
            ],
            "captured_rule": rule,
            "preview_lookup_error": rule_lookup_error,
            "impact": impact,
            "rollback": (
                "Recreate the rule with the captured fields: "
                f"hcloud VPC CreateSecurityGroupRule/v3 --cli-region={region} "
                "--security_group_rule.security_group_id=<captured.security_group_id> "
                "--security_group_rule.direction=<captured.direction> "
                "--security_group_rule.protocol=<captured.protocol> "
                "--security_group_rule.multiport=<captured.multiport> "
                "--security_group_rule.remote_ip_prefix=<captured.remote_ip_prefix>"
            ),
            "warning": (
                "DELETING A SECURITY GROUP RULE changes network connectivity: "
                "traffic previously permitted/denied by this rule may be "
                "allowed or blocked immediately after deletion (VPC default is "
                "DENY for unmatched traffic). Confirm the rule id and the "
                "affected direction/ports/remote before proceeding."
            ),
        }
    data = run_hcloud("VPC", "DeleteSecurityGroupRule/v3", region, params, project_id)
    return {
        "success": True,
        "preview": False,
        "command": cmd,
        "deleted": True,
        "response": data,
    }