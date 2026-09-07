#!/usr/bin/env python3
"""Run supported acceptance probe templates and emit local evidence statuses."""

from __future__ import annotations

import argparse
import ipaddress
import re
import shlex
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import hcloud_common

PLACEHOLDER_RE = re.compile(r"<([^>]+)>")
PASSED = "passed"
WARNING = "warning"
MISSING = "missing"
BLOCKED = "blocked"
STATUS_SEVERITY = {PASSED: 0, WARNING: 1, MISSING: 2, BLOCKED: 3}
METADATA_IPS = {"169.254.169.254"}
LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}


class ProbeRunError(ValueError):
    """Raised when a probe cannot be prepared safely."""


def normalize_key(value: str) -> str:
    """Return a normalized key for placeholder matching."""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def parse_values(values: list[str]) -> dict[str, str]:
    """Parse KEY=VALUE placeholder bindings."""
    parsed: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ProbeRunError(f"Expected --value KEY=VALUE, got {item!r}.")
        key, value = item.split("=", 1)
        if not key or not value:
            raise ProbeRunError(f"Expected non-empty --value KEY=VALUE, got {item!r}.")
        parsed[normalize_key(key)] = value
    return parsed


def resolve_placeholder(name: str, values: dict[str, str]) -> str | None:
    """Resolve a probe template placeholder from user values."""
    normalized = normalize_key(name)
    if normalized in values:
        return values[normalized]
    aliases = {
        "probe_url_or_public_ip_url": ("probe_url", "url", "public_ip_url"),
        "static_site_or_object_url": ("probe_url", "url", "static_site_url", "object_url"),
        "elb_probe_url": ("probe_url", "url"),
        "domain_name": ("domain", "host", "record_name"),
        "record_name": ("domain", "host", "domain_name"),
        "target_host": ("host", "domain", "address"),
        "elb_address": ("host", "domain", "address"),
        "port_range_min": ("port", "listener_port"),
        "listener_port": ("port", "port_range_min"),
    }
    for alias in aliases.get(normalized, ()):
        if alias in values:
            return values[alias]
    return None


def render_template(template: str, values: dict[str, str]) -> tuple[str | None, list[str]]:
    """Render placeholders in a probe template."""
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        value = resolve_placeholder(name, values)
        if value is None:
            missing.append(name)
            return match.group(0)
        return value

    rendered = PLACEHOLDER_RE.sub(replace, template)
    return (None if missing else rendered), missing


def status_result(status: str, summary: str, *, source: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build one normalized probe execution result."""
    return {
        "status": status,
        "summary": summary,
        "source": source,
        "detail": detail or {},
    }


def normalize_host(value: str) -> str:
    """Normalize a probe target host for safety classification."""
    return value.strip().strip("[]").rstrip(".").lower()


def classify_ip_target(address: str, *, allow_private_targets: bool) -> tuple[bool, str, str]:
    """Classify one IP address and return whether it may be probed."""
    ip = ipaddress.ip_address(address)
    mapped_ipv4 = getattr(ip, "ipv4_mapped", None)
    if mapped_ipv4:
        return classify_ip_target(str(mapped_ipv4), allow_private_targets=allow_private_targets)
    normalized = str(ip)
    if normalized in METADATA_IPS:
        return False, "metadata", "cloud metadata service targets are never allowed"
    if ip.is_unspecified:
        return False, "unspecified", "unspecified addresses are not valid probe targets"
    if ip.is_multicast:
        return False, "multicast", "multicast addresses are not valid acceptance targets"
    if ip.is_link_local:
        return False, "link_local", "link-local targets are not allowed for acceptance probes"
    if ip.is_loopback:
        if allow_private_targets:
            return True, "loopback", "loopback target allowed by explicit private-target confirmation"
        return False, "loopback", "loopback targets require --allow-private-targets"
    if ip.is_private or ip.is_reserved:
        if allow_private_targets:
            return True, "private", "private target allowed by explicit private-target confirmation"
        return False, "private", "private or reserved targets require --allow-private-targets"
    return True, "public", "public target"


def blocked_target_result(source: str, target: str, scope: str, reason: str) -> dict[str, Any]:
    """Build a blocked result for a refused probe target."""
    return status_result(
        BLOCKED,
        f"Probe target blocked: {reason}.",
        source=source,
        detail={"target": target, "target_scope": scope},
    )


def validate_host_target(
    host: str,
    *,
    source: str,
    allow_private_targets: bool,
    port: int | None = None,
    resolve: bool = True,
) -> dict[str, Any] | None:
    """Return a blocked result when a host is unsafe for live probing."""
    normalized = normalize_host(host)
    if not normalized:
        return blocked_target_result(source, host, "empty", "empty probe targets are not allowed")
    if normalized in LOCAL_HOSTNAMES or normalized.endswith(".localhost") or normalized.endswith(".local"):
        if not allow_private_targets:
            return blocked_target_result(source, host, "local_name", "local hostnames require --allow-private-targets")
        return None

    try:
        allowed, scope, reason = classify_ip_target(normalized, allow_private_targets=allow_private_targets)
    except ValueError:
        allowed = True
    else:
        if not allowed:
            return blocked_target_result(source, host, scope, reason)
        return None

    if not resolve:
        return None
    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(normalized, port) if item and item[4]})
    except OSError:
        return None
    for address in addresses:
        try:
            allowed, scope, reason = classify_ip_target(address, allow_private_targets=allow_private_targets)
        except ValueError:
            continue
        if not allowed:
            return blocked_target_result(source, host, scope, reason)
    return None


def validate_url_target(url: str, *, source: str, allow_private_targets: bool) -> dict[str, Any] | None:
    """Return a blocked result when a URL target is unsafe for live probing."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return blocked_target_result(source, url, "unsupported_scheme", "only http and https probe URLs are supported")
    if not parsed.hostname:
        return blocked_target_result(source, url, "missing_host", "probe URL must include a host")
    default_port = 443 if parsed.scheme == "https" else 80
    try:
        port = parsed.port or default_port
    except ValueError as exc:
        return blocked_target_result(source, url, "invalid_port", str(exc))
    return validate_host_target(
        parsed.hostname,
        source=source,
        allow_private_targets=allow_private_targets,
        port=port,
    )


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Disable HTTP redirects so probes cannot be redirected to unsafe targets."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401, ANN001
        """Return None so urllib reports redirects as HTTPError instead of following them."""
        return None


def http_probe(url: str, *, method: str, timeout: int, allow_private_targets: bool = False) -> dict[str, Any]:
    """Run a bounded HTTP/HTTPS probe."""
    blocked = validate_url_target(url, source="http", allow_private_targets=allow_private_targets)
    if blocked:
        return blocked
    request = urllib.request.Request(url, method=method)
    opener = urllib.request.build_opener(NoRedirectHandler)
    try:
        with opener.open(request, timeout=timeout) as response:
            status_code = getattr(response, "status", None) or response.getcode()
            response.read(256)
    except urllib.error.HTTPError as exc:
        return status_result(
            WARNING,
            f"HTTP probe returned {exc.code}.",
            source="http",
            detail={"url": url, "method": method, "status_code": exc.code},
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return status_result(BLOCKED, f"HTTP probe failed: {exc}", source="http", detail={"url": url, "method": method})
    status = PASSED if 200 <= int(status_code) < 400 else WARNING
    return status_result(
        status,
        f"HTTP probe returned {status_code}.",
        source="http",
        detail={"url": url, "method": method, "status_code": status_code},
    )


def tcp_probe(host: str, port: int, *, timeout: int, allow_private_targets: bool = False) -> dict[str, Any]:
    """Run a bounded TCP connect probe."""
    blocked = validate_host_target(host, source="tcp", allow_private_targets=allow_private_targets, port=port)
    if blocked:
        return blocked
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        return status_result(BLOCKED, f"TCP connect failed: {exc}", source="tcp", detail={"host": host, "port": port})
    return status_result(PASSED, f"TCP connect succeeded for {host}:{port}.", source="tcp", detail={"host": host, "port": port})


def dns_probe(record_name: str, *, allow_private_targets: bool = False) -> dict[str, Any]:
    """Resolve a DNS record using the local resolver."""
    blocked = validate_host_target(
        record_name,
        source="dns",
        allow_private_targets=allow_private_targets,
        resolve=False,
    )
    if blocked:
        return blocked
    try:
        answers = socket.getaddrinfo(record_name, None)
    except OSError as exc:
        return status_result(BLOCKED, f"DNS resolution failed: {exc}", source="dns", detail={"record_name": record_name})
    addresses = sorted({item[4][0] for item in answers if item and item[4]})
    for address in addresses:
        try:
            allowed, scope, reason = classify_ip_target(address, allow_private_targets=allow_private_targets)
        except ValueError:
            continue
        if not allowed:
            return blocked_target_result("dns", record_name, scope, reason)
    return status_result(
        PASSED if addresses else WARNING,
        f"DNS resolution returned {len(addresses)} address(es).",
        source="dns",
        detail={"record_name": record_name, "addresses": addresses[:10]},
    )


def tls_probe(domain_name: str, *, timeout: int, allow_private_targets: bool = False) -> dict[str, Any]:
    """Run a bounded TLS handshake probe."""
    blocked = validate_host_target(domain_name, source="tls", allow_private_targets=allow_private_targets, port=443)
    if blocked:
        return blocked
    context = ssl.create_default_context()
    try:
        with socket.create_connection((domain_name, 443), timeout=timeout) as raw_sock:
            with context.wrap_socket(raw_sock, server_hostname=domain_name) as tls_sock:
                cert = tls_sock.getpeercert()
    except (OSError, ssl.SSLError) as exc:
        return status_result(BLOCKED, f"TLS handshake failed: {exc}", source="tls", detail={"domain_name": domain_name})
    subject = cert.get("subject", []) if isinstance(cert, dict) else []
    return status_result(
        PASSED,
        "TLS handshake succeeded.",
        source="tls",
        detail={"domain_name": domain_name, "subject": subject[:3]},
    )


def runnable_from_template(
    rendered: str,
    timeout: int,
    *,
    allow_private_targets: bool = False,
) -> dict[str, Any] | None:
    """Run a rendered template if it maps to a supported safe probe."""
    parts = shlex.split(rendered)
    if not parts:
        return None
    if parts[0] == "curl":
        urls = [part for part in parts[1:] if part.startswith(("http://", "https://"))]
        if not urls:
            return None
        method = "HEAD" if "-I" in parts else "GET"
        return http_probe(urls[-1], method=method, timeout=timeout, allow_private_targets=allow_private_targets)
    if parts[0] == "tcp_connect" and len(parts) >= 3:
        try:
            port = int(parts[2])
        except ValueError:
            return status_result(BLOCKED, f"Invalid TCP port: {parts[2]}", source="tcp", detail={"template": rendered})
        return tcp_probe(parts[1], port, timeout=timeout, allow_private_targets=allow_private_targets)
    if parts[:2] == ["dig", "+short"] and len(parts) >= 3:
        return dns_probe(parts[2], allow_private_targets=allow_private_targets)
    if parts[0] == "nslookup" and len(parts) >= 2:
        return dns_probe(parts[1], allow_private_targets=allow_private_targets)
    if parts[:2] == ["openssl", "s_client"] and "-servername" in parts:
        domain = parts[parts.index("-servername") + 1]
        return tls_probe(domain, timeout=timeout, allow_private_targets=allow_private_targets)
    return None


def aggregate_template_results(results: list[dict[str, Any]]) -> str:
    """Return an aggregate evidence status for one probe."""
    if not results:
        return MISSING
    if any(item["status"] == PASSED for item in results):
        return PASSED
    return max((str(item["status"]) for item in results), key=lambda status: STATUS_SEVERITY[status])


def run_probe(
    probe: dict[str, Any],
    values: dict[str, str],
    *,
    execute: bool,
    timeout: int,
    allow_private_targets: bool = False,
) -> dict[str, Any]:
    """Run or prepare one probe."""
    probe_id = str(probe.get("id") or "unknown")
    if probe.get("status") == "skipped_missing_inputs":
        return status_result(MISSING, "Probe plan skipped this item because required inputs were missing.", source=probe_id)
    templates = [str(item) for item in probe.get("probe_templates", [])]
    if not templates:
        return status_result(MISSING, "Probe has no runnable templates.", source=probe_id)

    prepared = []
    missing_inputs: list[str] = []
    for template in templates:
        rendered, missing = render_template(template, values)
        missing_inputs.extend(missing)
        if rendered:
            prepared.append(rendered)
    if missing_inputs:
        return status_result(
            MISSING,
            f"Probe is missing placeholder values: {', '.join(sorted(set(missing_inputs)))}.",
            source=probe_id,
            detail={"missing_values": sorted(set(missing_inputs)), "templates": templates},
        )
    if not execute:
        return status_result(
            MISSING,
            "Probe was prepared but not executed. Pass --execute to run supported live probes.",
            source=probe_id,
            detail={"prepared_templates": prepared},
        )

    template_results: list[dict[str, Any]] = []
    unsupported: list[str] = []
    for rendered in prepared:
        result = runnable_from_template(rendered, timeout, allow_private_targets=allow_private_targets)
        if result is None:
            unsupported.append(rendered)
        else:
            template_results.append(result)
    if not template_results:
        return status_result(
            WARNING,
            "Probe has no supported automatic runner; collect this evidence manually.",
            source=probe_id,
            detail={"unsupported_templates": unsupported},
        )
    status = aggregate_template_results(template_results)
    return status_result(
        status,
        f"Executed {len(template_results)} supported probe template(s).",
        source=probe_id,
        detail={"template_results": template_results, "unsupported_templates": unsupported},
    )


def iter_probe_services(probe_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return services with probe lists from a probe plan."""
    return [item for item in probe_plan.get("services", []) if isinstance(item, dict)]


def build_execution(
    probe_plan: dict[str, Any],
    values: dict[str, str],
    *,
    execute: bool,
    timeout: int,
    allow_private_targets: bool = False,
) -> dict[str, Any]:
    """Run supported probes and build evidence status output."""
    services = []
    evidence: dict[str, dict[str, Any]] = {}
    for service in iter_probe_services(probe_plan):
        probe_results = []
        for probe in service.get("probes", []):
            if not isinstance(probe, dict):
                continue
            result = run_probe(
                probe,
                values,
                execute=execute,
                timeout=timeout,
                allow_private_targets=allow_private_targets,
            )
            probe_id = str(probe.get("id") or "unknown")
            evidence[probe_id] = {
                "status": result["status"],
                "summary": result["summary"],
                "source": result["source"],
            }
            probe_results.append({"id": probe_id, **result})
        services.append(
            {
                "service": service.get("service"),
                "probe_count": len(probe_results),
                "status_counts": {
                    status: sum(1 for item in probe_results if item["status"] == status)
                    for status in (PASSED, WARNING, MISSING, BLOCKED)
                },
                "probe_results": probe_results,
            }
        )
    return {
        "success": True,
        "mode": "execute" if execute else "plan",
        "execution_boundary": (
            "only built-in HTTP/TCP/DNS/TLS probes are executed; arbitrary shell templates are never executed"
        ),
        "target_policy": {
            "metadata_and_link_local": "blocked",
            "private_loopback_or_local": "requires --allow-private-targets",
            "redirects": "not followed",
            "source": "execute only probe targets derived from reviewed acceptance evidence plans",
        },
        "service_count": len(services),
        "services": services,
        "evidence": evidence,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-plan-file", type=Path, required=True, help="Probe plan JSON from hcloud_acceptance_probe_plan.py.")
    parser.add_argument("--value", action="append", default=[], help="Placeholder value as KEY=VALUE. Repeatable.")
    parser.add_argument("--execute", action="store_true", help="Run supported live probes. Without this flag, only prepare evidence gaps.")
    parser.add_argument(
        "--allow-private-targets",
        action="store_true",
        help="Allow private, loopback, or local probe targets after explicit user confirmation. Metadata/link-local targets remain blocked.",
    )
    parser.add_argument("--timeout", type=int, default=10, help="Network timeout for each supported probe.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Run supported acceptance probes."""
    args = parse_args()
    try:
        values = parse_values(args.value)
        result = build_execution(
            hcloud_common.load_json(args.probe_plan_file),
            values,
            execute=args.execute,
            timeout=args.timeout,
            allow_private_targets=args.allow_private_targets,
        )
    except ProbeRunError as exc:
        result = {"success": False, "error": str(exc)}
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
