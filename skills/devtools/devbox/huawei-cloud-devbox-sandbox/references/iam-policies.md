# API Key Authentication and Access Control

The **CLI** and the **SDKs** authenticate against their Manager with an API Key, but differ in how the key is provided and where the Manager lives. Configure both env vars when using both channels.

## CLI Authentication (`devbox`)

```bash
export HW_DEVBOX_API_KEY="devbox_xxx"        # env injection (automation)
devbox auth login --api-key "$HW_DEVBOX_API_KEY"   # validate & store (secure credential storage preferred)
devbox auth login                            # reuse stored key; browser login only if none
devbox auth status                           # login state (+ user name)
devbox auth logout                           # clear stored key and user info
```

- Resolution order: command-line flag > `HW_DEVBOX_API_KEY` env > OS secure credential storage > `~/.huawei/devbox/config.json`.
- API Key validation endpoint: `{AuthCheckDomain}/v1/api-keys/check` (build-time injected).
- **The CLI's Manager address is injected at build time** as the production `https://devbox.developer.myhuaweicloud.com` (same as the SDK default). Not configurable at runtime.

## SDK Authentication (JS / Python)

SDKs authenticate against the **Manager (control plane)** with an API Key. Configuration is pure environment/parameters:

| Setting | Env var (primary) | Env var (fallback) | Parameter |
|---------|-------------------|--------------------|-----------|
| API Key | `DEVBOX_API_KEY` | `E2B_API_KEY` | Python `api_key=` / JS `apiKey` |
| Manager URL | `DEVBOX_API_URL` | `E2B_API_URL` | Python `api_url=` / JS `apiUrl` |
| Gateway URL override | `DEVBOX_GATEWAY_URL` | — | Python `gateway_url=` / JS `gatewayUrl` |
| Gateway TLS skip (debug) | `DEVBOX_GATEWAY_SKIP_TLS_VERIFY` | — | — |

Defaults: Manager URL `https://devbox.developer.myhuaweicloud.com`; Gateway URL is returned per sandbox by the Manager.

Precedence: explicit parameters > `DEVBOX_*` env vars > `E2B_*` env vars > defaults.

## How Authentication Works

1. **API Key → Manager**: sent as the `X-API-Key` header on every control-plane request (sandbox CRUD, templates, lifecycle) — CLI and SDKs alike.
2. **connectToken → Gateway**: the Manager issues a per-sandbox `connectToken` (`tokenExpiration` = Unix seconds); the data-plane request carries it as `Cookie: relay_token=<connectToken>`.
3. **Silent renewal** (SDKs): before the token expires (5-minute window) the SDK re-requests connection info from the Manager and swaps the cookie. This does **not** extend sandbox lifetime.
4. The SDK never persists credentials, never logs them, and never forwards them on HTTP redirects. The CLI stores the key in the OS secure credential storage when available (fallback: local config file).
5. Manager returns no valid `connectToken` → the SDK refuses data-plane requests (`ProtocolError`).

## Configuring Credentials

```bash
# Linux / macOS — both channels
export HW_DEVBOX_API_KEY="devbox_xxx"    # CLI
export DEVBOX_API_KEY="devbox_xxx"       # SDKs
```

```python
# Python — per-call override (takes precedence over env)
from devbox import Sandbox
sandbox = Sandbox.create("default", api_key="devbox_xxx")
```

```js
// JS — per-client override
import { DevBox } from "devbox-js-sdk";
const client = new DevBox({ apiKey: "devbox_xxx" });
```

Windows CMD:

```bat
set "HW_DEVBOX_API_KEY=devbox_xxx"
set "DEVBOX_API_KEY=devbox_xxx"
```

```python
# Python — per-call override (takes precedence over env)
from devbox import Sandbox
sandbox = Sandbox.create("default", api_key="devbox_xxx")
```

> **Security note**: never write a real API Key into source code, scripts, notebooks, or CI pipeline definitions. Inject it through a protected environment variable or a secret service.

## Get an API Key

API Keys are issued by the DevBox management plane for the DevBox usage scenario. Keep in mind:

- The full key value is typically shown **only once at creation time**.
- Deleting a key invalidates it immediately.
- Quotas (sandbox count, concurrency) are enforced per account; quota may be shared across the account even if individual sandboxes are not visible in one client's `list()`.

## Required Permissions

DevBox uses its own API Key/account model rather than Huawei Cloud IAM resource policies. When requests fail with auth errors, the fix is always on the credential side:

| Symptom (exception) | HTTP | Likely Cause | Fix |
|---------------------|------|--------------|-----|
| `AuthenticationError` | 401 | Missing/invalid API Key | Set `DEVBOX_API_KEY`; verify value |
| `PermissionDeniedError` | 403 | Key revoked, or out of allowed scope | Re-issue an API Key for the DevBox scenario |
| `ConfigurationError` | — | No API Key configured at all | Set env var or pass parameter |
| `RateLimitError` | 429 | Quota exhausted (too many running sandboxes) | Honor `retry_after`; delete unused sandboxes; check `X-Total-Running` via `list()` |

## Auth Failure Handling Procedure

When any SDK call fails due to invalid or missing credentials:

1. **Check the environment** — confirm `DEVBOX_API_KEY` (or `E2B_API_KEY`) is set in the running process.
2. **Identify the key** — if a key is in use, verify it still exists and was not deleted; full values are shown only at creation.
3. **Re-issue and re-inject** — create a new API Key at the DevBox management page, inject via `DEVBOX_API_KEY`.
4. **Wait for confirmation** — pause execution until the user confirms credentials have been updated.
5. **Retry** — re-run the failed operation.

**✅ Correct handling:**

```text
devbox.AuthenticationError: request failed with status 401
→ echo ${DEVBOX_API_KEY:+set}        (confirm whether the env var is set at all)
→ Guide user to re-issue an API Key at the DevBox management page
→ Wait for user confirmation that DEVBOX_API_KEY has been updated
→ Retry Sandbox.create(...)
```

**❌ Incorrect handling:**

```text
devbox.AuthenticationError: request failed with status 401
→ Retry Sandbox.create(...) immediately (fails again)
→ Set DEVBOX_GATEWAY_SKIP_TLS_VERIFY=true (does not fix auth; disables TLS instead)
```

## Quota and Limits

- Sandbox lifetime: 10 s – 86400 s (default 300 s).
- Paused sandbox retention: 24 h.
- `list()` page size: 1–100 (`nextToken` pagination, `X-Total-Running` header for running count).
- Rate limits surface as `RateLimitError` with `retry_after` — back off; the SDK does not retry them.

Inspect current usage:

```python
from devbox import DevBox
with DevBox() as client:
    page = client.sandboxes.list(states=["running"])
    print("running:", page.total)
    for info in client.sandboxes.list().items:
        print(info.sandbox_id, info.state, info.metadata)
```

## Security Best Practices

1. **Never hardcode API Keys** — env vars or secret services only.
2. **Never commit keys** to repositories, notebooks, or logs; SDK errors include `request_id`, not credentials.
3. **Treat Git credentials the same** — pass `GitCredentials` from a token env var; the SDK injects them as process env vars inside the sandbox and never writes them to `.git/config`.
4. **`DEVBOX_GATEWAY_SKIP_TLS_VERIFY=true` is debug-only** — it disables Gateway certificate verification and exposes the connect token and sandbox data to interception. It never fixes auth or DNS problems. Remove it after debugging.
5. **Sandbox data is disposable** — do not treat sandbox storage as a secret store; a deleted sandbox is unrecoverable.
6. **Suspected leak?** Re-issue the API Key immediately (old key becomes invalid) and rotate any Git tokens that were used inside sandboxes.
