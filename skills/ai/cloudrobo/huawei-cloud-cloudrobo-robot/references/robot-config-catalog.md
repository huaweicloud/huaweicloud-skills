# Robot Config Reference

## RobotDto (create robot request body)

Required fields: `name`, `type`, `workspace_id`

| Field | Type | Required | Description | Example |
| ------- | ------ | ---------- | ------------- | --------- |
| `name` | string | Yes | Robot name (unique in workspace) | `my-biped-bot` |
| `type` | string enum | Yes | Robot type (uppercase, see enum below) | `HUMANOID` |
| `manufacturer` | string | Yes | Robot manufacturer | `Unitree` |
| `robot_model` | string | Yes | Robot model | `B2-W` |
| `workspace_id` | string (UUID) | Yes | Workspace ID | `w1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8` |
| `description` | string | No | Robot description | `Bipedal warehouse robot` |

> `manufacturer` and `robot_model` are required in the current feature design. The `description`
> field is optional.

## robot_type enum

| Value | Description |
| ------- | ------------- |
| `HUMANOID` | Humanoid robot |
| `QUADRUPED` | Quadruped robot |
| `ARM` | Robotic arm |
| `OPERATION` | Operation robot |
| `WHEELED` | Wheeled robot |
| `OTHER` | Other type |

> **Important**: `robot_type` enum values are displayed in uppercase (`ARM`, `HUMANOID`,
> `OPERATION`, `OTHER`, `QUADRUPED`, `WHEELED`), but the CLI accepts them
> case-insensitively (`click.Choice(..., case_sensitive=False)`). Only values outside the
> enum are rejected with a usage error. Do not hardcode a specific type; always query
> available robots/workspace first.

## Certificate / Access-Config Export Request

> **Two robot configs**: a robot has a **本体配置** (body config, built into `r2c_sdk` or distributed
> together with the robot adapter alongside other robots) and an **接入配置** (access config, the
> credential bundle used to connect to the platform). "Download/export config file" (下载/导出配置文件)
> **always refers to the 接入配置**, which is what `export-certificate` produces.

```yaml
# POST /v1/robots/{robot_id}/certificate/export
password: "<your-password>"   # optional; encrypts the exported access config (placeholder)
```

- The response is a **zip** credential bundle (access config) binary blob.
- The CLI auto-generates the filename as `cert_config_{robot_name}_{timestamp}.zip` and writes the
  binary to the `--output` directory using `wb` (binary-write) mode.
- `--output` is **required** and must be an existing directory; `--password` is optional; if provided
  it encrypts the certificate/access config. Treat it as sensitive.
- **Store the downloaded zip securely** (protected directory / secret storage); it is consumed by the
  robot side (e.g. `r2c_sdk` / R2C client) together with the body config already inside the SDK/adapter.

## SDK Info Response (GET /v1/robots/sdk)

Returns an SDK download descriptor:

| Field | Type | Description |
| ------- | ------ | ------------- |
| `file_name` | string | SDK package file name |
| `version` | string | SDK version |
| `signed_url` | string | OBS temporary download URL |

## SDK / CLI coverage matrix

SDK (7 methods) / CLI (7 commands) coverage:

| Operation | SDK method | CLI command | API path |
| ----------- | ------------ | ------------- | ---------- |
| create_robot | `create_robot(req)` | `create` | `POST /v1/robots` |
| list_robots | `list_robots(**params)` | `list` | `GET /v1/robots` |
| show_robot | `show_robot(robot_id)` | `show` | `GET /v1/robots/{robot_id}` |
| update_robot | `update_robot(robot_id, req)` | `update` | `PUT /v1/robots/{robot_id}` |
| delete_robot | `delete_robot(robot_id)` | `delete` | `DELETE /v1/robots/{robot_id}` |
| export_robot_certificate | `export_robot_certificate(robot_id, req)` | `export-certificate` | `POST /v1/robots/{robot_id}/certificate/export` |
| show_sdk | `show_sdk()` | `show-sdk` | `GET /v1/robots/sdk` |

**Key notes:**

- The backend validates request payloads (including JSON params passed as `str`); the tool layer does not re-validate.
- There is no separate "start/stop" for a robot — robot state is managed via `create`/`update`. Robot execution is driven by the dispatch module.
- `show-sdk` takes no parameters.

## Robot lifecycle states

Robot state is reported in the `status` field of list/show responses. The robot skill manages the
registration/CRUD lifecycle; scheduling/execution is delegated to the dispatch module via `robot_id`.
