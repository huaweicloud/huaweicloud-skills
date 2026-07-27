# Verification Method - SWR Image Management Skill

## Overview

This document defines the verification steps for the SWR image management skill. Verification is divided into three levels: installation verification, configuration verification, and functional verification.

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
hcloud SWR ListNamespaces --cli-region=cn-north-4
```

Expected: Returns HTTP 200 and namespace list (may be empty).

## Level 3: Functional Verification

### 3.1 Namespace Management

```bash
# List namespaces (read-only)
hcloud SWR ListNamespaces --cli-region=cn-north-4
```

Expected: Displays list of SWR namespaces.

```bash
# Create a test namespace
hcloud SWR CreateNamespace --namespace=test-verify --cli-region=cn-north-4
```

Expected: Namespace created successfully.

```bash
# Show namespace details
hcloud SWR ShowNamespace --namespace=test-verify --cli-region=cn-north-4
```

Expected: Returns namespace details including name and creator.

```bash
# Clean up: delete test namespace
hcloud SWR DeleteNamespaces --namespace=test-verify --cli-region=cn-north-4
```

Expected: Namespace deleted successfully.

### 3.2 Repository Management

```bash
# Create a test repository
hcloud SWR CreateRepo --namespace=test-verify --repository=test-image --is_public=false --description="Verification test" --cli-region=cn-north-4
```

Expected: Repository created successfully.

```bash
# List repositories
hcloud SWR ListReposDetails --namespace=test-verify --cli-region=cn-north-4
```

Expected: Lists repositories including the test repository.

```bash
# Show repository details
hcloud SWR ShowRepository --namespace=test-verify --repository=test-image --cli-region=cn-north-4
```

Expected: Returns repository details.

```bash
# Update repository
hcloud SWR UpdateRepo --namespace=test-verify --repository=test-image --is_public=true --description="Updated for verification" --cli-region=cn-north-4
```

Expected: Repository updated successfully.

### 3.3 Tag Management (Requires an image pushed to the repository)

Note: Tag operations require an image to be pushed to the repository first using `docker push`.

```bash
# List tags (will be empty for new repo without pushed images)
hcloud SWR ListRepositoryTags --namespace=test-verify --repository=test-image --cli-region=cn-north-4
```

Expected: Returns tag list (may be empty for newly created repository).

### 3.4 Authentication

```bash
# Get temporary login token
hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4
```

Expected: Returns login token and SWR registry host address.

```bash
# Get long-term login secret
hcloud SWR CreateSecret --cli-region=cn-north-4
```

Expected: Returns long-term login credentials.

### 3.5 Quota Check

```bash
hcloud SWR ListQuotas --cli-region=cn-north-4
```

Expected: Returns quota information with limits and current usage.

### 3.6 Clean Up

```bash
# Delete test repository
hcloud SWR DeleteRepo --namespace=test-verify --repository=test-image --cli-region=cn-north-4

# Delete test namespace
hcloud SWR DeleteNamespaces --namespace=test-verify --cli-region=cn-north-4
```

Expected: All test resources cleaned up.

### 3.7 Write Operation Verification

Write operations (Create/Delete/Update) return empty output on success. Always verify by running a query command after the write operation.

```bash
# Create namespace and verify
hcloud SWR CreateNamespace --namespace=test-verify --cli-region=cn-north-4
# Returns: {} (empty - normal)

hcloud SWR ListNamespaces --cli-region=cn-north-4
# Verify: test-verify appears in the list
```

```bash
# Create repository and verify
hcloud SWR CreateRepo --namespace=test-verify --repository=test-image --is_public=false --cli-region=cn-north-4
# Returns: {} (empty - normal)

hcloud SWR ListReposDetails --namespace=test-verify --cli-region=cn-north-4
# Verify: test-image appears in the list
```

```bash
# Update repository and verify
hcloud SWR UpdateRepo --namespace=test-verify --repository=test-image --is_public=true --cli-region=cn-north-4
# Returns: {} (empty - normal)

hcloud SWR ShowRepository --namespace=test-verify --repository=test-image --cli-region=cn-north-4
# Verify: is_public field shows true
```

```bash
# Delete repository and verify
hcloud SWR DeleteRepo --namespace=test-verify --repository=test-image --cli-region=cn-north-4
# Returns: empty (normal)

hcloud SWR ListReposDetails --namespace=test-verify --cli-region=cn-north-4
# Verify: test-image no longer appears in the list
```

**Success Criteria**: Exit code 0 and no stderr error output.

## Verification Checklist

| #  | Check Item                | Command                                             | Status |
| -- | ------------------------- | --------------------------------------------------- | ------ |
| 1  | hcloud version >= 7.2.2   | `hcloud version`                                    | ☐      |
| 2  | Credentials configured    | `hcloud configure list`                             | ☐      |
| 3  | API connectivity          | `hcloud SWR ListNamespaces --cli-region=cn-north-4` | ☐      |
| 4  | List namespaces           | `hcloud SWR ListNamespaces --cli-region=cn-north-4` | ☐      |
| 5  | Create namespace          | `hcloud SWR CreateNamespace --namespace=test-verify --cli-region=cn-north-4` | ☐ |
| 6  | Show namespace            | `hcloud SWR ShowNamespace --namespace=test-verify --cli-region=cn-north-4` | ☐ |
| 7  | Create repository         | `hcloud SWR CreateRepo --namespace=test-verify --repository=test-image --is_public=false --cli-region=cn-north-4` | ☐ |
| 8  | List repositories         | `hcloud SWR ListReposDetails --namespace=test-verify --cli-region=cn-north-4` | ☐ |
| 9  | Update repository         | `hcloud SWR UpdateRepo --namespace=test-verify --repository=test-image --is_public=true --cli-region=cn-north-4` | ☐ |
| 10 | Get login token           | `hcloud SWR CreateAuthorizationToken --cli-region=cn-north-4` | ☐ |
| 11 | Get long-term secret      | `hcloud SWR CreateSecret --cli-region=cn-north-4`   | ☐      |
| 12 | Check quotas              | `hcloud SWR ListQuotas --cli-region=cn-north-4`     | ☐      |
| 13 | Delete repository         | `hcloud SWR DeleteRepo --namespace=test-verify --repository=test-image --cli-region=cn-north-4` | ☐ |
| 14 | Delete namespace          | `hcloud SWR DeleteNamespaces --namespace=test-verify --cli-region=cn-north-4` | ☐ |
## Write Operation Return Values

Write operations in SWR return empty output on success. This is normal hcloud CLI behavior, not an error.

### Return Value Reference

| Operation | Return on Success | Meaning |
| --------- | ----------------- | ------- |
| `CreateNamespace` | `{}` (empty JSON object) | Namespace created successfully |
| `CreateRepo` | `{}` (empty JSON object) | Repository created successfully |
| `UpdateRepo` | `{}` (empty JSON object) | Repository updated successfully |
| `CreateRepoTag` | `{}` (empty JSON object) | Tag created successfully |
| `DeleteNamespaces` | (completely empty) | Namespace deleted successfully |
| `DeleteRepo` | (completely empty) | Repository deleted successfully |
| `DeleteRepoTag` | (completely empty) | Tag deleted successfully |

### Success Criteria

- **Exit code 0** and **no stderr error** → operation succeeded
- **Non-zero exit code** or **stderr contains error** → operation failed

### Post-Write Verification

After executing a write operation, verify the result by running the corresponding query command:

| Write Operation | Verification Command | Expected Result |
| --------------- | -------------------- | --------------- |
| `CreateNamespace --namespace=<ns>` | `hcloud SWR ListNamespaces` | New namespace appears in list |
| `CreateRepo --namespace=<ns> --repository=<repo>` | `hcloud SWR ListReposDetails --namespace=<ns>` | New repository appears in list |
| `UpdateRepo --namespace=<ns> --repository=<repo>` | `hcloud SWR ShowRepository --namespace=<ns> --repository=<repo>` | Updated properties reflected |
| `CreateRepoTag --namespace=<ns> --repository=<repo> --destination_tag=<tag>` | `hcloud SWR ListRepositoryTags --namespace=<ns> --repository=<repo>` | New tag appears in list |
| `DeleteNamespaces --namespace=<ns>` | `hcloud SWR ListNamespaces` | Deleted namespace no longer appears |
| `DeleteRepo --namespace=<ns> --repository=<repo>` | `hcloud SWR ListReposDetails --namespace=<ns>` | Deleted repository no longer appears |
| `DeleteRepoTag --namespace=<ns> --repository=<repo> --tag=<tag>` | `hcloud SWR ListRepositoryTags --namespace=<ns> --repository=<repo>` | Deleted tag no longer appears |

