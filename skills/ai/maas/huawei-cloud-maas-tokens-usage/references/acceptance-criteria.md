# Acceptance Criteria: Correct/Error Pattern Comparison

## Script Parameter Patterns

### service_type Values

**Correct:** Use 1, 2, 4
```bash
--service-type 2   # Preset Service
--service-type 1   # My Service
--service-type 4   # Custom Endpoint
```

**Error:** Use 3 (API does not support)
```bash
--service-type 3   # Returns 400 error
```

### Credential Provision

**Correct:** Environment variables or credentials file
```bash
export HW_ACCESS_KEY=xxx && export HW_SECRET_KEY=xxx
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21

python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21 --credentials-file /path/to/aksk.txt
```

**Error:** Hardcode AK/SK in code
```python
ak = "WTEBXXXXXX"
sk = "xxxxxxxxxx"
```

### Credentials File Format

**Correct:** Supports the following formats
```
# One value per line
<AK>
<SK>

# Comma-separated
<AK>,<SK>

# KEY=VALUE format
HW_ACCESS_KEY=<AK>
HW_SECRET_KEY=<SK>
```

## Security Standards

### Credential Handling

**Correct:** Guide users to configure credentials themselves
```
Please set environment variables HW_ACCESS_KEY and HW_SECRET_KEY
Or use --credentials-file to specify a credentials file
```

**Error:** Ask users for AK/SK in conversation
```
Please tell me your AK and SK
```

## Time Range Standards

**Correct:** Strictly distinguish "last 7 days" and "this month"
- "last 7 days": now-7d ~ now
- "this month": 1st of month ~ now

**Error:** Confuse time ranges
- User says "last 7 days" but calculate as "this month"

## Timezone Standards

**Correct:** Follow OS local timezone, auto-detect

**Error:** Hardcode CST/Asia/Shanghai
