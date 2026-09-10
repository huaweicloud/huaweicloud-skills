---
name: huawei-cloud-cloudrobo-robot
description: >
  Manage CloudRobo robot instances — register robots, query robot lists and details,
  update robot metadata, delete offline robots, export robot certificates for secure
  access, and fetch the latest robot-side SDK package information. Robots are the
  physical carriers of embodied intelligence tasks and serve as execution targets for
  the robo-dispatcher (dispatch) and embodied services.
  Triggers include: robot registration, robot management, robot type, robot certificate,
  export certificate, robot SDK, latest SDK, robot_model, manufacturer, 机器人注册,
  机器人管理, 机器人类型, 机器人证书, 导出证书, 机器人SDK, 机器人型号, 制造商.
tags:
  - huawei-cloud-cloudrobo
  - robot
  - robot-management
  - asset
  - certificate
  - sdk
  - robot-registration
  - robot-onboarding
---

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Single-quoted JSON `'{"a":"b"}'` works as-is.

## Overview

The `cloudrobo-robot` skill manages the full lifecycle of CloudRobo robot instances. A
robot is the physical carrier that executes embodied intelligence tasks, covering six
types: HUMANOID (人形), QUADRUPED (四足), ARM (机械臂), OPERATION (作业), WHEELED (轮式), and
OTHER (其他). This skill covers robot registration, list/detail query, metadata update,
offline-device deletion, certificate export (for robot-side secure access to the platform),
and latest robot-side SDK package retrieval (for software upgrade).

**Applicable scenarios:**

- **Robot registration** — Register a new robot (create → list → show); verify type/model/workspace
- **Robot lookup / O&M** — Query running/offline robots; `list` → `show` to check status and attributes
- **Certificate export & access** — Show robot → export the robot's **access config (接入配置)** via `export-certificate` → write the **zip** bundle to a file and store it securely for robot-side onboarding
- **SDK upgrade query** — `show-sdk` to fetch the latest robot-side SDK package (file_name/version/signed_url)
- **Cross-skill orchestration** — A registered robot can later be referenced by `robo-dispatcher`
  (dispatch tasks need a `robot_id`) and by robots that run embodied services deployed via
  `cloudrobo-infer`.

**Architecture:**

```text
Agent / LLM
    │
    ├── CLI  →  cloudrobo robot <command>
    └── SDK  →  RobotClient (Python)
                    │
                    ▼
              cloudrobo-service (REST API)
              /v1/robots/*
```

All operations target the `cloudrobo-service` backend and require a valid `workspace_id`
(default workspace is used unless explicitly provided). Robot metadata management is a pure
asset-level operation (no compute billing); certificate export returns binary content protected
by a user-provided password.

## Prerequisites

- See `references/cli-installation-guide.md` for CLI installation, AK/SK authentication, and
  workspace configuration.
- A valid `workspace_id` (default workspace or explicit `--workspace-id`) is required for robot
  create / list / update operations.
- The robot must have adapted the `r2c_sdk`; use `export-certificate` to produce the robot's
  **接入配置 (access-config zip / credential bundle)** used in robot-side onboarding. The **本体配置**
  (body config) is already built into `r2c_sdk` or distributed with the robot adapter, and is not
  what `export-certificate` downloads.

## Workflow

### Natural-Language-First Principle

Every workflow below starts from a user intent (1-2 sentences), not from manual CLI/SDK
orchestration. The skill then drives the matching command chain and reports state feedback.

### Robot Registration Workflow (module + workspace + asset)

Scenario: the user wants to register and onboard a new robot.

1. **Ask robot identity** — Ask name, type (HUMANOID/QUADRUPED/ARM/OPERATION/WHEELED/OTHER),
   manufacturer, robot_model if not provided. Verify the robot_type is a valid uppercase enum.
2. **Resolve workspace** — Confirm workspace via `cloudrobo workspace current` or ask user for
   `workspace_id`. Robot create/list require a workspace context (workspace is a foundational
   resource container).
3. **Register robot** — `cloudrobo robot create --name <name> --type <TYPE> --manufacturer <mfg> --robot-model <model> --workspace-id <ws>`. Confirm the config before
   submitting. Output the returned `robot_id`.
4. **Verify** — `cloudrobo robot list --name <name>` or `cloudrobo robot show --robot-id <id>` to
   confirm registration and current status.
5. **Guidance** — After registration, suggest onboarding: export certificate + provide robot SDK.

> **Asset note**: robot_model/manufacturer uniquely identify a robot model. Do not hardcode them;
> obtain from the user or prior queries.

### Robot Lookup / O&M Workflow (module + workspace)

Scenario: "Is my inspection robot online?" / "List all robots in this workspace."

1. **List robots** — `cloudrobo robot list [--workspace-id <ws>] [--status <status>] [--type <TYPE>]`
   to get an overview with pagination (`--limit`/`--offset`) and sorting (`--sort`).
2. **Filter** — Optionally filter by `--name`, `--manufacturer`, `--robot-model`, `--type`,
   `--status`, `--user-id`, `--user-name`.
3. **Show detail** — `cloudrobo robot show --robot-id <id>` for a full config snapshot (hardware
   model, current status). The client passes through backend status (REGISTERED/OFFLINE/ONLINE...);
   no local state machine is maintained.
4. **Report** — Output status and key attributes (type, manufacturer, robot_model, status) to the user.
5. **Guidance** — Based on status: offline robot → suggest update or delete; online robot → available
   as dispatch/execution target.

### Robot Update Workflow (module)

Scenario: "Rename robot X" / "Update its description."

1. **Confirm the robot** — `cloudrobo robot show --robot-id <id>` to verify it exists and get current metadata.
2. **Update** — `cloudrobo robot update --robot-id <id> [--name <name>] [--description <desc>] [--workspace-id <ws>]`. Confirm before executing (mutating operation).
3. **Verify** — `cloudrobo robot show --robot-id <id>` to confirm the field changed.

### Certificate / Access-Config Export Workflow (module + security)

> **"导出配置文件" = 导出接入配置（证书）**. A robot has **two** configurations:
> - **本体配置（robot body/main config）** — built into `r2c_sdk`, or distributed together with the
>   robot adapter alongside other robots. It is **not** what "download/export config" refers to.
> - **接入配置（access config）** — the robot's access credential bundle used to connect to the
>   platform. This is the one you download/export, and it is produced by `export-certificate`.
>
> The downloaded access config is a **zip** package — treat it as a sensitive credential bundle and
> **store it securely** (avoid commits to source control, shared drives, or unencrypted locations).

Scenario: "Export this robot's access certificate / 导出机器人的接入配置文件 for secure onboarding."

1. **Confirm the robot in real time** — `cloudrobo robot show --robot-id <id>` to confirm the robot
   exists and check its **current** `status`. Export is a one-off **job**; the robot must not have a
   running job to export. **Robot state is dynamic**: a robot that was INACTIVE/idle earlier may now
   be OFFLINE/ONLINE or have a running job, so always re-confirm with `show` right before exporting.
2. **Export access config (certificate)** —
   `cloudrobo robot export-certificate --robot-id <id> [--password <pwd>] --output <directory>`.
   The backend returns the access-config **zip** binary; the CLI auto-generates the filename as
   `cert_config_{robot_name}_{timestamp}.zip` (queries `show_robot` for the name, uses
   `datetime.now().strftime("%Y%m%d%H%M%S")` for the timestamp) and writes it to the `--output`
   directory in binary (`wb`) mode. `--password` is **optional**; `--output` is **required** and
   must be an existing directory.
   - **If export returns `CloudRobo.04010007 "The robot can only have one running job."` (HTTP 400;
     error code sourced from backend behavior, not in the local SDK — backend-verified, pending live
     confirmation)**:
     the robot currently has a running job (dispatch/debug task) or otherwise cannot start a new
     export job. Because **state is dynamic**, a robot that exported fine before (e.g. was INACTIVE)
     may now be OFFLINE/ONLINE with a running job and fail this time — re-check `show` and pick a
     robot with **no running job** (e.g. an INACTIVE/idle robot), or wait until the current job
     finishes, then retry. Do **not** treat a failed export as "certificate not available" and
     continue with an empty/partial file — verify the output file is a **non-empty zip** before using
     it.
3. **Store securely** — After export, place the downloaded zip under secure storage (a protected
   directory, secret manager, or the robot-side onboarding location). Do not leave it in a shared /
   world-readable path. This zip is consumed on the robot side (e.g. by `r2c_sdk` / the R2C client)
   together with the body config already carried inside the SDK or adapter.
4. **Feedback** — Prompt the user that the access-config zip was written to the specified file, and
   that it can be used for robot-side access configuration (e.g. with `r2c_sdk.cloudroboclient`).
5. **Security note** — Sensitive content (password/paths) is masked in runbooks; do not echo the
   password back, and treat the exported zip as credentials.

### Robot SDK Upgrade Workflow (module)

Scenario: "What is the latest robot-side SDK version?"

1. **Query SDK** — `cloudrobo robot show-sdk` (no parameters).
2. **Report** — Output `file_name`, `version`, `signed_url` for the robot to pull the upgrade package.

### Combined Workflow A — Register robot → deploy model → dispatch task (robot + infer + dispatch)

Scenario: "Register a robot, deploy a perception model as an inference service, and run tasks on the robot using it."

1. Register the robot as in the Robot Registration Workflow; record the returned `robot_id`.
2. Confirm the robot is online (`robot show --robot-id <id>`).
3. Deploy the model as an inference service via `cloudrobo-infer` (`infer deploy-and-wait`);
   record the `service_id` / `exec_model_id`.
4. Pass the `robot_id` and model to `robo-dispatcher`: `cloudrobo dispatch create-task --session-id <sid> --name <name> --task "<task>" --constraints-json '{"model":{"exec_model_id":"<exec_model_id>"},"robot_id":"<robot_id>","exec_constraints":{"max_run_time":10,"max_iter_num":100}}'`.
   > This skill does not call cloudrobo-infer/dispatch by name; the agent orchestrates across
   > skills by first obtaining the robot_id here, then using the infer and dispatch skills.

### Cleanup Workflow (module)

Scenario: "Remove this decommissioned robot."

1. Confirm the robot — `cloudrobo robot show --robot-id <id>` to verify it can be safely deleted
   (deletion is irreversible; the backend validates running status and business dependencies).
2. Delete — `cloudrobo robot delete --robot-id <id>`. Confirm before executing.
3. Verify — `cloudrobo robot show --robot-id <id>` → expect `ResourceNotFoundError`/not found.

## CLI Command Format Standard

```bash
cloudrobo robot <command> [OPTIONS]
```

| Feature | Description | Example |
| --------- | ------------- | --------- |
| Command group | `robot` (registered via entry point) | `cloudrobo robot` |
| Subcommand | kebab-case | `create`, `export-certificate`, `show-sdk` |
| Workspace | `--workspace-id <id>` (create/list/update) | `--workspace-id abc-123` |
| Output format | JSON to stdout | `out(result)` |
| JSON parameter | Passed as individual flags (e.g. `--name`, `--type`, `--manufacturer`, `--robot-model`) | `create --name r1 --type HUMANOID --manufacturer M --robot-model X` |
| Dry-run | `--dry-run` (on create/update/delete/export-certificate) | Preview without executing |
| Binary output | `--output <directory>` (export-certificate) | auto-generates `cert_config_{name}_{timestamp}.zip` in directory |

> **Full coverage**: The SDK exposes 7 methods, CLI exposes 7 commands (0 gaps).
> See `references/robot-config-catalog.md` for the full coverage matrix.

## Core Commands

> **SDK Direct Calls**: When CLI is inconvenient (dynamic JSON, cross-package queries), use the
> Python SDK directly. `RobotClient` exposes the 7 methods below.

### Create / Register a Robot

```bash
cloudrobo robot create --name <robot-name> --type HUMANOID --manufacturer "Manufacturer A" --robot-model "Model X" --workspace-id <workspace-id> [--description "inspection robot"] [--dry-run]
```

```python
# SDK
from cloudrobo_core.sdk import Config, HttpClient
from cloudrobo_robot import RobotClient

config = Config()
http_client = HttpClient(config)
client = RobotClient(http_client)

robot = client.create_robot({
    "name": "inspection-robot-001",
    "type": "HUMANOID",
    "manufacturer": "Manufacturer A",
    "robot_model": "Model X",
    "workspace_id": config.workspace_id,
    "description": "inspection robot for factory floor"
})
print(robot)  # includes robot_id
```

### List Robots

```bash
cloudrobo robot list [--limit 10] [--offset 0] [--status <status>] [--type <TYPE>] [--workspace-id <ws>]
```

```python
robots = client.list_robots(name="inspection-robot-001")
for r in robots.get("items", []):
    print(r["name"], r["type"], r["status"])
```

### Show Robot Detail

```bash
cloudrobo robot show --robot-id <robot-id>
```

```python
robot = client.show_robot("<robot-id>")
print(robot["name"], robot["type"], robot["manufacturer"], robot["status"])
```

### Update Robot

```bash
cloudrobo robot update --robot-id <robot-id> --description "new description" [--dry-run]
```

```python
client.update_robot("<robot-id>", {"description": "new description"})
```

### Delete Robot

```bash
cloudrobo robot delete --robot-id <robot-id> [--dry-run]
```

```python
client.delete_robot("<robot-id>")
```

### Export Robot Access Config / Certificate

```bash
cloudrobo robot export-certificate --robot-id <robot-id> [--password <password>] --output <directory> [--dry-run]
# Output: <directory>/cert_config_{robot_name}_{timestamp}.zip
```

```python
# Returns the access-config zip binary content
cert = client.export_robot_certificate("<robot-id>", {"password": "<password>"})
# CLI auto-generates filename and writes binary to --output directory in wb mode
```

> This command exports the robot's **接入配置 (access config / certificate)** — the credential
> bundle a robot uses to connect to the platform. It is a **zip** package: the CLI auto-generates
> the filename as `cert_config_{robot_name}_{timestamp}.zip` and writes it to the `--output`
> directory. **Store the zip securely**. `--password` (encrypts the bundle) is **optional**;
> `--output` (export directory, must exist) is **required**; see the Certificate / Access-Config
> Export Workflow.

### Show Latest Robot SDK

```bash
cloudrobo robot show-sdk
```

```python
sdk = client.show_sdk()
print(sdk["file_name"], sdk["version"], sdk["signed_url"])
```

## Parameter Confirmation

| Parameter | Source | Required | Confirmation Needed |
| ----------- | -------- | ---------- | --------------------- |
| `--name` | User | Yes (create) | Verify uniqueness/descriptiveness before create |
| `--type` | User | Yes (create) | Uppercase enum: HUMANOID/QUADRUPED/ARM/OPERATION/WHEELED/OTHER |
| `--manufacturer` / `--robot-model` | User | Yes (create) | Uniquely identify the robot model |
| `--workspace-id` | User or default workspace | Yes (create/list/update) | — |
| `--robot-id` | User or prior command output | Yes (show/update/delete/export) | Verify before update/delete |
| `--password` | User | No (export-certificate, default None) | Optional; encrypts the access-config zip; masked, not echoed |
| `--output` | User | Yes (export-certificate) | Required; directory to write the auto-generated `cert_config_{name}_{timestamp}.zip` |
| `--status`/`--type` filters | User | No (list) | — |
| `--dry-run` | — | No | Preview without submitting |

**Mutating operations** (create/update/delete/export-certificate) must prompt the user for
confirmation before execution.

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md) — cloudrobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege credential & access model
- [Verification Method](references/verification-method.md) — Verification method details
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagrams
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria
- [Robot Config Reference](references/robot-config-catalog.md) — RobotDto fields, type enum, status, certificate export, SDK info, SDK/CLI coverage matrix

## Edge Cases

| Scenario | Handling |
| ---------- | ---------- |
| Missing `workspace_id` | create/list/update may fall back to default workspace; if none, error with suggestion |
| Invalid `robot_type` | create rejects values outside HUMANOID/QUADRUPED/ARM/OPERATION/WHEELED/OTHER |
| Robot not found | show/update/delete return `ResourceNotFoundError`; verify `robot_id` |
| Path traversal | `validate_safe_id(robot_id)` blocks `../` input |
| Certificate export failure | Check password correctness and robot has a valid certificate; if `CloudRobo.04010007 "The robot can only have one running job"` (backend-verified, pending live confirmation), the robot has a running job — retry on an INACTIVE/idle robot with no running job, or wait for the current job to finish |
| Certificate output corruption | CLI writes binary with `wb` mode; never write text-encoded |
| Access-config (zip) storage | The exported access config is a **zip credential bundle**; store it securely and never commit/shared publicly |
| SDK retrieval failure | Check backend SDK package published; retry `show-sdk` |
| Workspace cross-tenant | API carries `workspace_id`; backend validates ownership |
| Deleting a running robot | Backend validates status and business dependencies; may reject |
| Deletion irreversible | Always confirm `robot_id` before delete |
| AK/SK not set | Operations fail at HTTP signing step; set `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` |
| robot_id / model values | Never hardcoded; obtained from user or `list`/`show` results |
| API paths | Sourced from OpenAPI YAML (`robo-operations.yaml`) and feature design, not inferred |
| Cross-skill invocation | This skill does not call other skills by name; it only produces a `robot_id` that dispatch/infer may consume |
| Mutating operations | create/update/delete/export-certificate should be confirmed by the user |

## Verification Method

### Specification Compliance Verification

```bash
bash scripts/test-cli-commands.sh
```

### Functional Testing

```bash
bash scripts/test-cli-commands.sh
```

### Test Cases

See `templates/test-vars.json` for the full test case list covering registration, lookup,
update, delete, certificate export, SDK query, and safety scenarios.

### Verification Checklist

- After `create`, verify via `list --name` / `show --robot-id` that the robot appears with correct type/status
- After `update`, `show` reflects the changed name/description
- After `delete`, `show` returns not-found
- After `export-certificate`, the output directory contains the auto-generated `cert_config_{name}_{timestamp}.zip` with the access-config binary
- `show-sdk` returns file_name/version/signed_url
- Path traversal (`../`) is blocked by `validate_safe_id`
- Mutating operations prompt user confirmation before executing

## Best Practices

- Always confirm `robot_id` and the full config before create/update/delete/export-certificate
- Use `--dry-run` to validate create/update/export params before actual submission
- Use `validate_safe_id`-backed CLI to prevent path traversal; never embed raw user input into paths
- Mask `password` and sensitive values in all runbooks and logs
- For access-config export, use `--output <directory>` (must exist); the CLI auto-generates the filename `cert_config_{robot_name}_{timestamp}.zip` and writes the zip in binary (`wb`) mode — **store the zip securely**
- Remember: "导出配置文件" means exporting the **接入配置 (access config)** via `export-certificate` —
  the body config is built into `r2c_sdk` / distributed with adapters and is not exported here
- Record the returned `robot_id` after registration for later dispatch/infer reference
- Prefer `cloudrobo robot list` for a workspace-wide overview; paginate with `--limit`/`--offset`
- Combine with workspace (`cloudrobo workspace current`) and asset skills to resolve workspace/model context before creating robots or wiring them into dispatch
