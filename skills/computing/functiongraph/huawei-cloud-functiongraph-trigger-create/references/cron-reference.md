# Cron Expression Reference

This reference applies to `TIMER` triggers (`--trigger-type TIMER`, the default). OBS triggers do
not use a Cron schedule; see [OBS Event Trigger Guide](./obs-trigger-guide.md).

## Special Characters

Supported characters:

| Character | Description | Example |
|-----------|-------------|---------|
| `*` | Any value | `* * * * * ?` = every second |
| `?` | No specific value (for day fields) | `0 0 0 * * ?` = daily at midnight |
| `-` | Range | `0 0 9-17 * * ?` = hourly 9AM-5PM |
| `,` | List | `0 0 9,12,15 * * ?` = 9AM, 12PM, 3PM |
| `/` | Step | `0 */5 * * * ?` = every 5 minutes |

Not supported:

| Character | Meaning in full Quartz | Behaviour here |
|-----------|------------------------|----------------|
| `L` | Last day of month / week | Rejected as an invalid field value |
| `W` | Nearest weekday | Rejected as an invalid field value |
| `#` | Nth weekday of the month | Rejected as an invalid field value |
| `LW` | Last weekday of the month | Rejected as an invalid field value |

This skill's Cron validator only accepts `*`, `?`, `-`, `,`, `/`, and plain numbers, plus the
`*/n` step form. Quartz advanced characters are rejected, so express those schedules some other
way (for example a `Rate` schedule, or a day-of-month range) instead of relying on `L`, `W`, `#`,
or `LW`.

## Common Examples

| Expression | Description |
|------------|-------------|
| `0 0 2 * * ?` | Daily at 2:00 AM |
| `0 */30 * * * ?` | Every 30 minutes |
| `0 0 0 1 * ?` | First day of each month at midnight |
| `0 0 9 ? * MON-FRI` | Weekdays at 9:00 AM |
| `0 0 12 1,15 * ?` | 1st and 15th of each month at noon |

## Parameter Reference

Flags of `scripts/create_trigger.py`:

| CLI argument | Required | Description | Example |
|--------------|----------|-------------|---------|
| `--function-urn` | Yes | Target function URN | `urn:fss:cn-north-4:xxx:function:default:my-func:latest` |
| `--trigger-type` | No, default `TIMER` | `TIMER` or `OBS`; this reference covers `TIMER` | `TIMER` |
| `--name` | Yes | `TIMER`: trigger name; `OBS`: event notification name (1-64 chars) | `daily-trigger` |
| `--schedule` | Required when `--trigger-type TIMER` | Cron expression or Rate value | `0 0 2 * * ?` or `5m` |
| `--schedule-type` | No, default `Cron` | `Cron` or `Rate` (TIMER only) | `Cron` |
| `--status` | No, default `ACTIVE` | `ACTIVE` or `DISABLED` | `ACTIVE` |
| `--user-event` | No | Additional user event data (TIMER only) | `optional info` |
| `--bucket`, `--events`, `--prefix`, `--suffix` | Required/optional for `--trigger-type OBS` | OBS-only — see [OBS Event Trigger Guide](./obs-trigger-guide.md) | `input-images` |

## Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `InvalidParameter` | Invalid parameter format | Validate the Cron expression and parameter values |
| `FunctionNotFound` | Target function not found | Verify the function URN and region |
| `NetworkError` | Transport failure (DNS, timeout, connection reset) | Check network/proxy connectivity and retry |
| `TriggerAlreadyExists` | Trigger name conflict | Use a different trigger name |
| `TriggerLimitExceeded` | Maximum triggers reached | Delete unused triggers |
| `InternalError` | Unexpected service or SDK error | Retry, then check the full error message |

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Trigger not firing (TIMER) | Status is `DISABLED` | Recreate the trigger with `--status ACTIVE` (this skill is create-only) |
| Trigger not firing (OBS) | Object key does not match the prefix/suffix, or the event type does not cover the operation | Check `event_data.prefix`, `event_data.suffix`, and `event_data.events` |
| Execution failures | Function runtime error | Check function logs |
| Permission denied | IAM policy missing | Add the required permissions from [IAM Policies](./iam-policies.md) |
| Invalid Cron | Syntax error, unsupported field, or unsupported character (`L`, `W`, `#`, `LW`) | Validate the expression format against this reference |

## Cron Expression Format

FunctionGraph uses **Quartz Cron** format with 6 or 7 fields (the 7th field, year, is optional).
The schedule is evaluated in UTC:

```
┌───────────── second (0-59)
│ ┌───────────── minute (0-59)
│ │ ┌───────────── hour (0-23)
│ │ │ ┌───────────── day of month (1-31)
│ │ │ │ ┌───────────── month (1-12)
│ │ │ │ │ ┌───────────── day of week (1-7, 1=Sunday)
│ │ │ │ │ │ ┌───────────── year (optional, e.g. 2026)
│ │ │ │ │ │ │
* * * * * ? *
```

## Related Documents

- [OBS Event Trigger Guide](./obs-trigger-guide.md) — event triggers, which do not use Cron
- [Verification Method](./verification-method.md)
- [Acceptance Criteria](./acceptance-criteria.md)
- [IAM Policies](./iam-policies.md)
