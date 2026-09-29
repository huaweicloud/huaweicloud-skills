"""Security group rule semantics: normalization, CIDR/port/protocol matching.

The VPC security group rule model (v3 API):

- direction:  ingress (入方向) | egress (出方向)
- ethertype:  IPv4 | IPv6
- protocol:   tcp | udp | icmp | icmpv6 | any (回应/any)
- ports:      single port ("22"), range ("22-25"), list ("22,80") or None (= all)
- remote:     remote_ip_prefix (CIDR) | remote_group_id (peer SG) |
              remote_address_group_id (address group) | None (unrestricted)
- action:     allow | deny (v3)
- priority:   1..65535 — lower number = higher priority (default 1)
- enabled:    true | false
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Rule normalization
# ---------------------------------------------------------------------------

def normalize_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw security-group-rule dict into a comparable structure."""
    direction = str(rule.get("direction") or "").lower()
    ethertype = str(rule.get("ethertype") or "IPv4")
    protocol = str(rule.get("protocol") or "any").lower()
    action = str(rule.get("action") or "allow").lower()
    enabled = rule.get("enabled")
    if enabled is None:
        enabled = True
    elif isinstance(enabled, str):
        enabled = enabled.lower() in ("true", "1")

    ports = _normalize_ports(rule.get("multiport") or rule.get("ports"))

    remote = _normalize_remote(rule)
    return {
        "id": rule.get("id") or rule.get("security_group_rule_id"),
        "security_group_id": rule.get("security_group_id") or rule.get("security_group_id"),
        "direction": direction,
        "ethertype": ethertype,
        "protocol": protocol,
        "ports": ports,  # None = all ports
        "remote": remote,
        "action": action,
        "priority": _normalize_priority(rule.get("priority")),
        "enabled": enabled,
        "description": rule.get("description") or "",
        "raw": rule,
    }


def _normalize_priority(value: Any) -> int:
    if value is None or value == "":
        return 1  # default priority when not specified
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1


def _normalize_ports(value: Any) -> Optional[List[Tuple[int, int]]]:
    """Convert '22', '22-25', '22,80,443-450' into [(lo, hi), ...] or None."""
    if value is None or str(value).strip() in ("", "null", "None"):
        return None
    text = str(value).strip()
    ranges: List[Tuple[int, int]] = []
    for chunk in re.split(r"[,\s]+", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo, _, hi = chunk.partition("-")
            try:
                ranges.append((int(lo), int(hi)))
            except ValueError:
                continue
        else:
            try:
                p = int(chunk)
                ranges.append((p, p))
            except ValueError:
                continue
    return ranges or None


def _normalize_remote(rule: Dict[str, Any]) -> Dict[str, Any]:
    ip_prefix = rule.get("remote_ip_prefix")
    remote_group_id = rule.get("remote_group_id") or rule.get("remote_group_id")
    remote_address_group_id = rule.get("remote_address_group_id")
    if ip_prefix and str(ip_prefix).strip() not in ("", "null", "None"):
        return {"type": "ip", "value": str(ip_prefix).strip()}
    if remote_group_id and str(remote_group_id).strip() not in ("", "null", "None"):
        return {"type": "group", "value": str(remote_group_id).strip()}
    if remote_address_group_id and str(remote_address_group_id).strip() not in ("", "null", "None"):
        return {"type": "address_group", "value": str(remote_address_group_id).strip()}
    return {"type": "any", "value": None}


# ---------------------------------------------------------------------------
# Matching primitives
# ---------------------------------------------------------------------------

def _cidr_contains(cidr_a: str, cidr_b: str) -> bool:
    """True when cidr_a contains cidr_b (or they are equal)."""
    try:
        net_a = ipaddress.ip_network(cidr_a, strict=False)
        net_b = ipaddress.ip_network(cidr_b, strict=False)
    except ValueError:
        return False
    if net_a.version != net_b.version:
        return False
    return net_b.subnet_of(net_a)


def _cidr_overlaps(cidr_a: str, cidr_b: str) -> bool:
    try:
        net_a = ipaddress.ip_network(cidr_a, strict=False)
        net_b = ipaddress.ip_network(cidr_b, strict=False)
    except ValueError:
        return False
    if net_a.version != net_b.version:
        return False
    return net_a.overlaps(net_b)


def remote_matches(rule_remote: Dict[str, Any], probe_remote: Optional[str]) -> Tuple[bool, str]:
    """Match a rule's remote against a probe remote CIDR.

    Returns (matched, reason). rule_remote type:
      - ip: CIDR containment check against probe (or any probe when probe is None)
      - group / address_group: cannot be resolved from SG rules alone
      - any: matches everything
    """
    rtype = rule_remote.get("type")
    if rtype == "any":
        return True, "rule has no remote restriction (all sources/destinations)"
    if rtype == "ip":
        rule_cidr = rule_remote.get("value") or ""
        if not probe_remote:
            return True, f"rule matches remote CIDR {rule_cidr} (no probe CIDR given)"
        if _cidr_contains(rule_cidr, probe_remote):
            return True, f"probe {probe_remote} is within rule CIDR {rule_cidr}"
        return False, f"probe {probe_remote} is NOT within rule CIDR {rule_cidr}"
    if rtype in ("group", "address_group"):
        # Membership requires the peer group's contained IPs, which are not
        # exposed by SG-rule APIs — treat as indeterminate, not a match.
        return False, f"remote is a {'group' if rtype == 'group' else 'address group'} " \
                      f"({rule_remote.get('value')}) — membership cannot be resolved from rules alone"
    return False, "unknown remote type"


def protocol_matches(proto: str, probe_protocol: str) -> bool:
    """Match rule protocol against probe protocol. 'any' matches everything."""
    if proto in ("any", ""):
        return True
    if probe_protocol in ("any", ""):
        return False
    return proto == probe_protocol


def port_matches(rule_ports: Optional[List[Tuple[int, int]]], probe_port: Optional[int]) -> bool:
    """Match rule port ranges against a probe port. rule_ports None = all ports."""
    if rule_ports is None:
        return True
    if probe_port is None:
        return True  # no probe port → rule scope only
    for lo, hi in rule_ports:
        if lo <= probe_port <= hi:
            return True
    return False


def ports_intersect(a: Optional[List[Tuple[int, int]]], b: Optional[List[Tuple[int, int]]]) -> bool:
    """True when two port-range lists overlap. None (= all ports) intersects everything."""
    if a is None or b is None:
        return True
    for alo, ahi in a:
        for blo, bhi in b:
            if alo <= bhi and blo <= ahi:
                return True
    return False


def rule_matches(
    rule: Dict[str, Any],
    direction: str,
    protocol: str,
    port: Optional[int],
    remote: Optional[str],
) -> Tuple[bool, str]:
    """Full match of a normalized rule against a connectivity probe."""
    if not rule.get("enabled"):
        return False, "rule is disabled"
    if rule.get("direction") and rule["direction"] != direction:
        return False, f"rule direction {rule['direction']} != probe direction {direction}"
    if not protocol_matches(rule.get("protocol") or "any", protocol):
        return False, f"rule protocol {rule['protocol']} != probe protocol {protocol}"
    if not port_matches(rule.get("ports"), port):
        return False, f"rule ports {rule['ports']} do not cover probe port {port}"
    matched, reason = remote_matches(rule.get("remote") or {"type": "any"}, remote)
    return matched, reason


def world_open_cidr(cidr: str) -> bool:
    """True when a CIDR represents the whole internet (0.0.0.0/0 or ::/0)."""
    try:
        net = ipaddress.ip_network(str(cidr), strict=False)
    except ValueError:
        return False
    return net.prefixlen == 0


def port_span(rule_ports: Optional[List[Tuple[int, int]]]) -> int:
    """Number of distinct ports covered by the rule (loose upper bound)."""
    if rule_ports is None:
        return 65535
    total = 0
    for lo, hi in rule_ports:
        total += max(0, hi - lo + 1)
    return total


def format_ports(rule_ports: Optional[List[Tuple[int, int]]]) -> str:
    if rule_ports is None:
        return "all"
    return ",".join(f"{lo}-{hi}" if lo != hi else str(lo) for lo, hi in rule_ports)