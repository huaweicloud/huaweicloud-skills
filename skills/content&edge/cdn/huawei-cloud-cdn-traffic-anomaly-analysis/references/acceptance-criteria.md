# Acceptance Criteria

## Functional Requirements

- [ ] Skill can query account billing mode via `ShowChargeModes`
- [ ] Skill can list all CDN domains via `ListDomains/v2`
- [ ] Skill validates target domain exists in domain list
- [ ] Skill calculates correct UTC+8 midnight-aligned timestamps for:
  - Current window (default 7 days)
  - Baseline windows (3 × 30-day non-overlapping windows)
- [ ] Skill selects correct metric based on billing mode:
  - `bw_95` → `ShowBandwidthCalc` (current: 1 × 7d, baseline: 3 × 30d)
  - `flux` / `combine_flux` → `ShowDomainStats/v2` (stat_type=flux, single 97d query)
  - `bw` / `bw_peak` → `ShowDomainStats/v2` (stat_type=bw, single 97d query)
- [ ] Skill correctly splits the 97-day ShowDomainStats result into baseline (first 90 days) and current (last 7 days)
- [ ] Skill respects API constraints:
  - ShowBandwidthCalc max range 31 days → baseline uses 30-day windows
  - ShowBandwidthCalc returns single aggregate value → no per-day breakdown expected
  - ShowDomainStats/v2 supports ≥365 days → single 97-day query is valid
- [ ] Skill computes baseline statistics:
  - bw_95 path: mean, max of 3 aggregate values
  - flux/bw paths: mean, P95, max of 90 daily values
- [ ] Skill applies dual-threshold anomaly detection:
  - Tier 1 (absolute): bw_95 ≥ 8 Gbps, flux > 5 TB/day, bw ≥ 3 Gbps/day
  - Tier 2 (relative): current > baseline × 1.5 (baseline_max for bw_95, baseline_P95 for flux/bw)
- [ ] Skill generates structured three-tier analysis report:
  - ⚠️ Anomalous: absolute threshold exceeded
  - 👀 Watch: baseline exceeded but not absolute threshold
  - ✅ Normal: neither threshold triggered

## Non-Functional Requirements

- [ ] All API calls use `--cli-region=cn-north-4`
- [ ] No credential hardcoding (AK/SK read from environment or CLI config)
- [ ] Read-only operations only (no write/delete/modify)
- [ ] ShowBandwidthCalc calls respect 2 calls/s rate limit (sleep 0.6s)
- [ ] Skill directory size ≤ 40 MB
- [ ] File count ≤ 30
- [ ] All hcloud parameters use `--key=value` format
- [ ] No cross-skill direct calls
- [ ] Baseline and current windows do not overlap

## Output Format

- [ ] Report includes billing mode used
- [ ] Report includes baseline statistics (mean, P95/max, relative limit)
- [ ] Report includes current window daily/aggregate values
- [ ] Report includes absolute threshold comparison
- [ ] Report includes baseline deviation percentage
- [ ] Report includes three-tier conclusion (Normal / Watch / Anomalous)
- [ ] Empty results (`result: {}` or `value: 0`) handled as Normal