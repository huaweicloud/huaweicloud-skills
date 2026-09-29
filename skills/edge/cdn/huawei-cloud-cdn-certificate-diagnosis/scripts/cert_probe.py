#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TLS certificate chain probe script.

Function:
    Connect to <domain>:443 via TLS, extract the peer certificate's
    subject CN, issuer CN, notBefore, notAfter, and SAN list, and
    output a single JSON object on stdout.

Library:
    ssl + socket (Python standard library only — no third-party dependency).

Command-line arguments:
    --domain <domain>      Target domain for TLS certificate probing.
    --timeout <seconds>    Connection timeout in seconds (default 10, range 1-30).

Output:
    JSON object on stdout:
    {
      "domain": "example.com",
      "connected": true,
      "tls": {
        "subject_cn": "example.com",
        "issuer_cn": "DigiCert Global G2",
        "not_before": "2025-01-01T00:00:00Z",
        "not_after": "2026-01-01T00:00:00Z",
        "san_list": ["example.com", "www.example.com"]
      },
      "duration_ms": 312,
      "error": null
    }

Exit codes:
    0 — Probe completed (including soft failures like TLS handshake failure).
    2 — Argument error or missing library import.

Security:
    Uses ssl.create_default_context() with check_hostname=True and
    verify_mode=ssl.CERT_REQUIRED. Does NOT relax verification under any
    code path. Does NOT modify the trust store. Does NOT output raw
    DER/PEM bytes or private key material.
"""

import argparse
import datetime
import json
import re
import socket
import ssl
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


def parse_rfc2822_to_iso8601(rfc2822_str):
    """
    Convert an RFC 2822 date string (e.g. 'Jan  1 00:00:00 2025 GMT')
    to ISO 8601 UTC (e.g. '2025-01-01T00:00:00Z').
    """
    try:
        dt = datetime.datetime.strptime(rfc2822_str, "%b %d %H:%M:%S %Y %Z")
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        try:
            dt = datetime.datetime.strptime(rfc2822_str, "%b %d %H:%M:%S %Y")
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            return rfc2822_str


def extract_san_list(cert):
    """
    Extract the subjectAltName list from a parsed certificate dict.
    """
    san_list = []
    san = cert.get("subjectAltName")
    if san:
        for san_type, san_value in san:
            if san_type.lower() == "dns":
                san_list.append(san_value)
    return san_list


def extract_cert_info(cert):
    """
    Extract subject CN, issuer CN, notBefore, notAfter, SAN from a
    parsed peer certificate dict.
    """
    subject = cert.get("subject", ())
    issuer = cert.get("issuer", ())

    subject_cn = ""
    for rdn in subject:
        for key, value in rdn:
            if key == "commonName":
                subject_cn = value
                break

    issuer_cn = ""
    for rdn in issuer:
        for key, value in rdn:
            if key == "commonName":
                issuer_cn = value
                break

    not_before = parse_rfc2822_to_iso8601(cert.get("notBefore", ""))
    not_after = parse_rfc2822_to_iso8601(cert.get("notAfter", ""))
    san_list = extract_san_list(cert)

    return {
        "subject_cn": subject_cn,
        "issuer_cn": issuer_cn,
        "not_before": not_before,
        "not_after": not_after,
        "san_list": san_list,
    }


def probe_tls(domain, timeout):
    """
    Perform the TLS certificate probe.

    Returns:
        (result_dict, None) on success.
        (result_dict, error_dict) on soft failure.
    """
    start_ms = int(time.time() * 1000)
    result = {
        "domain": domain,
        "connected": False,
        "tls": None,
        "duration_ms": 0,
        "error": None,
    }

    try:
        sock = socket.create_connection((domain, 443), timeout=timeout)
    except socket.timeout:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "connect_timeout",
            "message": "Connection to {}:{} timed out after {}s".format(
                domain, 443, timeout
            ),
        }
        return result, result["error"]
    except (ConnectionRefusedError, OSError) as exc:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "connect_failed",
            "message": str(exc),
        }
        return result, result["error"]

    try:
        context = ssl.create_default_context()
        # Explicitly enforce verification (default, but documented for clarity)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        ssl_sock = context.wrap_socket(sock, server_hostname=domain)
        result["connected"] = True

        cert = ssl_sock.getpeercert()
        if cert:
            result["tls"] = extract_cert_info(cert)

        ssl_sock.close()
    except ssl.SSLError as exc:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "tls_handshake_failed",
            "message": str(exc),
        }
        return result, result["error"]
    except socket.timeout:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "connect_timeout",
            "message": "TLS handshake timed out after {}s".format(timeout),
        }
        return result, result["error"]
    except Exception as exc:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "unexpected_probe_error",
            "message": "unexpected probe error",
        }
        # Full traceback to stderr only, not stdout
        print("Unexpected error during TLS probe: {}".format(exc), file=sys.stderr)
        return result, result["error"]
    finally:
        try:
            sock.close()
        except Exception:
            pass

    result["duration_ms"] = int(time.time() * 1000) - start_ms
    return result, None


def main():
    parser = argparse.ArgumentParser(
        description="TLS certificate chain probe. Connects to <domain>:443 and extracts peer certificate metadata as JSON."
    )
    parser.add_argument(
        "--domain",
        type=str,
        required=True,
        help="Target domain for TLS certificate probing.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Connection timeout in seconds (default 10, range 1-30).",
    )
    args, _ = parser.parse_known_args()

    # Validate domain
    valid, reason = validate_domain(args.domain)
    if not valid:
        error_result = {
            "domain": args.domain,
            "connected": False,
            "tls": None,
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
            "connected": False,
            "tls": None,
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

    result, _ = probe_tls(args.domain, args.timeout)
    print(json.dumps(format_output(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
