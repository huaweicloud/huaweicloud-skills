# Verification Method

## Overview

This document defines the verification and testing methodology for the `huawei-cloud-rds-smart-service` skill.

## Test Environment Requirements

| Requirement | Description |
|-------------|-------------|
| Huawei Cloud account | Active account with RDS service enabled |
| AK/SK credentials | Configured via environment variables |
| hcloud CLI | Version 7.2.0+ installed and authenticated |
| Python 3.8+ | With `huaweicloudsdkrds` package installed |
| Test RDS instance | At least one running RDS instance (MySQL recommended) |
| Region | `cn-north-4` (default) or any valid region |

## Verification Levels

### Level 1: Static Verification

- **SKILL.md structure**: Verify YAML frontmatter is valid
- **Command syntax**: Verify all `hcloud RDS` commands match CLI help output
- **Reference links**: Verify all referenced files exist
- **Parameter table**: Verify required parameters are documented

### Level 2: Functional Verification

| Test Case | Command | Expected Result |
|-----------|---------|-----------------|
| List instances | `hcloud RDS ListInstances` | Returns JSON array of instances |
| List flavors | `hcloud RDS ListFlavors --database_name=MySQL` | Returns available flavors |
| List datastores | `hcloud RDS ListDatastores --database_name=MySQL` | Returns database versions |
| Show instance detail | `hcloud RDS ShowInstance --instance_id={id}` | Returns instance details |
| List slow logs | `hcloud RDS ListSlowLogs --instance_id={id}` | Returns slow log entries |
| List error logs | `hcloud RDS ListErrorLogs --instance_id={id}` | Returns error log entries |
| List configurations | `hcloud RDS ListConfigurations` | Returns parameter groups |
| List backups | `hcloud RDS ListBackups --instance_id={id}` | Returns backup list |
| Show backup policy | `hcloud RDS ShowBackupPolicy --instance_id={id}` | Returns backup policy |

### Level 3: Mutation Verification (Requires Confirmation)

| Test Case | Command | Pre-conditions |
|-----------|---------|----------------|
| Restart instance | `hcloud RDS StartInstanceRestartAction` | Non-production instance |
| Create manual backup | `hcloud RDS CreateManualBackup` | Instance running |
| Update parameter | `hcloud RDS UpdateInstanceConfiguration` | Non-production instance |
| Set backup policy | `hcloud RDS SetBackupPolicy` | Instance exists |

### Level 4: SDK Fallback Verification

Verify Python SDK produces equivalent results for key operations:

```python
# Verify SDK list_instances matches CLI output
from huaweicloudsdkrds.v3.rds_client import RdsClient
# ... setup client ...
response = client.list_instances(ListInstancesRequest())
assert response.instances is not None
```

## Verification Checklist

- [ ] SKILL.md frontmatter parses correctly
- [ ] All `hcloud RDS` commands are valid (verified against `hcloud RDS --help`)
- [ ] All reference files exist and are readable
- [ ] ListInstances returns valid results
- [ ] ListFlavors returns valid results
- [ ] ListSlowLogs returns valid results (with date range)
- [ ] ListErrorLogs returns valid results (with date range)
- [ ] ListConfigurations returns valid results
- [ ] ListBackups returns valid results
- [ ] ShowBackupPolicy returns valid results
- [ ] Mutating operations prompt for confirmation
- [ ] SDK fallback works for at least 3 key operations
- [ ] Error handling provides actionable messages
- [ ] Region parameter is respected
