#!/usr/bin/env python3
"""CDN traffic anomaly analysis — millisecond timestamp calculation tool

Usage:
    python cdn_timestamp.py                   # Default: past 7 days
    python cdn_timestamp.py --days 14         # Past 14 days
    python cdn_timestamp.py --baseline        # 3×30-day baseline windows (no overlap with current)
    python cdn_timestamp.py --month           # Last full month
    python cdn_timestamp.py --cur-month       # Current month (1st to today)
    python cdn_timestamp.py --date 2026-07-20 # Specific date (00:00 to next day 00:00)

Output:
    Default mode:  start_time=<ms> end_time=<ms>
    Baseline mode: start_1=<ms> end_1=<ms> ... start_3=<ms> end_3=<ms>
    Raw mode:      raw millisecond timestamps only (space-separated)
"""

import argparse
from datetime import datetime, timezone, timedelta

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
        n = days or 7
        start = today - timedelta(days=n)
        end = today

    return to_ms(start), to_ms(end), start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def calc_baseline():
    """Calculate 3 non-overlapping 30-day baseline windows.

    Windows (backward from today, no overlap with current 7-day window):
      Window 1: today-97 to today-67  (oldest)
      Window 2: today-67 to today-37
      Window 3: today-37 to today-7   (most recent)

    Returns list of (start_ms, end_ms, start_str, end_str) for each window.
    """
    today = now_cst().replace(hour=0, minute=0, second=0, microsecond=0)

    windows = []
    # Window N (1=oldest, 3=most recent)
    for w in range(3, 0, -1):
        start = today - timedelta(days=w * 30 + 7)
        end = today - timedelta(days=(w - 1) * 30 + 7)
        windows.append((to_ms(start), to_ms(end), start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))

    return windows


def main():
    parser = argparse.ArgumentParser(description="CDN millisecond timestamp calculator")
    parser.add_argument("--days", type=int, default=7, help="Past N days (default 7)")
    parser.add_argument("--baseline", action="store_true", help="Output 3×30-day baseline windows")
    parser.add_argument("--month", action="store_true", help="Last full month")
    parser.add_argument("--cur-month", action="store_true", help="Current month (1st to today)")
    parser.add_argument("--date", type=str, help="Specific date YYYY-MM-DD")
    parser.add_argument("--raw", action="store_true", help="Output only raw millisecond timestamps")
    args = parser.parse_args()

    if args.baseline:
        windows = calc_baseline()
        if args.raw:
            # One line per window, start_ms end_ms
            for start_ms, end_ms, _, _ in windows:
                print(f"{start_ms} {end_ms}")
        else:
            for i, (start_ms, end_ms, start_str, end_str) in enumerate(windows, 1):
                print(f"baseline_{i}_start={start_ms} baseline_{i}_end={end_ms}")
                print(
                    f"# Window {i}: {start_str} 00:00 ~ {end_str} 00:00 (UTC+8, 30 days)"
                )
    else:
        start_ms, end_ms, start_str, end_str = calc_range(
            days=args.days, month=args.month, cur_month=args.cur_month, date=args.date
        )

        if args.raw:
            print(f"{start_ms} {end_ms}")
        else:
            print(f"start_time={start_ms} end_time={end_ms}")
            print(f"# Range: {start_str} 00:00 ~ {end_str} 00:00 (UTC+8)")


if __name__ == "__main__":
    main()