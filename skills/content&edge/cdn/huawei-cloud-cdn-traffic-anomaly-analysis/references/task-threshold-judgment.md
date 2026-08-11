# Step 7: Threshold Judgment

Compare queried metrics against absolute thresholds and baseline statistics. Generate a three-tier analysis report.

---

## Dual-Threshold Rules

### Tier 1: Absolute Threshold (Hard Anomaly)

Based on the billing mode obtained in Step 1, check whether the current window exceeds the absolute threshold:

| Billing Mode | Current Metric | Absolute Threshold | Judgment |
|-------------|---------------|-------------------|----------|
| `bw_95` | 7-day P95 aggregate (bit/s) | ≥ 8,000,000,000 (8 Gbps) | ⚠️ Anomalous |
| `flux` / `combine_flux` | Any day's traffic (Byte) | > 5,497,558,138,880 (5 TB) | ⚠️ Anomalous |
| `bw` / `bw_peak` | Any day's peak bandwidth (bit/s) | ≥ 3,000,000,000 (3 Gbps) | ⚠️ Anomalous |

If the absolute threshold is exceeded → **⚠️ Anomalous** (skip tier 2 evaluation).

### Tier 2: Relative Baseline Comparison (Surge Detection)

If absolute threshold is **NOT** exceeded, compare current values against the baseline:

| Billing Mode | Current Metric | Baseline Reference | Multiplier | Judgment |
|-------------|---------------|-------------------|------------|----------|
| `bw_95` | 7-day P95 aggregate | baseline_max (of 3 × 30-day windows) | × 1.5 | 👀 Watch |
| `flux` / `combine_flux` | Each day's traffic | baseline_P95 (of 90 daily values) | × 1.5 | 👀 Watch |
| `bw` / `bw_peak` | Each day's peak bandwidth | baseline_P95 (of 90 daily values) | × 1.5 | 👀 Watch |

If any daily value (or aggregate, for bw_95) exceeds baseline reference × multiplier → **👀 Watch**.

### Tier 3: Normal

Neither absolute threshold nor relativebaseline exceeded → **✅ Normal**.

### No Data Handling

If API returns `result: {}` or `value: 0`, the domain has no traffic data in the query period → treat as **✅ Normal**.

---

## Baseline Statistics Computation

### bw_95 Path

From the 3 baseline `ShowBandwidthCalc` calls, each returning a single P95 value:

```
baseline_values = [v1, v2, v3]  // bit/s
baseline_mean   = sum(baseline_values) / 3
baseline_max    = max(baseline_values)
baseline_min    = min(baseline_values)
relative_limit  = baseline_max × 1.5
```

### flux / bw Path

From the first 90 entries of the 97-day `ShowDomainStats/v2` result:

```
baseline_daily  = result[0:90]          // 90 daily values
baseline_mean   = mean(baseline_daily)
baseline_P95    = percentile(baseline_daily, 95)  // 95th percentile
baseline_max    = max(baseline_daily)
relative_limit  = baseline_P95 × 1.5
```

---

## Output Format

### ⚠️ Anomalous Domain Output (Absolute Threshold Exceeded)

```
==================== CDN Traffic Anomaly Analysis Report ====================
Analysis Time: 2026-08-09 10:00:00
Target Domain: www.example.com
Billing Mode: bw_95 (95th Percentile Bandwidth)
Metric: 7-Day P95 Bandwidth
Current Window: 2026-08-02 ~ 2026-08-08 (7 days)

--- Baseline (Past 3 Months) ---
Window 1 (2026-05-05 ~ 2026-06-04): 5.2 Gbps
Window 2 (2026-06-04 ~ 2026-07-04): 6.1 Gbps
Window 3 (2026-07-04 ~ 2026-08-02): 5.8 Gbps
Baseline Mean: 5.7 Gbps   Baseline Max: 6.1 Gbps

--- Current Window ---
7-Day P95 Bandwidth: 8.7 Gbps

--- Analysis Results ---
Status: ⚠️ Anomalous
  → Exceeds absolute threshold: 8.7 Gbps ≥ 8 Gbps
  → Deviation from baseline max: +42.6%

Conclusion: Current 7-day P95 bandwidth exceeds 8 Gbps absolute threshold.
Recommend investigating for potential traffic theft or abnormal business activity.
```

### 👀 Watch Domain Output (Relative Surge Only)

```
==================== CDN Traffic Anomaly Analysis Report ====================
Analysis Time: 2026-08-09 10:00:00
Target Domain: www.example.com
Billing Mode: flux (Traffic-based)
Metric: Daily Traffic
Current Window: 2026-08-02 ~ 2026-08-08 (7 days)

--- Baseline (Past 3 Months) ---
Period: 2026-05-04 ~ 2026-08-01 (90 days)
Daily Mean: 1.2 TB   Daily P95: 2.8 TB   Daily Max: 4.1 TB
Relative Limit (P95 × 1.5): 4.2 TB

--- Current Window ---
├─ 2026-08-02: Daily Traffic=2.1 TB
├─ 2026-08-03: Daily Traffic=1.8 TB
├─ 2026-08-04: Daily Traffic=2.5 TB
├─ 2026-08-05: Daily Traffic=3.9 TB 👀 (+39.3% vs P95)
├─ 2026-08-06: Daily Traffic=4.5 TB 👀 (+60.7% vs P95)
├─ 2026-08-07: Daily Traffic=2.2 TB
└─ 2026-08-08: Daily Traffic=1.9 TB

--- Analysis Results ---
Status: 👀 Watch
  → No day exceeds absolute threshold (5 TB)
  → 2 out of 7 days exceed baseline P95 × 1.5 (4.2 TB):
    - 2026-08-05: 3.9 TB (+39.3%)
    - 2026-08-06: 4.5 TB (+60.7%)

Conclusion: Traffic shows relative surge on 2 days compared to the 3-month baseline.
No absolute threshold exceeded. Recommend monitoring for continued surge patterns.
```

### ✅ Normal Domain Output

```
==================== CDN Traffic Anomaly Analysis Report ====================
Analysis Time: 2026-08-09 10:00:00
Target Domain: www.example.com
Billing Mode: bw (Bandwidth-based)
Metric: Daily Peak Bandwidth
Current Window: 2026-08-02 ~ 2026-08-08 (7 days)

--- Baseline (Past 3 Months) ---
Period: 2026-05-04 ~ 2026-08-01 (90 days)
Daily Mean: 1.2 Gbps   Daily P95: 2.1 Gbps   Daily Max: 2.8 Gbps
Relative Limit (P95 × 1.5): 3.15 Gbps

--- Current Window ---
├─ 2026-08-02: Daily Peak=1.5 Gbps
├─ 2026-08-03: Daily Peak=1.2 Gbps
├─ 2026-08-04: Daily Peak=1.8 Gbps
├─ 2026-08-05: Daily Peak=2.0 Gbps
├─ 2026-08-06: Daily Peak=1.6 Gbps
├─ 2026-08-07: Daily Peak=1.3 Gbps
└─ 2026-08-08: Daily Peak=1.7 Gbps

--- Analysis Results ---
Status: ✅ Normal
  → No day exceeds absolute threshold (3 Gbps)
  → No day exceeds baseline P95 × 1.5 (3.15 Gbps)
  → Traffic within normal range, consistent with historical baseline

Conclusion: Traffic normal for past 7 days. No anomalies detected.
```