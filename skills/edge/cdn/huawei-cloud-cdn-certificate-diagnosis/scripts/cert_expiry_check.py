#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CDN certificate days-remaining calculation script.

Function:
    Given expiration_time (ms timestamp), compute the days remaining until
    certificate expiration and output JSON.

Decision logic:
    days_remaining > 30           → status=normal
    0 < days_remaining ≤ 30       → status=warning
    days_remaining ≤ 0            → status=expired

If expiration_time is empty or missing, output
{"days_remaining": null, "status": "unknown"} and perform no calculation.

Command-line argument:
    --expiration_time <ms-timestamp>

Output:
    JSON format: {"days_remaining": <int|null>, "status": "normal|warning|expired|unknown"}

Note:
    This script handles only the days-remaining calculation logic; it does not
    handle business flow (e.g., API calls, report generation).
"""

import argparse
import json
import sys
import time


def format_output(result_dict):
    """Wrap result in Yunbao standard output format."""
    return {
        "result": "success",
        "data": result_dict,
        "error_msg": "",
    }


def parse_expiration_time(raw_value):
    """
    Parse the expiration_time argument.

    Returns:
        (int, None) on success, where int is the ms timestamp.
        (None, reason) on failure, where reason is the failure cause.
    """
    if raw_value is None or raw_value == "":
        return None, "empty"

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None, "invalid"

    if value <= 0:
        return None, "invalid"

    return value, None


def compute_days_remaining(expiration_time_ms, now_ms=None):
    """
    Compute days remaining from a ms timestamp.

    Parameters:
        expiration_time_ms: certificate expiration time (ms timestamp)
        now_ms: current time (ms timestamp); defaults to time.time() * 1000

    Returns:
        int: days remaining (floor; may be negative)
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)

    diff_ms = expiration_time_ms - now_ms
    # Floor: less than 1 day remaining counts as 0 days (about to expire)
    days_remaining = int(diff_ms // (24 * 60 * 60 * 1000))
    return days_remaining


def decide_status(days_remaining):
    """
    Decide status based on days remaining.

    Decision logic:
        days_remaining > 30           → normal
        0 < days_remaining ≤ 30       → warning
        days_remaining ≤ 0            → expired
    """
    if days_remaining > 30:
        return "normal"
    elif days_remaining > 0:
        return "warning"
    else:
        return "expired"


def build_result(days_remaining, status):
    """Build the JSON output dict."""
    return {"days_remaining": days_remaining, "status": status}


def main():
    parser = argparse.ArgumentParser(
        description="Compute CDN certificate days remaining and output JSON result."
    )
    parser.add_argument(
        "--expiration_time",
        type=str,
        default="",
        help="Certificate expiration time (ms timestamp). When empty or missing, outputs unknown status.",
    )
    args, _ = parser.parse_known_args()

    expiration_time_ms, reason = parse_expiration_time(args.expiration_time)

    # When expiration_time is empty or missing, perform no calculation
    if expiration_time_ms is None:
        result = build_result(None, "unknown")
        print(json.dumps(format_output(result), ensure_ascii=False))
        return

    days_remaining = compute_days_remaining(expiration_time_ms)
    status = decide_status(days_remaining)
    result = build_result(days_remaining, status)
    print(json.dumps(format_output(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
