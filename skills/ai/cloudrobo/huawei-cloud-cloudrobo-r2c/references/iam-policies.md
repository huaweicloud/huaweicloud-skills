# Authentication & Access Control

> The R2C data plane uses **mTLS (mutual TLS)** authentication via a platform-issued
> credential bundle, not APIG HMAC-SHA256 signing. The platform API (robot registration,
> certificate export) used to produce the bundle does use APIG signing — that is covered by
> the `robot` skill. This document covers the R2C data-plane security model.

## Authentication Model

The R2C data plane has two authentication layers:

| Layer | Method | Used By | Purpose |
|-------|--------|---------|---------|
| Platform API | APIG HMAC-SHA256 signing | `cloudrobo robot` skill | Robot registration, certificate export |
| Data plane | mTLS (credential bundle) | `cloudrobo r2c client` (edge client; the cloud adapter is an SDK module, not a CLI command) | Zenoh pub/sub authentication |

### Platform API (robot skill)

The `robot` skill uses AK/SK credentials to sign REST API requests for robot registration and
certificate export. See the `robot` skill's `iam-policies.md` for details.

```bash
export HUAWEI_CLOUD_AK="your-access-key"
export HUAWEI_CLOUD_SK="your-secret-key"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="your-access-key"
$env:HUAWEI_CLOUD_SK="your-secret-key"
```

### Data Plane (R2C SDK)

The R2C SDK uses the credential bundle (produced by `robot export-certificate`) for mTLS
authentication with the Zenoh router. No AK/SK is needed for data-plane operations.

## Credential Bundle Structure

The credential bundle is a zip file (or unpacked directory) containing:

```text
cert_config_<robot-name>_<timestamp>.zip   # produced by robot export-certificate
├── device_info.json      # Device identity
├── zenoh.json            # Zenoh connection + mTLS config
├── ca.pem                # CA certificate (server verification)
├── server_cert.pem        # Client certificate (mTLS)
├── server_key.pem        # Private key (optionally encrypted)
└── perf.yaml             # (optional) Performance tuning
```

### device_info.json

```json
{
  "account_id": "<account-uuid>",
  "robot_id": "<robot-uuid>",
  "permission_role": "operator"
}
```

### zenoh.json

```json
{
  "mode": "client",
  "connect_endpoints": ["tls/cloudrobo-router.myhuaweicloud.com:7447"],
  "enable_mtls": true,
  "root_ca_certificate": "ca.pem",
  "connect_private_key": "server_key.pem",
  "connect_certificate": "server_cert.pem",
  "verify_name_on_connect": true,
  "close_link_on_expiration": true
}
```

## Least-Privilege Model

### Layer 1: Platform API (Identity)

- Only requests with valid AK/SK signatures can register robots and export certificates
- The AK/SK must correspond to a Huawei Cloud account authorized to access CloudRobo
- Certificate export requires the requesting user to have access to the robot's workspace

### Layer 2: mTLS (Data Plane Access)

- The Zenoh router only accepts connections with valid client certificates signed by the
  platform's CA
- The credential bundle's `server_cert.pem` and `server_key.pem` are bound to a specific `robot_id`
- mTLS ensures only authorized robots can publish observations and subscribe to actions
- The `permission_role` in `device_info.json` controls what operations the client can perform

### Layer 3: Topic Isolation (Resource Scope)

- Zenoh topics are namespaced by `project_id` and `device_id`:
  `{project_id}/{device_id}/{message_path}`
- A robot can only publish/subscribes to topics matching its own `device_id`
- The cloud adapter (SDK module/example) subscribes to a specific device's observations and publishes actions to
  the same device

## Minimal Access for r2c skill

| Capability | Required Credential |
|------------|-------------------|
| Start robot edge client (`r2c client`) | Valid credential bundle (server_cert.pem + server_key.pem + CA) |
| Run a cloud adapter example (SDK module) | Valid credential bundle (same as client) |
| Discover hardware adapter types | None (local `r2c_sdk.adapters` entry-point discovery) |
| Validate robot config | None (local YAML parsing at `r2c client` startup) |

## Security Constraints

- **No hardcoded credentials**: AK/SK must come from environment variables (platform API);
  the credential bundle must come from `robot export-certificate` (data plane)
- **Private key password is sensitive**: Never log or echo the password; use
  `--private-key-password-env` for non-interactive setups
- **Credential bundle is device-bound**: A bundle produced for robot A cannot be used for
  robot B; the `robot_id` in `device_info.json` must match the registered robot
- **Write operations require user confirmation**: Starting `r2c client` is a long-running,
  externally visible operation — confirm parameters before launch
- **mTLS certificate expiry**: Certificates have a validity period; re-export from
  `robot export-certificate` when expired
- **Bundle file permissions**: Store the credential bundle in a secure location with
  restricted file permissions (0o600 for private key)
- **No credential logging**: The R2C SDK logs connection info but never logs private keys or
  passwords

## Environment Variable Reference

| Variable | Purpose |
|----------|---------|
| `HUAWEI_CLOUD_AK` | Access key for platform API (robot skill, not r2c data plane) |
| `HUAWEI_CLOUD_SK` | Secret key for platform API (robot skill, not r2c data plane) |
| `<R2C_KEY_PASSWORD>` | Private key password (name specified via `--private-key-password-env`) |

## Cross-Skill Security Flow

```text
robot skill (AK/SK signing)
  → robot export-certificate --robot-id <id> --password <pwd> --output <dir>
    (writes cert_config_<robot-name>_<timestamp>.zip into <dir>)
    → credential bundle (mTLS certs + Zenoh config)
      → r2c skill (mTLS authentication)
        → cloudrobo r2c client --bundle <path/to/cert_config_*.zip>
```

The r2c skill depends on the robot skill for credential bundle production but does not call
the robot skill directly. The agent orchestrates: first use the robot skill to register and
export, then use the r2c skill to start the data-plane client.
