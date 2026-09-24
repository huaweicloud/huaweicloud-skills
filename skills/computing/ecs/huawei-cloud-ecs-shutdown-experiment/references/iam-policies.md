# IAM Policies — Required Permissions

## Overview

This skill covers the full ECS shutdown experiment lifecycle (prepare → execute → analyze). Each phase requires different permissions: Phase 1 needs ECS/AS read; Phase 2 adds ECS write (stop/start); Phase 3 adds LTS and CES read.

## Permissions by Phase

### Phase 1: Prepare — ECS Read + AS Read

| API | Action | Purpose |
|---|---|---|
| `ListServersDetails` | `ecs:servers:list` | Discover ECS instances for experiment targets |
| `ListScalingInstances` | `as:scalingInstances:list` | Check if target instances are in AS groups (validation gate, optional) |

### Phase 2: Execute — ECS Read + Write + CES Read (optional)

| API | Action | Purpose |
|---|---|---|
| `ListServersDetails` | `ecs:servers:list` | Query instance status (pre-check, monitoring, verification) |
| `BatchStopServers` | `ecs:servers:stop` | Execute shutdown fault injection |
| `BatchStartServers` | `ecs:servers:start` | Rollback / recovery after experiment |
| `ListAlarmHistories` | `ces:alarmHistories:list` | Check CES alarm state as stop condition (optional) |

### Phase 3: Analyze — ECS Read + LTS Read + CES Read

| API | Action | Purpose |
|---|---|---|
| `ListServersDetails` | `ecs:servers:list` | Query target ECS instance IPs, DNS names, and EIPs |
| `ListLogs` | `lts:logs:search` | Query application logs within the experiment time window |
| `ListLogGroups` | LTS read | Locate the log group that collects the target ECS's application logs |
| `ListLogStreams` | LTS read | Locate the log stream within the group |
| `ShowMetricData` | `ces:metricData:get` | Query CES monitoring metrics (CPU, network, disk, memory) |

> The exact IAM action names for `ListLogGroups` / `ListLogStreams` depend on the LTS permission matrix of your region — grant `LTS ReadOnlyAccess` or the read/list actions from the table above.

## Sample IAM Policy (JSON — Full Lifecycle)

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecs:servers:list",
                "ecs:servers:stop",
                "ecs:servers:start"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "as:scalingInstances:list"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ces:alarmHistories:list",
                "ces:metricData:get"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "lts:logs:search"
            ],
            "Resource": "*"
        }
    ]
}
```

## Permission Scope Recommendations

- **Prepare only** (discovery + validation): `ecs:servers:list` + `as:scalingInstances:list`
- **Full experiment** (prepare + execute): Add `ecs:servers:stop`, `ecs:servers:start`, optionally `ces:alarmHistories:list`
- **Full lifecycle** (prepare + execute + analyze): Add `lts:logs:search`, `ces:metricData:get`, LTS read
- **Production environments**: Use resource-level restrictions to limit which ECS instances can be stopped/started and which log groups can be queried.

## Notes

- The AS group check is **optional** — if the AS API is not available or permission is denied, validation skips the AS check and marks it as "skipped".
- Phase 3 (Analyze) is **read-only** — it queries resources and collects logs/metrics but does not modify any cloud resources.
- AK/SK credentials should be passed via environment variables (`HW_ACCESS_KEY`, `HW_SECRET_KEY`), never hardcoded in scripts.
- Subprocess environment uses an explicit whitelist (`PATH`, `HOME`, `LANG`, `LC_ALL`, Huawei Cloud credential vars) — never full `os.environ` inheritance.
