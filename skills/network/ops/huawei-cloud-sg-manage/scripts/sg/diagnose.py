"""huawei_diagnose_sg_port_connectivity — port reachability diagnosis.

Evaluates ingress/egress rule matching for a (direction, protocol, port,
remote) probe against one security group and reports the effective verdict in
priority order, including the matched rule that decides the outcome.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .common import get_security_group, list_security_group_rules
from .rules import (
    format_ports,
    normalize_rule,
    port_matches,
    protocol_matches,
    remote_matches,
    rule_matches,
)

def diagnose_connectivity(
    region: str,
    security_group_id: str,
    direction: str = "ingress",
    protocol: str = "tcp",
    port: Optional[int] = None,
    remote: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Diagnose whether a probe (protocol/port/remote) is allowed for the SG.

    Matching semantics (VPC default):
      - rules are evaluated in priority order; lower numerical priority wins
      - the first enabled rule that matches the probe decides the verdict
      - when several rules match, the highest-priority one prevails
      - if no rule matches, the default VPC behaviour is DENY — except that the
        default security group ships built-in rules allowing in-group traffic
    """
    try:
        sg = get_security_group(region, security_group_id, project_id)
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}

    try:
        raw_rules = list_security_group_rules(
            region, project_id, security_group_id=security_group_id
        )
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}

    probe = {
        "direction": direction,
        "protocol": protocol,
        "port": port,
        "remote": remote,
    }

    candidates: List[Dict[str, Any]] = []
    indeterminate: List[Dict[str, Any]] = []
    for raw in raw_rules:
        rule = normalize_rule(raw)
        if rule["direction"] != direction:
            continue
        if not protocol_matches(rule["protocol"], protocol):
            continue
        if not port_matches(rule["ports"], port):
            continue
        matched, reason = remote_matches(rule["remote"], remote)
        if matched:
            rule["_match_reason"] = reason
            candidates.append(rule)
        else:
            # Keep group/address-group remotes as candidates for note when no
            # deterministic match exists — membership cannot be resolved here.
            if rule["remote"]["type"] in ("group", "address_group"):
                rule["_match_reason"] = reason
                indeterminate.append(rule)

    candidates.sort(key=lambda r: (r["priority"], r["id"] or ""))

    verdict: Dict[str, Any]
    if candidates:
        winner = candidates[0]
        if not winner.get("enabled"):
            # A disabled rule cannot decide; continue to the next enabled match.
            enabled_candidates = [c for c in candidates if c.get("enabled")]
            if not enabled_candidates:
                verdict = _default_verdict(sg, probe)
            else:
                winner = enabled_candidates[0]
                verdict = {
                    "verdict": "ALLOW" if winner["action"] == "allow" else "DENY",
                    "decided_by": winner,
                    "confidence": "high",
                    "evaluated_rule_count": len(candidates),
                }
        else:
            verdict = {
                "verdict": "ALLOW" if winner["action"] == "allow" else "DENY",
                "decided_by": winner,
                "confidence": "high",
                "evaluated_rule_count": len(candidates),
            }
    elif indeterminate:
        verdict = {
            "verdict": "INDETERMINATE",
            "confidence": "low",
            "reason": "no deterministic rule matched; match depends on a remote "
                      "security group / address group whose member IPs cannot be "
                      "resolved from security group rules alone",
            "relevant_group_rules": indeterminate[:10],
        }
    else:
        verdict = _default_verdict(sg, probe)

    return {
        "success": True,
        "security_group_id": security_group_id,
        "security_group_name": sg.get("name", ""),
        "probe": probe,
        "verdict": verdict["verdict"],
        "confidence": verdict.get("confidence", "high"),
        "detail": verdict,
        "matching_rules": candidates[:20],
        "rule_count": len(candidates),
    }


def _default_verdict(sg: Dict[str, Any], probe: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "verdict": "DENY",
        "confidence": "medium",
        "reason": "no enabled rule matched the probe; VPC default security group "
                  "policy is DENY for unmatched traffic (except the built-in "
                  "default-SG in-group allow rules)",
        "security_group_name": sg.get("name", ""),
    }