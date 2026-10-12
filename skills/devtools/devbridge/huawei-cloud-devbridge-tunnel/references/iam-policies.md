# API Key Authentication and Access Control

## Overview

DevBridge CLI v0.2.x supports two authentication methods:

1. **Interactive login** (recommended for personal development) — browser-based OAuth flow, credentials managed via the OS secure storage (falls back to a config file).
2. **API Key authentication** (for automation environments) — fixed service account or automated task login.

> **v0.2.x change**: AK/SK authentication (`--access-key`, `--secret-key`, `--security-token`) has been **removed**. Use API Key or interactive login.

## Authentication Methods

### Method 1: Interactive Login (Recommended for personal use)

```bash
devbridge auth login
```

The CLI opens a browser to complete identity authentication and saves the login credential to the local protected storage. Credential storage prefers the OS secure storage, falling back to a config file when unavailable.

### Method 2: API Key (Recommended for automation)

```bash
devbridge auth login --api-key "$HW_API_KEY"
```

Or inject via environment variable — the CLI reads it automatically:

```bash
export HW_API_KEY="<your-api-key>"
devbridge auth login
```

> **Security note**: Never write a real API Key directly into commands, scripts, or pipeline definitions. Inject it through a protected environment variable or secret service.

### Get an API Key

Create and manage API Keys at the DevBridge management page:

```
https://devstation.connect.huaweicloud.com/space/devbridge/apikey
```

- API Keys are distinguished by usage scenario (DevBridge / DevBox); **up to 20 API Keys per scenario**.
- The **full API Key value is shown only once at creation time**; the list shows a masked value and last usage time.
- Deleting an API Key invalidates it immediately.

### Check Authentication Status

```bash
devbridge auth status
```

The status command confirms the current identity and credential validity; it must not output the full API Key.

### Logout

```bash
devbridge auth logout
```

Logging out clears CLI-saved credentials but does not delete created tunnels. Do not delete the config directory manually as a substitute for a normal logout (unless the CLI is unusable and you confirm local state is not needed).

## Using API Key with Host / Connect

`host` and `connect` support `--api-key` / `-k` to authenticate directly via API Key, skipping TunnelToken issuance:

```bash
devbridge host <tunnelId> --api-key <key>
devbridge connect <tunnelId> --api-key <key>
```

Explicit JWT token mode (for integrating other clients, skips API calls):

```bash
devbridge host <tunnelId> --token <jwt>
devbridge connect <tunnelId> --token <jwt>
```

`--token` mode skips token issuance and port lookup; ports are delivered by the gateway over the relay channel. The tunnel ID must be explicitly specified. Host tokens cannot be used for Connect, and Connect tokens cannot be used for Host.

## Quota and Limits

```bash
devbridge limits
```

Shows account quota and current usage: reset time, traffic quota and used traffic, active tunnel count, tunnel/port/Host count limits, tunnel bandwidth limit, single-port HTTP request rate limit, single-port connection count limit.

## Required Permissions

DevBridge uses its own account/scenario model rather than Huawei Cloud IAM resource permissions. In failure scenarios, the error message points to the API Key management page — delete and re-create the key, then retry. Typical cases:

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `401 Unauthorized` / `token not found` | Invalid or missing API Key | `devbridge auth login --api-key "$HW_API_KEY"` with a valid key |
| `403 Forbidden` | API Key deleted, expired, or insufficient for the scenario | Re-create an API Key (DevBridge scenario) at the management page |
| Repeated login failures | Key revoked | Delete the old key at the management page and re-create |
| Quota exceeded | Account at limits | `devbridge limits` to inspect; delete unused tunnels/resources |

## Auth Failure Handling Procedure

When any DevBridge command fails due to invalid or missing credentials:

1. **Check status** — `devbridge auth status`; confirm whether the CLI is logged in.
2. **Identify the API Key** — if an API Key is in use, verify it still exists and is not deleted; the full value was shown only at creation time.
3. **Re-create or re-inject** — create a new API Key at `https://devstation.connect.huaweicloud.com/space/devbridge/apikey`, inject via `HW_API_KEY`, and re-login.
4. **Wait for confirmation** — pause execution until the user confirms credentials have been updated.
5. **Retry the command** — after confirmation, re-run the failed command.

**✅ Correct handling:**

```text
Error: authentication failed
→ devbridge auth status
→ Guide user to API Key management page (devstation.connect.huaweicloud.com/space/devbridge/apikey)
→ Wait for user confirmation that a new API Key is injected
→ Retry command
```

**❌ Incorrect handling:**

```text
Error: authentication failed
→ Immediately fail without guidance
→ User left without knowing how to fix credentials
```

## Security Best Practices

1. **Use interactive login for personal development** — no manual credential management.
2. **Use API Key for automation** — inject through environment variables, never hardcoded.
3. **Never share credentials** — API Key full values are shown once; treat them as secrets.
4. **Do not commit `~/.huawei/devbridge/` to version control** — contains auth tokens and tunnel state.
5. **Do not pass API Key via chat, logs, or tickets**.
6. **Suspect credential leak?** Immediately log out, revoke, and re-issue.
7. **Host/Connect tokens are short-lived** — only for the corresponding tunnel and direction; don't treat them as long-term identity.