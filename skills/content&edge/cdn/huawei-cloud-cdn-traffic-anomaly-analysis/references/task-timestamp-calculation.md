# Step 4: Timestamp Calculation

Calculate time ranges for the current window (default 7 days) and 3 baseline windows (30 days each), aligned to UTC+8 midnight.

## Built-in Tool

Use the built-in script `scripts/cdn_timestamp.py` to calculate timestamps.

## Current Window (Default 7 Days)

```bash
# Past 7 days (default)
read START_TIME END_TIME <<< $(python scripts/cdn_timestamp.py --raw --days 7)

# View time range
python scripts/cdn_timestamp.py --days 7
# Example output:
# start_time=1753228800000 end_time=1753833600000
# Range: 2026-08-02 00:00 ~ 2026-08-09 00:00 (UTC+8)
```

## Baseline Windows (3 × 30 Days)

```bash
# Generate 3 non-overlapping 30-day windows
python scripts/cdn_timestamp.py --baseline

# Raw output (one line per window, start_ms end_ms)
python scripts/cdn_timestamp.py --baseline --raw
# Example output:
# 1783728000000 1786320000000
# 1786320000000 1788912000000
# 1788912000000 1791504000000
```

**Window layout** (no overlap with current 7-day window):
- Window 1 (oldest): today-97 to today-67
- Window 2: today-67 to today-37
- Window 3 (most recent): today-37 to today-7

This ensures the baseline (90 days total) and current window (7 days) are cleanly separated without overlapping data.

## Script Options

| Option | Description |
|--------|-------------|
| `--days N` | Past N days (default 7) |
| `--baseline` | Output 3 × 30-day baseline windows |
| `--month` | Last month (full month) |
| `--cur-month` | Current month (1st to today) |
| `--date YYYY-MM-DD` | Specific date (00:00 to next day 00:00) |
| `--raw` | Output only raw millisecond timestamps |

## Important Notes

> When `interval=86400`, timestamps must be aligned to **UTC+8 midnight**. The script handles this alignment automatically.
>
> **ShowBandwidthCalc** max range is 31 days — baseline windows are set to 30 days to stay within the limit.