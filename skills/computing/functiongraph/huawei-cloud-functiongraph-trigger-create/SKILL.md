---
name: huawei-cloud-functiongraph-trigger-create
description: Create and configure scheduled TIMER triggers for Huawei Cloud FunctionGraph functions using Quartz Cron expressions. Use this skill when users ask to create triggers, schedule function execution, set up periodic tasks, or configure timers for functions. Triggered by keywords like "create trigger", "set up trigger", "schedule function", "periodic task", "timer", "cron", "创建云函数触发器", "配置云函数触发器", "云函数定时触发", "定时执行", "定时任务", "创建定时器", "FunctionGraph trigger", "schedule function execution".
version: 1.0.0
tags:
  - functiongraph
  - trigger
  - timer
  - cron
  - huaweicloud
---

# Overview

This skill enables the creation and configuration of scheduled triggers (TIMER type) for Huawei Cloud FunctionGraph functions. It supports Quartz Cron expression format for flexible scheduling configurations.

The trigger allows automatic execution of serverless functions at specified time intervals, making it ideal for:

- Periodic data processing tasks
- Scheduled backup operations
- Regular monitoring and health checks
- Time-based notification systems

# Prerequisites

Before using this skill, ensure the following requirements are met:

1. **Python Environment**: Python 3.9+ installed
2. **SDK Installation**: Install FunctionGraph SDK: `pip install huaweicloudsdkfunctiongraph`
3. **Environment Variables**: Configure the following environment variables:
   - `HUAWEI_AK`: Huawei Cloud Access Key
   - `HUAWEI_SK`: Huawei Cloud Secret Key
   - `HUAWEI_REGION`: Target region (e.g., `cn-north-4`)
   - `HUAWEI_PROJECT_ID`: Project ID
4. **FunctionGraph Function**: Target function must already exist in the specified region
5. **Network Access**: Stable network connection to Huawei Cloud API endpoints

# Workflow（工作流）

The complete workflow for creating a scheduled TIMER trigger consists of the following steps:

**Step 1: Load environment variables and authenticate（加载环境变量/鉴权）**

The script reads the following environment variables at startup:

- `HUAWEI_AK`: Huawei Cloud Access Key (required)
- `HUAWEI_SK`: Huawei Cloud Secret Key (required)
- `HUAWEI_REGION`: Target region, defaults to `cn-north-4`
- `HUAWEI_PROJECT_ID`: Project ID

If `HUAWEI_AK` or `HUAWEI_SK` is missing, the script prints `Config error: Please set environment variables HUAWEI_AK and HUAWEI_SK` and exits before any API call.

**Step 2: Confirm the target function URN（确认 function_urn）**

Pass the target function URN via `--function-urn`, e.g. `urn:fss:cn-north-4:project_id:function:default:my-function:latest`. Before creating the trigger, the script verifies that the function exists by calling `ShowFunctionConfig`. If the function is not found, it returns `FunctionNotFound` and stops without creating anything.

**Step 3: Confirm the trigger configuration（确认触发配置）**

Verify the trigger parameters (see [Parameters Confirmation](#parameters-confirmation)):

- `--name`: Trigger name, 1-64 characters
- `--schedule`: Quartz Cron expression (6-7 fields) for `Cron`, or a rate value such as `5m` for `Rate`
- `--schedule-type`: `Cron` (default) or `Rate`
- `--status`: `ACTIVE` (default) or `DISABLED`
- `--user-event`: Optional additional user event data

The script validates all parameters (required fields, Cron syntax, name length, status value) before calling the API.

**Step 4: Execute the creation script（执行 create_trigger.py）**

Run from the skill directory:

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --name "daily-trigger" \
    --schedule "0 0 2 * * ?" \
    --schedule-type "Cron" \
    --status "ACTIVE"
```

**Step 5: Verify the result（验证结果）**

- On success, the script prints a JSON response with `status: "success"`, containing the created `trigger_id`, `trigger_name`, `trigger_type` (`TIMER`), `schedule` and `enable_status`.
- On failure, it prints `status: "failed"` with an `error_code` (`InvalidParameter`, `FunctionNotFound`, `TriggerAlreadyExists`, `TriggerLimitExceeded`, `InternalError`) and exits with a non-zero code. Fix the corresponding parameter and re-run the script.
- You can also confirm the result in the FunctionGraph console: Function details → Triggers tab, where the new TIMER trigger should be listed with Active status.

# Usage

## Basic Command Structure

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --name "daily-trigger" \
    --schedule "0 0 2 * * ?" \
    --schedule-type "Cron" \
    --status "ACTIVE"
```

## Examples

### Cron Expression Trigger

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --name "hourly-report" \
    --schedule "0 0 8 * * ?" \
    --schedule-type "Cron"
```

### Fixed Rate Trigger

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --name "every-5min" \
    --schedule "5m" \
    --schedule-type "Rate"
```

## Cron Expression Format

FunctionGraph uses **Quartz Cron** format with 6 or 7 fields (the 7th field `year` is optional):

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

For detailed Cron expression reference including special characters and common examples, see [Cron Expression Reference](./references/cron-reference.md).

# Parameters Confirmation

Before creating the trigger, confirm the following parameters:

| Parameter | CLI Argument | Required | Description | Example |
|-----------|--------------|----------|-------------|---------|
| `function_urn` | `--function-urn` | Yes | Target function URN | `urn:fss:cn-north-4:xxx:function:default:my-func:latest` |
| `trigger_name` | `--name` | Yes | Trigger name (1-64 chars) | `daily-trigger` |
| `schedule` | `--schedule` | Yes | Cron expression or Rate value | `0 0 2 * * ?` or `5m` |
| `schedule_type` | `--schedule-type` | No | `Cron` (default) or `Rate` | `Cron` |
| `enable_status` | `--status` | No | `ACTIVE` (default) or `DISABLED` | `ACTIVE` |
| `user_event` | `--user-event` | No | Additional user event data | `optional info` |

## Confirmation Checklist

- [ ] Function URN is correct and function exists
- [ ] Cron expression has been validated
- [ ] Trigger name follows naming conventions
- [ ] IAM permissions are sufficient
- [ ] Region matches the function location

# Output Format

## Success Response

```json
{
    "status": "success",
    "trigger_id": "timer-xxx-xxx-xxx",
    "trigger_name": "daily-trigger",
    "trigger_type": "TIMER",
    "schedule": "0 0 2 * * ?",
    "enable_status": "ACTIVE",
    "message": "Trigger created successfully"
}
```

## Error Response

```json
{
    "status": "failed",
    "error_code": "TriggerAlreadyExists",
    "message": "Trigger with the same name already exists"
}
```

For complete error codes and troubleshooting information, see [Cron Expression Reference](./references/cron-reference.md).

# Verification Method

After creating the trigger, verify the configuration:

## 1. List Function Triggers

Navigate to FunctionGraph console → Function details → Triggers tab to view all triggers

## 2. Check Trigger Details

Navigate to FunctionGraph console → Function details → Triggers → View trigger details

## 3. Monitor Trigger Execution

Navigate to FunctionGraph console → Function details → Triggers → View execution history

Expected indicators:

- Trigger status: **Active**
- Next execution time: Correctly calculated
- Execution history: No failed invocations

# Best Practices

## Cron Expression Best Practices

1. **Avoid frequent executions**: Use intervals ≥ 5 minutes unless necessary
2. **Consider timezone**: FunctionGraph uses UTC by default
3. **Use `?` for unused day field**: Either day-of-month or day-of-week should use `?`
4. **Validate before creation**: Test expressions using online Cron validators

## Naming Conventions

- Use descriptive names: `daily-data-sync`, `hourly-health-check`
- Follow pattern: `[frequency]-[purpose]`
- Maximum 64 characters
- Use lowercase with hyphens

## Security Considerations

1. **Least privilege**: Grant minimal IAM permissions
2. **Enable encryption**: Use KMS for sensitive function inputs
3. **Monitor executions**: Set up Cloud Eye alarms for failures
4. **Rate limiting**: Configure appropriate retry parameters

## Operational Recommendations

1. **Start with disabled status** for testing
2. **Document trigger purpose** in description field
3. **Set appropriate retries** for transient failures
4. **Monitor first executions** after enabling

# Reference Documents

For detailed information, refer to:

- [SDK Installation Guide](./references/sdk-installation-guide.md)
- [IAM Policies](./references/iam-policies.md)
- [Verification Method](./references/verification-method.md)
- [Acceptance Criteria](./references/acceptance-criteria.md)
- [Cron Expression Reference](./references/cron-reference.md)

# Important Notes

## Compatibility Notes

This skill is designed to work with Huawei Cloud FunctionGraph API. The `tags` field helps with skill discovery and categorization.

## Limitations

1. **Maximum triggers**: Each function supports up to 10 triggers by default
2. **Cron precision**: Second-level scheduling may have minor delays
3. **Timeout handling**: Function timeout should be less than trigger interval
4. **Cold start**: First executions may have additional latency

## Cost Implications

- No additional cost for trigger configuration
- Function execution billed per invocation
- Consider execution frequency for cost optimization

## Common Pitfalls

1. **Wrong timezone**: Remember FunctionGraph uses UTC
2. **Overlapping schedules**: Multiple triggers may cause concurrent executions
3. **Long-running functions**: Ensure function completes before next trigger
4. **Cron syntax errors**: Validate expression format before deployment

For troubleshooting and error codes, refer to [Cron Expression Reference](./references/cron-reference.md).

---

**Related Skills**:

- `huawei-cloud-functiongraph-function-create`
- `huawei-cloud-functiongraph-deploy`

