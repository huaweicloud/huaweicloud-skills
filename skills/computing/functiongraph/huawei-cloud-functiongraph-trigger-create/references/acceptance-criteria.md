# Acceptance Criteria

## Overview

This document defines the acceptance criteria for FunctionGraph TIMER and OBS trigger
configuration. All criteria must be met for successful deployment.

Scope of this skill:

- **Supported trigger types**: `TIMER` and `OBS`.
- **Supported operations**: *create* only. Update, disable, query, and delete are not part of the
  skill and must be done through the console, KooCLI, or the SDK.
- **Out of scope**: APIG, CTS, DDS, DMS, DIS, LTS, SMN, KAFKA, RABBITMQ and every other trigger
  type.

## Functional Requirements

### FR-01: Trigger Creation

**Criterion**: Trigger must be successfully created with the requested type

**Validation**:

- [ ] `scripts/create_trigger.py` exits with status 0
- [ ] Output JSON has `status: "success"` and a valid `trigger_id`
- [ ] `trigger_type` equals the requested type (`TIMER` or `OBS`)
- [ ] `trigger_name` matches the requested `--name`
- [ ] `enable_status` equals the requested `--status`
- [ ] Trigger appears in the function's trigger list

**Test Command**:

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --name "daily-trigger" \
    --schedule "0 0 2 * * ?"

hcloud FunctionGraph ListFunctionTriggers \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest"
```

### FR-02: Cron Expression Configuration

Cron applies to `TIMER` triggers only; it is not part of OBS acceptance.

**Criterion**: Cron expression must be correctly stored and parsed

**Validation**:

- [ ] `event_data.schedule` matches the input expression
- [ ] Expression is valid Quartz Cron format
- [ ] All 6-7 fields are present
- [ ] Next execution time is calculable

**Test Cases**:

| Input Expression | Expected Behavior | Valid |
|-----------------|-------------------|-------|
| `0 0 2 * * ?` | Daily at 2:00 AM | ✓ |
| `0 */30 * * * ?` | Every 30 minutes | ✓ |
| `0 0 9 ? * MON-FRI` | Weekdays at 9:00 AM | ✓ |
| `0 0 * * *` | Invalid (missing field) | ✗ |
| `60 0 0 * * ?` | Invalid (second > 59) | ✗ |
| `0 0 0 L * ?` | Invalid (unsupported `L` character) | ✗ |

### FR-03: Trigger Activation

**Criterion**: Trigger activation status must match configuration

**Validation**:

- [ ] `enable_status` in the output JSON equals the `--status` input value
- [ ] `trigger_status` in `ListFunctionTriggers` / `ShowFunctionTrigger` is `ACTIVE`
- [ ] TIMER: an active trigger executes per its schedule
- [ ] OBS: an active trigger fires on matching object events

**Test Steps (TIMER)**:

1. Create the trigger with `--status ACTIVE`
2. Verify `enable_status` is `ACTIVE`
3. Wait for one scheduled execution
4. Confirm the execution in history

**Test Steps (OBS)**:

1. Create the trigger with `--status ACTIVE`
2. Verify `enable_status` is `ACTIVE`
3. Upload a matching object
4. Confirm the invocation in history

> OBS triggers cannot be disabled after creation: the FunctionGraph API states that only TIMER,
> DDS, DMS, KAFKA, and LTS triggers support being disabled. Do not accept a test plan that
> requires setting an OBS trigger to `DISABLED`.

### FR-04: Function Association

**Criterion**: Trigger must be correctly associated with target function

**Validation**:

- [ ] Trigger is linked to correct function URN
- [ ] Function exists and is accessible
- [ ] Trigger appears in function's trigger list

### FR-05: Naming Conventions

**Criterion**: Trigger name must follow naming standards

**Validation**:

- [ ] Name length: 1-64 characters
- [ ] Name is unique within the function
- [ ] TIMER: name follows pattern: `[frequency]-[purpose]`
- [ ] OBS: name is the event notification name on the bucket and is descriptive of the event
      source, e.g. `realtime-redact` or `redact-jpg-uploads`

**Valid Examples**:

- `daily-backup`
- `hourly-health-check`
- `realtime-redact` (OBS)
- `redact-jpg-uploads` (OBS)

**Invalid Examples**:

- `` (empty)
- `a` * 65 (65 characters)
- `Daily Backup` (contains spaces, though allowed)

### FR-06: OBS Trigger Creation

**Criterion**: An OBS event trigger must be created with the requested bucket and events

**Validation**:

- [ ] `--bucket` and `--events` are accepted and sent as `event_data.bucket` /
      `event_data.events`
- [ ] Output JSON has `trigger_type: "OBS"`, and echoes `bucket` and the parsed `events` array
- [ ] `--prefix` / `--suffix` reach `event_data.prefix` / `event_data.suffix` (when provided)
- [ ] `ListFunctionTriggers` / `ShowFunctionTrigger` report `event_data.bucket` and
      `event_data.events` matching the request
- [ ] Uploading a matching object produces exactly one invocation
- [ ] Uploading a non-matching object (wrong prefix or suffix) produces none

**Test Command**:

```bash
python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:redact-image:latest" \
    --trigger-type "OBS" \
    --name "realtime-redact" \
    --bucket "input-images" \
    --events "ObjectCreated" \
    --prefix "uploads/" \
    --suffix ".jpg"

hcloud FunctionGraph ShowFunctionTrigger \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:redact-image:latest" \
    --trigger_type_code OBS \
    --trigger_id "<trigger_id from the output>"
```

**Negative cases** (must fail with `InvalidParameter`):

- `--trigger-type OBS` without `--bucket`
- `--trigger-type OBS` without `--events`
- `--events ",,,"` (no usable event value)

### FR-07: Documented Capability Boundary

**Criterion**: The skill must state what it can and cannot do, so users are not misled

**Validation**:

- [ ] `SKILL.md` declares that only creation is supported (no delete/update/disable/query)
- [ ] `SKILL.md` declares the supported trigger types as `TIMER` and `OBS` only, and names the
      unsupported ones
- [ ] The references contain no delete/update/list-trigger command presented as a skill
      operation (read-only verification commands are acceptable and are clearly marked as such)
- [ ] No reference to the safety-bypass argument that was removed in an earlier change
- [ ] Every `--flag` documented for `scripts/create_trigger.py` exists in the script's
      `--help` output: `--function-urn`, `--trigger-type`, `--name`, `--status`, `--schedule`,
      `--schedule-type`, `--user-event`, `--bucket`, `--events`, `--prefix`, `--suffix`

## Non-Functional Requirements

### NFR-01: Response Time

**Criterion**: Trigger creation must complete within acceptable time

**Threshold**: < 5 seconds for API response

**Measurement**:

```bash
time python3 scripts/create_trigger.py \
    --function-urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --name "perf-check" \
    --schedule "0 0 2 * * ?"
```

### NFR-02: Error Handling

**Criterion**: All errors must return meaningful messages from the documented error-code set

The skill's error codes are `InvalidParameter`, `FunctionNotFound`, `NetworkError`,
`TriggerAlreadyExists`, `TriggerLimitExceeded`, and `InternalError`.

**Validation**:

- [ ] Invalid Cron returns `InvalidParameter` with details
- [ ] `--trigger-type TIMER` without `--schedule` returns `InvalidParameter`
- [ ] `--trigger-type OBS` without `--bucket` or without `--events` returns `InvalidParameter`
- [ ] Missing function returns `FunctionNotFound`
- [ ] Transport failures (DNS, timeout, connection reset) return `NetworkError`, not an
      uncaught traceback
- [ ] Duplicate name returns `TriggerAlreadyExists`
- [ ] Trigger quota exhausted returns `TriggerLimitExceeded`
- [ ] Unexpected failures return `InternalError`
- [ ] Errors exit non-zero and never print credential values

> `AccessDenied` was listed in earlier revisions of this document but is not part of the skill's
> error-code set. A real permission problem surfaces as an HTTP 403 from the API and is reported
> through the underlying `error_code` / `InternalError` path.

### NFR-03: Idempotency

**Criterion**: Re-running with same parameters should not cause errors

**Validation**:

- [ ] Duplicate creation returns `TriggerAlreadyExists`
- [ ] Existing trigger is not modified
- [ ] No duplicate triggers created

### NFR-04: Security

**Criterion**: Operations must enforce IAM permissions

**Validation**:

- [ ] Operations fail without required permissions
- [ ] Audit logs capture trigger operations
- [ ] No credential exposure in logs

## Integration Requirements

### IR-01: Cloud Eye Integration

**Criterion**: Function must have monitoring capability

**Validation**:

- [ ] Executions appear in Cloud Eye metrics
- [ ] Alarm rules can be configured
- [ ] Error notifications are sent

### IR-02: LTS Integration

**Criterion**: Function logs must be accessible

**Validation**:

- [ ] Execution logs appear in LTS
- [ ] Log stream exists for function
- [ ] Logs are queryable

### IR-03: Event Flow

**Criterion**: Trigger-to-function event flow must work for both supported trigger types

**Validation**:

- [ ] TIMER: the scheduled invocation reaches the function
- [ ] TIMER: the event payload contains `trigger_type`, `trigger_name`, and `user_event`
- [ ] OBS: an object created in the source bucket reaches the function
- [ ] OBS: the event payload identifies the bucket and the object key
- [ ] Function receives the correct event structure for the trigger type

## Operational Requirements

### OR-01: Documentation

**Criterion**: Trigger must have adequate documentation

**Validation**:

- [ ] Description field is populated
- [ ] Purpose is clearly stated
- [ ] Cron expression is documented

### OR-02: Monitoring

**Criterion**: Trigger execution must be monitorable

**Validation**:

- [ ] Execution history is available
- [ ] Success/failure metrics exist
- [ ] Alerting is configured

### OR-03: Backup/Recovery

**Criterion**: Trigger configuration must be recoverable

**Validation**:

- [ ] Trigger details are retrievable via API
- [ ] Configuration can be exported
- [ ] Recreation from backup works

## Acceptance Test Procedure

### Pre-Test Setup

```bash
# Set environment variables
export HUAWEI_AK="your-ak"
export HUAWEI_SK="your-sk"
export HUAWEI_REGION="cn-north-4"
export HUAWEI_PROJECT_ID="your-project-id"

# Verify CLI is working
hcloud FunctionGraph ListFunctions --cli-region=cn-north-4 --maxitems 1
```

### Test Suite

```python
#!/usr/bin/env python3
"""Acceptance test suite for FunctionGraph trigger creation"""

import unittest
import json

class TestTriggerAcceptance(unittest.TestCase):

    def setUp(self):
        # Initialize test client
        pass

    def test_fr01_trigger_creation(self):
        """FR-01: Trigger must be created successfully"""
        # Create trigger
        # Verify trigger_id is returned
        # Verify trigger_type is the requested type (TIMER or OBS)
        pass

    def test_fr02_cron_configuration(self):
        """FR-02: Cron expression must be valid"""
        # Test valid expressions
        # Test invalid expressions
        pass

    def test_fr03_trigger_activation(self):
        """FR-03: Trigger status must match configuration"""
        # Create with active status
        # Verify status
        pass

    def test_fr04_function_association(self):
        """FR-04: Trigger must be linked to function"""
        # Verify function URN
        # Check trigger list
        pass

    def test_fr05_naming_conventions(self):
        """FR-05: Name must follow conventions"""
        # Test valid names
        # Test invalid names
        pass

    def test_fr06_obs_trigger_creation(self):
        """FR-06: OBS trigger must carry the requested bucket and events"""
        # Create with --trigger-type OBS --bucket ... --events ...
        # Verify output has trigger_type OBS, bucket and parsed events
        # Upload matching object -> one invocation
        # Upload non-matching object -> no invocation
        pass

    def test_fr07_capability_boundary_documented(self):
        """FR-07: Documentation must state the capability boundary"""
        # SKILL.md: create-only, TIMER + OBS only
        # No removed safety-bypass argument anywhere
        # Every documented flag exists in scripts/create_trigger.py --help
        pass

    def test_nfr01_response_time(self):
        """NFR-01: Response must be timely"""
        # Measure response time
        # Assert < 5 seconds
        pass

    def test_nfr02_error_handling(self):
        """NFR-02: Errors must be meaningful"""
        # Test various error conditions
        # Verify error messages
        pass

if __name__ == '__main__':
    unittest.main()
```

### Post-Test Cleanup

```bash
# Remove a test trigger (this skill does not delete anything; use KooCLI or the console)
hcloud FunctionGraph DeleteFunctionTrigger \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest" \
    --trigger_type_code TIMER \
    --trigger_id "test-trigger-id"

# Verify removal
hcloud FunctionGraph ListFunctionTriggers \
    --cli-region=cn-north-4 \
    --function_urn "urn:fss:cn-north-4:project_id:function:default:my-function:latest"
```

## Acceptance Sign-off

### Approval Checklist

| Criterion | Status | Approver | Date |
|-----------|--------|----------|------|
| FR-01: Trigger Creation | ☐ | | |
| FR-02: Cron Configuration | ☐ | | |
| FR-03: Trigger Activation | ☐ | | |
| FR-04: Function Association | ☐ | | |
| FR-05: Naming Conventions | ☐ | | |
| FR-06: OBS Trigger Creation | ☐ | | |
| FR-07: Capability Boundary Documented | ☐ | | |
| NFR-01: Response Time | ☐ | | |
| NFR-02: Error Handling | ☐ | | |
| NFR-03: Idempotency | ☐ | | |
| NFR-04: Security | ☐ | | |
| IR-01: Cloud Eye | ☐ | | |
| IR-02: LTS | ☐ | | |
| IR-03: Event Flow | ☐ | | |
| OR-01: Documentation | ☐ | | |
| OR-02: Monitoring | ☐ | | |
| OR-03: Backup/Recovery | ☐ | | |

### Final Approval

- **Test Date**: _______________
- **Tester**: _______________
- **Approver**: _______________
- **Status**: ☐ PASS / ☐ FAIL
- **Sign-off Date**: _______________

## Regression Test Triggers

Perform regression testing when:

1. FunctionGraph API version changes
2. Huawei Cloud SDK updates
3. IAM policy modifications
4. Network configuration changes
5. Function code updates

## Related Documentation

- [Verification Method](./verification-method.md)
- [IAM Policies](./iam-policies.md)
- [SDK Installation Guide](./sdk-installation-guide.md)
- [OBS Event Trigger Guide](./obs-trigger-guide.md)
- [Cron Expression Reference](./cron-reference.md)
