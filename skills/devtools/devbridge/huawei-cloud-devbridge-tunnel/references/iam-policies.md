# IAM Permission Policies and Authentication

## Overview

DevBridge CLI supports two authentication methods:

1. **Interactive login** (recommended for personal development) — browser-based OAuth flow.
2. **AK/SK authentication** (for automation environments) — Access Key / Secret Key credentials.

## Authentication Methods

### Method 1: Interactive Login (Recommended)

```bash
devbridge auth login
```

This command opens a browser for Huawei Cloud account login. After successful login, credentials are stored locally in `~/.huawei/devbridge/config`.

**Advantages:**
- No need to manually manage AK/SK.
- Automatic support for MFA and SSO.
- Short-lived credentials with automatic refresh.

### Method 2: AK/SK Authentication

```bash
devbridge auth login --access-key <AK> --secret-key <SK>
```

For temporary credentials (STS):

```bash
devbridge auth login --access-key <AK> --secret-key <SK> --security-token <TOKEN>
```

**Use cases:**
- CI/CD pipelines.
- Automation scripts.
- Service accounts.

> **Security note:** Never hardcode AK/SK in scripts, config files, or version control. Use environment variables or a secret manager.

**✅ Correct usage (environment variables):**

```bash
export DEVBRIDGE_AK="your-access-key"
export DEVBRIDGE_SK="your-secret-key"
devbridge auth login --access-key "$DEVBRIDGE_AK" --secret-key "$DEVBRIDGE_SK"
```

**❌ Incorrect usage (hardcoded in script):**

```bash
# Security risk: credentials exposed in source code
devbridge auth login --access-key AKXYZ123 --secret-key SKABC456
```

### Check Authentication Status

```bash
devbridge auth status
```

### Logout

```bash
devbridge auth logout
```

This command clears all locally stored credentials.

## Required Permissions

DevBridge tunnel operations require the following IAM permissions:

### Tunnel Management Permissions

| Operation | Required Permission |
|-----------|-------------------|
| Create tunnel | `devbridge:tunnels:create` |
| List tunnels | `devbridge:tunnels:list` |
| View tunnel details | `devbridge:tunnels:get` |
| Update tunnel | `devbridge:tunnels:update` |
| Delete tunnel | `devbridge:tunnels:delete` |
| Issue tunnel token | `devbridge:tunnels:token` |

### Port Management Permissions

| Operation | Required Permission |
|-----------|-------------------|
| Create port | `devbridge:ports:create` |
| List ports | `devbridge:ports:list` |
| View port details | `devbridge:ports:get` |
| Update port | `devbridge:ports:update` |
| Delete port | `devbridge:ports:delete` |

### Host/Connect Permissions

| Operation | Required Permission |
|-----------|-------------------|
| Host tunnel | `devbridge:tunnels:host` |
| Connect tunnel | `devbridge:tunnels:connect` |

## IAM Policy Examples

### Minimum Development Policy

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "devbridge:tunnels:create",
        "devbridge:tunnels:list",
        "devbridge:tunnels:get",
        "devbridge:tunnels:update",
        "devbridge:tunnels:delete",
        "devbridge:tunnels:token",
        "devbridge:tunnels:host",
        "devbridge:tunnels:connect",
        "devbridge:ports:create",
        "devbridge:ports:list",
        "devbridge:ports:get",
        "devbridge:ports:update",
        "devbridge:ports:delete"
      ],
      "Resource": "*"
    }
  ]
}
```

### Read-Only Policy

For users who only need to view and connect to existing tunnels:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "devbridge:tunnels:list",
        "devbridge:tunnels:get",
        "devbridge:tunnels:connect",
        "devbridge:ports:list",
        "devbridge:ports:get"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security Best Practices

1. **Use interactive login for personal development** — Provides MFA/SSO support and short-lived tokens.
2. **Use temporary AK/SK (STS) for automation** — Temporary credentials auto-expire, reducing risk.
3. **Apply least privilege policies** — Grant only the permissions required for the user's role.
4. **Never share credentials** — Each developer should use their own authentication.
5. **Do not commit `~/.huawei/devbridge/` to version control** — This directory contains auth tokens and tunnel state.
6. **Rotate AK/SK regularly** — If using permanent AK/SK, rotate them periodically.
7. **Logout on shared machines** — Run `devbridge auth logout` after finishing work on shared or public machines.

## Permission Failure Handling

When a DevBridge command fails due to insufficient permissions, follow this procedure:

1. **Identify the required permission** — Check the error message and cross-reference with the permission tables above.
2. **Display the minimum policy** — Show the user the Minimum Development Policy JSON (see above) or a subset matching their use case.
3. **Guide the user to create the policy** — In the Huawei Cloud console, navigate to IAM > Policies > Create Custom Policy, paste the JSON, and attach it to the user or group.
4. **Wait for confirmation** — Pause execution until the user confirms the policy has been granted.
5. **Retry the command** — After confirmation, re-run the failed command.

**✅ Correct handling:**

```text
Error: devbridge:tunnels:create permission denied
→ Display minimum policy JSON to user
→ Guide user to IAM console
→ Wait for user confirmation
→ Retry command
```

**❌ Incorrect handling:**

```text
Error: devbridge:tunnels:create permission denied
→ Immediately fail without guidance
→ User left without knowing what permissions are needed
```
