"""Action dispatch for the huawei-cloud-sg-manage skill.

Maps the 11 registered huawei_* action names to their implementations.
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Dict

from . import audit, conflict, diagnose, manage, query
from .common import clear_cache, error_payload

Handler = Callable[[Dict[str, str]], Dict[str, Any]]


def _missing(params: Dict[str, str], *keys: str) -> Dict[str, Any] | None:
    """Structured failure for missing required parameters (or None)."""
    missing = [k for k in keys if not params.get(k)]
    if not missing:
        return None
    return {
        "success": False,
        "error": f"missing required parameter(s): {', '.join(missing)}",
        "error_code": "missing_parameter",
        "hint": f"Pass {' '.join(k + '=<value>' for k in missing)} next to the action name.",
    }


def _int(value: str | None, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return None


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "y")


def _region(params: Dict[str, str], default: str = "cn-north-4") -> str:
    return params.get("region") or default


def _common(params: Dict[str, str]) -> Dict[str, Any]:
    return {
        "region": _region(params),
        "project_id": params.get("project_id"),
    }


def _hdl_list_sgs(params: Dict[str, str]) -> Dict[str, Any]:
    err = _missing(params)
    if err:
        return err
    ctx = _common(params)
    try:
        groups = query.list_security_groups(
            ctx["region"],
            project_id=ctx["project_id"],
            name=params.get("name"),
            sg_id=params.get("security_group_id"),
        )
    except RuntimeError as exc:
        return error_payload(exc)
    return {"success": True, "security_groups": groups, "count": len(groups)}


def _hdl_list_rules(params: Dict[str, str]) -> Dict[str, Any]:
    err = _missing(params)
    if err:
        return err
    ctx = _common(params)
    try:
        rules = query.list_security_group_rules(
            ctx["region"],
            project_id=ctx["project_id"],
            security_group_id=params.get("security_group_id"),
        )
    except RuntimeError as exc:
        return error_payload(exc)
    return {"success": True, "security_group_rules": rules, "count": len(rules)}


def _hdl_get_sg(params: Dict[str, str]) -> Dict[str, Any]:
    err = _missing(params, "security_group_id")
    if err:
        return err
    ctx = _common(params)
    try:
        sg = query.get_security_group(
            ctx["region"], params["security_group_id"], project_id=ctx["project_id"]
        )
    except RuntimeError as exc:
        return error_payload(exc)
    return {"success": True, "security_group": sg}


def _hdl_diagnose(params: Dict[str, str]) -> Dict[str, Any]:
    err = _missing(params, "security_group_id")
    if err:
        return err
    ctx = _common(params)
    port = _int(params.get("port"))
    if params.get("port") is not None and port is None:
        return {
            "success": False,
            "error": "port must be an integer",
            "error_code": "invalid_parameter",
            "hint": "port=<1-65535>; omit the parameter to match every port.",
        }
    return diagnose.diagnose_connectivity(
        ctx["region"],
        params["security_group_id"],
        direction=(params.get("direction") or "ingress").lower(),
        protocol=(params.get("protocol") or "tcp").lower(),
        port=port,
        remote=params.get("remote"),
        project_id=ctx["project_id"],
    )


def _hdl_conflict(params: Dict[str, str]) -> Dict[str, Any]:
    ctx = _common(params)
    return conflict.analyze_conflicts(
        ctx["region"],
        security_group_id=params.get("security_group_id"),
        project_id=ctx["project_id"],
    )


def _hdl_audit(params: Dict[str, str]) -> Dict[str, Any]:
    ctx = _common(params)
    return audit.audit_overexposed(
        ctx["region"],
        security_group_id=params.get("security_group_id"),
        project_id=ctx["project_id"],
    )


def _hdl_create_sg(params: Dict[str, str]) -> Dict[str, Any]:
    err = _missing(params, "name")
    if err:
        return err
    ctx = _common(params)
    return manage.create_security_group(
        ctx["region"],
        params["name"],
        description=params.get("description"),
        enterprise_project_id=params.get("enterprise_project_id"),
        confirmed=_bool(params.get("confirmed")),
        project_id=ctx["project_id"],
    )


def _hdl_create_rule(params: Dict[str, str]) -> Dict[str, Any]:
    err = _missing(params, "security_group_id", "direction")
    if err:
        return err
    ctx = _common(params)
    priority = _int(params.get("priority"))
    if params.get("priority") is not None and priority is None:
        return {
            "success": False,
            "error": "priority must be an integer",
            "error_code": "invalid_parameter",
            "hint": "priority=<1-65535>; lower numbers take precedence.",
        }
    remotes = [
        params.get(k)
        for k in ("remote_ip_prefix", "remote_group_id", "remote_address_group_id")
    ]
    if sum(1 for r in remotes if r) > 1:
        return {
            "success": False,
            "error": "only one of remote_ip_prefix/remote_group_id/remote_address_group_id may be set",
            "error_code": "invalid_parameter",
            "hint": "Pick a single remote selector — a CIDR, a peer security group, or an address group.",
        }
    return manage.create_security_group_rule(
        ctx["region"],
        params["security_group_id"],
        params["direction"].lower(),
        protocol=params.get("protocol"),
        ethertype=params.get("ethertype"),
        multiport=params.get("multiport") or params.get("ports"),
        remote_ip_prefix=params.get("remote_ip_prefix"),
        remote_group_id=params.get("remote_group_id"),
        remote_address_group_id=params.get("remote_address_group_id"),
        action=params.get("action"),
        priority=priority,
        enabled=_bool(params.get("enabled")) if params.get("enabled") is not None else None,
        description=params.get("description"),
        confirmed=_bool(params.get("confirmed")),
        project_id=ctx["project_id"],
    )


def _hdl_update_sg(params: Dict[str, str]) -> Dict[str, Any]:
    err = _missing(params, "security_group_id")
    if err:
        return err
    if not params.get("name") and not params.get("description"):
        return {
            "success": False,
            "error": "at least one of name/description must be provided to update",
            "error_code": "missing_parameter",
            "hint": "Pass name=<new-name> and/or description=<new-description>.",
        }
    ctx = _common(params)
    return manage.update_security_group(
        ctx["region"],
        params["security_group_id"],
        name=params.get("name"),
        description=params.get("description"),
        confirmed=_bool(params.get("confirmed")),
        project_id=ctx["project_id"],
    )


def _hdl_delete_sg(params: Dict[str, str]) -> Dict[str, Any]:
    err = _missing(params, "security_group_id")
    if err:
        return err
    ctx = _common(params)
    return manage.delete_security_group(
        ctx["region"],
        params["security_group_id"],
        confirmed=_bool(params.get("confirmed")),
        project_id=ctx["project_id"],
    )


def _hdl_delete_rule(params: Dict[str, str]) -> Dict[str, Any]:
    err = _missing(params, "security_group_rule_id")
    if err:
        return err
    ctx = _common(params)
    return manage.delete_security_group_rule(
        ctx["region"],
        params["security_group_rule_id"],
        confirmed=_bool(params.get("confirmed")),
        project_id=ctx["project_id"],
    )


ACTION_SPECS: Dict[str, tuple[tuple[str, ...], Handler]] = {
    "huawei_list_security_groups": ((), _hdl_list_sgs),
    "huawei_list_security_group_rules": ((), _hdl_list_rules),
    "huawei_get_security_group": (("security_group_id",), _hdl_get_sg),
    "huawei_diagnose_sg_port_connectivity": (("security_group_id",), _hdl_diagnose),
    "huawei_analyze_sg_rule_conflict": ((), _hdl_conflict),
    "huawei_audit_sg_overexposed_rules": ((), _hdl_audit),
    "huawei_create_security_group": (("name",), _hdl_create_sg),
    "huawei_create_sg_rule": (("security_group_id", "direction"), _hdl_create_rule),
    "huawei_update_security_group": (("security_group_id",), _hdl_update_sg),
    "huawei_delete_security_group": (("security_group_id",), _hdl_delete_sg),
    "huawei_delete_sg_rule": (("security_group_rule_id",), _hdl_delete_rule),
}


def is_registered_action(action: str) -> bool:
    return action in ACTION_SPECS


def dispatch_action(action: str, params: Dict[str, str]) -> Dict[str, Any]:
    # One intent = one fresh cache. Within the intent, list/SG lookups are
    # shared between diagnose/conflict/audit instead of re-querying the API.
    clear_cache()
    if action not in ACTION_SPECS:
        return {
            "success": False,
            "error": f"unknown action: {action}",
            "error_code": "unknown_action",
            "hint": "Run `python3 scripts/huawei-cloud.py list_actions` to see the 11 supported actions.",
        }
    _, handler = ACTION_SPECS[action]
    try:
        return handler(params)
    except (ValueError, TypeError) as exc:
        return {"success": False, "error": str(exc)}
    except RuntimeError as exc:
        return error_payload(exc)
    except Exception as exc:  # noqa: BLE001 — report any failure as JSON
        return error_payload(exc)


def list_actions() -> Dict[str, Any]:
    return {
        "success": True,
        "actions": sorted(ACTION_SPECS.keys()),
    }