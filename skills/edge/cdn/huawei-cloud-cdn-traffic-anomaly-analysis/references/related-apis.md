# API and CLI Command Reference

## API Quick Reference

| Step | API | Method | Rate Limit | Notes |
|------|-----|--------|------------|-------|
| Billing Mode | `ShowChargeModes` | GET | 5 calls/s | — |
| Domain List | `ListDomains/v2` | GET | — | Paginate if > 100 domains |
| Daily Traffic / Peak (flux/bw) | `ShowDomainStats/v2` (flux/bw) | GET | 15 calls/s | interval=86400 max range 31-32 days; baseline split into 3×30-day queries |
| P95 Bandwidth (bw_95) | `ShowBandwidthCalc` (bw_95) | GET | 2 calls/s | Max 31-day range, single aggregate |

## Single Domain Analysis — API Call Budget

### bw_95 Path: 6 API Calls

```
1 (ShowChargeModes)
+ 1 (ListDomains/v2)
+ 1 (ShowBandwidthCalc — current 7-day window)
+ 3 (ShowBandwidthCalc — baseline 3 × 30-day windows)
= 6 calls (rate limit: 2/s → ~3s with sleep 0.6s)
```

### flux / bw Path: 6 API Calls

```
1 (ShowChargeModes)
+ 1 (ListDomains/v2)
+ 1 (ShowDomainStats/v2 — current 7-day window)
+ 3 (ShowDomainStats/v2 — baseline 3 × 30-day windows)
= 6 calls (rate limit: 15/s → no bottleneck)
```

`ShowDomainStats/v2` with `interval=86400` has a max query range of **31-32 days** (a single 97-day query fails with `CDN.0202`). Query the current 7-day window plus 3 non-overlapping 30-day baseline windows separately.

## Important Notes

- **ShowBandwidthCalc rate limit**: Only 2 calls/s, add `sleep(0.6)` between calls
- **ShowBandwidthCalc max range**: 31 days. Baseline windows must stay within this limit (30 days each)
- **ShowBandwidthCalc return format**: Single aggregate P95 value for the entire query period; no per-day breakdown
- **ShowDomainStats/v2 max range**: `interval=86400` (1 day) supports at most 31-32 days per query — baseline must be split into 3×30-day windows; a single 97-day query fails with `CDN.0202`
- **Pagination**: If domain count > 100, need to paginate ListDomains/v2
- **Region**: Always use `--cli-region=cn-north-1` for CDN APIs