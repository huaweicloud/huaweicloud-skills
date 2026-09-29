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
    parts = ["hcloud", "VPC", operation, f"--cli-region={region}", "--cli-output=json"]
    for key, value in params.items():
        parts.append(f"--{key}={value}")
    if project_id:
        parts.append(f"--project_id={project_id}")
    return " ".join(parts)


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
            "impact": impact,
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
            "impact": impact,
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

    impact = {
        "action": "update security group",
        "security_group_id": security_group_id,
        "new_name": name or "(unchanged)",
        "new_description": description or "(unchanged)",
    }
    cmd = _cmd("UpdateSecurityGroup", region, params, project_id)
    if not confirmed:
        return {
            "success": True,
            "preview": True,
            "message": "PREVIEW ONLY — no resource was changed. Re-run with confirmed=true after user approval.",
            "command": cmd,
            "impact": impact,
            "warning": WRITE_WARNING,
        }
    data = run_hcloud("VPC", "UpdateSecurityGroup", region, params, project_id)
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
    try:
        sg = get_security_group(region, security_group_id, project_id)
    except RuntimeError:
        sg = {}
    try:
        rules = list_security_group_rules(
            region, project_id, security_group_id=security_group_id
        )
    except RuntimeError:
        rules = []

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
            "impact": impact,
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
    except RuntimeError:
        rule = {}

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
            "impact": impact,
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