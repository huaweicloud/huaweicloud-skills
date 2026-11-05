# OBS Event Trigger Guide

## Overview

This skill creates two trigger types:

| Trigger type | `--trigger-type` | Purpose |
|--------------|------------------|---------|
| Timer | `TIMER` (default) | Runs a function on a Quartz Cron schedule or at a fixed rate |
| Object Storage Service | `OBS` | Runs a function when objects are created or removed in an OBS bucket |

An OBS trigger turns an object event into a function invocation. It is the building block for
"upload-triggered, real-time" pipelines such as:

- Real-time masking / redaction of uploaded files: an object lands in the input bucket, the
  function redacts the sensitive region, and writes the result back to OBS
- Thumbnail generation and format conversion on upload
- Virus scanning, metadata extraction, text indexing, and content moderation
- Object-removal housekeeping (cache invalidation, audit trails, quota accounting)

**Capability boundary:** this skill only *creates* triggers. It does not update, disable, query,
or delete them. Use the FunctionGraph console, KooCLI, or the SDK for the rest of the trigger
lifecycle. Only `TIMER` and `OBS` triggers are supported; APIG, CTS, DDS, DMS, DIS, LTS, SMN,
KAFKA, RABBITMQ and the other trigger types are out of scope.

## Prerequisites

1. The target FunctionGraph function already exists in the region you call.
2. The OBS bucket used as the event source exists and belongs to the account you authenticate
   with.
3. `HUAWEI_AK`, `HUAWEI_SK`, `HUAWEI_REGION`, `HUAWEI_PROJECT_ID` are exported. See
   [SDK Installation Guide](./sdk-installation-guide.md).
4. The IAM principal holds the trigger permissions described in
   [IAM Policies](./iam-policies.md). The authorization item documented for trigger creation is
   `FunctionGraph:trigger:create`.
5. Python 3.9+ and `huaweicloudsdkfunctiongraph` are installed.

## Parameters

All parameters come from the skill's CLI contract (`scripts/create_trigger.py --help`):

| Parameter | CLI argument | Required | Description | Example |
|-----------|--------------|----------|-------------|---------|
| Function URN | `--function-urn` | Always | Target function URN | `urn:fss:cn-north-4:xxx:function:default:my-func:latest` |
| Trigger type | `--trigger-type` | No, default `TIMER` | Set to `OBS` for an object event trigger | `OBS` |
| Name | `--name` | Always | For `OBS`: the event notification name (1-64 characters). The API defaults it to the trigger ID when omitted, but this skill always requires it | `realtime-redact` |
| Status | `--status` | No, default `ACTIVE` | `ACTIVE` or `DISABLED` | `ACTIVE` |
| Bucket | `--bucket` | Required for `OBS` | Name of the OBS bucket used as the event source | `input-bucket` |
| Events | `--events` | Required for `OBS` | Comma-separated event types | `ObjectCreated` or `Put,Post` |
| Prefix | `--prefix` | No | Only objects whose key starts with this string raise the notification | `uploads/` |
| Suffix | `--suffix` | No | Only objects whose key ends with this string raise the notification | `.jpg` |

Notes:

- `--schedule`, `--schedule-type`, and `--user-event` are TIMER-only. They are ignored for
  `OBS`; `--schedule` is not required when `--trigger-type OBS` is used.
- `--bucket`, `--events`, `--prefix`, and `--suffix` are OBS-only.
- OBS triggers **cannot be disabled** after creation (see
  [Limitations](#limitations)), so keep `--status ACTIVE`.

## Event Types

`--events` is passed to the API field `event_data.events`. The following values are the event
names documented for that field (FunctionGraph API reference and the
`TriggerEventDataRequestBody` docstring of the Python SDK):

| Event value | Meaning |
|-------------|---------|
| `ObjectCreated` | All object-creation operations, including `Put`, `Post`, `Copy`, and multipart upload completion |
| `Put` | Object uploaded with the PUT method |
| `Post` | Object uploaded with the POST method |
| `Copy` | Object copied |
| `CompleteMultipartUpload` | Multipart upload parts merged into one object |
| `ObjectRemoved` | Object deleted |
| `Delete` | Object deleted with an explicit object version |
| `DeleteMarkerCreated` | Deletion that does not specify an object version (a delete marker is created) |

Qualified forms: the CLI also accepts an event name with a `:*` qualifier, for example
`ObjectCreated:*`. The script splits the value on commas, trims whitespace, and forwards each
entry unchanged, so the qualified form reaches the API verbatim. Only the plain names above are
attested by the API reference and the SDK docstring used to write this guide.

Combine several events with commas: `--events "Put,Post,CompleteMultipartUpload"`.

## Examples

### 1. Upload-triggered real-time masking (the issue #945 scenario)

Process every newly uploaded object and write the redacted result back to OBS. The function is
invoked as soon as an object is created, so the pipeline is near real time rather than batch.

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:redact-image:latest" \
    --trigger-type "OBS" \
    --name "realtime-redact" \
    --bucket "input-images" \
    --events "ObjectCreated" \
    --status "ACTIVE"
```

### 2. Restrict the trigger to one key space and file type

Use `--prefix` and `--suffix` so only uploads under `uploads/` that end in `.jpg` invoke the
function. Everything else stays invisible to the trigger:

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:redact-image:latest" \
    --trigger-type "OBS" \
    --name "redact-jpg-uploads" \
    --bucket "input-images" \
    --events "ObjectCreated" \
    --prefix "uploads/" \
    --suffix ".jpg"
```

### 3. React to several upload methods at once

`Put` and `Post` cover the common upload paths; `CompleteMultipartUpload` adds large files that
arrive as multipart uploads:

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:index-document:latest" \
    --trigger-type "OBS" \
    --name "index-uploads" \
    --bucket "documents" \
    --events "Put,Post,CompleteMultipartUpload" \
    --status "ACTIVE"
```

### 4. React to object deletion

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:cleanup-cache:latest" \
    --trigger-type "OBS" \
    --name "cache-invalidation" \
    --bucket "published-assets" \
    --events "ObjectRemoved"
```

## Success Response

On success the script prints JSON containing the keys required by the CLI contract plus the
OBS-specific `bucket` and `events`:

```json
{
    "status": "success",
    "trigger_id": "obs-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "trigger_name": "realtime-redact",
    "trigger_type": "OBS",
    "enable_status": "ACTIVE",
    "message": "Trigger created successfully",
    "bucket": "input-images",
    "events": ["ObjectCreated"]
}
```

The `events` array contains the whitespace-trimmed entries parsed from `--events`. On failure the
response contains `status`, `error_code`, and `message`, and the script exits non-zero.

## SDK Equivalent

The script builds the same request shown here. Use it directly when you want to create the OBS
trigger from your own code:

```python
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient
from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
from huaweicloudsdkfunctiongraph.v2.model.create_function_trigger_request import (
    CreateFunctionTriggerRequest,
)
from huaweicloudsdkfunctiongraph.v2.model.create_function_trigger_request_body import (
    CreateFunctionTriggerRequestBody,
)
from huaweicloudsdkfunctiongraph.v2.model.trigger_event_data_request_body import (
    TriggerEventDataRequestBody,
)

credentials = BasicCredentials(
    ak=os.environ.get("HUAWEI_AK"),
    sk=os.environ.get("HUAWEI_SK"),
    project_id=os.environ.get("HUAWEI_PROJECT_ID"),
)

client = FunctionGraphClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(FunctionGraphRegion.value_of(os.environ.get("HUAWEI_REGION", "cn-north-4"))) \
    .build()

# OBS trigger: bucket and events are required, prefix/suffix are optional.
event_data = TriggerEventDataRequestBody(
    name="realtime-redact",
    bucket="input-images",
    events=["ObjectCreated"],
    prefix="uploads/",
    suffix=".jpg",
)

request = CreateFunctionTriggerRequest(
    function_urn="urn:fss:cn-north-4:project_id:function:default:redact-image:latest",
    body=CreateFunctionTriggerRequestBody(
        trigger_type_code="OBS",
        trigger_status="ACTIVE",
        event_data=event_data,
    ),
)

response = client.create_function_trigger(request)
print(response.trigger_id)
```

For the TIMER variant (`.with_region(FunctionGraphRegion.value_of(region))`,
`schedule_type`, `schedule`, `user_event`) see
[SDK Installation Guide](./sdk-installation-guide.md).

## Verification

Confirm the trigger and its OBS settings after creation. Full procedures are in
[Verification Method](./verification-method.md):

```bash
# Show the OBS trigger itself (KooCLI)
hcloud FunctionGraph ShowFunctionTrigger \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:redact-image:latest" \
    --trigger_type_code OBS \
    --trigger_id "obs-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

The response exposes `trigger_type_code`, `trigger_status`, and an `event_data` object that
carries the OBS properties `bucket`, `prefix`, `suffix`, and `events`. Check that:

- `trigger_type_code` is `OBS`
- `trigger_status` is `ACTIVE`
- `event_data.bucket` equals the `--bucket` value
- `event_data.events` contains exactly the requested event types
- `event_data.prefix` / `event_data.suffix` match the filters you passed (when used)

You can also confirm it in the FunctionGraph console: function details → **Triggers** tab. Then
upload a matching object to the bucket and check the function's execution history for an
invocation.

## Limitations

1. **OBS triggers cannot be disabled.** The FunctionGraph API states that only TIMER, DDS, DMS,
   KAFKA, and LTS triggers support being disabled; other trigger types, including OBS, do not.
   Create the trigger only when you intend to use it, and delete it to stop invocations.
2. **The bucket cannot be changed after creation.** The event-source bucket is fixed at creation
   time; changing the source requires deleting and recreating the trigger.
3. **Bucket naming.** The bucket is used as the event source and cannot duplicate a bucket name
   already used by your account or by another account for the same purpose.
4. **`--name` is the event notification name.** For OBS it names the notification configured on
   the bucket, not the function; it defaults to the trigger ID only when the API field is absent,
   and this skill always sends it.
5. **One source bucket per trigger.** To watch several buckets, create one trigger per bucket.
6. **Trigger quota.** FunctionGraph limits the number of triggers per function. When the limit is
   reached, creation fails with `TriggerLimitExceeded`; remove unused triggers first.
7. **Create-only.** Update, disable, query, and delete operations are outside this skill.

## Related Documents

- [SDK Installation Guide](./sdk-installation-guide.md)
- [IAM Policies](./iam-policies.md)
- [Verification Method](./verification-method.md)
- [Acceptance Criteria](./acceptance-criteria.md)
- [Cron Expression Reference](./cron-reference.md) (TIMER triggers)
