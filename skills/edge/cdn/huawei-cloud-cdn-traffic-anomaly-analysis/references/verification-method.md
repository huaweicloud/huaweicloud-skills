# Verification Method

Verify the analysis results are correct and complete.

## Verification Steps

### 1. Verify Billing Mode

```bash
hcloud CDN ShowChargeModes --cli-region=cn-north-1 --product_type=base
```

Check that the returned `charge_mode` matches the expected billing mode.

### 2. Verify Domain Exists

```bash
hcloud CDN ListDomains/v2 --cli-region=cn-north-1 --page_size=100 --domain_status=online
```

Check that the target domain is in the returned list.

### 3. Verify Current Window Metric Query

Based on billing mode, run the corresponding query and check the response:

- **bw_95**: `ShowBandwidthCalc` should return `bandwidth_calc.value` (single aggregate, bit/s)
- **flux/combine_flux**: `ShowDomainStats/v2` with `stat_type=flux` should return daily traffic values (Byte)
- **bw/bw_peak**: `ShowDomainStats/v2` with `stat_type=bw` should return daily peak bandwidth values (bit/s)

### 4. Verify Baseline Metric Query

- **bw_95**: Run `cdn_timestamp.py --baseline` to generate 3 × 30-day windows, then call `ShowBandwidthCalc` for each. Verify 3 aggregate values are returned.
- **flux/bw**: Run `cdn_timestamp.py --baseline` to generate 3 × 30-day windows, then call `ShowDomainStats/v2` for each (plus the 7-day current query from section 3). Verify each call returns daily values and that a single 97-day query is NOT used (interval=86400 max range 31-32 days).

### 5. Verify Threshold Judgment

| Billing Mode | Current Metric | Absolute Threshold | Relative Baseline |
|--------------|---------------|-------------------|-------------------|
| bw_95 | 7-day P95 bandwidth (bit/s) | ≥ 8 Gbps → ⚠️ | current > baseline_max × 1.5 → 👀 |
| flux/combine_flux | Daily traffic (Byte) | Any day > 5 TB → ⚠️ | Any day > baseline_P95 × 1.5 → 👀 |
| bw/bw_peak | Daily peak bandwidth (bit/s) | Any day ≥ 3 Gbps → ⚠️ | Any day > baseline_P95 × 1.5 → 👀 |

### 6. Verify Output Format

Check that the output report includes:
- Analysis time and target domain
- Billing mode and metric type
- Baseline statistics (mean, P95/max, relative limit)
- Current window daily values with deviation percentages
- Three-tier conclusion (Normal / Watch / Anomalous)

## Expected Output

The output should follow the format specified in [task-threshold-judgment.md](task-threshold-judgment.md).