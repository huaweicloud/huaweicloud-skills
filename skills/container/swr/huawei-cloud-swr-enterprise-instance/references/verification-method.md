# Verification Method - SWR Enterprise Instance Skill

## Overview

This document defines the verification steps for the SWR enterprise instance skill. Verification is divided into three levels: installation verification, configuration verification, and functional verification.

## Level 1: Installation Verification

### 1.1 hcloud CLI Installation

| Item                 | Command           | Success Criteria                          |
| -------------------- | ------------------ | ----------------------------------------- |
| hcloud installed     | `hcloud version`   | Returns version number >= 7.2.2           |
| Docker installed     | `docker --version` | Returns Docker version (optional for login test) |

### 1.2 hcloud CLI First Run

```bash
# Accept privacy statement (first time only)
printf "y\n" | hcloud version
```

Expected: Version number displayed without error.

## Level 2: Configuration Verification

### 2.1 Credential Configuration

| Item                    | Command                | Success Criteria                        |
| ----------------------- | ---------------------- | --------------------------------------- |
| Credentials configured  | `hcloud configure list` | Shows valid AK/SK configuration (values masked) |

✅ **Correct**: Use `hcloud configure list` to verify
❌ **Incorrect**: Do NOT use `echo $HUAWEI_CLOUD_AK` to check credentials

### 2.2 Connectivity Test

```bash
# Test API connectivity with a read-only operation
hcloud SWR ListInstance --cli-region=cn-north-4
```

Expected: Returns HTTP 200 and instance list (may be empty).

## Level 3: Functional Verification

### 3.1 Instance Management (Read-only)

```bash
# List existing instances (read-only)
hcloud SWR ListInstance --cli-region=cn-north-4
```

Expected: Displays list of enterprise instances (may be empty if none created).

### 3.2 Instance Creation (Requires VPC)

Note: Instance creation requires an existing VPC and subnet. This step may incur costs.

**⚠️ hcloud CLI `CreateInstance` has a known bug** (duplicate `--project_id` parameter). Use the Python SDK script instead:

```bash
# ✅ CORRECT - Create a test instance using Python SDK script
python scripts/swr_instance_helper.py create --name=test-verify --spec=swr.ee.basic \
    --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0

# ❌ BROKEN - hcloud CLI CreateInstance fails with duplicate --project_id error
# hcloud SWR CreateInstance --name=test-verify ...
```

Expected: Instance creation initiated (asynchronous).

```bash
# Wait and check instance status
hcloud SWR ListInstance --status=Running --cli-region=cn-north-4
```

Expected: Instance eventually reaches `Running` status.

```bash
# Show instance details
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: Returns instance details.

### 3.3 Instance Configuration

```bash
# View instance configuration
hcloud SWR ShowInstanceConfiguration --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: Returns configuration including anonymous access setting.

```bash
# Update instance configuration
hcloud SWR UpdateInstanceConfiguration --instance_id=<instance-id> --anonymous_access=false --cli-region=cn-north-4
```

Expected: Configuration updated.

### 3.4 Namespace Management

```bash
# Create a namespace
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=test-verify --metadata.public=false --cli-region=cn-north-4
```

Expected: Namespace created.

```bash
# List namespaces
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: Lists namespaces including test-verify.

```bash
# Show namespace details
hcloud SWR ShowInstanceNamespace --instance_id=<instance-id> --namespace_name=test-verify --cli-region=cn-north-4
```

Expected: Returns namespace details.

```bash
# Update namespace (enable auto-scan)
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=test-verify --metadata.public=false --metadata.auto_scan=true --cli-region=cn-north-4
```

Expected: Namespace updated.

### 3.5 Credential Management

```bash
# Get temporary credential
hcloud SWR CreateInstanceTempCredential --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: Returns temporary login credentials.

```bash
# Create a long-term credential
hcloud SWR CreateInstanceLtCredential --instance_id=<instance-id> --name=test-cred --cli-region=cn-north-4
```

Expected: Returns long-term credential information.

```bash
# List long-term credentials
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: Lists credentials.

### 3.6 Endpoint Management

```bash
# List internal endpoints (may be empty)
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: Returns internal endpoint list.

```bash
# View public access status
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: Returns public access configuration.

### 3.7 Domain Management

```bash
# List domain names
hcloud SWR ListDomainNames --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: Returns domain list (should include default domain).

### 3.8 Statistics and Jobs

```bash
# Get instance statistics
hcloud SWR ListInstanceStatistics --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: Returns statistics data.

```bash
# List jobs
hcloud SWR ListInstanceJobs --cli-region=cn-north-4
```

Expected: Returns job list (should include instance creation job).

### 3.9 Clean Up

```bash
# Delete test namespace
hcloud SWR DeleteInstanceNamespace --instance_id=<instance-id> --namespace_name=test-verify --cli-region=cn-north-4

# Delete long-term credential
hcloud SWR DeleteInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --cli-region=cn-north-4

# Delete test instance (CAUTION: removes all data permanently)
hcloud SWR DeleteInstance --instance_id=<instance-id> --cli-region=cn-north-4
```

Expected: All test resources cleaned up.

## Verification Checklist

| #  | Check Item                | Command                                             | Status |
| -- | ------------------------- | --------------------------------------------------- | ------ |
| 1  | hcloud version >= 7.2.2   | `hcloud version`                                    | ☐      |
| 2  | Credentials configured    | `hcloud configure list`                             | ☐      |
| 3  | API connectivity          | `hcloud SWR ListInstance --cli-region=cn-north-4`   | ☐      |
| 4  | List instances            | `hcloud SWR ListInstance --cli-region=cn-north-4`   | ☐      |
| 5  | Create instance           | `hcloud SWR CreateInstance --name=test-verify --spec=swr.ee.basic --charge_mode=postPaid --vpc_id=<id> --subnet_id=<id> --enterprise_project_id=0 --cli-region=cn-north-4` | ☐ |
| 6  | Show instance             | `hcloud SWR ShowInstance --instance_id=<id> --cli-region=cn-north-4` | ☐ |
| 7  | Show instance config      | `hcloud SWR ShowInstanceConfiguration --instance_id=<id> --cli-region=cn-north-4` | ☐ |
| 8  | Update instance config    | `hcloud SWR UpdateInstanceConfiguration --instance_id=<id> --anonymous_access=false --cli-region=cn-north-4` | ☐ |
| 9  | Create namespace          | `hcloud SWR CreateInstanceNamespace --instance_id=<id> --namespace_name=test-verify --metadata.public=false --cli-region=cn-north-4` | ☐ |
| 10 | List namespaces           | `hcloud SWR ListInstanceNamespaces --instance_id=<id> --cli-region=cn-north-4` | ☐ |
| 11 | Show namespace            | `hcloud SWR ShowInstanceNamespace --instance_id=<id> --namespace_name=test-verify --cli-region=cn-north-4` | ☐ |
| 12 | Update namespace          | `hcloud SWR UpdateInstanceNamespace --instance_id=<id> --namespace_name=test-verify --metadata.public=true --cli-region=cn-north-4` | ☐ |
| 13 | Get temp credential       | `hcloud SWR CreateInstanceTempCredential --instance_id=<id> --cli-region=cn-north-4` | ☐ |
| 14 | Create LT credential      | `hcloud SWR CreateInstanceLtCredential --instance_id=<id> --name=test-cred --cli-region=cn-north-4` | ☐ |
| 15 | List LT credentials       | `hcloud SWR ListInstanceLtCredentials --instance_id=<id> --cli-region=cn-north-4` | ☐ |
| 16 | List internal endpoints   | `hcloud SWR ListInstanceInternalEndpoints --instance_id=<id> --cli-region=cn-north-4` | ☐ |
| 17 | Show endpoint policy      | `hcloud SWR ShowInstanceEndpointPolicy --instance_id=<id> --cli-region=cn-north-4` | ☐ |
| 18 | List domain names         | `hcloud SWR ListDomainNames --instance_id=<id> --cli-region=cn-north-4` | ☐ |
| 19 | Get statistics            | `hcloud SWR ListInstanceStatistics --instance_id=<id> --cli-region=cn-north-4` | ☐ |
| 20 | List jobs                 | `hcloud SWR ListInstanceJobs --cli-region=cn-north-4` | ☐ |
| 21 | Delete namespace          | `hcloud SWR DeleteInstanceNamespace --instance_id=<id> --namespace_name=test-verify --cli-region=cn-north-4` | ☐ |
| 22 | Delete LT credential      | `hcloud SWR DeleteInstanceLtCredential --instance_id=<id> --credential_id=<id> --cli-region=cn-north-4` | ☐ |
| 23 | Delete instance           | `hcloud SWR DeleteInstance --instance_id=<id> --cli-region=cn-north-4` | ☐ |