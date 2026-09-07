#!/usr/bin/env python3
"""Local security policy checks for Huawei Cloud planning scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

UNRESTRICTED_IPV4_CIDRS = {"0.0.0.0/0", "0.0.0.0"}
SENSITIVE_INGRESS_PORTS = {
    22: "SSH",
    80: "HTTP",
    443: "HTTPS",
    3000: "common web",
    5000: "common web",
    8000: "common web",
    8080: "common web",
}
PUBLIC_WEB_INGRESS_PORTS = {80, 443}

CIDR_KEYS = {
    "cidr",
    "cidr_ip",
    "ip_range",
    "remote_address",
    "remote_cidr",
    "remote_ip",
    "remote_ip_address",
    "remote_ip_prefix",
    "source_cidr",
    "source_ip",
    "source_ip_address",
}
DIRECTION_KEYS = {"direction", "dir"}
EGRESS_VALUES = {"egress", "out", "outbound"}
PROTOCOL_KEYS = {"protocol", "ip_protocol"}
NON_TCP_PROTOCOLS = {"udp", "icmp", "icmpv6", "gre"}
PORT_KEYS = {
    "port",
    "ports",
    "port_range",
    "port_ranges",
    "destination_port",
    "destination_ports",
    "service_port",
    "service_ports",
}
MIN_PORT_KEYS = {"from_port", "min_port", "port_min", "port_range_min", "start_port"}
MAX_PORT_KEYS = {"max_port", "port_max", "port_range_max", "end_port", "to_port"}


def normalize_key(value: Any) -> str:
    """Normalize a CLI argument or JSON key for policy matching."""
    return str(value).strip().lstrip("-").replace("-", "_").lower()


def format_path(path: tuple[str | int, ...]) -> str:
    """Format a JSON path for human-readable policy violations."""
    if not path:
        return "$"
    parts: list[str] = []
    for item in path:
        if isinstance(item, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{item}]"
            else:
                parts.append(f"[{item}]")
        else:
            parts.append(item)
    return ".".join(parts)


def parse_cli_args(arg_tokens: list[str]) -> dict[str, Any]:
    """Parse repeated raw hcloud argument tokens into a normalized mapping."""
    values: dict[str, Any] = {}
    pending_key: str | None = None
    for token in arg_tokens:
        text = str(token).strip()
        if not text:
            continue
        if text.startswith("--"):
            pending_key = None
            stripped = text[2:]
            if "=" in stripped:
                key, raw_value = stripped.split("=", 1)
                append_field(values, normalize_key(key), raw_value)
            else:
                pending_key = normalize_key(stripped)
                append_field(values, pending_key, True)
            continue
        if pending_key:
            values[pending_key] = text
            pending_key = None
    return values


def append_field(values: dict[str, Any], key: str, value: Any) -> None:
    """Append a field while preserving repeated CLI arguments."""
    if key not in values:
        values[key] = value
        return
    existing = values[key]
    if isinstance(existing, list):
        existing.append(value)
    else:
        values[key] = [existing, value]


def is_unrestricted_ipv4(value: Any) -> bool:
    """Return True when a value explicitly represents unrestricted IPv4 access."""
    if isinstance(value, str):
        return value.strip() in UNRESTRICTED_IPV4_CIDRS
    return False


def values_for_keys(fields: dict[str, Any], keys: set[str]) -> list[tuple[str, Any]]:
    """Return direct field values matching normalized key names."""
    return [(key, value) for key, value in fields.items() if normalize_key(key) in keys]


def first_value_for_keys(fields: dict[str, Any], keys: set[str]) -> Any:
    """Return the first direct field value matching any normalized key."""
    for _, value in values_for_keys(fields, keys):
        return value
    return None


def rule_is_egress(fields: dict[str, Any]) -> bool:
    """Return True when a rule candidate is explicitly egress/outbound."""
    direction = first_value_for_keys(fields, DIRECTION_KEYS)
    if not isinstance(direction, str):
        return False
    return direction.strip().lower() in EGRESS_VALUES


def rule_can_include_tcp(fields: dict[str, Any]) -> bool:
    """Return True unless the rule is explicitly limited to a non-TCP protocol."""
    protocol = first_value_for_keys(fields, PROTOCOL_KEYS)
    if protocol is None:
        return True
    if isinstance(protocol, (int, float)):
        return int(protocol) in {-1, 0, 6}
    protocol_text = str(protocol).strip().lower()
    if protocol_text in {"", "-1", "all", "any", "tcp", "6"}:
        return True
    return protocol_text not in NON_TCP_PROTOCOLS


def rule_is_explicit_tcp(fields: dict[str, Any]) -> bool:
    """Return True only when a rule explicitly limits traffic to TCP."""
    protocol = first_value_for_keys(fields, PROTOCOL_KEYS)
    if isinstance(protocol, bool):
        return False
    if isinstance(protocol, (int, float)):
        return int(protocol) == 6
    return str(protocol).strip().lower() in {"tcp", "6"}


def to_int(value: Any) -> int | None:
    """Parse an integer port value."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d+", value.strip()):
        return int(value.strip())
    return None


def port_intervals_from_value(value: Any) -> list[tuple[int, int]]:
    """Return port intervals parsed from a JSON/CLI value."""
    if isinstance(value, list):
        intervals: list[tuple[int, int]] = []
        for item in value:
            intervals.extend(port_intervals_from_value(item))
        return intervals

    port = to_int(value)
    if port is not None:
        return [(port, port)]

    if not isinstance(value, str):
        return []
    text = value.strip().lower()
    if text in {"*", "all", "any", "-1"}:
        return [(0, 65535)]

    range_match = re.fullmatch(r"\s*(\d+)\s*[-:]\s*(\d+)\s*", text)
    if range_match:
        start, end = sorted((int(range_match.group(1)), int(range_match.group(2))))
        return [(start, end)]

    intervals = []
    for number in re.findall(r"\d+", text):
        port_number = int(number)
        intervals.append((port_number, port_number))
    return intervals


def port_intervals_from_fields(fields: dict[str, Any]) -> list[tuple[int, int]]:
    """Return every port interval declared by one rule candidate."""
    intervals: list[tuple[int, int]] = []
    min_value = first_value_for_keys(fields, MIN_PORT_KEYS)
    max_value = first_value_for_keys(fields, MAX_PORT_KEYS)
    min_port = to_int(min_value)
    max_port = to_int(max_value)
    if min_port is not None and max_port is not None:
        start, end = sorted((min_port, max_port))
        intervals.append((start, end))
    elif min_port is not None:
        intervals.append((min_port, min_port))
    elif max_port is not None:
        intervals.append((max_port, max_port))

    for _, value in values_for_keys(fields, PORT_KEYS):
        intervals.extend(port_intervals_from_value(value))
    return intervals


def sensitive_ports_from_fields(fields: dict[str, Any]) -> list[int]:
    """Return sensitive SSH/Web ports included by a rule candidate."""
    intervals = port_intervals_from_fields(fields)

    matches = []
    for port, _label in SENSITIVE_INGRESS_PORTS.items():
        if any(start <= port <= end for start, end in intervals):
            matches.append(port)
    return sorted(matches)


def rule_is_exact_public_web(fields: dict[str, Any]) -> bool:
    """Return True for explicit TCP rules containing only exact port 80/443 entries."""
    intervals = port_intervals_from_fields(fields)
    return (
        bool(intervals)
        and rule_is_explicit_tcp(fields)
        and all(start == end and start in PUBLIC_WEB_INGRESS_PORTS for start, end in intervals)
    )


def iter_dict_candidates(value: Any, path: tuple[str | int, ...] = ()) -> list[tuple[tuple[str | int, ...], dict[str, Any]]]:
    """Return every dictionary candidate from a JSON-like value."""
    candidates: list[tuple[tuple[str | int, ...], dict[str, Any]]] = []
    if isinstance(value, dict):
        candidates.append((path, value))
        for key, child in value.items():
            candidates.extend(iter_dict_candidates(child, path + (str(key),)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            candidates.extend(iter_dict_candidates(child, path + (index,)))
    return candidates


def build_violation(path: str, cidr_field: str, cidr: str, ports: list[int]) -> dict[str, Any]:
    """Build a structured policy violation."""
    labels = [f"{SENSITIVE_INGRESS_PORTS[port]} {port}" for port in ports]
    return {
        "code": "unrestricted_sensitive_ingress_port",
        "path": path,
        "cidr_field": cidr_field,
        "cidr": cidr,
        "ports": ports,
        "port_labels": labels,
        "message": (
            "Ingress rule opens SSH/Web port(s) "
            f"{', '.join(labels)} to {cidr}. Use a restricted source CIDR, VPN, bastion host, "
            "office network, or private CIDR instead of 0.0.0.0/0."
        ),
    }


def check_rule_candidate(
    fields: dict[str, Any],
    path: str,
    *,
    allow_public_web: bool = False,
) -> list[dict[str, Any]]:
    """Return policy violations for one rule-like field mapping."""
    if rule_is_egress(fields) or not rule_can_include_tcp(fields):
        return []
    ports = sensitive_ports_from_fields(fields)
    if allow_public_web and rule_is_exact_public_web(fields):
        ports = [port for port in ports if port not in PUBLIC_WEB_INGRESS_PORTS]
    if not ports:
        return []

    violations = []
    for key, value in values_for_keys(fields, CIDR_KEYS):
        if is_unrestricted_ipv4(value):
            violations.append(build_violation(path, key, str(value).strip(), ports))
    return violations


def check_json_payload(data: Any, *, allow_public_web: bool = False) -> list[dict[str, Any]]:
    """Return unrestricted sensitive ingress violations from a JSON-like payload."""
    violations: list[dict[str, Any]] = []
    for path, fields in iter_dict_candidates(data):
        normalized_fields = {normalize_key(key): value for key, value in fields.items()}
        violations.extend(
            check_rule_candidate(
                normalized_fields,
                format_path(path),
                allow_public_web=allow_public_web,
            )
        )
    return violations


def check_cli_args(
    arg_tokens: list[str],
    *,
    allow_public_web: bool = False,
) -> list[dict[str, Any]]:
    """Return unrestricted sensitive ingress violations from hcloud CLI arguments."""
    fields = parse_cli_args(arg_tokens)
    return check_rule_candidate(
        fields,
        "args",
        allow_public_web=allow_public_web,
    )


def check_json_file(
    path: str | None,
    *,
    allow_public_web: bool = False,
) -> tuple[list[dict[str, Any]], str | None]:
    """Return policy violations from a JSON file and a non-fatal scan error."""
    if not path:
        return [], None
    file_path = Path(path)
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], f"JSON input file was not found during security policy scan: {file_path}"
    except json.JSONDecodeError as exc:
        return [], f"JSON input file could not be parsed during security policy scan: {exc}"
    return check_json_payload(data, allow_public_web=allow_public_web), None


def check_change_inputs(
    arg_tokens: list[str],
    json_input_file: str | None = None,
    *,
    allow_public_web: bool = False,
) -> dict[str, Any]:
    """Return security policy findings for a planned hcloud change."""
    cli_violations = check_cli_args(
        arg_tokens,
        allow_public_web=allow_public_web,
    )
    json_violations, scan_error = check_json_file(
        json_input_file,
        allow_public_web=allow_public_web,
    )
    return {
        "violations": cli_violations + json_violations,
        "scan_error": scan_error,
    }
