#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP/HTTPS origin reachability probe script.

Function:
    Connect to an origin server via HTTP or HTTPS and report the HTTP
    status code and connectivity as a single JSON object on stdout.
    Uses HEAD by default with a GET fallback when the origin returns
    HTTP 405 (Method Not Allowed).

Library:
    requests (third-party, >= 2.25).

Command-line arguments:
    --scheme <http|https>    URL scheme.
    --host <origin_addr>     Origin host (IP or domain).
    --port <port>            Origin port (1-65535).
    --timeout <seconds>      Request timeout in seconds (default 10, range 1-30).

Output:
    JSON object on stdout:
    {
      "scheme": "https",
      "host": "origin.example.com",
      "port": 443,
      "connected": true,
      "http_status": 200,
      "is_private_address": false,
      "duration_ms": 210,
      "error": null
    }

Exit codes:
    0 — Probe completed (including soft failures like HTTP 4xx/5xx).
    2 — Argument error or missing library import.

Security:
    Scheme restricted to http/https.
    Redirects are NOT followed (allow_redirects=False).
    is_private_address flag is set when the resolved host falls in a
    private/loopback/link-local range (accepted residual risk R-SEC-1).
    No Authorization, Cookie, or caller-supplied headers are sent.
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


# RFC 1035 domain validation pattern
_DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)"
    r"(?!-)(?:[A-Za-z0-9-]{1,63}(?<!-)\.)+"
    r"[A-Za-z0-9-]{1,63}(?<!-)$"
)


def validate_host(host):
    """
    Validate that the host is a well-formed IP literal or RFC 1035 domain.

    Returns:
        (True, None) on success.
        (False, reason) on failure.
    """
    if not host or not isinstance(host, str):
        return False, "empty"
    # Try IP literal first
    try:
        ipaddress.ip_address(host)
        return True, None
    except ValueError:
        pass
    # Try domain name
    if _DOMAIN_PATTERN.match(host):
        return True, None
    return False, "invalid_format"


def validate_port(port):
    """
    Validate the port argument.

    Returns:
        (True, None) on success.
        (False, reason) on failure.
    """
    if port < 1 or port > 65535:
        return False, "out_of_range"
    return True, None


def validate_scheme(scheme):
    """
    Validate the scheme argument.

    Returns:
        (True, None) on success.
        (False, reason) on failure.
    """
    if scheme.lower() not in ("http", "https"):
        return False, "unsupported_scheme"
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


def check_is_private_address(host):
    """
    Check if the host is a private/loopback/link-local IP address.

    Returns:
        True if the host is a private IP literal, False otherwise.
    """
    try:
        ip = ipaddress.ip_address(host)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
        )
    except ValueError:
        # Domain name — cannot determine without resolution
        return False


def probe_origin(scheme, host, port, timeout):
    """
    Perform the origin reachability probe.

    Returns:
        (result_dict, None) on success.
        (result_dict, error_dict) on soft failure.
    """
    start_ms = int(time.time() * 1000)
    result = {
        "scheme": scheme,
        "host": host,
        "port": port,
        "connected": False,
        "http_status": None,
        "is_private_address": check_is_private_address(host),
        "duration_ms": 0,
        "error": None,
    }

    try:
        import requests
    except ImportError:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "missing_library",
            "message": "Missing Python library: requests. Install with: pip install requests>=2.25",
        }
        return result, result["error"]

    url = "{}://{}:{}/".format(scheme, host, port)

    try:
        # Try HEAD first (matching original curl -o /dev/null behavior)
        response = requests.head(
            url,
            timeout=timeout,
            allow_redirects=False,
        )

        # Fallback to GET if HEAD is not allowed (HTTP 405)
        if response.status_code == 405:
            # Release the HEAD response before rebinding the variable, otherwise
            # its connection would be leaked.
            response.close()
            response = requests.get(
                url,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            )

        result["connected"] = True
        result["http_status"] = response.status_code
        # Always release the response; this also covers the non-405 HEAD path.
        response.close()

    except Exception as exc:
        # requests.exceptions.SSLError inherits from ConnectionError
        exc_type_name = type(exc).__name__
        exc_mro = [cls.__name__ for cls in type(exc).__mro__]
        if "ConnectTimeout" in exc_type_name or "TimeoutError" in exc_type_name:
            reason = "connect_timeout"
        elif "SSLError" in exc_type_name or "SSLError" in exc_mro:
            reason = "tls_handshake_failed"
        elif "ConnectionError" in exc_type_name or "ConnectionError" in exc_mro:
            reason = "connect_failed"
        else:
            reason = "unexpected_probe_error"
            print(
                "Unexpected error during origin probe: {}".format(exc),
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
        description="HTTP/HTTPS origin reachability probe. Connects to an origin and reports HTTP status as JSON."
    )
    parser.add_argument(
        "--scheme",
        type=str,
        required=True,
        help="URL scheme (http or https).",
    )
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="Origin host (IP literal or domain name).",
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Origin port (1-65535).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default 10, range 1-30).",
    )
    args, _ = parser.parse_known_args()

    # Validate scheme
    valid, reason = validate_scheme(args.scheme)
    if not valid:
        error_result = {
            "scheme": args.scheme,
            "host": args.host,
            "port": args.port,
            "connected": False,
            "http_status": None,
            "is_private_address": False,
            "duration_ms": 0,
            "error": {
                "reason": "invalid_scheme",
                "message": "Scheme must be 'http' or 'https', got '{}'".format(
                    args.scheme
                ),
            },
        }
        print(json.dumps(format_output(error_result), ensure_ascii=False))
        sys.exit(2)

    # Validate host
    valid, reason = validate_host(args.host)
    if not valid:
        error_result = {
            "scheme": args.scheme,
            "host": args.host,
            "port": args.port,
            "connected": False,
            "http_status": None,
            "is_private_address": False,
            "duration_ms": 0,
            "error": {
                "reason": "invalid_host",
                "message": "Invalid host '{}': {}".format(args.host, reason),
            },
        }
        print(json.dumps(format_output(error_result), ensure_ascii=False))
        sys.exit(2)

    # Validate port
    valid, reason = validate_port(args.port)
    if not valid:
        error_result = {
            "scheme": args.scheme,
            "host": args.host,
            "port": args.port,
            "connected": False,
            "http_status": None,
            "is_private_address": False,
            "duration_ms": 0,
            "error": {
                "reason": "invalid_port",
                "message": "Port must be in range [1, 65535], got {}".format(
                    args.port
                ),
            },
        }
        print(json.dumps(format_output(error_result), ensure_ascii=False))
        sys.exit(2)

    # Validate timeout
    valid, reason = validate_timeout(args.timeout)
    if not valid:
        error_result = {
            "scheme": args.scheme,
            "host": args.host,
            "port": args.port,
            "connected": False,
            "http_status": None,
            "is_private_address": False,
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

    result, _ = probe_origin(args.scheme, args.host, args.port, args.timeout)
    print(json.dumps(format_output(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
