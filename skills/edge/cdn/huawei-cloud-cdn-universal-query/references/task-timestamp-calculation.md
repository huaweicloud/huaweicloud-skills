# Timestamp Calculation

Calculate the time range for CDN API queries, aligned to UTC+8 midnight. All CDN APIs require **millisecond-precision UTC timestamps**.

## Built-in Tool

Use the built-in script `scripts/cdn_timestamp.py` to calculate timestamps.

## Usage

```bash
# Past 3 days (default) — outputs JSON with start_time and end_time
python scripts/cdn_timestamp.py --days 3

# Past 7 days
python scripts/cdn_timestamp.py --days 7

# Last full month
python scripts/cdn_timestamp.py --month

# Current month (1st to today)
python scripts/cdn_timestamp.py --cur-month

# Specific date
python scripts/cdn_timestamp.py --date 2026-08-11
```

**Example output:**
```json
{"result": "success", "data": {"start_time": 1786291200000, "end_time": 1786550400000, "start_date": "2026-08-10", "end_date": "2026-08-13"}, "error_msg": ""}
```

**Usage flow**: Run the script first to get the timestamp values, then manually fill them into the `--start_time` and `--end_time` parameters of the hcloud command.

## Script Options

| Option | Description |
|--------|-------------|
| `--days N` | Past N days (default 3) |
| `--month` | Last month (full month) |
| `--cur-month` | Current month (1st to today) |
| `--date YYYY-MM-DD` | Specific date (00:00 to next day 00:00) |

## Important Notes

> When `interval=86400`, timestamps must be aligned to **UTC+8 midnight**. The script handles this alignment automatically.
