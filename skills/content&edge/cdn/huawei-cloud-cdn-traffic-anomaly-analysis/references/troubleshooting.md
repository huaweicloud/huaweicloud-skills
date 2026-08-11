# Troubleshooting

## Common Issues

### Issue: Domain Not Found

**Symptom**: Error message "Domain not in current account's online domain list"

**Resolution**:
1. Verify the domain name spelling
2. Check if the domain status is `online`
3. Ensure you're using the correct account
4. Run `hcloud CDN ListDomains/v2 --cli-region=cn-north-4 --domain_status=online` to see all available domains

### Issue: No Traffic Data

**Symptom**: API returns `result: {}` or `value: 0`

**Resolution**:
- This is normal if the domain has no traffic in the query period
- The domain is considered normal (not anomalous)
- Try extending the analysis period (e.g., 14 days instead of 7 days)

### Issue: Permission Denied

**Symptom**: API returns permission denied error

**Resolution**:
1. Verify IAM user has required permissions (see [iam-policies.md](iam-policies.md))
2. Check if using the correct AK/SK
3. Contact account administrator to grant necessary permissions

### Issue: ShowBandwidthCalc Rate Limit Exceeded

**Symptom**: API returns rate limit error for ShowBandwidthCalc

**Resolution**:
- ShowBandwidthCalc has a rate limit of 2 calls/s
- The bw_95 path makes 4 ShowBandwidthCalc calls total (1 current + 3 baseline)
- Add `sleep(0.6)` between consecutive calls
- For other APIs, the rate limit is higher (5-15 calls/s)

### Issue: Timestamp Alignment

**Symptom**: Incorrect time range in query results

**Resolution**:
- When `interval=86400`, timestamps must be aligned to UTC+8 midnight
- Use the built-in script `scripts/cdn_timestamp.py` which handles alignment automatically
- Manual timestamp calculation may lead to misalignment

### Issue: Incorrect Billing Mode

**Symptom**: Queried metric doesn't match expected billing mode

**Resolution**:
1. Verify the billing mode from Step 1
2. Check if `status == "active"` and `service_area == "mainland_china"`
3. Ensure the correct metric is queried based on billing mode

### Issue: ShowBandwidthCalc Returns Single Value for Large Range

**Symptom**: ShowBandwidthCalc with a 30-day range returns only one value, not 30 daily values

**Resolution**:
- This is **expected behavior** — ShowBandwidthCalc always returns a single aggregate P95 value for the entire query period
- Maximum query range is 31 days
- For per-day breakdown, use `ShowDomainStats/v2` with `stat_type=bw` and `interval=86400` instead
- For baseline analysis, query 3 separate 30-day windows to get 3 aggregate values for comparison

## Best Practices

### 1. Always Verify Credentials First

Before starting analysis, verify:
```bash
hcloud configure list
```

### 2. Use Fixed Region

Always use `--cli-region=cn-north-4` for CDN APIs to avoid confusion.

### 3. Check Domain Status

Ensure the target domain is `online` before analysis.

### 4. Handle Pagination

If domain count > 100, implement pagination in ListDomains/v2.

### 5. Rate Limiting for bw_95 Path

For ShowBandwidthCalc, add `sleep(0.6)` between calls to avoid rate limit errors. The bw_95 path needs 4 such calls (1 current window + 3 baseline windows).

### 6. Timestamp Alignment

Always use the built-in timestamp script to ensure proper UTC+8 midnight alignment.

### 7. Baseline Window Isolation

Ensure baseline windows (30 days each) and the current window (7 days) do not overlap. The `cdn_timestamp.py --baseline` script automatically isolates the windows.

## Notes

| Scenario | Handling |
|----------|----------|
| Domain has no traffic data | `result: {}` or `value: 0`, skip, not counted as anomalous |
| Domain not in list | Error and stop, prompt user to check domain |
| Timestamp alignment | `interval=86400` must align to UTC+8 midnight, use `cdn_timestamp.py` |
| ShowBandwidthCalc rate limit | Only 2 calls/s, add sleep(0.6) between calls |
| ShowBandwidthCalc output | Single aggregate P95 value per query; no per-day breakdown |
| ShowDomainStats/v2 output | One value per day at interval=86400; supports ≥365-day range |
| Overseas domains | Need to confirm service_area parameter |
| 3-month baseline (bw_95) | Requires 3 separate 30-day queries due to 31-day max range |
| 3-month baseline (flux/bw) | Single 97-day query, split result into 90d baseline + 7d current |