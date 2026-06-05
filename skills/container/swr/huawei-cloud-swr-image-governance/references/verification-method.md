# Verification Method - SWR Image Governance Skill

## Overview

This document defines the verification steps for the SWR image governance skill. Verification is divided into three levels: installation verification, configuration verification, and functional verification.

## Level 1: Installation Verification

### 1.1 hcloud CLI Installation

| Item                 | Command           | Success Criteria                          |
| -------------------- | ------------------ | ----------------------------------------- |
| hcloud installed     | `hcloud version`   | Returns version number >= 7.2.2           |

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
hcloud SWR CheckAgency --cli-region=cn-north-4
```

Expected: Returns HTTP 200 and agency status JSON.

## Level 3: Functional Verification

### 3.1 Namespace Permissions

```bash
# Show namespace permissions (requires an existing namespace)
hcloud SWR ShowNamespaceAuth --namespace=<your-namespace> --cli-region=cn-north-4
```

Expected: Returns namespace auth information with `self_auth` and `others_auths`.

```bash
# Grant namespace permission (requires IAM user ID and name)
hcloud SWR CreateNamespaceAuth --namespace=<your-namespace> --1.auth=1 --1.user_id=<user-id> --1.user_name=<user-name> --cli-region=cn-north-4
```

Expected: Permission created successfully.

```bash
# Verify permission was granted
hcloud SWR ShowNamespaceAuth --namespace=<your-namespace> --cli-region=cn-north-4
```

Expected: New user appears in `others_auths` with auth level 1.

```bash
# Clean up: revoke permission
hcloud SWR DeleteNamespaceAuth --namespace=<your-namespace> --1.user_id=<user-id> --1.user_name=<user-name> --cli-region=cn-north-4
```

Expected: Permission revoked successfully.

### 3.2 Repository Permissions

```bash
# Show repository permissions
hcloud SWR ShowUserRepositoryAuth --namespace=<your-namespace> --repository=<your-repo> --cli-region=cn-north-4
```

Expected: Returns repository auth information.

### 3.3 Agency Check

```bash
# Check agency delegation status
hcloud SWR CheckAgency --cli-region=cn-north-4
```

Expected: Returns `is_agency` boolean.

### 3.4 Feature Gates

```bash
# Check sharing feature gates
hcloud SWR ShowShareFeatureGates --cli-region=cn-north-4
```

Expected: Returns feature gate object with boolean values.

```bash
# Check global feature gates
hcloud SWR ListGlobalFeatureGates --cli-region=cn-north-4
```

Expected: Returns global feature gate object.

### 3.5 Shared Domains

```bash
# List shared domains for a repository
hcloud SWR ListRepoDomains --namespace=<your-namespace> --repository=<your-repo> --cli-region=cn-north-4
```

Expected: Returns domain list (may be empty array `[]`).

### 3.6 Retention Rules

```bash
# List retention rules
hcloud SWR ListRetentions --namespace=<your-namespace> --repository=<your-repo> --cli-region=cn-north-4
```

Expected: Returns retention rule list (may be empty array `[]`).

### 3.7 Repository Accessories

```bash
# List accessories
hcloud SWR ListRepoAccessories --namespace=<your-namespace> --repository=<your-repo> --cli-region=cn-north-4
```

Expected: Returns accessories object with `total` and `accessories` fields.

## Verification Checklist

| #  | Check Item                | Command                                             | Status |
| -- | ------------------------- | --------------------------------------------------- | ------ |
| 1  | hcloud version >= 7.2.2   | `hcloud version`                                    | ☐      |
| 2  | Credentials configured    | `hcloud configure list`                             | ☐      |
| 3  | API connectivity          | `hcloud SWR CheckAgency --cli-region=cn-north-4`    | ☐      |
| 4  | Show namespace auth       | `hcloud SWR ShowNamespaceAuth --namespace=<ns> --cli-region=cn-north-4` | ☐ |
| 5  | Create namespace auth     | `hcloud SWR CreateNamespaceAuth --namespace=<ns> --1.auth=1 --1.user_id=<id> --1.user_name=<name> --cli-region=cn-north-4` | ☐ |
| 6  | Show repository auth      | `hcloud SWR ShowUserRepositoryAuth --namespace=<ns> --repository=<repo> --cli-region=cn-north-4` | ☐ |
| 7  | Check agency              | `hcloud SWR CheckAgency --cli-region=cn-north-4`    | ☐      |
| 8  | Show share feature gates  | `hcloud SWR ShowShareFeatureGates --cli-region=cn-north-4` | ☐ |
| 9  | List global feature gates | `hcloud SWR ListGlobalFeatureGates --cli-region=cn-north-4` | ☐ |
| 10 | List shared domains       | `hcloud SWR ListRepoDomains --namespace=<ns> --repository=<repo> --cli-region=cn-north-4` | ☐ |
| 11 | List retention rules      | `hcloud SWR ListRetentions --namespace=<ns> --repository=<repo> --cli-region=cn-north-4` | ☐ |
| 12 | List repo accessories     | `hcloud SWR ListRepoAccessories --namespace=<ns> --repository=<repo> --cli-region=cn-north-4` | ☐ |
| 13 | Delete namespace auth     | `hcloud SWR DeleteNamespaceAuth --namespace=<ns> --1.user_id=<id> --1.user_name=<name> --cli-region=cn-north-4` | ☐ |