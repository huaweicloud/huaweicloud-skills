# Verification Method

## Quick Verification

Verify the skill is working correctly by running a minimal query:

```bash
hcloud WAF ListEvent --recent=today --pagesize=1
```

**Expected Result:** JSON response with event data structure (even if empty results — the query itself should succeed without errors).

## Verification Checklist

| Step | Command | Expected Outcome |
|------|---------|-----------------|
| 1. CLI configured | `hcloud configure list` | Valid profile with AK/SK, region, project_id |
| 2. Basic query | `hcloud WAF ListEvent --recent=today --pagesize=1` | Successful JSON response |
| 3. Attack type filter | `hcloud WAF ListEvent --recent=1week --attacks.1=sqli --pagesize=1` | Filtered response (may be empty) |
| 4. Sort by IP | `hcloud WAF ListEvent --recent=today --sort_key=sort_ip --pagesize=5` | Events sorted by source IP |
| 5. Event detail | `hcloud WAF ShowEvent --eventid={id}` | Full event details for a known event ID |
| 6. Dirty data tolerance | Parse a response whose `payload`/`request_body` contains unescaped backslashes (e.g. `"[com.s\un.\r\owse\x74...]"`) | Analysis continues despite `Invalid \uXXXX escape` — malformed records are skipped/sanitized, the overall aggregation is not aborted, and skipped dirty records are counted |

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid \uXXXX escape` while parsing | `payload`/`request_body` contains unescaped backslashes from malicious requests | Sanitize invalid escapes before `ConvertFrom-Json`/`json.load`, or fall back to per-record field-level extraction; never abort the whole analysis on a single dirty record (see SKILL.md "数据容错") |
| `connection timeout` | Network unreachable or proxy not configured | Check network/proxy settings |
| `unauthorized` | Invalid AK/SK | Re-run `hcloud configure` |
| `project_id not found` | Missing or wrong project ID | Set correct project ID via `hcloud configure set --cli-project-id=<id>` |
| Empty results | No events in time range | Try wider time range (`--recent=1month`) |
| `Parent proxy unreachable` | Proxy service not running | Start local proxy or adjust proxy URL |

## Output Quality Criteria

A successful analysis should produce:
- Total event count within the specified time range
- At least one populated dimension in the multi-dimensional analysis
- Rule recommendations that reference specific observed attack patterns
- Source IPs and target URLs drawn from actual event data (not fabricated)
