#!/usr/bin/env python3
"""Fetch a CDN access-log file, decompress it, and extract abnormal-status rows.

This is a read-only helper for the CDN abnormal status-code analysis skill.
It downloads a single CDN log download link (as returned by `hcloud CDN
ShowLogs`), decompresses the gzip payload, and prints the log lines whose
status field matches the requested status codes as a single JSON object on
stdout. Diagnostic messages go to stderr.

Usage:
    python scripts/fetch_cdn_log.py --url <log_download_url> \
        [--status 403,502,503,504] [--timeout 30] [--max-lines 200]

The CDN access-log format follows the Huawei Cloud official field order
(see https://support.huaweicloud.com/intl/zh-cn/bestpractice-cdn/cdn_01_0252.html):

    [time] client_ip rt referer protocol method host url status
    size cache_status user_agent range edge_node_ip

| # | Field (official) | Example | Note |
|---|------------------|---------|------|
| 1 | time (log generated time) | `[10/Aug/2026:15:29:14 +0800]` | **contains a space** (time + timezone) — must be kept as ONE token when parsing |
| 2 | client_ip (access IP) | `116.205.148.159` | end-user source IP |
| 3 | rt (response time, ms) | `464` | |
| 4 | referer | `"http://testhw.laohand.com/"` or `-` | quoted; may be `-` |
| 5 | protocol (HTTP version) | `"HTTP/1.1"` | quoted |
| 6 | method (request method) | `"GET"` | quoted |
| 7 | host (accelerated domain) | `"testhw.laohand.com"` | quoted |
| 8 | url (request path) | `"/favicon.svg"` | quoted |
| 9 | status (HTTP status code) | `200` | 3-digit number |
| 10 | size (returned bytes) | `2291` | |
| 11 | cache_status (hit status) | `HIT` / `MISS` | |
| 12 | user_agent | `"Mozilla/5.0 ..."` or `"curl/8.2.1"` | quoted; **contains spaces** |
| 13 | range | `-` or `bytes=-256` | |
| 14 | edge_node_ip (CDN serving IP) | `183.60.255.103` | |

Exit codes:
    0  probe ran to completion (including soft failures: HTTP 4xx/5xx,
       empty result, bad gzip)
    2  argument or missing-library prerequisite failure
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
from typing import List, Optional


def _emit(obj: dict) -> None:
    """Emit exactly one JSON object on stdout."""
    json.dump(obj, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _fail(reason: str, message: str, url: str, **extra) -> None:
    payload = {"url": url, "rows": [], "count": 0, "error": {"reason": reason, "message": message}}
    payload.update(extra)
    _emit(payload)
    sys.exit(0)  # soft failure: exit 0 so the caller can parse JSON


def _parse_status(token: str) -> Optional[int]:
    token = token.strip().strip('"')
    if token.isdigit():
        return int(token)
    return None


def _split_fields(raw: str) -> List[str]:
    """Split one CDN log line into the official 14 fields.

    The first field is a bracketed timestamp that itself contains a space
    (e.g. `[10/Aug/2026:15:29:14 +0800]`), so it must be captured as ONE
    token before splitting the remainder. Quoted fields (referer, protocol,
    method, host, url, user_agent) may contain spaces and are kept together
    via shlex. Field order follows the Huawei Cloud official log format.
    """
    import re
    import shlex
    m = re.match(r'^(\[[^\]]*\])\s*(.*)$', raw, re.DOTALL)
    if m:
        time_token = m.group(1)          # e.g. [10/Aug/2026:15:29:14 +0800]
        rest = m.group(2)
        try:
            parts = shlex.split(rest, posix=True)
        except ValueError:
            parts = rest.split()
        return [time_token] + parts
    try:
        return shlex.split(raw, posix=True)
    except ValueError:
        return raw.split()


def _extract_rows(text: str, statuses: set, max_lines: int) -> List[dict]:
    rows: List[dict] = []
    # Official 14-field order (Huawei Cloud CDN log format):
    # 0 time, 1 client_ip, 2 rt, 3 referer, 4 protocol, 5 method,
    # 6 host, 7 url, 8 status, 9 size, 10 cache_status,
    # 11 user_agent, 12 range, 13 edge_node_ip
    for raw in text.splitlines():
        if not raw.strip():
            continue
        parts = _split_fields(raw)
        if len(parts) < 9:
            # Too few fields to contain a status token — skip malformed lines.
            continue
        status_val = _parse_status(parts[8])
        # Fallback: if the fixed position is not a status code (e.g. a
        # malformed or non-standard line), scan for the first 3-digit code.
        if status_val is None:
            for tok in parts:
                s = _parse_status(tok)
                if s is not None and 100 <= s < 600:
                    status_val = s
                    break
        if status_val is None or status_val not in statuses:
            continue
        row = {
            "status": status_val,
            "client_ip": parts[1] if len(parts) > 1 else "",
            "url": parts[7] if len(parts) > 7 else "",
            "cache_status": parts[10] if len(parts) > 10 else "",
            "user_agent": parts[11] if len(parts) > 11 else "",
            "edge_node_ip": parts[13] if len(parts) > 13 else "",
            "time": parts[0] if parts else "",
            "raw": raw,
        }
        rows.append(row)
        if len(rows) >= max_lines:
            break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch/decompress a CDN log and extract abnormal-status rows (read-only)."
    )
    parser.add_argument("--url", required=True, help="CDN log download link (http/https only)")
    parser.add_argument("--status", default="403,404,499,500,502,503,504,530",
                        help="Comma-separated HTTP status codes to extract")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Request timeout in seconds, range [1, 60]")
    parser.add_argument("--max-lines", type=int, default=200,
                        help="Maximum matching rows to return, range [1, 10000]")
    args = parser.parse_args()

    # Validate args.
    if not (args.url.lower().startswith("http://") or args.url.lower().startswith("https://")):
        _fail("invalid_url", "URL must use http or https scheme", args.url)
    if not (1 <= args.timeout <= 60):
        print(json.dumps({"error": {"reason": "invalid_timeout",
                                    "message": "--timeout must be in [1, 60]"}}))
        return 2
    if not (1 <= args.max_lines <= 10000):
        print(json.dumps({"error": {"reason": "invalid_max_lines",
                                    "message": "--max-lines must be in [1, 10000]"}}))
        return 2

    try:
        statuses = {int(s.strip()) for s in args.status.split(",") if s.strip().isdigit()}
    except ValueError:
        _fail("invalid_status", "--status must be comma-separated integers", args.url)
    if not statuses:
        _fail("invalid_status", "no valid status codes parsed from --status", args.url)

    try:
        import requests  # noqa: required dependency
    except ImportError:
        print(json.dumps({"url": args.url, "rows": [], "count": 0,
                          "error": {"reason": "missing_library",
                                    "message": "requests>=2.25 is required; pip install requests>=2.25"}}))
        return 2

    import time
    t0 = time.time()
    try:
        resp = requests.get(args.url, timeout=args.timeout, allow_redirects=True, stream=True)
    except requests.exceptions.Timeout:
        _fail("connect_timeout", f"request timed out after {args.timeout}s", args.url,
              duration_ms=int((time.time() - t0) * 1000))
    except requests.exceptions.RequestException as exc:
        _fail("connect_failed", str(exc), args.url,
              duration_ms=int((time.time() - t0) * 1000))

    http_status = resp.status_code
    if http_status != 200:
        _fail("http_error", f"download returned HTTP {http_status}", args.url,
              http_status=http_status, duration_ms=int((time.time() - t0) * 1000))

    raw_bytes = resp.content
    # Decompress gzip if needed.
    if raw_bytes[:2] == b"\x1f\x8b":
        try:
            text = gzip.decompress(raw_bytes).decode("utf-8", errors="replace")
        except OSError as exc:
            _fail("bad_gzip", f"failed to decompress gzip: {exc}", args.url,
                  http_status=http_status, duration_ms=int((time.time() - t0) * 1000))
    else:
        text = raw_bytes.decode("utf-8", errors="replace")

    rows = _extract_rows(text, statuses, args.max_lines)
    _emit({
        "url": args.url,
        "http_status": http_status,
        "byte_size": len(raw_bytes),
        "status_filter": sorted(statuses),
        "rows": rows,
        "count": len(rows),
        "duration_ms": int((time.time() - t0) * 1000),
        "error": None,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
