#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNS A-record resolution probe script.

Function:
    Resolve A records for a given domain and report the resolved IP
    addresses as a single JSON object on stdout.

Library:
    dnspython (third-party, >= 2.1).

Command-line arguments:
    --domain <domain_name>    Domain to resolve for A records.
    --timeout <seconds>       Query lifetime in seconds (default 10, range 1-30).

Output:
    JSON object on stdout:
    {
      "domain": "example.com",
      "resolved_ips": ["93.184.216.34"],
      "duration_ms": 38,
      "error": null
    }

    NXDOMAIN failure example:
    {
      "domain": "nope.example.invalid",
      "resolved_ips": [],
      "duration_ms": 27,
      "error": { "reason": "dns_nxdomain", "message": "..." }
    }

Exit codes:
    0 — Probe completed (including soft failures like NXDOMAIN, NoAnswer).
    2 — Argument error or missing library import.

Security:
    Query types restricted to A (no AXFR, SRV, NS, ANY).
    The host's /etc/resolv.conf is never echoed in the output.
"""

import argparse
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


# RFC 1035 domain validation pattern
_DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)"
    r"(?!-)(?:[A-Za-z0-9-]{1,63}(?<!-)\.)+"
    r"[A-Za-z0-9-]{1,63}(?<!-)$"
)


def validate_domain(domain):
    """
    Validate a domain name against RFC 1035.

    Returns:
        (True, None) on success.
        (False, reason) on failure.
    """
    if not domain or not isinstance(domain, str):
        return False, "empty"
    if not _DOMAIN_PATTERN.match(domain):
        return False, "invalid_format"
    return True, None


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


def probe_dns_resolve(domain, timeout):
    """
    Perform the DNS A-record resolution probe.

    Returns:
        (result_dict, None) on success.
        (result_dict, error_dict) on soft failure.
    """
    start_ms = int(time.time() * 1000)
    result = {
        "domain": domain,
        "resolved_ips": [],
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
        answer = dns.resolver.resolve(domain, "A", lifetime=timeout)

        # Flatten A RRset into a list of IP strings
        resolved_ips = []
        for rr in answer:
            resolved_ips.append(str(rr))

        result["resolved_ips"] = resolved_ips

    except dns.resolver.NXDOMAIN:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "dns_nxdomain",
            "message": "Domain '{}' does not exist".format(domain),
        }
        return result, result["error"]
    except dns.resolver.NoAnswer:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "dns_no_answer",
            "message": "No A records found for '{}'".format(domain),
        }
        return result, result["error"]
    except dns.resolver.LifetimeTimeout:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "dns_timeout",
            "message": "DNS query for '{}' timed out after {}s".format(
                domain, timeout
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
                "Unexpected error during DNS resolve probe: {}".format(exc),
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
        description="DNS A-record resolution probe. Resolves A records for a domain and outputs JSON."
    )
    parser.add_argument(
        "--domain",
        type=str,
        required=True,
        help="Domain to resolve for A records.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Query lifetime in seconds (default 10, range 1-30).",
    )
    args = parser.parse_args()

    # Validate domain
    valid, reason = validate_domain(args.domain)
    if not valid:
        error_result = {
            "domain": args.domain,
            "resolved_ips": [],
            "duration_ms": 0,
            "error": {
                "reason": "invalid_domain",
                "message": "Invalid domain '{}': {}".format(args.domain, reason),
            },
        }
        print(json.dumps(format_output(error_result), ensure_ascii=False))
        sys.exit(2)

    # Validate timeout
    valid, reason = validate_timeout(args.timeout)
    if not valid:
        error_result = {
            "domain": args.domain,
            "resolved_ips": [],
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

    result, _ = probe_dns_resolve(args.domain, args.timeout)
    print(json.dumps(format_output(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
