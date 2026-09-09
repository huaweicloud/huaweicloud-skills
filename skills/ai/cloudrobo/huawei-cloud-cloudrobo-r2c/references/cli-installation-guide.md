# CLI Installation Guide

## Install cloudrobo CLI

### Option 1: Install all packages (recommended)

```bash
pip install hw-cloudrobo-client
```

This installs the aggregate package with all functional modules (asset, dataset, train, eval,
infer, robot, dispatch, workspace) plus the R2C data-plane SDK.

### Option 2: Install only R2C package

```bash
pip install hw-cloudrobo-r2c
```

This installs `cloudrobo-core` (CLI framework) + `cloudrobo-r2c` (R2C data-plane SDK).

### Option 3: Install with extras

```bash
# R2C client with Zenoh transport, Protobuf, and media processing
pip install hw-cloudrobo-r2c[client]

# Cloud adapter with Zenoh transport and Protobuf
pip install hw-cloudrobo-r2c[cloud-adapter]

# UR5e robot support (ur-rtde, pyserial, pyrealsense2)
pip install hw-cloudrobo-r2c[ur5e]

# Flexiv robot support (flexivrdk, Linux x86_64 only)
pip install hw-cloudrobo-r2c[flexiv]

# Jaka robot support (scipy)
pip install hw-cloudrobo-r2c[jaka]

# A1Z robot support (python-can, pin)
pip install hw-cloudrobo-r2c[a1z]

# All extras
pip install hw-cloudrobo-r2c[all]
```

### Option 4: Development install (editable)

```bash
git clone <cloudrobo-client-repo>
cd cloudrobo-client/packages/cloudrobo-r2c
pip install -e ".[client,cloud-adapter]"
```

## Verify Installation

```bash
# Check CLI is available
cloudrobo --help

# Check r2c subcommand is registered
cloudrobo r2c --help
```

> **Note:** `cloudrobo r2c` today exposes a single subcommand, `r2c client`. There is no
> `r2c list-adapters`, `r2c validate-config`, or `r2c cloud-adapter` CLI subcommand.
> Built-in hardware adapter types are registered via the `r2c_sdk.adapters` entry-point group
> (see `pyproject.toml`); the cloud adapter is provided as a Python module/example, not a CLI
> command. Robot config YAML is validated automatically at `r2c client` startup.

## Credential Bundle Preparation

The R2C client and cloud adapter require a **credential bundle** for mTLS authentication.
The bundle is produced by the `robot` skill:

```bash
# 1. Register the robot (if not already registered)
cloudrobo robot create --name <robot-name> --type HUMANOID --manufacturer <mfg> --robot-model <model> --workspace-id <workspace-id>

# 2. Export the credential bundle
#    --output is a DIRECTORY (not a zip path); the command writes
#    cert_config_<robot-name>_<timestamp>.zip into it
cloudrobo robot export-certificate --robot-id <robot-id> --password <encryption-password> --output ./
```

The credential bundle contains:

| File | Description |
|------|-------------|
| `device_info.json` | Device identity: `account_id`, `robot_id`, `permission_role` |
| `zenoh.json` | Zenoh connection config: `mode`, `connect_endpoints`, mTLS settings |
| `ca.pem` | CA certificate for server verification |
| `server_cert.pem` | Client certificate for mTLS (named `server_cert.pem` in the exported bundle) |
| `server_key.pem` | Private key (optionally encrypted with password) |
| `perf.yaml` | (optional) Performance/tuning parameters |

> Pass the exported access-config **zip directly** to `--bundle` (the SDK resolves the cert paths
> inside `zenoh.json`, including its `certs/`-style layout). Do not rename or relocate the cert files.

### Private Key Password

If `server_key.pem` is encrypted, the client will prompt for a password at startup. Use one
of these options to provide it non-interactively:

```bash
# Option 1: Environment variable name
cloudrobo r2c client --bundle ./cert.zip --private-key-password-env R2C_KEY_PASSWORD

# Option 2: Direct password (avoid on shared shells)
cloudrobo r2c client --bundle ./cert.zip --private-key-password <password>

# Option 3: Disable prompting (fail if encrypted)
cloudrobo r2c client --bundle ./cert.zip --no-prompt-password
```

## Authentication Configuration

### Platform API (AK/SK)

The `cloudrobo robot` skill uses AK/SK for platform REST API calls (robot registration,
certificate export). Set these environment variables:

```bash
export HUAWEI_CLOUD_AK="your-access-key"
export HUAWEI_CLOUD_SK="your-secret-key"
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK="your-access-key"
$env:HUAWEI_CLOUD_SK="your-secret-key"
```

### Data Plane (mTLS credential bundle)

The `cloudrobo r2c` commands use the credential bundle for Zenoh mTLS authentication. No
AK/SK is needed for the data plane — the bundle contains all necessary certificates and keys.

## Configuration Precedence

Connection configuration is resolved in this order:

```text
--bundle (credential bundle, recommended)
  > --client-config (client_config.yaml)
    > explicit CLI parameters (--project-id, --device-id, --endpoints, --mode)
```

When using `--bundle`, all connection parameters (project_id, device_id, endpoints, mTLS
certificates) are extracted from the bundle. When using `--client-config`, parameters come
from the YAML file, with CLI options overriding. When using neither, explicit CLI parameters
are required (`--project-id` and `--device-id` are mandatory).

## r2c Subcommand

`cloudrobo r2c` currently exposes a single subcommand:

| Subcommand | Purpose |
|------------|---------|
| `cloudrobo r2c client` | Start the robot edge client (long-running) |

The cloud adapter is available as a Python module/examples (`inference/r2c_cloud_adapter.py`,
`examples/*_cloud_adapter.py`) in the `cloudrobo-r2c` package rather than as a `cloudrobo r2c`
CLI subcommand. Use `cloudrobo r2c client --help` for all client options.

## Robot Config Files

Robot config YAML files define the hardware adapter, translator, and field mappings. Built-in
configs are in `config/`:

| Config File | Adapter | Description |
|-------------|---------|-------------|
| `robot_dummy_config.yaml` | dummy | Simulated 6-DOF robot for testing |
| `robot_ur5e_config.yaml` | ur5e_rtde | Universal Robots UR5e |
| `robot_jaka_sdk_config.yaml` | jaka | Jaka arm via SDK |
| `robot_flexiv_config.yaml` | flexiv | Flexiv arm |
| `robot_so101_lerobot_config.yaml` | lerobot | SO-101 via LeRobot |
| `robot_q25_config.yaml` | q25 | Q25 robot direct SDK |
| `robot_moz1_config.yaml` | moz1 | MOZ1 robot |
| `robot_tsd_config.yaml` | tsd | TSD robot |
| `robot_playback_config.yaml` | playback | Replay recorded observations |
| `robot_a1z_config.yaml` | a1z | A1Z + G1Z gripper |
| ... | ... | See `config/` and its subdirectories for the full set of configs |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `cloudrobo: command not found` | Ensure `cloudrobo-core` is installed; check PATH |
| `r2c subcommand missing` | Ensure `cloudrobo-r2c` is installed; run `cloudrobo --help` |
| `ImportError: openpi_client` | Install with `pip install hw-cloudrobo-r2c[cloud-adapter]` and `pip install openpi-client` |
| `R2CConnectionError` | Check Zenoh endpoints, TLS certificates, and network connectivity |
| `CredentialBundleError` | Verify bundle zip is not corrupted; re-export from `cloudrobo robot export-certificate` |
| `ValidationError` in robot config | Startup fails with the `ValidationError` message listing all schema errors; fix the YAML and re-run `cloudrobo r2c client` |
| Encrypted key prompt fails | Provide `--private-key-password` or `--private-key-password-env`, or remove `--no-prompt-password` |
| `ModuleNotFoundError` for adapter | Install the appropriate extra: `[ur5e]`, `[flexiv]`, `[jaka]` |
| Zenoh connection timeout | Check router is running; verify `--endpoints` format (`tls/host:port`) |
| No observations published | Check `hardware.type` in robot config matches available adapter; verify hardware is connected |
