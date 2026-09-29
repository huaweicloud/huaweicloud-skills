"""Query actions — read-only access to security groups and rules."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import (
    get_security_group as _get_security_group,
    get_security_group_rule as _get_security_group_rule,
    list_security_group_rules as _list_security_group_rules,
    list_security_groups as _list_security_groups,
)

def list_security_groups(
    region: str,
    project_id: Optional[str] = None,
    limit: int = 2000,
    name: Optional[str] = None,
    sg_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return _list_security_groups(region, project_id, limit, name, sg_id)


def list_security_group_rules(
    region: str,
    project_id: Optional[str] = None,
    security_group_id: Optional[str] = None,
    limit: int = 2000,
) -> List[Dict[str, Any]]:
    return _list_security_group_rules(region, project_id, security_group_id, limit)


def get_security_group(
    region: str, security_group_id: str, project_id: Optional[str] = None
) -> Dict[str, Any]:
    return _get_security_group(region, security_group_id, project_id)


def get_security_group_rule(
    region: str, security_group_rule_id: str, project_id: Optional[str] = None
) -> Dict[str, Any]:
    return _get_security_group_rule(region, security_group_rule_id, project_id)