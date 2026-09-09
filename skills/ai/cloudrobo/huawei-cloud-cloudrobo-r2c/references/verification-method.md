# Verification Method

## Verification Levels

### Level 1: CLI Smoke Test

Verify the R2C CLI is installed and the subcommand is registered:

```bash
# Check r2c subcommand is available
cloudrobo r2c --help

# Check the client subcommand help
cloudrobo r2c client --help
```

> `cloudrobo r2c` exposes a single subcommand, `r2c client`. There is no `r2c list-adapters`
> or `r2c validate-config` command. Built-in hardware adapter types are registered via the
> `r2c_sdk.adapters` entry-point group (see `pyproject.toml`): dummy, a1z, flexiv, jaka,
> lerobot, moz1, playback, q25, q25_ros2, raw_sdk, ros2, tsd, ur5e_rtde, zenoh_ros1.

**Pass criteria**: `cloudrobo r2c --help` exits 0 and shows the `client` subcommand.

### Level 2: Config Validation Test

Robot config YAML is validated automatically at `r2c client` startup by the `RobotConfig`
pydantic schema (`load_yaml` in `cloudroboclient`):

```bash
# A valid config starts normally (validation passes)
cloudrobo r2c client --bundle <bundle> --robot-config config/robot_dummy_config.yaml --duration 2

# An invalid config fails at startup with ValidationError details
echo "not: [a valid: robot: config" > /tmp/bad_config.yaml
cloudrobo r2c client --bundle <bundle> --robot-config /tmp/bad_config.yaml --duration 2
# Expected: "Invalid robot config in <path>:" followed by all schema errors, exit 1
```

**Pass criteria**: Valid configs start; invalid configs report all schema errors and exit 1.

### Level 3: Client Startup Test (Dummy Adapter)

Start the R2C client with the dummy adapter for a timed test:

```bash
# Start client with dummy adapter, run for 10 seconds
cloudrobo r2c client --bundle <path/to/cert_config_*.zip> --robot-config config/robot_dummy_config.yaml --duration 10 --log-level INFO
```

**Pass criteria**: Log output shows:
- "Connecting with platform credential bundle: ..."
- "Heartbeat auto publish started ..."
- "Starting cloudroboclient with robot_config=... duration=10.000s"
- Process exits after 10 seconds with graceful shutdown

### Level 4: Dry-Run Test

Test the R2C client in dry_run mode (observations published, actions logged but not executed):

```bash
# 1. Set dry_run: true in robot config (or use a config that has it set)
# Edit config/robot_dummy_config.yaml: runtime.dry_run: true

# 2. Start client
cloudrobo r2c client --bundle <path/to/cert_config_*.zip> --robot-config config/robot_dummy_config.yaml --duration 30 --log-level DEBUG

# 3. Verify observations are published (check logs)
# 4. If cloud adapter is running, verify actions are received but logged only
```

**Pass criteria**: Observations published to Zenoh; received actions logged with "dry_run" indicator;
no hardware movement.

### Level 5: Cloud Adapter (OpenPI) — out of scope for this skill

The cloud-side OpenPI inference adapter is **not** a `cloudrobo r2c` CLI subcommand. It is
provided as SDK Python modules and examples (`inference/r2c_cloud_adapter.py`,
`examples/*_cloud_adapter.py`) in the `cloudrobo-r2c` package. This skill covers the
robot-side edge client only.

If you need to verify the full observation→action round-trip, run a cloud adapter example
(e.g. `examples/dummy_cloud_adapter.py`) as a Python script while `cloudrobo r2c client`
runs in dry-run mode, then confirm the client logs received actions without executing them.

### Level 6: Observation Recording Test

```bash
# Record observations for 10 seconds
cloudrobo r2c client --bundle <path/to/cert_config_*.zip> --robot-config config/robot_dummy_config.yaml --duration 10 --record ./test_observations.pkl

# Verify recording file
ls -la ./test_observations.pkl
# Expected: non-empty .pkl file
```

**Pass criteria**: `.pkl` file created and non-empty.

### Level 7: Private Key Password Test

```bash
# Test with encrypted private key (should prompt)
cloudrobo r2c client --bundle <encrypted_bundle.zip> --robot-config config/robot_dummy_config.yaml --duration 1
# Expected: prompts "Encrypted private key password:"

# Test with --no-prompt-password (should fail if encrypted)
cloudrobo r2c client --bundle <encrypted_bundle.zip> --robot-config config/robot_dummy_config.yaml --duration 1 --no-prompt-password
# Expected: Error "Encrypted private key detected, but password prompting is disabled."

# Test with env var (placeholder value — set the real password at runtime)
export R2C_KEY_PASSWORD="<your-password>"
cloudrobo r2c client --bundle <encrypted_bundle.zip> --robot-config config/robot_dummy_config.yaml --duration 1 --private-key-password-env R2C_KEY_PASSWORD
# Expected: connects without prompting
```

> **PowerShell:** replace `export R2C_KEY_PASSWORD="<your-password>"` above with `$env:R2C_KEY_PASSWORD="<your-password>"`.

**Pass criteria**: Password handling matches configuration.

## Expected Results Matrix

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| TC-01: client startup (dummy) | `r2c client --bundle <zip> --duration 10` | Heartbeat + connection logs, exits after 10s |
| TC-02: client startup (client-config) | `r2c client --client-config <yaml> --project-id <id> --device-id <id> --duration 10` | Connects via Zenoh |
| TC-03: dry_run mode | `r2c client --bundle <zip> --duration 30` (dry_run config) | Observations published, actions logged only |
| TC-04: invalid config | `r2c client --bundle <zip> --robot-config <bad.yaml>` | ValidationError listing all errors, exit 1 |
| TC-05: observation recording | `r2c client --bundle <zip> --record ./obs.pkl --duration 10` | Non-empty .pkl file |
| TC-06: log file | `r2c client --bundle <zip> --log-file ./r2c.log --duration 5` | Log file created with content |
| TC-07: encrypted key prompt | `r2c client --bundle <encrypted.zip> --duration 1` | Password prompt |
| TC-08: no-prompt-password | `r2c client --bundle <encrypted.zip> --duration 1 --no-prompt-password` | Error, exit 1 |
| TC-09: env var password | `r2c client --bundle <encrypted.zip> --private-key-password-env VAR --duration 1` | Connects without prompt |
| TC-10: missing bundle | `r2c client --robot-config <config> --duration 1` (no bundle, no project-id) | Error "project_id is required" |
| TC-11: custom hardware class | `r2c client --bundle <zip> --hardware-class <pkg.adapter> --duration 10` | Custom adapter loaded, client starts |

> These cases match `templates/test-vars.json`, which contains the authoritative machine-readable
> test case list for this skill.

## Common Verification Failures

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| `r2c: command not found` | cloudrobo-r2c not installed | `pip install hw-cloudrobo-r2c` |
| `ImportError: openpi_client` | openpi-client not installed | `pip install openpi-client` |
| `R2CConnectionError` | Zenoh router unreachable, TLS failure | Check endpoints, certificates, network |
| `CredentialBundleError` | Bundle corrupted or missing files | Re-export from `robot export-certificate` |
| `ValidationError` in config | Missing required fields, wrong types | Fix the YAML; errors are reported at `r2c client` startup |
| Unknown `hardware.type` | Adapter type not registered | Check `pyproject.toml` `r2c_sdk.adapters` entry points; reinstall: `pip install hw-cloudrobo-r2c[client]` |
| Encrypted key prompt fails | `--no-prompt-password` set | Remove flag or provide `--private-key-password-env` |
| No observations published | Hardware adapter not connected | Check `hardware.type` and physical connection |
| Action timeout | Cloud adapter not running or network latency | Increase `action_response_timeout_s` in config |
