# Robot Config Reference

## Robot Config YAML (schema_version v2.1)

The robot config YAML defines the hardware adapter, translator, device-to-R2C field mappings,
and runtime behavior. It is validated by `cloudrobo r2c validate-config` against the
`RobotConfig` pydantic schema.

```yaml
schema_version: "v2.1"

runtime:
  publish_hz: 30.0
  max_duration_s: 0.0
  dry_run: false
  action_response_timeout_s: 30.0
  action_response_timeout_initial_s: 3.0
  action_response_timeout_backoff: 2.0
  max_enqueue_actions_per_chunk: -1
  enable_action_chunk_alignment: false
  skip_initial_observations: 1
  async_request:
    enabled: false
    publish_trigger_threshold: 50
    fusion:
      strategy: weighted_average
      window_size: 10
      state_types: [joint_angle, joint_angle, ...]
  heartbeat:
    enabled: true
    interval_ms: 5000
    jitter_ms: 500
    status: "ONLINE"
    mode: "AUTO"
  keyboard_control:
    enabled: true
    keymap:
      "j": go_home
      "s": state

hardware:
  type: "dummy"
  config:
    joint_names: ["shoulder_pan.pos", ...]
    initial_joint_positions: [0.0, 0.1, -0.2, 0.0, 0.0, 0.5]
    max_joint_speed_rad_s: 1.5
    image_specs:
      front: { h: 255, w: 255, c: 3 }
      wrist: { h: 255, w: 255, c: 3 }
    commands:
      go_home: { type: go_home, joints: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }
      state: { type: get_state }

translator:
  type: "configurable"

device_to_r2c:
  task: "pick the pen into the box"
  mappings:
    - target_key: "joint_states.names"
      default: ["joint_1", "joint_2", ...]
    - target_key: "joint_states.position"
      source_paths: ["shoulder_pan.pos", ...]
    - target_key: "images.color.front"
      source_path: "front"
      transforms: ndarray_to_jpeg
    - target: "extensions.language_goal"
      source_path: "task_instruction"
      extension: { dtype: STRING, shape: [] }

r2c_to_device:
  mappings:
    - target: "shoulder_pan.pos"
      source: "joint_states.position"
      source_index: 0
      required: true
    - target: "gripper.pos"
      source: "joint_states.position"
      source_index: 5
      required: true
```

## Top-Level Sections

| Section | Required | Description |
|---------|----------|-------------|
| `schema_version` | Yes | Config schema version (currently `"v2.1"`) |
| `runtime` | Yes | Runtime behavior: frequencies, timeouts, dry_run, heartbeat, keyboard control |
| `hardware` | Yes | Hardware adapter type and adapter-specific config |
| `translator` | Yes | Translator type (usually `configurable`) |
| `device_to_r2c` | Yes | Mapping: device observation → R2C Observation message |
| `r2c_to_device` | Yes | Mapping: R2C Action message → device action |

## runtime Section

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `publish_hz` | float | `30.0` | Action execution frequency (Hz); also determines observation publish check frequency. Recommended 10–30 Hz |
| `max_duration_s` | float | `0.0` | Max runtime in seconds; 0 = run forever (Ctrl+C stops) |
| `dry_run` | bool | `false` | If true: publish real observations but do not execute received actions (logs only) |
| `action_response_timeout_s` | float | `30.0` | Wait time for action after publishing observation; re-publish on timeout. For weak networks/large models, recommend ≥ 30s |
| `action_response_timeout_initial_s` | float | `3.0` | Initial timeout on first attempt |
| `action_response_timeout_backoff` | float | `2.0` | Backoff multiplier for subsequent timeouts (doubles each time) |
| `max_enqueue_actions_per_chunk` | int | `-1` | Max action steps enqueued per chunk; -1 = accept all |
| `enable_action_chunk_alignment` | bool | `false` | Enable action chunk alignment to prevent trajectory jumps |
| `skip_initial_observations` | int | `1` | Number of observations to skip at startup (lets action queue fill before execution) |

### runtime.async_request

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Enable async request fusion |
| `publish_trigger_threshold` | int | `50` | Observation count threshold to trigger publish |
| `fusion.strategy` | string | `weighted_average` | Fusion strategy: `replace` / `weighted_average` / `nearest_neighbor` |
| `fusion.window_size` | int | `10` | Fusion window size (for weighted_average / nearest_neighbor) |
| `fusion.state_types` | list[string] | — | Per-element physical semantics: `joint_angle` / `position_xyz` / `euler` / `quaternion` |

### runtime.heartbeat

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Enable automatic heartbeat publishing |
| `interval_ms` | int | `5000` | Heartbeat interval in milliseconds (must be > 0) |
| `jitter_ms` | int | `500` | Random jitter in milliseconds (must be ≥ 0) |
| `status` | string | `"ONLINE"` | Heartbeat status field |
| `mode` | string | `"AUTO"` | Heartbeat mode field |

### runtime.keyboard_control

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Enable keyboard control during client runtime |
| `keymap` | dict | — | Key-to-command mapping; keys are case-sensitive |

> Keyboard control keys: space = pause/resume, h = go_home (when paused), e = graceful exit.
> Key mapping is case-sensitive (pressing `j` triggers `go_home`, but `Shift+J` does not).

## hardware Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Adapter type name (from `r2c list-adapters`) or `"custom"` |
| `class_path` | string | No (required for `custom`) | Dotted import path for custom adapter class |
| `config` | dict | No | Adapter-specific configuration (joint names, image specs, etc.) |

### Built-in Adapter Types

| Type | Config Requirements | Description |
|------|---------------------|-------------|
| `dummy` | joint_names, initial_joint_positions, image_specs, commands | Simulated robot for testing |
| `lerobot` | robot_type, port, etc. | LeRobot-compatible robots |
| `ros2` | node_name, topic mappings | ROS 2 based robots |
| `raw_sdk` | vendor SDK config | Vendor SDK via VendorSDKHardwareAdapter |
| `jaka` | IP address, joint config | Jaka robotic arms |
| `ur5e_rtde` | IP address, RTDE config | Universal Robots UR5e |
| `zenoh_ros1` | Zenoh bridge config | ROS 1 robots via Zenoh bridge |
| `flexiv` | IP address, joint config | Flexiv robotic arms |
| `playback` | recording file path | Replay recorded observations |
| `moz1` | MOZ1-specific config | MOZ1 robot |
| `q25` | Q25 SDK config | Q25 robot (direct SDK) |
| `q25_ros2` | ROS 2 config for Q25 | Q25 robot via ROS 2 |
| `tsd` | TSD-specific config | TSD robot |
| `custom` | class_path required | Custom adapter loaded via dotted import path |

## translator Section

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | `"configurable"` | Translator type (only `configurable` supported built-in) |

> `ConfigurableDeviceTranslator` uses the `device_to_r2c` and `r2c_to_device` sections for
> field mapping. For custom translators, use `--translator-class` on the CLI.

## device_to_r2c Section

Maps device observations to R2C Observation Protobuf messages.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task` | string | No | Task description string (passed as observation context) |
| `mappings` | list[Mapping] | Yes | List of field mappings |

### device_to_r2c Mapping Fields

| Field | Type | Description |
|-------|------|-------------|
| `target_key` / `target` | string | R2C Observation field path (dotted), e.g. `joint_states.position` |
| `source_path` / `source_paths` | string / list[string] | Device observation field path(s) |
| `default` | any | Default value if source not available |
| `transforms` | string / list[string] | Transform function(s): `ndarray_to_jpeg`, `jpeg_to_ndarray`, etc. |
| `use_lookup_dotted` | bool | Use dotted key lookup (default: false) |
| `extension.dtype` | string | Extension field data type: STRING/INT64/FLOAT32/INT32/etc. |
| `extension.shape` | list | Extension field shape (empty for scalar) |

## r2c_to_device Section

Maps R2C Action Protobuf messages to device actions.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mappings` | list[Mapping] | Yes | List of field mappings |

### r2c_to_device Mapping Fields

| Field | Type | Description |
|-------|------|-------------|
| `target` | string | Device action field path (dotted), e.g. `shoulder_pan.pos` |
| `source` | string | R2C Action field path, e.g. `joint_states.position` |
| `source_index` | int | Index into source array (for array fields) |
| `use_assign_dotted` | bool | Use dotted assignment (default: false) |
| `required` | bool | If true, mapping must succeed (error on missing source) |
| `transforms` | string / list[string] | Transform function(s) |

## Built-in Robot Config Files

17 robot config YAML files are available in `config/`:

| Config File | Adapter Type | Robot |
|-------------|-------------|-------|
| `robot_dummy_config.yaml` | dummy | Simulated 6-DOF robot |
| `robot_a1z_config.yaml` | — | A1Z robot |
| `robot_example_config.yaml` | — | Example/template config |
| `robot_flexiv_config.yaml` | flexiv | Flexiv arm |
| `robot_jaka_sdk_config.yaml` | jaka | Jaka arm via SDK |
| `robot_mini2_ros_config.yaml` | ros2 | Mini2 robot via ROS 2 |
| `robot_moz1_config.yaml` | moz1 | MOZ1 robot |
| `robot_playback_config.yaml` | playback | Observation playback |
| `robot_q25_config.yaml` | q25 | Q25 robot (direct SDK) |
| `robot_q25_config_joystick.yaml` | q25 | Q25 with joystick control |
| `robot_r1_playback_config.yaml` | playback | R1 playback |
| `robot_r1_zenoh_ros1_config.yaml` | zenoh_ros1 | R1 via Zenoh ROS 1 bridge |
| `robot_so101_bimanual_config.yaml` | lerobot | SO-101 bimanual |
| `robot_so101_lerobot_config.yaml` | lerobot | SO-101 via LeRobot |
| `robot_tsd_config.yaml` | tsd | TSD robot |
| `robot_ur5e_config.yaml` | ur5e_rtde | UR5e via RTDE |
| `robot_ur5e_ros_config.yaml` | ros2 | UR5e via ROS 2 |
