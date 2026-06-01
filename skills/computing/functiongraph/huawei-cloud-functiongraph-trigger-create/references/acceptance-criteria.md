# Acceptance Criteria

## Overview

This document defines the acceptance criteria for FunctionGraph scheduled trigger configuration. All criteria must be met for successful deployment.

## Functional Requirements

### FR-01: Trigger Creation

**Criterion**: Trigger must be successfully created with correct type

**Validation**:

- [ ] API returns success status (HTTP 201)
- [ ] Response contains valid `trigger_id`
- [ ] `trigger_type` equals `TIMER`
- [ ] Trigger appears in function trigger list

**Test Command**:

```bash
hcloud functiongraph v2 list-function-triggers \
    --function-urn "urn:fss:..." | grep -A 5 "TIMER"
```

### FR-02: Cron Expression Configuration

**Criterion**: Cron expression must be correctly stored and parsed

**Validation**:

- [ ] `trigger_config.schedule` matches input expression
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

### FR-03: Trigger Activation

**Criterion**: Trigger activation status must match configuration

**Validation**:

- [ ] `enable_status` equals input value
- [ ] Active triggers execute per schedule
- [ ] Disabled triggers do not execute

**Test Steps**:

1. Create trigger with `status=active`
2. Verify `enable_status` is `active`
3. Wait for one scheduled execution
4. Confirm execution in history

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
- [ ] Name is unique within function
- [ ] Name follows pattern: `[frequency]-[purpose]`

**Valid Examples**:

- `daily-backup`
- `hourly-health-check`
- `weekly-report-generation`

**Invalid Examples**:

- `` (empty)
- `a` * 65 (65 characters)
- `Daily Backup` (contains spaces, though allowed)

## Non-Functional Requirements

### NFR-01: Response Time

**Criterion**: Trigger creation must complete within acceptable time

**Threshold**: < 5 seconds for API response

**Measurement**:

```bash
time hcloud functiongraph v2 create-function-trigger ...
```

### NFR-02: Error Handling

**Criterion**: All errors must return meaningful messages

**Validation**:

- [ ] Invalid Cron returns `InvalidParameter` with details
- [ ] Missing function returns `FunctionNotFound`
- [ ] Duplicate name returns `TriggerAlreadyExists`
- [ ] Permission denied returns `AccessDenied`

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

**Criterion**: Trigger-to-function event flow must work

**Validation**:

- [ ] Trigger event reaches function
- [ ] Event payload contains trigger metadata
- [ ] Function receives correct event structure

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
hcloud functiongraph v2 list-functions --limit 1
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
        # Verify trigger_type is TIMER
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
# Remove test triggers
hcloud functiongraph v2 delete-function-trigger \
    --function-urn "..." \
    --trigger-id "test-trigger-id"

# Verify removal
hcloud functiongraph v2 list-function-triggers \
    --function-urn "..."
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
- [CLI Installation Guide](./sdk-installation-guide.md)
