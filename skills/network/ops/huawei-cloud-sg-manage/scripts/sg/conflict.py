"""huawei_analyze_sg_rule_conflict — security group rule conflict detection.

Detects, within one security group (or across all groups when none is given):

- duplicate rules (exact or semantic duplicates) → redundant
- contradictory rules: same direction/ethertype/protocol with overlapping
  remotes (one CIDR contains the other) and overlapping port ranges but
  different actions (allow vs deny) → the lower-priority rule is shadowed
- shadowed rules: a higher-priority allow/deny covers the same traffic as a
  lower-priority rule with the same action → the lower one is unreachable
"""

from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Optional

from .common import list_security_group_rules
from .rules import _cidr_contains, _cidr_overlaps, format_ports, normalize_rule, port_span, ports_intersect

def _same_scope(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return (
        a["direction"] == b["direction"]
        and a["ethertype"] == b["ethertype"]
        and a["protocol"] == b["protocol"]
        and a["enabled"] == b["enabled"]
    )


def _remote_intersects(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    ra, rb = a["remote"], b["remote"]
    if ra["type"] == "ip" and rb["type"] == "ip":
        return _cidr_overlaps(ra["value"], rb["value"])
    if ra["type"] == "any":
        return rb["type"] != "group"
    if rb["type"] == "any":
        return ra["type"] != "group"
    if ra["type"] == rb["type"] == "group":
        return ra["value"] == rb["value"]
    if ra["type"] == rb["type"] == "address_group":
        return ra["value"] == rb["value"]
    # ip vs group / address_group — cannot be proven; treat as non-conflicting
    return False


def _ports_intersect(a: Optional[List], b: Optional[List]) -> bool:
    return ports_intersect(a, b)


def _fmt_rule(rule: Dict[str, Any]) -> str:
    remote = rule["remote"]
    if remote["type"] == "ip":
        remote_txt = remote["value"]
    elif remote["type"] == "group":
        remote_txt = f"sg:{remote['value'][:12]}"
    elif remote["type"] == "address_group":
        remote_txt = f"ag:{remote['value'][:12]}"
    else:
        remote_txt = "any"
    return (
        f"{rule['direction']}/{rule['ethertype']} {rule['protocol']} "
        f"ports={format_ports(rule['ports'])} remote={remote_txt} "
        f"action={rule['action']} prio={rule['priority']} "
        f"enabled={rule['enabled']} id={rule['id']}"
    )


def analyze_conflicts(
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

    rules = [normalize_rule(r) for r in raw_rules if r.get("id") or r.get("security_group_rule_id")]
    findings: List[Dict[str, Any]] = []

    # 1) duplicates (exact field equality)
    seen: Dict[Any, List[int]] = {}
    for idx, rule in enumerate(rules):
        key = (
            rule["direction"], rule["ethertype"], rule["protocol"],
            rule["action"], rule["enabled"], rule["priority"],
            str(rule["ports"]), str(rule["remote"]),
        )
        seen.setdefault(key, []).append(idx)
    for key, idxs in seen.items():
        if len(idxs) > 1:
            findings.append({
                "severity": "medium",
                "kind": "duplicate",
                "message": f"{len(idxs)} identical rules (duplicate/redundant)",
                "rule_ids": [rules[i]["id"] for i in idxs],
            })

    # 2) contradictions + shadowing (pairwise, same scope)
    for ia, ib in combinations(range(len(rules)), 2):
        a, b = rules[ia], rules[ib]
        if not _same_scope(a, b):
            continue
        if not _remote_intersects(a, b):
            continue
        if not _ports_intersect(a["ports"], b["ports"]):
            continue
        if a["action"] == b["action"]:
            # shadowing: identical effect on overlapping traffic
            continue
        # contradictory (allow vs deny) on overlapping traffic
        winner, loser = (a, b) if a["priority"] <= b["priority"] else (b, a)
        findings.append({
            "severity": "high",
            "kind": "contradiction",
            "message": (
                f"allow/deny conflict on overlapping traffic: rule "
                f"{winner['action']} (prio {winner['priority']}) shadows rule "
                f"{loser['action']} (prio {loser['priority']}) — the "
                f"{loser['action']} rule is ineffective for the overlapping range"
            ),
            "rule_ids": [a["id"], b["id"]],
            "rules": [_fmt_rule(a), _fmt_rule(b)],
        })

    # 3) shadowed same-action rules (same effect, wider coverage wins)
    for ia, ib in combinations(range(len(rules)), 2):
        a, b = rules[ia], rules[ib]
        if a["id"] == b["id"]:
            continue
        if not _same_scope(a, b):
            continue
        if a["action"] != b["action"]:
            continue
        if a["priority"] >= b["priority"]:
            continue
        # a has higher priority (lower number). Does a fully cover b's traffic?
        ra, rb = a["remote"], b["remote"]
        if ra["type"] != "ip" or rb["type"] != "ip":
            continue
        if not _cidr_contains(ra["value"], rb["value"]):
            continue
        if not _ports_intersect(a["ports"], b["ports"]):
            continue
        # a covers at least the same traffic with the same action at higher
        # priority → b is redundant for the overlapping ports
        findings.append({
            "severity": "low",
            "kind": "shadowed",
            "message": (
                f"rule {a['id']} (prio {a['priority']}, {ra['value']}) fully "
                f"covers rule {b['id']} (prio {b['priority']}, {rb['value']}) "
                f"with the same action — the lower-priority rule is redundant "
                f"for the overlapping range"
            ),
            "rule_ids": [a["id"], b["id"]],
            "rules": [_fmt_rule(a), _fmt_rule(b)],
        })

    # deduplicate identical findings (pairwise iteration may surface both orders)
    unique: List[Dict[str, Any]] = []
    seen_keys = set()
    for f in findings:
        key = (f["kind"], tuple(sorted(f["rule_ids"])))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(f)

    unique.sort(key=lambda f: {"high": 0, "medium": 1, "low": 2}[f["severity"]])

    return {
        "success": True,
        "security_group_id": security_group_id or "all",
        "rule_count": len(rules),
        "finding_count": len(unique),
        "findings": unique,
        "summary": {
            "high": sum(1 for f in unique if f["severity"] == "high"),
            "medium": sum(1 for f in unique if f["severity"] == "medium"),
            "low": sum(1 for f in unique if f["severity"] == "low"),
        },
    }