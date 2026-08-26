# Task: Instance Credentials

## Overview

SWR enterprise instance credentials provide authentication for accessing
the instance registry via Docker CLI or other container tools.
Enterprise instances support both long-term credentials (for CI/CD)
and temporary credentials (for short-lived access).
This task covers creating, listing, enabling/disabling, and deleting credentials.

## Operations Catalog

| Operation                    | Method | Description              | Key Parameters                                  |
| ---------------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `CreateInstanceLtCredential` | POST   | Create long-term credential | `--instance_id`, `--name`                       |
| `CreateInstanceTempCredential` | POST | Get temporary credential  | `--instance_id`                                 |
| `ListInstanceLtCredentials`  | GET    | List long-term credentials | `--instance_id`, `--limit`, `--offset`, `--self_only` |
| `UpdateInstanceLtCredential` | PUT    | Enable/disable long-term credential | `--instance_id`, `--credential_id`, `--enable`  |
| `DeleteInstanceLtCredential` | DELETE | Delete long-term credential | `--instance_id`, `--credential_id`              |

## Workflows

### W1: Create a Long-term Access Credential

Long-term credentials are suitable for CI/CD pipelines, automation tools, and persistent access.

```bash
# Create a long-term credential
hcloud SWR CreateInstanceLtCredential --instance_id=<instance-id> --name=ci-pipeline --cli-region=cn-north-4

# Create credential for automation
hcloud SWR CreateInstanceLtCredential --instance_id=<instance-id> --name=automation-bot --cli-region=cn-north-4

# Create credential for a specific team
hcloud SWR CreateInstanceLtCredential --instance_id=<instance-id> --name=team-backend --cli-region=cn-north-4
```

**Credential Naming Rules**:

- Start with lowercase letter or digit
- Followed by lowercase letters, digits, dots, underscores, or hyphens
- Dots, underscores, hyphens cannot be directly connected
- End with lowercase letter or digit
- Length: 1-64 characters

**Post-creation**:

- Response format needs verification — returns credential information including authentication details
- Store the credential securely; the secret/token is only returned once during creation

⚠️ **Security Warning**: Never expose, log, or share credential secrets. Store them securely in CI/CD secret management tools.

### W2: Create a Temporary Access Credential

Temporary credentials are suitable for short-lived access, developer testing, or one-time operations.

```bash
# Create a temporary credential
hcloud SWR CreateInstanceTempCredential --instance_id=<instance-id> --cli-region=cn-north-4
```

**Use Cases**:

- Developer testing for a limited time
- One-time image push or pull
- Debugging access issues

**Post-creation**:

- Response format needs verification — returns temporary authentication details
- Temporary credentials have limited validity period

### W3: List Long-term Credentials

```bash
# List all long-term credentials (requires te_admin role)
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --cli-region=cn-north-4

# List only self-created credentials
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --self_only=true --cli-region=cn-north-4

# List with pagination
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4
```

**Use Cases**:

- Audit all credentials in the instance
- Verify credential creation was successful
- Check credential enable/disable status
- Review who has access to the instance

⚠️ **Note**: `--self_only=false` (with `te_admin` role) lists ALL credentials. `--self_only=true` lists only the current user's credentials.

### W4: Enable/Disable a Long-term Credential

```bash
# Disable a credential (pause access without deleting)
hcloud SWR UpdateInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --enable=false --cli-region=cn-north-4

# Re-enable a credential
hcloud SWR UpdateInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --enable=true --cli-region=cn-north-4
```

**Common Use Cases**:

- Temporarily disable credentials during security incidents
- Disable credentials for maintenance windows
- Re-enable after incident resolution
- Disable credentials of team members who have left

### W5: Delete a Long-term Credential

```bash
hcloud SWR DeleteInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --cli-region=cn-north-4
```

⚠️ **Warning**: Deleting a credential permanently removes it. Any systems using this credential will immediately lose access.

**Best Practice**: Disable the credential first (`--enable=false`) before deleting to ensure no active connections are disrupted.

```bash
# 1. Disable credential first (recommended)
hcloud SWR UpdateInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --enable=false --cli-region=cn-north-4

# 2. Verify no active connections are affected

# 3. Delete credential
hcloud SWR DeleteInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --cli-region=cn-north-4
```

## Common Scenarios

### S1: CI/CD Pipeline Credential Setup

Set up credentials for a CI/CD pipeline:

```bash
# 1. Create long-term credential for CI/CD
hcloud SWR CreateInstanceLtCredential --instance_id=<instance-id> --name=ci-cd-pipeline --cli-region=cn-north-4

# 2. Store the credential secret securely in CI/CD tool (e.g., Jenkins, GitLab CI secrets)

# 3. Use the credential in docker login:
# docker login -u <username_from_response> -p <password_from_response> <instance-endpoint>

# 4. Push images:
# docker push <instance-endpoint>/namespace/repository:tag
```

### S2: Credential Rotation

Periodically rotate credentials for security:

```bash
# 1. Create a new credential
hcloud SWR CreateInstanceLtCredential --instance_id=<instance-id> --name=ci-cd-v2 --cli-region=cn-north-4

# 2. Update CI/CD pipeline to use the new credential

# 3. Disable the old credential
hcloud SWR UpdateInstanceLtCredential --instance_id=<instance-id> --credential_id=<old-cred-id> --enable=false --cli-region=cn-north-4

# 4. Verify new credential works correctly

# 5. Delete the old credential
hcloud SWR DeleteInstanceLtCredential --instance_id=<instance-id> --credential_id=<old-cred-id> --cli-region=cn-north-4
```

### S3: Credential Audit

Review all credentials and their status:

```bash
# 1. List all credentials
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --cli-region=cn-north-4

# 2. Identify unused or stale credentials

# 3. Disable unused credentials
hcloud SWR UpdateInstanceLtCredential --instance_id=<instance-id> --credential_id=<unused-id> --enable=false --cli-region=cn-north-4

# 4. Delete obsolete credentials
hcloud SWR DeleteInstanceLtCredential --instance_id=<instance-id> --credential_id=<obsolete-id> --cli-region=cn-north-4
```

### S4: Temporary Developer Access

Provide temporary access for a developer to test image operations:

```bash
# 1. Create temporary credential
hcloud SWR CreateInstanceTempCredential --instance_id=<instance-id> --cli-region=cn-north-4

# 2. Share the temporary credentials with the developer (via secure channel)

# 3. Developer uses credentials for docker login and push/pull operations

# 4. Temporary credentials expire automatically after the validity period
```