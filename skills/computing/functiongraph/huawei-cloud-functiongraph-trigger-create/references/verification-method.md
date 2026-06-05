# Verification Method

## Overview

This document provides comprehensive methods to verify that FunctionGraph scheduled triggers have been correctly configured and are functioning as expected.

## Verification Steps

### Step 1: Confirm Trigger Creation

#### Using KooCLI

```bash
# List all triggers for the function
hcloud functiongraph v2 list-function-triggers \
    --function-urn "urn:fss:cn-north-4:project-id:function:default:my-function:latest"
```

Expected output structure:

```json
{
    "triggers": [
        {
            "trigger_id": "timer-xxx-xxx-xxx",
            "trigger_type": "TIMER",
            "trigger_name": "daily-trigger",
            "trigger_config": "{\"name\":\"daily-trigger\",\"schedule\":\"0 0 2 * * ?\",\"scheduleType\":\"Rate\"}",
            "enable_status": "active",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z"
        }
    ]
}
```

#### Using Python SDK

```python
from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient

def verify_trigger(client, function_urn, trigger_name):
    from huaweicloudsdkfunctiongraph.v2.model.list_function_triggers_request import ListFunctionTriggersRequest
    
    request = ListFunctionTriggersRequest(function_urn=function_urn)
    response = client.list_function_triggers(request)
    
    for trigger in response.triggers:
        if trigger.trigger_name == trigger_name:
            print(f"✓ Trigger found: {trigger.trigger_id}")
            print(f"  Type: {trigger.trigger_type}")
            print(f"  Status: {trigger.enable_status}")
            return trigger
    
    print("✗ Trigger not found")
    return None
```

### Step 2: Validate Trigger Configuration

#### Check Trigger Properties

```bash
# Query specific trigger type
hcloud functiongraph v2 show-function-trigger \
    --function-urn "urn:fss:cn-north-4:project-id:function:default:my-function:latest" \
    --trigger-type-codes "TIMER"
```

Validation checklist:

| Property | Expected Value | Verification Method |
|----------|---------------|---------------------|
| `trigger_type` | `TIMER` | Confirm in list output |
| `trigger_name` | Matches input | Compare with specification |
| `enable_status` | `active` | Verify in trigger details |
| `schedule` | Valid Cron | Parse trigger_config JSON |
| `maxRetryTime` | As configured | Check trigger_config |

### Step 3: Validate Cron Expression

#### Cron Expression Parser

```python
import json
from datetime import datetime

def validate_cron_config(trigger_config):
    config = json.loads(trigger_config)
    cron = config.get('schedule')
    
    print(f"Cron Expression: {cron}")
    
    # Parse and display schedule
    parts = cron.split()
    fields = ['Second', 'Minute', 'Hour', 'Day', 'Month', 'Weekday']
    
    for field, value in zip(fields, parts):
        print(f"  {field}: {value}")
    
    # Additional validation logic here
    return True
```

### Step 4: Test Trigger Execution

#### Option A: Manual Trigger Invocation

```bash
# Invoke function manually to verify execution path
hcloud functiongraph v2 invoke-function \
    --function-urn "urn:fss:cn-north-4:project-id:function:default:my-function:latest" \
    --body '{"test": true}'
```

#### Option B: Wait for Scheduled Execution

For triggers with long intervals, temporarily update to a shorter schedule:

```bash
# Temporarily set to 1-minute interval for testing
hcloud functiongraph v2 update-function-trigger \
    --function-urn "..." \
    --trigger-id "timer-xxx" \
    --body '{
        "trigger_config": "{\"schedule\":\"0 */1 * * * ?\",\"scheduleType\":\"Rate\"}"
    }'

# Monitor for 1-2 executions
# Then restore original schedule
```

### Step 5: Monitor Execution History

#### Via Console

1. Navigate to **FunctionGraph Console**
2. Select **Functions** → Click function name
3. Go to **Triggers** tab
4. Click **Execution History** for the trigger
5. Verify recent executions

#### Via API

```python
def get_execution_history(client, function_urn, limit=10):
    from huaweicloudsdkfunctiongraph.v2.model.list_function_statistics_request import ListFunctionStatisticsRequest
    
    request = ListFunctionStatisticsRequest(
        function_urn=function_urn,
        period='1h'  # Last hour
    )
    response = client.list_function_statistics(request)
    
    print(f"Executions in last hour: {len(response.statistic)}")
    
    for stat in response.statistic:
        print(f"  Duration: {stat.duration}ms")
        print(f"  Status: {stat.status}")
```

### Step 6: Verify Alarm Configuration

Ensure Cloud Eye alarms are configured:

```bash
# Check alarm rules for the function
hcloud ces v2 list-alarms \
    --namespace "SYS.FunctionGraph" \
    --dimensions "name=function_urn,value=urn:fss:..."
```

## Automated Verification Script

```python
#!/usr/bin/env python3
import os
import json
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient, FunctionGraphRegion

class TriggerVerifier:
    def __init__(self, ak, sk, project_id, region):
        credentials = BasicCredentials(ak=ak, sk=sk, project_id=project_id)
        self.client = FunctionGraphClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(FunctionGraphRegion.value_of(region)) \
            .build()
    
    def verify(self, function_urn, trigger_name, expected_cron):
        results = []
        
        # 1. List triggers
        triggers = self._list_triggers(function_urn)
        trigger = next((t for t in triggers if t.trigger_name == trigger_name), None)
        
        if not trigger:
            return {"status": "failed", "error": "Trigger not found"}
        
        # 2. Verify properties
        results.append(("trigger_type", trigger.trigger_type == "TIMER"))
        results.append(("enable_status", trigger.enable_status == "active"))
        
        # 3. Verify cron
        config = json.loads(trigger.trigger_config)
        results.append(("cron_match", config.get("schedule") == expected_cron))
        
        # 4. Summary
        all_passed = all(r[1] for r in results)
        
        return {
            "status": "passed" if all_passed else "failed",
            "trigger_id": trigger.trigger_id,
            "checks": [{"name": n, "passed": p} for n, p in results]
        }
    
    def _list_triggers(self, function_urn):
        from huaweicloudsdkfunctiongraph.v2.model.list_function_triggers_request import ListFunctionTriggersRequest
        request = ListFunctionTriggersRequest(function_urn=function_urn)
        response = self.client.list_function_triggers(request)
        return response.triggers

# Usage
if __name__ == "__main__":
    verifier = TriggerVerifier(
        ak=os.environ.get("HUAWEI_AK"),
        sk=os.environ.get("HUAWEI_SK"),
        project_id=os.environ.get("HUAWEI_PROJECT_ID"),
        region=os.environ.get("HUAWEI_REGION", "cn-north-4")
    )
    
    result = verifier.verify(
        function_urn="urn:fss:cn-north-4:xxx:function:default:my-function:latest",
        trigger_name="daily-trigger",
        expected_cron="0 0 2 * * ?"
    )
    
    print(json.dumps(result, indent=2))
```

## Verification Checklist

### Pre-Deployment

- [ ] Cron expression validated
- [ ] Function exists in target region
- [ ] IAM permissions confirmed
- [ ] Network connectivity verified

### Post-Deployment

- [ ] Trigger appears in function trigger list
- [ ] Trigger type is `TIMER`
- [ ] Enable status is correct
- [ ] Cron expression matches specification
- [ ] Trigger ID returned from API

### Post-Execution

- [ ] Function execution logs present
- [ ] No execution errors in history
- [ ] Execution duration within limits
- [ ] Memory usage acceptable

## Troubleshooting Verification Failures

### Trigger Not Found

**Symptoms**: Trigger not in list output

**Checks**:

1. Verify function URN is correct
2. Check if creation request succeeded
3. Verify trigger name spelling
4. Check region alignment

### Trigger Not Executing

**Symptoms**: No execution history entries

**Checks**:

1. Confirm trigger status is `active`
2. Verify function is deployed (not failed state)
3. Check Cron expression validity
4. Review function timeout settings

### Execution Failures

**Symptoms**: Execution history shows failures

**Checks**:

1. Review function code logs
2. Verify function has correct runtime
3. Check function timeout settings
4. Validate function input/output

## Monitoring Commands

### Real-time Monitoring

```bash
# Stream function logs
hcloud lts v2 list-logs \
    --log-group-id "functiongraph-logs" \
    --log-stream-id "my-function-logs" \
    --start-time $(date -d '5 minutes ago' +%s)000
```

### Statistics Summary

```bash
# Get function statistics
hcloud functiongraph v2 list-function-statistics \
    --function-urn "..." \
    --period "1d"
```

## Related Documentation

- [FunctionGraph Console Guide](https://support.huaweicloud.com/usermanual-functiongraph/functiongraph_01_0100.html)
- [Trigger Management](https://support.huaweicloud.com/api-functiongraph/FunctionGraph_06_0123.html)
- [Execution Monitoring](https://support.huaweicloud.com/functiongraph/index.html)
