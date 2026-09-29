#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP file verification probe script.

Function:
    Fetch a verification file via HTTP/HTTPS and report the status code,
    content length, and a content preview as a single JSON object on stdout.

Library:
    requests (third-party, >= 2.25).

Command-line arguments:
    --url <file_verify_url>    URL of the verification file to fetch.
    --timeout <seconds>        Request timeout in seconds (default 10, range 1-30).

Output:
    JSON object on stdout:
    {
      "url": "https://example.com/.well-known/verify.txt",
      "http_status": 200,
      "content_length": 36,
      "content_preview": "20240101-abcdef-verify-token",
      "duration_ms": 180,
      "error": null
    }

Exit codes:
    0 — Probe completed (including soft failures like HTTP 4xx/5xx).
    2 — Argument error or missing library import.

Security:
    Scheme restricted to http/https (no file://, ftp://, gopher://).
    Redirects are NOT followed (allow_redirects=False).
    No Authorization, Cookie, or caller-supplied headers are sent.
    content_preview is capped at 256 bytes, decoded as UTF-8 with errors="replace".
"""

import argparse
import json
import sys
import time
from urllib.parse import urlparse


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


def validate_url(url):
    """
    Validate the URL scheme is http or https only.

    Returns:
        (True, None) on success.
        (False, reason) on failure.
    """
    if not url or not isinstance(url, str):
        return False, "empty"
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "invalid_format"
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, "unsupported_scheme"
    if not parsed.netloc:
        return False, "missing_host"
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


def probe_file(url, timeout):
    """
    Perform the HTTP file verification probe.

    Returns:
        (result_dict, None) on success.
        (result_dict, error_dict) on soft failure.
    """
    start_ms = int(time.time() * 1000)
    result = {
        "url": url,
        "http_status": None,
        "content_length": None,
        "content_preview": None,
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

    try:
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=False,
        )
        result["http_status"] = response.status_code

        content = response.content or b""
        result["content_length"] = len(content)

        # Cap preview at 256 bytes, decode as UTF-8 with errors replaced
        preview_bytes = content[:256]
        try:
            result["content_preview"] = preview_bytes.decode(
                "utf-8", errors="replace"
            )
        except Exception:
            result["content_preview"] = ""

    except ImportError:
        result["duration_ms"] = int(time.time() * 1000) - start_ms
        result["error"] = {
            "reason": "missing_library",
            "message": "Missing Python library: requests. Install with: pip install requests>=2.25",
        }
        return result, result["error"]
    except Exception as exc:
        # Check for specific exception types from requests
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
                "Unexpected error during file probe: {}".format(exc),
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
        description="HTTP file verification probe. Fetches a URL and reports status, content length, and preview as JSON."
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="URL of the verification file to fetch (http or https only).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default 10, range 1-30).",
    )
    args, _ = parser.parse_known_args()

    # Validate URL
    valid, reason = validate_url(args.url)
    if not valid:
        error_result = {
            "url": args.url,
            "http_status": None,
            "content_length": None,
            "content_preview": None,
            "duration_ms": 0,
            "error": {
                "reason": "invalid_url",
                "message": "Invalid URL '{}': {}".format(args.url, reason),
            },
        }
        print(json.dumps(format_output(error_result), ensure_ascii=False))
        sys.exit(2)

    # Validate timeout
    valid, reason = validate_timeout(args.timeout)
    if not valid:
        error_result = {
            "url": args.url,
            "http_status": None,
            "content_length": None,
            "content_preview": None,
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

    result, _ = probe_file(args.url, args.timeout)
    print(json.dumps(format_output(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
