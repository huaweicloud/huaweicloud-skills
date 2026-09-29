#!/usr/bin/env python3
"""CDN query reference - millisecond timestamp calculation tool

Usage:
    python cdn_timestamp.py                   # Default: past 3 days
    python cdn_timestamp.py --days 7          # Past 7 days
    python cdn_timestamp.py --month           # Last full month
    python cdn_timestamp.py --cur-month       # Current month (1st to today)
    python cdn_timestamp.py --date 2026-07-20 # Specific date (00:00 to next day 00:00)

Output format (cloud-compatible JSON):
    {"result": "success", "data": {"start_time": <ms>, "end_time": <ms>, ...}, "error_msg": ""}
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone, timedelta

# 日志输出到 stderr，不污染 stdout（stdout 是返回值通道）
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

TZ_CST = timezone(timedelta(hours=8))


def now_cst():
    """Current UTC+8 time"""
    return datetime.now(TZ_CST)


def to_ms(dt):
    """datetime -> millisecond timestamp (int)"""
    return int(dt.timestamp() * 1000)


def calc_range(days=None, month=False, cur_month=False, date=None):
    """Calculate time range, returns (start_ms, end_ms, start_str, end_str)"""
    today = now_cst().replace(hour=0, minute=0, second=0, microsecond=0)

    if date:
        dt = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=TZ_CST)
        start = dt
        end = dt + timedelta(days=1)
    elif month:
        first_this = today.replace(day=1)
        end = first_this
        start = (first_this - timedelta(days=1)).replace(day=1)
    elif cur_month:
        start = today.replace(day=1)
        end = today
    else:
        n = days or 3
        start = today - timedelta(days=n)
        end = today

    return to_ms(start), to_ms(end), start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(description="CDN millisecond timestamp calculator")
    parser.add_argument("--days", type=int, default=3, help="Past N days (default 3)")
    parser.add_argument("--month", action="store_true", help="Last full month")
    parser.add_argument("--cur-month", action="store_true", help="Current month (1st to today)")
    parser.add_argument("--date", type=str, help="Specific date YYYY-MM-DD")
    args, _ = parser.parse_known_args()

    try:
        start_ms, end_ms, start_str, end_str = calc_range(
            days=args.days, month=args.month, cur_month=args.cur_month, date=args.date
        )
        logger.info(f"Range: {start_str} 00:00 ~ {end_str} 00:00 (UTC+8)")

        result = {
            "result": "success",
            "data": {
                "start_time": start_ms,
                "end_time": end_ms,
                "start_date": start_str,
                "end_date": end_str,
            },
            "error_msg": "",
        }
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        result = {
            "result": "failed",
            "data": {},
            "error_msg": str(e),
        }
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
