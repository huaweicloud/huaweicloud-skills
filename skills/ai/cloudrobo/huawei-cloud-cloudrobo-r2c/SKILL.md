---
name: huawei-cloud-cloudrobo-r2c
description: >
  Run the R2C (Robot-to-Cloud) data-plane client — start the robot-side edge client
  (Zenoh pub/sub with mTLS credential bundle, hardware adapter, translator, control loop).
  The credential bundle is produced by the robot skill's export-certificate command.
  This skill does NOT cover robot registration or certificate export (use the robot skill).
  Triggers include: r2c client, robot edge client, Zenoh, mTLS, credential bundle,
  hardware adapter, robot config, dry_run, observation recording, custom adapter,
  robot-to-cloud, R2C客户端, 硬件适配器, 机器人配置, 凭证包.
tags:
  - huawei-cloud-cloudrobo
  - r2c
  - data-plane
  - zenoh
  - mtls
  - credential-bundle
  - hardware-adapter
  - robot-config
  - edge-client
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

## Overview 概述

The `cloudrobo-r2c` skill operates the R2C (Robot-to-Cloud) data-plane SDK. Unlike other
cloudrobo skills that call REST APIs via `cloudrobo-service`, this skill runs **long-lived
data-plane processes** that use Zenoh pub/sub with Protobuf serialization and mTLS
authentication. It covers one CLI command: `r2c client` (robot edge client).

**Applicable scenarios:**

- **Robot edge client** — Start the robot-side process that bridges physical hardware to the
  cloud via Zenoh. Reads sensor observations from a hardware adapter, translates to R2C
  Protobuf messages, publishes to Zenoh, subscribes to cloud actions, translates back, and
  executes on hardware.
- **Custom adapter development** — Guide developers through implementing custom
  `IRobotHardwareAdapter` classes and `ConfigurableDeviceTranslator` mappings for robots
  not in the built-in adapter list.

**Architecture:**

```text
                          Zenoh pub/sub (mTLS)
  ┌─────────────┐  observations  ┌──────────────────┐
  │ Robot Edge  │ ─────────────► │                  │
  │ Client      │                │  Zenoh Router    │
  │ (r2c client)│ ◄───────────── │                  │
  └──────┬──────┘     actions    └──────────────────┘
         │
  ┌──────▼──────┐
  │ Hardware     │
  │ Adapter      │
  │ (robot arm,  │
  │  gripper...) │
  └─────────────┘

  Credential Bundle (from robot skill export-certificate)
  ├── device_info.json   (account_id, robot_id, permission_role)
  ├── zenoh.json         (mode, endpoints, mTLS config)
  ├── ca.pem             (CA certificate)
  ├── server_cert.pem    (client certificate — note: named server_cert.pem in the exported bundle)
  └── server_key.pem     (private key, optionally encrypted)
```
> `--bundle` accepts the access-config **zip directly** (or an extracted directory); the SDK resolves
> the certificate paths inside `zenoh.json` (which references a `certs/`-style layout) automatically.
> Do not manually rename the cert files.

The R2C data plane is decoupled from the CloudRobo REST API. The platform's `cloudrobo-service`
handles robot registration and certificate export (covered by the `robot` skill); the R2C
SDK consumes the exported credential bundle to establish mTLS-authenticated Zenoh sessions.

## Prerequisites 前置条件

- See `references/cli-installation-guide.md` for CLI installation, R2C package extras, and
  credential bundle preparation.
- A valid **credential bundle** — produced by `cloudrobo robot export-certificate` (robot skill).
  The bundle contains `device_info.json`, `zenoh.json`, `ca.pem`, `server_cert.pem`, and
  `server_key.pem`.
- A **robot config YAML** — defines the hardware adapter, translator, and device-to-R2C
  field mappings.
- The robot must be **registered** on the CloudRobo platform (use the `robot` skill: create →
  export-certificate). The `robot_id` in the credential bundle identifies the robot.

## Workflow 工作流

### Robot Edge Client Startup Workflow 机器人边缘客户端启动

Scenario: "Start the R2C client on the robot to stream observations and execute cloud actions."

1. **Start the client** — Launch the edge client with the credential bundle and robot config.
   `export-certificate` writes `cert_config_<robot-name>_<timestamp>.zip` into the output
   **directory** — pass that zip path to `--bundle`:
   ```bash
   cloudrobo r2c client --bundle <path/to/cert_config_*.zip> --robot-config config/robot_dummy_config.yaml
   ```
   If the private key is encrypted, you will be prompted for a password (or use
   `--private-key-password` / `--private-key-password-env`).
2. **Verify connection** — Check log output for "Heartbeat auto publish started" and
   "Starting cloudroboclient" messages. The client publishes observations and subscribes to
   actions in a control loop.
3. **Stop** — Press Ctrl+C for graceful shutdown (hardware disconnect → session close).

### Dry-Run Testing Workflow 干运行测试

Scenario: "Test the R2C client without moving the real robot."

1. **Set dry_run** — In the robot config YAML, set `runtime.dry_run: true`. This publishes
   real observations but does not execute received actions (logs only).
2. **Start client** — Launch with the dummy adapter or real hardware:
   ```bash
   cloudrobo r2c client --bundle <bundle> --robot-config config/robot_dummy_config.yaml
   ```
3. **Verify observation publishing** — Check logs for observation publish events. On the
   cloud side, verify observations are received.
4. **Test action receiving** — From the cloud adapter or a test publisher, send a test action.
   Verify the action is logged but not executed (dry_run mode).
5. **Disable dry_run** — Set `runtime.dry_run: false` and restart for real execution.

### Custom Adapter Development Workflow 自定义适配器开发

Scenario: "My robot is not in the built-in adapter list. How do I add support?"

The R2C SDK provides two approaches for custom adapters: **entry_point registration**
(recommended for reusable, shareable adapters) and **CLI override** (for quick prototyping).

**Approach A: Entry-Point Registration (Recommended) 入口点注册（推荐）**

1. **Review the guide** — See `references/custom-adapter-guide.md` for the full development guide.
2. **Implement adapter class** — Create a class implementing `IRobotHardwareAdapter`
   (`connect()`, `disconnect()`, `get_observation()`, `send_action()`).
3. **Implement factory function** — Create a factory function that returns an adapter instance:
   `def create_my_adapter(config, **kwargs) -> IRobotHardwareAdapter`.
4. **Register via entry_point** — In your package's `pyproject.toml`, register under
   `[project.entry-points."r2c_sdk.adapters"]`: `my_robot = "my_adapter_module:create_my_adapter"`.
5. **Install package** — `pip install .` registers the adapter under the
   `r2c_sdk.adapters` entry-point group, making it discoverable by the SDK's
   `AdapterRegistry` (used by `RobotFactory` and robot-config schema validation).
6. **Configure** — Set `hardware.type: "my_robot"` (matching the entry_point name) in the
   robot config YAML. No `--hardware-class` CLI override needed.
7. **Optionally register commands** — Use `register_command_class()` in `__post_init__` for
   custom commands (e.g., `go_home`), then reference them in `hardware.config.commands` in
   the robot config.
8. **Configure translator** — Use `ConfigurableDeviceTranslator` with `device_to_r2c` and
   `r2c_to_device` mapping sections in the robot config YAML.
9. **Test with dry_run** — Validate config → start client with `dry_run: true` → verify
   observation publishing and action logging.
10. **Test real execution** — Disable dry_run and verify the robot moves correctly.

**Approach B: CLI Override (Quick Prototyping) CLI 覆盖（快速原型）**

1. **Implement adapter class** — Same as above, but no entry_point registration needed.
2. **Configure** — Set `hardware.type: "custom"` and `hardware.class_path` to the dotted
   import path of your adapter class in the robot config YAML. Alternatively, use
   `--hardware-class my_pkg.my_module.MyAdapter` on the CLI.
3. **Test with dry_run** — Validate config → start client with `dry_run: true` → verify
   observation publishing and action logging.
4. **Test real execution** — Disable dry_run and verify the robot moves correctly.

> **When to use which:** Use entry_point registration when the adapter will be reused across
> projects or shared with other teams. Use CLI override for one-off testing or when you
> cannot create a separate package.

### Observation Recording Workflow 观测录制

Scenario: "Record observations for later playback analysis."

1. **Start with --record** — `cloudrobo r2c client --bundle <bundle> --robot-config <config> --record ./observations.pkl`
2. **Operate** — Run the robot normally; observations are serialized to the `.pkl` file.
3. **Playback** — Use the `playback` adapter type with the recorded file for replay.

## CLI Command Format Standard CLI命令格式标准

```bash
cloudrobo r2c client [OPTIONS]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Command group | `r2c` (registered via entry point) | `cloudrobo r2c` |
| Subcommand | `client` | `cloudrobo r2c client` |
| Credential bundle | `--bundle <path>` (zip or directory, recommended) | `--bundle ./cert.zip` |
| Client config | `--client-config <path>` (default `config/client_config.yaml`) | alternative to `--bundle` |
| Robot config | `--robot-config <path>` (default `config/robot_dummy_config.yaml`) | `--robot-config config/robot_jaka_sdk_config.yaml` |
| Endpoints | `--endpoints tls/127.0.0.1:7447` (comma-separated) | Zenoh router address |
| Output format | Log output to stdout/stderr | structured logging |
| Long-running | Runs until Ctrl+C or `--duration` | `--duration 60` |

## Core Commands 核心命令

### Start Robot Edge Client

```bash
cloudrobo r2c client --bundle <path/to/cert_config_*.zip> --robot-config config/robot_dummy_config.yaml [--client-config config/client_config.yaml] [--duration 0] [--log-level INFO] [--log-file ./r2c.log] [--record ./observations.pkl] [--hardware-class my_pkg.my_module.MyAdapter] [--translator-class my_pkg.my_module.MyTranslator] [--private-key-password <password>] [--private-key-password-env <ENV_VAR>] [--no-prompt-password]
```

Alternative (without bundle, using client config + explicit parameters):

```bash
cloudrobo r2c client --client-config config/client_config.yaml --project-id <project-id> --device-id <device-id> --endpoints tls/127.0.0.1:7447 --mode peer --robot-config config/robot_dummy_config.yaml
```

**Connection priority:** `--bundle` (recommended) > `--client-config` > explicit CLI params
(requires `--project-id` and `--device-id`).

**Lifecycle:** `load_yaml(robot_config)` → `build_session(args)` →
`_maybe_start_heartbeats(session, robot_config)` → `build_sync_robot_client(...)` →
`hardware_adapter.connect()` → `robot_client.start()` → wait (duration or Ctrl+C) →
`robot_client.stop()` → `hardware_adapter.disconnect()` → `session.close()`.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--bundle` | None | Path to credential bundle zip/dir (recommended; supersedes client-config) |
| `--client-config` | `config/client_config.yaml` | Path to R2C client config YAML |
| `--project-id` | None | Project ID (required if no bundle and no client-config) |
| `--device-id` | None | Device ID (required if no bundle and no client-config) |
| `--client-id` | None | Client ID (defaults to `sync-robot-client`) |
| `--endpoints` | `""` | Comma-separated Zenoh endpoints, e.g. `tls/127.0.0.1:7447` |
| `--mode` | `peer` | Zenoh mode: `peer` or `client` |
| `--endpoint-role` | None | `connect` (active, default) or `listen` (passive) |
| `--robot-config` | `config/robot_dummy_config.yaml` | Path to robot config YAML |
| `--hardware-class` | None | Dotted class path for custom IRobotHardwareAdapter |
| `--translator-class` | None | Dotted class path for custom IDeviceTranslator |
| `--duration` | `0.0` | Run duration in seconds; 0 = run forever |
| `--log-level` | `INFO` | Logging level: CRITICAL/ERROR/WARNING/INFO/DEBUG/NOTSET |
| `--log-file` | None | Rotating log file path (100 MB max, 5 backups) |
| `--record` | None | Path to save recorded observations (.pkl) |
| `--private-key-password` | None | Password for encrypted server_key.pem |
| `--private-key-password-env` | None | Environment variable name holding the password |
| `--prompt-password` | True (default) | Prompt for password only when encrypted key detected |
| `--no-prompt-password` | False | Never prompt; fail if password required |

### Built-in Hardware Adapters

The following hardware adapter types are registered via `r2c_sdk.adapters` entry points
and can be used by setting `hardware.type` in the robot config YAML:

| Adapter | Description |
|---------|-------------|
| `dummy` | Simulated robot for testing and development |
| `a1z` | A1Z + G1Z gripper (6-DOF arm, GALAXEA-A1Z SDK via SocketCAN) |
| `lerobot` | LeRobot-compatible robots (SO-101, etc.) |
| `ros2` | ROS 2 based robots |
| `raw_sdk` | Vendor SDK via VendorSDKHardwareAdapter |
| `jaka` | Jaka robotic arms |
| `ur5e_rtde` | Universal Robots UR5e via RTDE |
| `zenoh_ros1` | ROS 1 robots via Zenoh bridge |
| `flexiv` | Flexiv robotic arms |
| `playback` | Replay recorded observations |
| `moz1` | MOZ1 robot |
| `q25` | Q25 robot (direct SDK) |
| `q25_ros2` | Q25 robot via ROS 2 |
| `tsd` | TSD robot |

The `a1z` adapter is registered in `pyproject.toml` but requires the `[a1z]` extra
(`python-can`, `pin`) and the GALAXEA-A1Z SDK. Installing `cloudrobo-r2c[all]` includes it.

Custom adapters can also be loaded via `--hardware-class` (dotted import path) or
`hardware.type: "custom"` + `hardware.class_path` in the robot config.
See `references/custom-adapter-guide.md` for details.

## Parameter Confirmation 参数确认

| Parameter | Source | Required | Confirmation Needed |
|-----------|--------|----------|---------------------|
| `--bundle` | User (from robot skill export-certificate) | Yes (recommended) | Verify file exists and is readable |
| `--robot-config` | User | Yes | Ensure YAML is valid before starting |
| `--client-config` | User | No (fallback to bundle) | — |
| `--project-id` / `--device-id` | User | Yes (if no bundle) | Verify against platform registration |
| `--endpoints` | User or bundle | No (from bundle) | Verify Zenoh router is reachable |
| `--hardware-class` | User | No | Verify class implements IRobotHardwareAdapter |
| `--duration` | User | No | 0 = run forever; set a value for timed tests |
| `--record` | User | No | Ensure output path is writable |
| `--private-key-password` | User | No (only if key encrypted) | Masked; never echo back |

**Starting the client is a long-running, externally visible operation.**
Confirm the credential bundle, robot config, and endpoint reachability before launching.

## Reference Documents 参考文档

- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation, R2C package extras, credential bundle preparation
- [Authentication & Access Control](references/iam-policies.md) — mTLS credential bundle model, Zenoh security
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagrams for R2C data plane
- [Verification Method](references/verification-method.md) — Verification method details
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria
- [Client Config Reference](references/client-config-catalog.md) — client_config.yaml field mapping, Zenoh QoS settings
- [Robot Config Reference](references/robot-config-catalog.md) — Robot config YAML schema (v2.1), hardware/translator/mapping sections
- [Custom Adapter Guide](references/custom-adapter-guide.md) — IRobotHardwareAdapter interface, ConfigurableDeviceTranslator, dry_run testing

## Edge Cases 边界情况

| Scenario | Handling |
|----------|----------|
| Missing credential bundle | Client fails with error; use `cloudrobo robot export-certificate` to produce one |
| Encrypted private key | Prompt for password (default), or use `--private-key-password` / `--private-key-password-env`; `--no-prompt-password` fails if password required |
| Invalid robot config | Client startup fails with `ValidationError` details listing all schema errors |
| Unknown hardware adapter type | Use `custom` type with `--hardware-class` for unlisted robots; see built-in adapters list above |
| Third-party adapter not found after install | Verify entry_point is registered in `pyproject.toml` under `[project.entry-points."r2c_sdk.adapters"]`; reinstall with `pip install -e .` |
| Zenoh connection failure | Client fails with `R2CConnectionError`; check endpoints, TLS certificates, and network |
| dry_run mode | Observations are published normally; received actions are logged but not executed on hardware |
| Duration 0 | Client runs indefinitely until Ctrl+C or process termination |
| Robot config missing required fields | Client startup fails with `ValidationError` for missing `hardware.type`, `translator.type`, or mapping sections |
| Heartbeat disabled | Set `runtime.heartbeat.enabled: false` in robot config; no heartbeat messages sent |
| Observation recording | `--record` path must be writable; observations saved as `.pkl` (pickle format) |
| Config directory resolution | `_config_dir` is injected into robot_config for relative path resolution (e.g., custom adapter modules) |
| Keyboard control | Enabled via `runtime.keyboard_control.enabled: true`; space=pause/resume, h=go_home (when paused), e=graceful exit |
| Action timeout | `runtime.action_response_timeout_s` controls wait time; backoff configured via `_initial_s` and `_backoff` |
| Action chunk alignment | `runtime.enable_action_chunk_alignment` prevents trajectory jumps; default false |
| Async request fusion | `runtime.async_request` configures observation fusion strategy (replace/weighted_average/nearest_neighbor) |
| Cross-skill dependency | This skill depends on the `robot` skill for credential bundle production; it does not call the robot skill directly |
| API paths | This skill does not call REST APIs; it uses Zenoh pub/sub with Protobuf serialization |
| Mutating operations | Starting `r2c client` is a long-running process; confirm parameters before launch |
| `obs://` paths | Not applicable to this skill; R2C uses Zenoh topics, not object storage |

## Verification Method 验证方法

### Specification Compliance Verification 规范合规验证

```bash
bash scripts/test-cli-commands.sh
```

### Functional Testing 功能测试

```bash
# CLI (optionally scope workspace tests: bash scripts/test-cli-commands.sh -w <workspace-id>)
bash scripts/test-cli-commands.sh
```

### Test Cases 测试用例

See `templates/test-vars.json` for the full test case list covering client startup, dry_run scenarios, and observation recording.

### Verification Checklist 验证清单

- `r2c client` with `--bundle` and a valid robot config starts and logs heartbeat/connection messages
- `r2c client` with `dry_run: true` publishes observations but does not execute actions
- Encrypted private key triggers password prompt (or fails with `--no-prompt-password`)
- `--duration N` stops the client after N seconds
- `--record` produces a non-empty `.pkl` file
- `--log-file` produces a rotating log file

## Best Practices 最佳实践

- Verify your robot config YAML is valid before starting the client to catch configuration errors early
- Use `--bundle` (recommended) instead of explicit `--project-id`/`--device-id` for simpler setup
- Refer to the built-in adapters list above to identify which robot types are supported
- Start with `dry_run: true` to verify observation publishing without risking robot movement
- Use the `dummy` adapter for development and testing when real hardware is unavailable
- Set `--duration` for timed tests instead of running indefinitely during development
- Use `--log-level DEBUG` and `--log-file` for detailed troubleshooting
- Use `--private-key-password-env` instead of `--private-key-password` to avoid secrets in shell history
- For custom adapters, implement all four `IRobotHardwareAdapter` methods and test with `dry_run` first
- Use `ConfigurableDeviceTranslator` (config-driven mapping) instead of writing a custom translator class when possible
- Record observations with `--record` for offline analysis and playback testing
- Keep heartbeat enabled (default) for connection health monitoring; disable only for debugging
- The credential bundle is produced by the `robot` skill — do not attempt to create one manually
