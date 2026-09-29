#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNS TXT record probe script.

Function:
    Query TXT records for a given DNS name and report the record values
    as a single JSON object on stdout. Supports an optional explicit
    resolver (the @8.8.8.8 use case from the original dig command).

Library:
    dnspython (third-party, >= 2.1).

Command-line arguments:
    --name <dns_verify_name>    DNS name to query for TXT records.
    --resolver <ip>             Optional explicit DNS resolver IP (e.g. 8.8.8.8).
    --timeout <seconds>         Query lifetime in seconds (default 10, range 1-30).

Output:
    JSON object on stdout:
    {
      "name": "_cdnverify.example.com",
      "resolver": "system",
      "txt_records": ["verify-token-20240101"],
      "duration_ms": 42,
      "error": null
    }

    With --resolver 8.8.8.8, resolver reports "8.8.8.8".

Exit codes:
    0 — Probe completed (including soft failures like NXDOMAIN, NoAnswer).
    2 — Argument error or missing library import.

Security:
    --resolver accepts a single IPv4/IPv6 literal only (validated via
    ipaddress.ip_address). Hostnames, comma-separated lists, and non-IP
    strings are rejected with exit code 2.
    Query types restricted to TXT (no AXFR, SRV, NS, ANY).
    The host's /etc/resolv.conf is never echoed in the output.
"""

import argparse
import ipaddress
import json
import re
import sys
import time


def format_output(result_dict):
    """Wrap result in Yunbao standard output format."""
    error = result_dict.get("error")
    if error:
        return {
            "result": "failed",
            "data": result_dict,
            "error_msg": error.get("reason", "unknown_error"),
        }
    return {
        "result": "success",
        "data": result_dict,
        "error_msg": "",
    }


# RFC 1035 domain validation pattern.
# Note: allow underscore ('_') inside labels because CDN ownership-verification
# TXT record names (e.g. `cdn_verification`, `_cdn-verification`, `_dnsauth`)
# contain underscores by design. Hyphen still cannot start/end a label.
_DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)"
    r"(?!-)(?:[A-Za-z0-9_-]{1,63}(?<!-)\.)+"
    r"[A-Za-z0-9_-]{1,63}(?<!-)$"
)


def validate_name(name):
    """
    Validate a DNS name against RFC 1035.

    Returns:
        (True, None) on success.
        (False, reason) on failure.
    """
    if not name or not isinstance(name, str):
        return False, "empty"
    if not _DOMAIN_PATTERN.match(name):
        return False, "invalid_format"
    return True, None


def validate_resolver(resolver):
    """
    Validate that the resolver argument is a single IP literal.

    Returns:
        (True, None) on success.
        (False, reason) on failure.
    """
    if not resolver:
        return True, None  # Optional argument
    try:
        ipaddress.ip_address(resolver)
        return True, None
    except ValueError:
        return False, "not_ip_literal"


def validate_timeout(timeout):
    """
    Validate the timeout argument.

    Returns:
        (True, None) on success.
        (False, reason) on failure.
    """
    if timeout < 1 or timeout > 30:
        return False, "out_of_range"
    return True, None


def probe_dns_txt(name, resolver, timeout):
    """
    Perform the DNS TXT record probe.

    Returns:
        (result_dict, None) on success.
        (result_dict, error_dict) on soft failure.
    """
    start_ms = int(time.time() * 1000)
    resolver_label = resolver if resolver else "system"
    result = {
        "name": name,
        "resolver": resolver_label,
        "txt_records": [],
        "duration_ms": 0,
        "error": None,
    }

    try:
        import dns.resolver
    except ImportError:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "missing_library",
            "message": "Missing Python library: dnspython. Install with: pip install dnspython>=2.1",
        }
        return result, result["error"]

    try:
        if resolver:
            # Use explicit resolver
            custom_resolver = dns.resolver.Resolver(configure=False)
            custom_resolver.nameservers = [resolver]
            custom_resolver.lifetime = timeout
            answer = custom_resolver.resolve(name, "TXT", lifetime=timeout)
        else:
            # Use system default resolver
            answer = dns.resolver.resolve(name, "TXT", lifetime=timeout)

        # Flatten TXT RRset into a list of strings
        txt_records = []
        for rr in answer:
            # TXT records are lists of byte strings
            txt_parts = []
            for part in rr.strings:
                if isinstance(part, bytes):
                    txt_parts.append(part.decode("utf-8", errors="replace"))
                else:
                    txt_parts.append(str(part))
            txt_records.append("".join(txt_parts))

        result["txt_records"] = txt_records

    except dns.resolver.NXDOMAIN:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "dns_nxdomain",
            "message": "Domain '{}' does not exist".format(name),
        }
        return result, result["error"]
    except dns.resolver.NoAnswer:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "dns_no_answer",
            "message": "No TXT records found for '{}'".format(name),
        }
        return result, result["error"]
    except dns.resolver.LifetimeTimeout:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "dns_timeout",
            "message": "DNS query for '{}' timed out after {}s".format(
                name, timeout
            ),
        }
        return result, result["error"]
    except Exception as exc:
        exc_type_name = type(exc).__name__
        if "Timeout" in exc_type_name:
            reason = "dns_timeout"
        elif "NXDOMAIN" in exc_type_name:
            reason = "dns_nxdomain"
        else:
            reason = "unexpected_probe_error"
            print(
                "Unexpected error during DNS TXT probe: {}".format(exc),
                file=sys.stderr,
            )

        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": reason,
            "message": str(exc) if reason != "unexpected_probe_error" else "unexpected probe error",
        }
        return result, result["error"]

    result["duration_ms"] = int(time.time() * 1000) - start_ms
    return result, None


def main():
    parser = argparse.ArgumentParser(
        description="DNS TXT record probe. Queries TXT records for a given name and outputs JSON."
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="DNS name to query for TXT records.",
    )
    parser.add_argument(
        "--resolver",
        type=str,
        default=None,
        help="Optional explicit DNS resolver IP (e.g. 8.8.8.8). Must be a single IP literal.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Query lifetime in seconds (default 10, range 1-30).",
    )
    args, _ = parser.parse_known_args()

    # Validate name
    valid, reason = validate_name(args.name)
    if not valid:
        error_result = {
            "name": args.name,
            "resolver": args.resolver or "system",
            "txt_records": [],
            "duration_ms": 0,
            "error": {
                "reason": "invalid_name",
                "message": "Invalid DNS name '{}': {}".format(args.name, reason),
            },
        }
        print(json.dumps(format_output(error_result), ensure_ascii=False))
        sys.exit(2)

    # Validate resolver
    valid, reason = validate_resolver(args.resolver)
    if not valid:
        error_result = {
            "name": args.name,
            "resolver": args.resolver or "system",
            "txt_records": [],
            "duration_ms": 0,
            "error": {
                "reason": "invalid_resolver",
                "message": "Invalid resolver '{}': {} (must be a single IP literal)".format(
                    args.resolver, reason
                ),
            },
        }
        print(json.dumps(format_output(error_result), ensure_ascii=False))
        sys.exit(2)

    # Validate timeout
    valid, reason = validate_timeout(args.timeout)
    if not valid:
        error_result = {
            "name": args.name,
            "resolver": args.resolver or "system",
            "txt_records": [],
            "duration_ms": 0,
            "error": {
                "reason": "invalid_timeout",
                "message": "Timeout must be in range [1, 30], got {}".format(
                    args.timeout
                ),
            },
        }
        print(json.dumps(format_output(error_result), ensure_ascii=False))
        sys.exit(2)

    result, _ = probe_dns_txt(args.name, args.resolver, args.timeout)
    print(json.dumps(format_output(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
