# Cron Expression Reference

## Special Characters

| Character | Description | Example |
|-----------|-------------|---------|
| `*` | Any value | `* * * * * ?` = every second |
| `?` | No specific value (for day fields) | `0 0 0 * * ?` = daily at midnight |
| `-` | Range | `0 0 9-17 * * ?` = hourly 9AM-5PM |
| `,` | List | `0 0 9,12,15 * * ?` = 9AM, 12PM, 3PM |
| `/` | Step | `0 */5 * * * ?` = every 5 minutes |

## Common Examples

| Expression | Description |
|------------|-------------|
| `0 0 2 * * ?` | Daily at 2:00 AM |
| `0 */30 * * * ?` | Every 30 minutes |
| `0 0 0 1 * ?` | First day of each month at midnight |
| `0 0 9 ? * MON-FRI` | Weekdays at 9:00 AM |
| `0 0 12 1,15 * ?` | 1st and 15th of each month at noon |

## Parameter Reference

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `function_urn` | Yes | Target function URN | `urn:fss:cn-north-4:xxx:function:default:my-func:latest` |
| `trigger_name` | Yes | Trigger name (1-64 chars) | `daily-trigger` |
| `schedule` | Yes | Cron expression or Rate value | `0 0 2 * * ?` or `5m` |
| `schedule_type` | No | `Cron` (default) or `Rate` | `Cron` |
| `enable_status` | No | `ACTIVE` (default) or `DISABLED` | `ACTIVE` |
| `user_event` | No | Additional user event data | `optional info` |

## Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `InvalidParameter` | Invalid parameter format | Validate Cron expression and parameter values |
| `FunctionNotFound` | Target function not found | Verify function URN and region |
| `TriggerAlreadyExists` | Trigger name conflict | Use a different trigger name |
| `TriggerLimitExceeded` | Maximum triggers reached | Delete unused triggers |
| `AccessDenied` | IAM permission denied | Add required IAM policies |

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Trigger not firing | Status is `disabled` | Enable the trigger |
| Execution failures | Function runtime error | Check function logs |
| Permission denied | IAM policy missing | Add required permissions |
| Invalid Cron | Syntax error | Validate expression format |

## Cron Expression Format

FunctionGraph uses **Quartz Cron** format with 6 or 7 fields:

```
┌───────────── second (0-59)
│ ┌───────────── minute (0-59)
│ │ ┌───────────── hour (0-23)
│ │ │ ┌───────────── day of month (1-31)
│ │ │ │ ┌───────────── month (1-12)
│ │ │ │ │ ┌───────────── day of week (1-7, 1=Sunday)
│ │ │ │ │ │
* * * * * ?
```