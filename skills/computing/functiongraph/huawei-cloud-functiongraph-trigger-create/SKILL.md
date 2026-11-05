---
name: huawei-cloud-functiongraph-trigger-create
description: Create FunctionGraph triggers on Huawei Cloud. Supports scheduled TIMER triggers (Quartz Cron expressions or fixed Rate values) and event-driven OBS triggers that run a function when objects are created or deleted in an OBS bucket. Use this skill when users ask to create a trigger, schedule function execution, set up periodic tasks, configure a timer, or run a function as soon as a file is uploaded to OBS. Triggered by keywords like "create trigger", "set up trigger", "schedule function", "periodic task", "timer", "cron", "OBS trigger", "object storage trigger", "event trigger", "event-driven", "trigger on upload", "bucket notification", "FunctionGraph trigger", "创建云函数触发器", "配置云函数触发器", "云函数定时触发", "定时执行", "定时任务", "创建定时器", "OBS触发器", "对象存储触发器", "事件触发器", "上传触发".
tags:
  - functiongraph
  - trigger
  - timer
  - obs
  - huaweicloud
---

## Overview

This skill enables the creation of triggers for Huawei Cloud FunctionGraph functions. Two trigger types are supported:

- **TIMER** (scheduled trigger): invokes the function on a schedule described by a Quartz Cron expression or by a fixed Rate value.
- **OBS** (event-driven trigger, new): invokes the function when objects are created or deleted in an OBS bucket, which covers real-time processing scenarios such as masking or sanitizing sensitive data as soon as a file is uploaded.

Typical scenarios:

- Periodic data processing, scheduled backup operations, regular monitoring and health checks, time-based notifications (TIMER).
- Upload-triggered processing: real-time data masking, thumbnail generation, format conversion, search indexing or malware scanning of newly uploaded objects (OBS).

## Supported Trigger Types and Capability Boundaries

### Supported trigger types

| `--trigger-type` | Trigger | Configuration parameters | Typical use |
|------------------|---------|--------------------------|-------------|
| `TIMER` (default) | Scheduled trigger | `--schedule` with `--schedule-type` (`Cron` or `Rate`), optional `--user-event` | Periodic function execution |
| `OBS` | Object storage event trigger | `--bucket` and `--events`, optional `--prefix` and `--suffix` | Run the function when an object is created or deleted |

### Trigger types that are NOT supported

This skill implements **only TIMER and OBS**. The FunctionGraph service also offers other trigger types, but this skill does not support them and does not document them:

- APIG, CTS, DDS, DMS, DIS, LTS, SMN, KAFKA, RABBITMQ, DEDICATEDGATEWAY, OPENSOURCEKAFKA, APIC, GAUSSMONGO, EVENTGRID

For those types, use the FunctionGraph console or the KooCLI `hcloud FunctionGraph` trigger commands.

### Capability boundary: create only

This skill **only creates** triggers. It does **not**:

- delete a trigger
- update or modify an existing trigger
- disable or enable an existing trigger
- list or query existing triggers

Triggers that need to be removed, changed or inspected must be handled by the user in the FunctionGraph console (Function details → Triggers) or with the KooCLI `hcloud FunctionGraph` commands. Every run of this skill creates a new trigger; running it again with the same trigger name for the same function fails with `TriggerAlreadyExists` instead of updating the existing trigger.

## Prerequisites

Before using this skill, ensure the following requirements are met:

1. **Python Environment**: Python 3.9+ installed
2. **SDK Installation**: Install FunctionGraph SDK: `pip install huaweicloudsdkfunctiongraph`
3. **Environment Variables**: Configure the following environment variables:
   - `HUAWEI_AK`: Huawei Cloud Access Key
   - `HUAWEI_SK`: Huawei Cloud Secret Key
   - `HUAWEI_REGION`: Target region (e.g., `cn-north-4`)
   - `HUAWEI_PROJECT_ID`: Project ID
4. **FunctionGraph Function**: Target function must already exist in the specified region
5. **OBS Bucket** (OBS triggers only): The bucket must already exist in the same region as the function, and the function must be authorized to read from it
6. **Network Access**: Stable network connection to Huawei Cloud API endpoints

## Workflow

The complete workflow consists of the following steps.

**Step 1: Load environment variables and authenticate（加载环境变量/鉴权）**

The script reads the following environment variables at startup:

- `HUAWEI_AK`: Huawei Cloud Access Key (required)
- `HUAWEI_SK`: Huawei Cloud Secret Key (required)
- `HUAWEI_REGION`: Target region, defaults to `cn-north-4`
- `HUAWEI_PROJECT_ID`: Project ID

If `HUAWEI_AK` or `HUAWEI_SK` is missing, the script prints `Config error: Please set environment variables HUAWEI_AK and HUAWEI_SK` and exits before any API call.

**Step 2: Confirm the target function URN（确认 function_urn）**

Pass the target function URN via `--function-urn`, e.g. `urn:fss:cn-north-4:project_id:function:default:my-function:latest`. Before creating the trigger, the script verifies that the function exists by calling `ShowFunctionConfig`. If the function is not found, it returns `FunctionNotFound` and stops without creating anything.

**Step 3: Choose the trigger type（选择触发器类型）**

Pass `--trigger-type TIMER` (the default) or `--trigger-type OBS`. The type determines which parameters are required in the next step:

- `TIMER` requires `--schedule`; `--bucket`, `--events`, `--prefix` and `--suffix` are ignored.
- `OBS` requires `--bucket` and `--events`; `--schedule`, `--schedule-type` and `--user-event` are ignored.

**Step 4: Confirm the trigger configuration（确认触发配置）**

Verify the trigger parameters (see [Parameter Confirmation](#parameter-confirmation)):

For a TIMER trigger:

- `--name`: Trigger name, 1-64 characters
- `--schedule`: Quartz Cron expression (6-7 fields) for `Cron`, or a rate value such as `5m` for `Rate`
- `--schedule-type`: `Cron` (default) or `Rate`
- `--user-event`: Optional additional user event data

For an OBS trigger:

- `--name`: Event notification name, 1-64 characters
- `--bucket`: Name of the existing OBS bucket that acts as the event source; it cannot be changed after the trigger is created
- `--events`: Comma-separated object events, e.g. `ObjectCreated:*` or `Put,Post` (see [OBS Event Types](#obs-event-types))
- `--prefix` / `--suffix`: Optional filters that limit the notification to object keys starting with / ending with the given string
- `--status`: use `ACTIVE`; OBS triggers cannot be disabled after creation

The script validates all parameters (required fields per trigger type, Cron syntax, name length, status value) before calling the API.

**Step 5: Execute the creation script（执行 create_trigger.py）**

Run from the skill directory. TIMER example:

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --trigger-type "TIMER" \
    --name "daily-trigger" \
    --schedule "0 0 2 * * ?" \
    --schedule-type "Cron" \
    --status "ACTIVE"
```

OBS example:

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --trigger-type "OBS" \
    --name "mask-on-upload" \
    --bucket "my-input-bucket" \
    --events "ObjectCreated:*" \
    --prefix "uploads/" \
    --status "ACTIVE"
```

**Step 6: Verify the result（验证结果）**

- On success, the script prints a JSON response with `status: "success"`, the created `trigger_id`, `trigger_name`, `trigger_type` (`TIMER` or `OBS`) and `enable_status`. A TIMER response also contains `schedule`; an OBS response also contains `bucket` and `events`.
- On failure, it prints `status: "failed"` with an `error_code` (`InvalidParameter`, `FunctionNotFound`, `NetworkError`, `TriggerAlreadyExists`, `TriggerLimitExceeded`, `InternalError`) and exits with a non-zero code. Fix the corresponding parameter and re-run the script.
- You can also confirm the result in the FunctionGraph console: Function details → Triggers tab, where the new trigger should be listed with its status.

## Core Commands

### Basic Command Structure

```bash
python3 scripts/create_trigger.py \
    --function-urn "<function-urn>" \
    --trigger-type "<TIMER|OBS>" \
    --name "<trigger-name>" \
    --status "<ACTIVE|DISABLED>" \
    <type-specific parameters>
```

### TIMER Trigger Examples

#### Cron Expression Trigger

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --name "hourly-report" \
    --schedule "0 0 8 * * ?" \
    --schedule-type "Cron"
```

#### Fixed Rate Trigger

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --name "every-5min" \
    --schedule "5m" \
    --schedule-type "Rate"
```

#### Timer with Additional User Event

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --trigger-type "TIMER" \
    --name "nightly-job" \
    --schedule "0 30 1 * * ?" \
    --schedule-type "Cron" \
    --user-event "{\"mode\": \"full\"}" \
    --status "ACTIVE"
```

### OBS Trigger Examples

#### Run on Every Object Creation

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --trigger-type "OBS" \
    --name "on-object-created" \
    --bucket "my-input-bucket" \
    --events "ObjectCreated:*" \
    --status "ACTIVE"
```

#### Real-Time Data Masking for Uploads under a Prefix

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --trigger-type "OBS" \
    --name "mask-uploads" \
    --bucket "my-input-bucket" \
    --events "Put,Post" \
    --prefix "uploads/" \
    --suffix ".csv" \
    --status "ACTIVE"
```

#### Run on Object Deletion

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --trigger-type "OBS" \
    --name "on-object-removed" \
    --bucket "my-input-bucket" \
    --events "ObjectRemoved:*" \
    --status "ACTIVE"
```

### OBS Event Types

Pass one or more events as a comma-separated list, e.g. `--events "Put,Post"` or `--events "ObjectCreated:*"`.

| Event | Meaning |
|-------|---------|
| `ObjectCreated` | All object creation operations: `Put`, `Post`, `Copy` and multipart upload completion. `ObjectCreated:*` also matches them |
| `Put` | Object uploaded with the Put method |
| `Post` | Object uploaded with the Post method |
| `Copy` | Object created by copying another object |
| `CompleteMultipartUpload` | Multipart upload (segments) merged into a complete object |
| `ObjectRemoved` | Object deleted. `ObjectRemoved:*` also matches `Delete` and `DeleteMarkerCreated` |
| `Delete` | Object version deleted with an explicit version ID |
| `DeleteMarkerCreated` | Delete marker created when no version ID is specified |

### OBS Prefix and Suffix Filters

- `--prefix` limits notifications to object keys that **start with** the given string, e.g. `uploads/`.
- `--suffix` limits notifications to object keys that **end with** the given string, e.g. `.csv`.
- Both are optional and can be combined. Leave them out to be notified for every matching event in the bucket.
- Prefix/suffix filtering is performed by OBS and reduces function invocations, which also reduces cost.

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

Only this subset is supported: numbers, `*`, `?` (day or day-of-week only), ranges (`a-b`), steps (`*/n`) and lists (`a,b,c`). Quartz modifiers such as `L`, `W` and `#` are not supported and are rejected with an explicit error message instead of a generic numeric error.

For detailed Cron expression reference including special characters and common examples, see [Cron Expression Reference](./references/cron-reference.md).

## Parameter Confirmation

Before creating the trigger, confirm the following parameters:

| Parameter | CLI Argument | Required | Description | Example |
|-----------|--------------|----------|-------------|---------|
| `function_urn` | `--function-urn` | Yes (always) | Target function URN | `urn:fss:cn-north-4:xxx:function:default:my-func:latest` |
| `trigger_type` | `--trigger-type` | No (default `TIMER`) | `TIMER` or `OBS` | `OBS` |
| `trigger_name` | `--name` | Yes (always) | TIMER: trigger name; OBS: event notification name (1-64 chars) | `daily-trigger` |
| `enable_status` | `--status` | No (default `ACTIVE`) | `ACTIVE` or `DISABLED`; OBS triggers cannot be disabled after creation (only TIMER, DDS, DMS, KAFKA and LTS trigger types support disabling), so use `ACTIVE` with `--trigger-type OBS` | `ACTIVE` |
| `schedule` | `--schedule` | Yes for `TIMER`, ignored for `OBS` | Cron expression or Rate value | `0 0 2 * * ?` or `5m` |
| `schedule_type` | `--schedule-type` | No (default `Cron`) | `Cron` or `Rate`; TIMER only | `Cron` |
| `user_event` | `--user-event` | No (default empty) | Additional user event data; TIMER only | `optional info` |
| `bucket` | `--bucket` | Yes for `OBS`, ignored for `TIMER` | OBS bucket name that acts as the event source | `my-input-bucket` |
| `events` | `--events` | Yes for `OBS`, ignored for `TIMER` | Comma-separated object events | `ObjectCreated:*` or `Put,Post` |
| `prefix` | `--prefix` | No; OBS only | Object key prefix filter | `uploads/` |
| `suffix` | `--suffix` | No; OBS only | Object key suffix filter | `.csv` |

### Confirmation Checklist

- [ ] Function URN is correct and the function exists
- [ ] Trigger type selected (`TIMER` or `OBS`)
- [ ] For TIMER: Cron expression or Rate value has been validated
- [ ] For OBS: bucket exists in the same region and the events are valid
- [ ] Trigger name follows naming conventions
- [ ] IAM permissions are sufficient (including OBS read access for OBS triggers)
- [ ] Region matches the function location

## Output Format

### Success Response (TIMER)

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

### Success Response (OBS)

```json
{
    "status": "success",
    "trigger_id": "obs-xxx-xxx-xxx",
    "trigger_name": "mask-uploads",
    "trigger_type": "OBS",
    "bucket": "my-input-bucket",
    "events": ["Put", "Post"],
    "enable_status": "ACTIVE",
    "message": "Trigger created successfully"
}
```

### Error Response

```json
{
    "status": "failed",
    "error_code": "TriggerAlreadyExists",
    "message": "Trigger with the same name already exists"
}
```

Error codes: `InvalidParameter`, `FunctionNotFound`, `NetworkError`, `TriggerAlreadyExists`, `TriggerLimitExceeded`, `InternalError`.

For complete error codes and troubleshooting information, see [Cron Expression Reference](./references/cron-reference.md).

## Verification Method

After creating the trigger, verify the configuration:

### 1. List Function Triggers

Navigate to FunctionGraph console → Function details → Triggers tab to view all triggers

### 2. Check Trigger Details

Navigate to FunctionGraph console → Function details → Triggers → View trigger details

### 3. Check the OBS Event Source (OBS triggers)

Navigate to the OBS console → the target bucket → Events/Notification rules, and confirm the rule that matches the trigger name, bucket, events, prefix and suffix.

### 4. Monitor Trigger Execution

Navigate to FunctionGraph console → Function details → Triggers → View execution history

Expected indicators:

- Trigger status: **Active**
- TIMER only: next execution time is correctly calculated
- OBS only: uploading a matching object (respecting the prefix/suffix filter) produces a function invocation

## Best Practices

### TIMER Best Practices

1. **Avoid frequent executions**: Use intervals ≥ 5 minutes unless necessary
2. **Consider timezone**: FunctionGraph uses UTC by default
3. **Use `?` for unused day field**: Either day-of-month or day-of-week should use `?`
4. **Validate before creation**: Test expressions using online Cron validators

### OBS Best Practices

1. **Filter aggressively**: Use `--prefix` and `--suffix` so the function runs only for the objects it is meant to process
2. **Keep the function idempotent**: OBS notifications are at-least-once; the same object event can be delivered more than once, so mask/replace operations must produce the same result when repeated
3. **Write results to a different bucket or prefix**: Avoid writing the function output back into the same prefix that triggers it, which would create an infinite invocation loop
4. **Pick precise events**: Use `Put`/`Post` for uploads and `ObjectRemoved` for deletions instead of `ObjectCreated`/`ObjectRemoved` when the function only handles one operation
5. **Watch the runtime**: Large objects may need more memory and a longer timeout than the default configuration

### Naming Conventions

- Use descriptive names: `daily-data-sync`, `mask-on-upload`
- Follow pattern: `[frequency|event]-[purpose]`
- Maximum 64 characters
- Use lowercase with hyphens

### Security Considerations

1. **Least privilege**: Grant minimal IAM permissions, including read access to the OBS bucket for OBS triggers
2. **Enable encryption**: Use KMS for sensitive function inputs
3. **Monitor executions**: Set up Cloud Eye alarms for failures
4. **Protect notification payloads**: OBS events may contain object keys; make sure log and trace settings do not leak sensitive names

### Operational Recommendations

1. **Start with disabled status** for testing
2. **Document trigger purpose** in the trigger name
3. **Set appropriate retries** for transient failures
4. **Monitor first executions** after enabling

## Reference Documents

For detailed information, refer to:

- [SDK Installation Guide](./references/sdk-installation-guide.md)
- [IAM Policies](./references/iam-policies.md)
- [Verification Method](./references/verification-method.md)
- [Acceptance Criteria](./references/acceptance-criteria.md)
- [Cron Expression Reference](./references/cron-reference.md)
- [OBS Trigger Guide](./references/obs-trigger-guide.md)

## Important Notes

### Compatibility Notes

This skill is designed to work with Huawei Cloud FunctionGraph API. The `tags` field helps with skill discovery and categorization.

### Limitations

1. **Create only**: triggers cannot be deleted, updated, disabled or listed by this skill
2. **TIMER and OBS only**: other trigger types (APIG, CTS, DDS, DMS, DIS, LTS, SMN, KAFKA, RABBITMQ and so on) are not supported
3. **Maximum triggers**: Each function supports up to 10 triggers by default
4. **OBS event delivery**: notifications may be delivered more than once, so functions must tolerate duplicate events
5. **OBS bucket**: the bucket cannot be renamed or replaced after the trigger is created, and the function must be able to read the bucket
6. **Cron precision**: Second-level scheduling may have minor delays
7. **Timeout handling**: Function timeout should be less than trigger interval
8. **Cold start**: First executions may have additional latency

### Cost Implications

- No additional cost for trigger configuration
- Function execution billed per invocation
- For OBS triggers, cost grows with the number of matching object events; prefix/suffix filters reduce invocations
- Consider execution frequency for cost optimization

### Common Pitfalls

1. **Wrong timezone**: Remember FunctionGraph uses UTC
2. **Overlapping schedules**: Multiple triggers may cause concurrent executions
3. **Long-running functions**: Ensure function completes before the next trigger
4. **Cron syntax errors**: Validate expression format before deployment
5. **Recursive OBS triggers**: writing output into the watched prefix triggers the function again
6. **Mismatched region**: the OBS bucket and the function must be in the same region

For troubleshooting and error codes, refer to [Cron Expression Reference](./references/cron-reference.md).
