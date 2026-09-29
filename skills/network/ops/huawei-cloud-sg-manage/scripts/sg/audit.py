"""huawei_audit_sg_overexposed_rules — security audit of over-exposed rules.

Flags security group rules that are more open than best practice allows:

- CRITICAL — inbound allow to 0.0.0.0/0 / ::/0 (world-open ingress)
- HIGH     — world-open allow with a wide port span or protocol any;
             world-open egress allow
- MEDIUM   — any world-open allow (single narrow port still flagged);
             broad port ranges to trusted-but-large remotes
- WARN     — ineffective deny rules (shadowed by a higher-priority allow)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import list_security_group_rules
from .rules import (
    _cidr_contains,
    format_ports,
    normalize_rule,
    port_span,
    ports_intersect,
    world_open_cidr,
)

def audit_overexposed(
    region: str,
    security_group_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        raw_rules = list_security_group_rules(
            region, project_id, security_group_id=security_group_id
        )
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}

    rules = [normalize_rule(r) for r in raw_rules]
    findings: List[Dict[str, Any]] = []

    for rule in rules:
        if not rule.get("enabled"):
            continue
        remote = rule["remote"]
        direction = rule["direction"]
        action = rule["action"]
        protocol = rule["protocol"]
        ports = rule["ports"]
        span = port_span(ports)

        is_world = remote["type"] == "ip" and world_open_cidr(remote["value"])
        is_any_remote = remote["type"] == "any"

        if action != "allow":
            # deny rules are restrictive by definition, but a world-open deny
            # with lower priority than a covering allow is ineffective
            continue

        exposed = is_world or is_any_remote
        if not exposed:
            continue

        severity = "medium"
        direction_label = "inbound" if direction == "ingress" else "outbound"
        message = (
            f"{direction_label} allow rule exposes ports {format_ports(ports)} "
            f"({protocol}) to the entire internet {remote['value']}"
        )
        if direction == "ingress":
            if span >= 100 or protocol in ("any", "icmp", "icmpv6"):
                severity = "critical" if is_world else "high"
                message = (
                    f"CRITICAL: world-open inbound {protocol} access to "
                    f"{format_ports(ports)} on {remote['value']} — any host on "
                    f"the internet can reach these ports"
                )
            else:
                severity = "high" if is_world else "medium"
                message = (
                    f"world-open inbound {protocol} access to port(s) "
                    f"{format_ports(ports)} on {remote['value']}"
                )
        elif direction == "egress" and is_world:
            severity = "medium"
            message = (
                f"world-open egress allow: outbound {protocol} to "
                f"{format_ports(ports)} on {remote['value']} (data exfiltration "
                f"and lateral movement surface)"
            )

        findings.append({
            "severity": severity,
            "rule_id": rule["id"],
            "security_group_id": rule["security_group_id"],
            "direction": direction,
            "protocol": protocol,
            "ports": format_ports(ports),
            "remote": remote["value"] or "any",
            "action": action,
            "priority": rule["priority"],
            "message": message,
        })

    # ineffective deny detection: an allow with priority < a deny covering the
    # same traffic scope makes the deny pointless
    allows = [r for r in rules if r["action"] == "allow" and r.get("enabled")]
    denies = [r for r in rules if r["action"] == "deny" and r.get("enabled")]
    for deny in denies:
        for allow in allows:
            if allow["direction"] != deny["direction"]:
                continue
            if allow["priority"] > deny["priority"]:
                continue
            if allow["remote"]["type"] != "ip" or deny["remote"]["type"] != "ip":
                continue
            if not _cidr_contains(allow["remote"]["value"], deny["remote"]["value"]):
                continue
            if not ports_intersect(allow["ports"], deny["ports"]):
                continue
            findings.append({
                "severity": "warn",
                "rule_id": deny["id"],
                "security_group_id": deny["security_group_id"],
                "direction": deny["direction"],
                "protocol": deny["protocol"],
                "ports": format_ports(deny["ports"]),
                "remote": deny["remote"]["value"],
                "action": "deny",
                "priority": deny["priority"],
                "message": (
                    f"ineffective deny rule: higher-priority allow rule "
                    f"{allow['id']} already permits the same traffic — the deny "
                    f"never takes effect"
                ),
            })
            break

    order = {"critical": 0, "high": 1, "medium": 2, "warn": 3}
    findings.sort(key=lambda f: order.get(f["severity"], 9))

    return {
        "success": True,
        "security_group_id": security_group_id or "all",
        "rule_count": len(rules),
        "finding_count": len(findings),
        "findings": findings,
        "summary": {
            severity: sum(1 for f in findings if f["severity"] == severity)
            for severity in ("critical", "high", "medium", "warn")
        },
    }