# Verification Method

## Overview

This document describes how to verify that a FunctionGraph trigger created by this skill is
correctly configured and working. It covers both trigger types the skill supports:

| Trigger type | What to verify |
|--------------|----------------|
| `TIMER` | Trigger type, status, name, and the schedule (`event_data.schedule` / `event_data.schedule_type`) |
| `OBS` | Trigger type, status, event-notification name, source `bucket`, `events`, and the optional `prefix` / `suffix` filters |

This skill only creates triggers; verification is read-only and can be done with KooCLI, the
Python SDK, or the console.

> Field names in this document were checked against the unpacked
> `huaweicloudsdkfunctiongraph` 3.1.220 models. In particular,
> `ListFunctionTriggersResponse` exposes the trigger list as **`body`**
> (`list[ListFunctionTriggerResult]`) — there is no `triggers` attribute — and the trigger name
> lives in **`event_data.name`**, the status in **`trigger_status`**.

## Verification Steps

### Step 1: Confirm Trigger Creation

#### Using KooCLI

```bash
hcloud FunctionGraph ListFunctionTriggers \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest"
```

The response contains one entry per trigger with `trigger_id`, `trigger_type_code`,
`trigger_status`, `event_data`, and `created_time` / `last_updated_time`.

A TIMER entry looks like this (abridged):

```json
{
    "trigger_id": "timer-xxx-xxx-xxx",
    "trigger_type_code": "TIMER",
    "trigger_status": "ACTIVE",
    "event_data": {
        "name": "daily-trigger",
        "schedule": "0 0 2 * * ?",
        "schedule_type": "Cron"
    },
    "created_time": "2024-01-15T10:00:00Z",
    "last_updated_time": "2024-01-15T10:00:00Z"
}
```

An OBS entry looks like this (abridged):

```json
{
    "trigger_id": "obs-xxx-xxx-xxx",
    "trigger_type_code": "OBS",
    "trigger_status": "ACTIVE",
    "event_data": {
        "name": "realtime-redact",
        "bucket": "input-images",
        "events": ["ObjectCreated"],
        "prefix": "uploads/",
        "suffix": ".jpg"
    },
    "created_time": "2024-01-15T10:00:00Z",
    "last_updated_time": "2024-01-15T10:00:00Z"
}
```

#### Using Python SDK

```python
from huaweicloudsdkfunctiongraph.v2.model.list_function_triggers_request import (
    ListFunctionTriggersRequest,
)

def find_trigger(client, function_urn, trigger_name):
    request = ListFunctionTriggersRequest(function_urn=function_urn)
    response = client.list_function_triggers(request)

    # ListFunctionTriggersResponse.body is list[ListFunctionTriggerResult].
    for trigger in (response.body or []):
        event_data = trigger.event_data
        name = event_data.name if event_data else None
        if name == trigger_name:
            print(f"Trigger found: {trigger.trigger_id}")
            print(f"  Type: {trigger.trigger_type_code}")
            print(f"  Status: {trigger.trigger_status}")
            return trigger

    print("Trigger not found")
    return None
```

The script itself prints the `trigger_id` on success, so you can also jump straight to
Step 2 with that id.

### Step 2: Validate Trigger Configuration

Query one trigger directly. For TIMER:

```bash
hcloud FunctionGraph ShowFunctionTrigger \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --trigger_type_code TIMER \
    --trigger_id "timer-xxx-xxx-xxx"
```

For OBS:

```bash
hcloud FunctionGraph ShowFunctionTrigger \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:redact-image:latest" \
    --trigger_type_code OBS \
    --trigger_id "obs-xxx-xxx-xxx"
```

`ShowFunctionTrigger` returns `trigger_id`, `trigger_type_code`, `trigger_status`, `event_data`,
`created_time`, and `last_updated_time`. The `event_data` object is the type-specific part; the
OBS fields it can carry (`bucket`, `prefix`, `suffix`, `events`) are defined by the
`TriggerEventDataResponseBody` model.

#### TIMER validation checklist

| Property | Expected value | Where to look |
|----------|----------------|---------------|
| `trigger_type_code` | `TIMER` | Response root |
| `event_data.name` | The `--name` you passed | `event_data` |
| `trigger_status` | `ACTIVE` (or `DISABLED`) | Response root |
| `event_data.schedule` | The `--schedule` value | `event_data` |
| `event_data.schedule_type` | `Cron` or `Rate` | `event_data` |
| `event_data.user_event` | The `--user-event` value, when set | `event_data` |

#### OBS validation checklist

| Property | Expected value | Where to look |
|----------|----------------|---------------|
| `trigger_type_code` | `OBS` | Response root |
| `event_data.name` | The `--name` you passed (event notification name) | `event_data` |
| `trigger_status` | `ACTIVE` | Response root |
| `event_data.bucket` | The `--bucket` value | `event_data` |
| `event_data.events` | Exactly the `--events` entries, e.g. `["ObjectCreated"]` or `["Put", "Post"]` | `event_data` |
| `event_data.prefix` | The `--prefix` value, when set | `event_data` |
| `event_data.suffix` | The `--suffix` value, when set | `event_data` |

For OBS triggers the `name` is the event-notification name, not a schedule name; do not expect a
`schedule` field on an OBS trigger.

### Step 3: Validate the Cron Expression (TIMER only)

Cron applies to TIMER triggers only. Read the expression from `event_data.schedule`, not from a
top-level `trigger_config` field (the SDK models have no `trigger_config` attribute):

```python
def describe_schedule(trigger, expected_cron=None):
    event_data = trigger.event_data
    if trigger.trigger_type_code != "TIMER":
        print(f"Not a TIMER trigger: {trigger.trigger_type_code}")
        return False

    schedule = event_data.schedule if event_data else None
    schedule_type = event_data.schedule_type if event_data else None
    print(f"Schedule: {schedule} (type: {schedule_type})")

    if schedule_type == "Cron" and schedule:
        parts = schedule.split()
        field_names = ["Second", "Minute", "Hour", "Day", "Month", "Weekday", "Year"]
        for field_name, value in zip(field_names, parts):
            print(f"  {field_name}: {value}")

    return expected_cron is None or schedule == expected_cron
```

For the Cron syntax accepted by this skill's validator, see
[Cron Expression Reference](./cron-reference.md).

### Step 4: Test Trigger Execution

#### TIMER: invoke the function manually

Verify the function body works before waiting for a scheduled invocation. Use the console
(Function details → **Test**) or the SDK invoke API, and confirm a normal response.

#### TIMER: wait for a scheduled execution

For a long interval, create a second, temporary trigger that runs more often instead of modifying
the original. The skill is create-only, so this also keeps the production trigger untouched:

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --name "verification-1min" \
    --schedule "0 * * * * ?" \
    --schedule-type "Cron" \
    --status "ACTIVE"
```

Watch the execution history for one or two invocations, then delete the temporary trigger from
the FunctionGraph console.

#### OBS: upload a matching object (end-to-end test)

This is the decisive test for an upload-triggered pipeline:

1. Note the trigger's `bucket`, `prefix`, `suffix`, and `events`.
2. Upload an object that matches all of them, for example `uploads/sample.jpg` into
   `input-images`.
3. Wait a few seconds and open Function details → **Triggers** → **Execution history** (or the
   function's logs).
4. Confirm one invocation appears and that the event payload contains the object key.

Then upload an object that does **not** match (wrong prefix or suffix) and confirm no extra
invocation is recorded — that proves the filters are active. Remember that `ObjectCreated` fires
on creation only; re-uploading the same key overwrites the object and does fire, but modifying
metadata alone may not.

### Step 5: Monitor Execution History

#### Via Console

1. Navigate to **FunctionGraph Console**
2. Select **Functions** → click the function name
3. Open the **Triggers** tab
4. Select the trigger → **Execution history**
5. Verify recent executions, their result, and the event payload

#### Via Logs

Function invocations write to LTS. Use the console log viewer for the function (Function details
→ **Logs**) and filter on the trigger's execution window. The KooCLI log-query operation is not
verified in this document, so no command is shown.

### Step 6: Verify Alarm Configuration

Configure Cloud Eye alarms on the `SYS.FunctionGraph` namespace for the function (for example on
error count or invocation count) from the Cloud Eye console. The exact KooCLI operation and
parameters for listing alarms are not verified in this document.

## Automated Verification Script

```python
#!/usr/bin/env python3
"""Read-only verification of a FunctionGraph TIMER or OBS trigger."""
import json
import os

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
from huaweicloudsdkfunctiongraph.v2.model.list_function_triggers_request import (
    ListFunctionTriggersRequest,
)


class TriggerVerifier:
    def __init__(self, ak, sk, project_id, region):
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
        self.client = FunctionGraphClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(FunctionGraphRegion.value_of(region)) \
            .build()

    def verify(self, function_urn, trigger_name, expected_type="TIMER",
               expected_schedule=None, expected_bucket=None, expected_events=None):
        request = ListFunctionTriggersRequest(function_urn=function_urn)
        response = self.client.list_function_triggers(request)
        triggers = response.body or []

        trigger = next(
            (t for t in triggers
             if t.event_data and t.event_data.name == trigger_name),
            None,
        )
        if not trigger:
            return {"status": "failed", "error": "Trigger not found"}

        event_data = trigger.event_data
        results = [
            ("trigger_type_code", trigger.trigger_type_code == expected_type),
            ("trigger_status", trigger.trigger_status == "ACTIVE"),
        ]

        if expected_type == "OBS":
            results.append(("bucket", event_data.bucket == expected_bucket))
            if expected_events is not None:
                results.append(
                    ("events", set(event_data.events or []) == set(expected_events))
                )
        else:
            if expected_schedule is not None:
                results.append(("schedule", event_data.schedule == expected_schedule))

        all_passed = all(passed for _, passed in results)
        return {
            "status": "passed" if all_passed else "failed",
            "trigger_id": trigger.trigger_id,
            "checks": [{"name": name, "passed": passed} for name, passed in results],
        }


if __name__ == "__main__":
    verifier = TriggerVerifier(
        ak=os.environ.get("HUAWEI_AK"),
        sk=os.environ.get("HUAWEI_SK"),
        project_id=os.environ.get("HUAWEI_PROJECT_ID"),
        region=os.environ.get("HUAWEI_REGION", "cn-north-4"),
    )

    # TIMER example
    result = verifier.verify(
        function_urn="urn:fss:cn-north-4:xxx:function:default:my-function:latest",
        trigger_name="daily-trigger",
        expected_type="TIMER",
        expected_schedule="0 0 2 * * ?",
    )

    # OBS example
    # result = verifier.verify(
    #     function_urn="urn:fss:cn-north-4:xxx:function:default:redact-image:latest",
    #     trigger_name="realtime-redact",
    #     expected_type="OBS",
    #     expected_bucket="input-images",
    #     expected_events=["ObjectCreated"],
    # )

    print(json.dumps(result, indent=2))
```

## Verification Checklist

### Pre-Deployment

- [ ] Function exists in the target region
- [ ] Region in `HUAWEI_REGION` matches the function's region
- [ ] IAM permissions confirmed (see [IAM Policies](./iam-policies.md))
- [ ] Network connectivity to the FunctionGraph endpoint verified
- [ ] TIMER: Cron expression validated
- [ ] OBS: bucket exists, and the source bucket needs no further setup

### Post-Deployment

- [ ] Trigger appears in the function's trigger list
- [ ] `trigger_type_code` is the requested type (`TIMER` or `OBS`)
- [ ] `trigger_status` is correct
- [ ] Trigger ID returned by the creation call matches the listed trigger
- [ ] TIMER: `event_data.schedule` matches the requested expression
- [ ] OBS: `event_data.bucket` matches the requested bucket
- [ ] OBS: `event_data.events` contains exactly the requested event types
- [ ] OBS: `event_data.prefix` / `event_data.suffix` match the requested filters (when used)

### Post-Execution

- [ ] Function execution logs present
- [ ] No execution errors in history
- [ ] Execution duration within limits
- [ ] Memory usage acceptable
- [ ] OBS: only matching object events produced invocations

## Troubleshooting Verification Failures

### Trigger Not Found

**Symptoms**: the trigger is missing from the list output

**Checks**:

1. Verify the function URN is correct
2. Check whether the creation call itself succeeded (non-zero exit means it did not)
3. Verify the trigger name spelling — for OBS compare `event_data.name`
4. Check region alignment between the client and the function

### OBS Trigger Not Firing

**Symptoms**: objects are uploaded but no execution history entries appear

**Checks**:

1. Is `trigger_status` `ACTIVE`?
2. Does the uploaded object key match `event_data.prefix` / `event_data.suffix` exactly?
   Prefix/suffix matching is literal, so `uploads/` does not match `upload/`.
3. Do the events cover this operation? `ObjectCreated` covers uploads; a deletion event such as
   `ObjectRemoved` is a different value.
4. Was the object uploaded **before** the trigger was created? Only events after creation fire.
5. Is the object in the bucket named in `event_data.bucket`? A different bucket has no
   notification attached.
6. Does the function itself succeed when invoked manually? A failing function still appears in
   history, so combine this with a manual test.

### TIMER Trigger Not Executing

**Symptoms**: no execution history entries

**Checks**:

1. Confirm `trigger_status` is `ACTIVE`
2. Verify the function is deployed, not in a failed state
3. Check the Cron expression: 6 or 7 fields, and no advanced Quartz characters (see
   [Cron Expression Reference](./cron-reference.md))
4. Remember the schedule is evaluated in UTC
5. Review function timeout settings

### Execution Failures

**Symptoms**: execution history shows failures

**Checks**:

1. Review the function code logs
2. Verify the function runtime and handler
3. Check timeout and memory settings
4. For OBS, validate that the function handles the OBS event payload

## Monitoring Commands

```bash
# All triggers of a function, including type and status
hcloud FunctionGraph ListFunctionTriggers \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest"

# One trigger, including the full event_data payload
hcloud FunctionGraph ShowFunctionTrigger \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --trigger_type_code OBS \
    --trigger_id "obs-xxx-xxx-xxx"
```

Both commands were verified against the KooCLI 7.2.12 `--help` output. For execution history and
metrics, use the FunctionGraph console.

## Related Documentation

- [CreateFunctionTrigger API](https://support.huaweicloud.com/api-functiongraph/functiongraph_06_0122.html) — verified (fetched 2026-11-03)
- [ShowFunctionTrigger API](https://support.huaweicloud.com/api-functiongraph/functiongraph_06_0120.html) — verified (fetched 2026-11-03)
- [FunctionGraph Permissions and Authorization Items](https://support.huaweicloud.com/api-functiongraph/functiongraph_06_1100.html) — verified (fetched 2026-11-03)
- [OBS Event Trigger Guide](./obs-trigger-guide.md)
- [Acceptance Criteria](./acceptance-criteria.md)
- [IAM Policies](./iam-policies.md)
