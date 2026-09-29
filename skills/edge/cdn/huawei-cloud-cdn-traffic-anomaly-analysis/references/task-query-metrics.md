# Step 5-6: Query Traffic/Bandwidth Metrics

Query the corresponding metrics for both the current window and the baseline window, based on the billing mode obtained in Step 1.

---

## Current Window: 7 Days

### Billing Mode = `bw_95` (Query 7-Day P95 Bandwidth — Single Aggregate)

**API behavior:** `ShowBandwidthCalc` returns a **single aggregate value** for the entire query period — no per-day breakdown. Maximum query range is **31 days**.

```bash
hcloud CDN ShowBandwidthCalc \
  --cli-region=cn-north-1 \
  --domain_name=<domain> \
  --calc_type=bw_95 \
  --start_time=<7-days-ago-00:00-ms> \
  --end_time=<today-00:00-ms>
```

**Response Parsing:**
- `bandwidth_calc.value` — single P95 value for the entire 7-day window, unit is **bit/s**
- `bandwidth_calc.time_point` — timestamp when the 95th percentile peak occurred (ms)
- Conversion: `value / 10^9` to get Gbps
- The `value` represents the P95 bandwidth across all 5-minute data points within the 7 days

```json
{
  "bandwidth_calc": {
    "value": 8750000000,
    "calc_type": "bw_95",
    "time_point": 1786082700000
  }
}
```

### Billing Mode = `flux` / `combine_flux` (Query Daily Traffic)

**API behavior:** `ShowDomainStats/v2` with `interval=86400` returns one data point per day, but the **max query range is 31-32 days** — a single 97-day query fails (`CDN.0202`). Query the current 7-day window in one call (baseline is handled in 3 separate 30-day calls in the baseline section below).

```bash
hcloud CDN ShowDomainStats/v2 \
  --cli-region=cn-north-1 \
  --domain_name=<domain> \
  --stat_type=flux \
  --interval=86400 \
  --start_time=<7-days-ago-00:00-ms> \
  --end_time=<today-00:00-ms> \
  --action=detail
```

**Response Parsing:**
- `result.<domain>` is an array, each element is one day's data (7 entries for the current window)
- `value` unit is **Byte**
- Conversion: `value / 1024^4` to get TB
- The 7 daily values are compared against the baseline (absolute threshold + baseline_P95 × 1.5)

### Billing Mode = `bw` / `bw_peak` (Query Daily Peak Bandwidth)

Same strategy as flux — 1 call for the current 7-day window (`stat_type=bw`).

```bash
hcloud CDN ShowDomainStats/v2 \
  --cli-region=cn-north-1 \
  --domain_name=<domain> \
  --stat_type=bw \
  --interval=86400 \
  --start_time=<7-days-ago-00:00-ms> \
  --end_time=<today-00:00-ms> \
  --action=detail
```

**Response Parsing:**
- `result.<domain>` is an array, each element is one day's data
- `value` unit is **bit/s**, peak bandwidth for that day
- Conversion: `value / 10^9` to get Gbps

---

## Baseline Window: Past 3 Months

### Billing Mode = `bw_95` (3 × 30-Day Aggregates)

**Why 3 calls:** `ShowBandwidthCalc` max range is 31 days, and returns a single aggregate P95 value (no per-day data). To establish a 3-month baseline, query **3 non-overlapping 30-day windows**.

**Rate limit:** 2 calls/s — insert `sleep(0.6)` between calls.

```bash
# Generate 3 baseline window timestamps
python scripts/cdn_timestamp.py --baseline --raw
# Output (3 lines, each: start_ms end_ms) — values vary per run date; example below is illustrative only:
# <win1_start_ms> <win1_end_ms>  ← Window 1: today-97 ~ today-67
# <win2_start_ms> <win2_end_ms>  ← Window 2: today-67 ~ today-37
# <win3_start_ms> <win3_end_ms>  ← Window 3: today-37 ~ today-7

# Query each window separately
hcloud CDN ShowBandwidthCalc \
  --cli-region=cn-north-1 \
  --domain_name=<domain> \
  --calc_type=bw_95 \
  --start_time=<window_1_start> \
  --end_time=<window_1_end>
sleep 0.6

hcloud CDN ShowBandwidthCalc \
  --cli-region=cn-north-1 \
  --domain_name=<domain> \
  --calc_type=bw_95 \
  --start_time=<window_2_start> \
  --end_time=<window_2_end>
sleep 0.6

hcloud CDN ShowBandwidthCalc \
  --cli-region=cn-north-1 \
  --domain_name=<domain> \
  --calc_type=bw_95 \
  --start_time=<window_3_start> \
  --end_time=<window_3_end>
```

**Baseline statistics to compute from the 3 aggregate values:**
- `baseline_mean` — average of 3 values
- `baseline_max` — maximum of 3 values (used as the relative threshold base)
- `baseline_min` — minimum of 3 values (for context only)

### Billing Mode = `flux` / `bw` / `bw_peak` (3 × 30-Day Daily Aggregates)

**Why 3 calls:** `ShowDomainStats/v2` with `interval=86400` has a max query range of 31-32 days, so the 3-month baseline must be split into **3 non-overlapping 30-day windows**, identical to the bw_95 path.

```bash
# Generate 3 baseline window timestamps (reuse --baseline from Step 4)
python scripts/cdn_timestamp.py --baseline --raw
# Output (3 lines, each: start_ms end_ms) — values vary per run date; example below is illustrative only:
# <win1_start_ms> <win1_end_ms>  ← Window 1: today-97 ~ today-67
# <win2_start_ms> <win2_end_ms>  ← Window 2: today-67 ~ today-37
# <win3_start_ms> <win3_end_ms>  ← Window 3: today-37 ~ today-7

# Query each window separately (stat_type=flux or bw per billing mode)
hcloud CDN ShowDomainStats/v2 \
  --cli-region=cn-north-1 \
  --domain_name=<domain> \
  --stat_type=<flux|bw> \
  --interval=86400 \
  --start_time=<window_1_start> \
  --end_time=<window_1_end> \
  --action=detail

hcloud CDN ShowDomainStats/v2 \
  --cli-region=cn-north-1 \
  --domain_name=<domain> \
  --stat_type=<flux|bw> \
  --interval=86400 \
  --start_time=<window_2_start> \
  --end_time=<window_2_end> \
  --action=detail

hcloud CDN ShowDomainStats/v2 \
  --cli-region=cn-north-1 \
  --domain_name=<domain> \
  --stat_type=<flux|bw> \
  --interval=86400 \
  --start_time=<window_3_start> \
  --end_time=<window_3_end> \
  --action=detail
```

**Baseline statistics to compute from the 3 windows:**
- `baseline_mean` — average of the 3 window aggregates (each window's daily values averaged, then averaged across windows)
- `baseline_P95` — 95th percentile across the daily values of all 3 windows (used as the relative threshold base)
- `baseline_max` — maximum daily value across all 3 windows (for context only)

---

## Unit Conversion Quick Reference

| Metric | API Unit | Absolute Threshold | Relative Multiplier | Conversion |
|--------|----------|-------------------|---------------------|------------|
| Daily Traffic | Byte | 5 TB | baseline_P95 × 1.5 | `value / 1024^4` |
| Daily Peak | bit/s | 3 Gbps | baseline_P95 × 1.5 | `value / 10^9` |
| P95 Aggregate (current 7d) | bit/s | 8 Gbps | baseline_max × 1.5 | `value / 10^9` |
| P95 Aggregate (baseline 30d) | bit/s | — | — (used as base) | `value / 10^9` |