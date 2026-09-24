# Monitoring Guide

## Overview

During an experiment, instance state changes must be continuously monitored to ensure the fault is injected as expected and to respond promptly to abnormal conditions.

## ECS instance state machine

### Shutdown process

```
ACTIVE → STOPPING → SHUTOFF
```

| State | Description | Typical duration |
|---|---|---|
| `ACTIVE` | Instance running | - |
| `STOPPING` | Shutting down (OS is closing) | 10-60 seconds |
| `SHUTOFF` | Stopped | - |

### Start process (rollback)

```
SHUTOFF → STARTING → ACTIVE
```

| State | Description | Typical duration |
|---|---|---|
| `SHUTOFF` | Stopped | - |
| `STARTING` | Booting (OS is starting) | 30-120 seconds |
| `ACTIVE` | Instance running | - |

### Other possible states

| State | Description | Handling |
|---|---|---|
| `ERROR` | Instance abnormal | Mark failure, attempt rollback |
| `REBOOT` | Rebooting | Wait until done |
| `HARD_REBOOT` | Force rebooting | Wait until done |
| `MIGRATING` | Migrating | Wait until done or timeout |

## Polling mechanism

### Polling parameters

| Parameter | Default | Description |
|---|---|---|
| `poll_interval` | 10 seconds | Interval between queries |
| `shutdown_timeout` | 300 seconds | Shutdown completion timeout |
| `start_timeout` | 300 seconds | Start completion timeout |
| `verify_timeout` | 300 seconds | Recovery verification timeout |

### Polling logic

```python
def poll_until_status(instance_ids, target_status, timeout, interval=10):
    """Poll instance status until all reach the target status or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        statuses = query_instance_statuses(instance_ids)
        if all(s == target_status for s in statuses):
            return True  # all reached target status
        time.sleep(interval)
    return False  # timeout
```

### State change detection

On each poll, compare the current status with the previous status:
- Status unchanged → keep polling
- Status changed → record a timeline event `{timestamp, instance_id, old_status, new_status}`
- Abnormal state (ERROR) → mark failure immediately

## CES alarm as a stop condition

### Configuration

Configure CES alarm rules in `stop_conditions` of `experiment.json`:

```json
{
  "stop_conditions": [
    {
      "type": "ces_alarm",
      "alarm_id": "al-xxx",
      "description": "CPU utilization above 90% on standby instance"
    }
  ]
}
```

### Check logic

During the experiment, each poll also checks the CES alarm status:

```bash
# Query alarm history
hcloud CES ListAlarmHistories --cli-region=cn-north-4 --alarm_id.1=al-xxx --cli-output=json  # --alarm_id.[N] 是数组参数，v2 要求此格式
```

If the alarm state is `alarm` or `ALARM` (triggered) — not `ok` (resolved) — then:
1. Record the alarm trigger event
2. Terminate the experiment early (do not wait for duration_seconds)
3. Enter the rollback flow immediately

## Monitoring output format

The monitoring script emits real-time status JSON:

```json
{
  "timestamp": "2026-09-08T10:01:30Z",
  "instances": [
    {
      "id": "i-xxx",
      "status": "STOPPING",
      "previous_status": "ACTIVE",
      "changed_at": "2026-09-08T10:01:25Z"
    }
  ],
  "all_target_status": false,
  "target_status": "SHUTOFF",
  "elapsed_seconds": 25,
  "remaining_seconds": 275
}
```

## Best practices

1. **Do not make the monitoring interval too short** - a 10-second interval balances real-time responsiveness and API call frequency, avoiding ECS API rate limits
2. **Set reasonable timeouts** - shutdown usually completes in 30-60 seconds but can take longer under high load; the default 300-second timeout leaves headroom
3. **Record a complete timeline** - record a timestamp for every state change for post-incident recovery time analysis
4. **Handle abnormal states immediately** - on ERROR, do not wait for timeout; enter rollback right away
5. **CES alarm check frequency** - match the instance status polling frequency to avoid extra API call overhead