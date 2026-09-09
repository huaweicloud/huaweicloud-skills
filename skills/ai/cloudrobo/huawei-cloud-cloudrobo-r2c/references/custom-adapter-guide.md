# Custom Adapter Development Guide

This guide covers implementing custom hardware adapters and translators for robots not in
the built-in adapter list. The R2C SDK provides three integration paths:

| Path | Discovery | Use Case | Recommended When |
|------|-----------|----------|------------------|
| **Entry-point adapter** | `r2c_sdk.adapters` entry point; appears in `list-adapters` | Reusable third-party adapters | Sharing across projects/teams, pip-installable packages |
| **`--hardware-class` CLI override** | Dotted import path on CLI; no registration needed | One-off custom adapters | Quick prototyping, local development |
| **`hardware.type: "custom"` + `class_path`** | Config-driven dynamic loading | Config-only loading | When CLI flags are inconvenient |

## Path 1: Third-Party Adapter via Entry Point (Recommended) 入口点注册第三方适配器

Create a standalone pip package that registers a hardware adapter via the `r2c_sdk.adapters`
entry-point group. After `pip install`, the adapter is automatically discovered by
`AdapterRegistry` and appears in `cloudrobo r2c list-adapters`.

> A complete working example is available at
> `cloudrobo-r2c/examples/third_party_adapter/` in the `cloudrobo-r2c` package.

### Package Structure

```text
my-robot-r2c-adapter/
├── pyproject.toml                  # Package metadata + entry_point registration
├── my_robot_adapter.py             # Adapter class + factory function
├── my_robot_commands.py            # (Optional) Custom command implementations
└── robot_my_robot_config.yaml      # Robot config YAML
```

### Step 1: Create pyproject.toml

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "my-robot-r2c-adapter"
version = "0.1.0"
description = "Third-party R2C adapter for MyRobot"
requires-python = ">=3.10"
dependencies = [
    "hw-r2c-sdk",
]

# Register the adapter module(s) for inclusion in the package
[tool.setuptools]
py-modules = ["my_robot_adapter", "my_robot_commands"]

# ═════════════════════════════════════════════════════════════════════
# Register this adapter so RobotFactory discovers it automatically.
# The entry_point name ("my_robot") becomes the hardware.type value
# users put in their robot config YAML:
#
#     hardware:
#       type: my_robot
#       config:
#         ip: "192.168.1.x"
#         port: 502
# ═════════════════════════════════════════════════════════════════════
[project.entry-points."r2c_sdk.adapters"]
my_robot = "my_robot_adapter:create_my_robot_adapter"
```

**Key rules:**

- The entry-point group **must** be `r2c_sdk.adapters`.
- The entry-point name (`my_robot`) becomes the `hardware.type` value in the robot config YAML.
- The entry-point value points to a **factory function** (not a class): `"module:function_name"`.
- The factory function receives `config: Mapping[str, Any]` and returns an `IRobotHardwareAdapter` instance.

### Step 2: Implement the Adapter Class and Factory Function

```python
# my_robot_adapter.py

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Mapping

from cloudrobo_r2c.core.interfaces import IRobotHardwareAdapter

logger = logging.getLogger(__name__)


def create_my_robot_adapter(
    config: Mapping[str, Any], **extra_kwargs: Any
) -> IRobotHardwareAdapter:
    """Entry-point factory — called by AdapterRegistry via RobotFactory."""
    return MyRobotHardwareAdapter(config=dict(config))


@dataclass
class MyRobotHardwareAdapter(IRobotHardwareAdapter):
    """Third-party adapter wrapping MyRobot SDK."""

    config: Mapping[str, Any]

    _connected: bool = field(default=False, init=False, repr=False)
    _joint_names: List[str] = field(default_factory=list, init=False, repr=False)
    _state: List[float] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        # Register custom command classes (optional)
        from my_robot_commands import MyRobotHomeCommand
        self.register_command_class("go_home", MyRobotHomeCommand)

    def connect(self) -> None:
        if self._connected:
            return
        self._joint_names = list(self.config.get("joint_names", []))
        if not self._joint_names:
            self._joint_names = [
                "joint_1", "joint_2", "joint_3",
                "joint_4", "joint_5", "joint_6",
            ]
        self._state = [0.0] * len(self._joint_names)
        self._connected = True
        logger.info(
            "MyRobot connected to %s:%s",
            self.config.get("ip"), self.config.get("port"),
        )

    def disconnect(self) -> None:
        self._connected = False
        logger.info("MyRobot disconnected")

    def get_observation(self) -> Mapping[str, Any]:
        if not self._connected:
            raise RuntimeError("Not connected")
        # Read joint positions from hardware
        self._state = [v + 0.01 for v in self._state]
        return dict(zip(self._joint_names, self._state))

    def send_action(self, command: Mapping[str, Any]) -> None:
        if not self._connected:
            raise RuntimeError("Not connected")
        logger.info("MyRobot action: %s", command)
```

### Step 3: (Optional) Implement Custom Commands

Commands are reusable actions that can be triggered via keyboard control or CLI. They are
registered in `__post_init__` via `register_command_class()`.

```python
# my_robot_commands.py

from __future__ import annotations

from typing import Any

from cloudrobo_r2c.robots.commands.base import AdapterCommand


class MyRobotHomeCommand(AdapterCommand):
    """Send robot to home position via send_action."""

    def execute(self, **kwargs: Any) -> None:
        target = self.config.get("joints")
        if target is not None:
            self.adapter.send_action({"joint_target": list(target)})
```

Commands are referenced in the robot config YAML under `hardware.config.commands`:

```yaml
hardware:
  type: my_robot
  config:
    # ... other config ...
    commands:
      go_home:
        type: go_home              # Matches the registered command class name
        joints: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

### Step 4: Create Robot Config YAML

Use the entry-point name as `hardware.type`:

```yaml
# robot_my_robot_config.yaml

schema_version: "v2.1"

runtime:
  publish_hz: 30.0
  max_duration_s: 30.0
  action_response_timeout_s: 30.0
  action_response_timeout_initial_s: 3.0
  action_response_timeout_backoff: 2.0
  skip_initial_observations: 0
  keyboard_control:
    enabled: true
    keymap:
      "j": go_home              # Keyboard key "j" triggers the go_home command

hardware:
  type: my_robot                # Matches the entry_point name in pyproject.toml
  config:
    ip: "192.168.1.100"
    port: 502
    joint_names:
      - "joint_1"
      - "joint_2"
      - "joint_3"
      - "joint_4"
      - "joint_5"
      - "joint_6"
    commands:
      go_home:
        type: go_home           # References MyRobotHomeCommand
        joints: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

translator:
  type: "configurable"

device_to_r2c:
  task: default_task
  mappings:
    - target_key: "joint_states.names"
      default:
        - "joint_1"
        - "joint_2"
        - "joint_3"
        - "joint_4"
        - "joint_5"
        - "joint_6"

    - target_key: "joint_states.position"
      source_paths:
        - joint_1
        - joint_2
        - joint_3
        - joint_4
        - joint_5
        - joint_6

r2c_to_device:
  mappings:
    - target: joint_1
      source: joint_states.position
      source_index: 0
      required: true
    - target: joint_2
      source: joint_states.position
      source_index: 1
      required: true
    - target: joint_3
      source: joint_states.position
      source_index: 2
      required: true
    - target: joint_4
      source: joint_states.position
      source_index: 3
      required: true
    - target: joint_5
      source: joint_states.position
      source_index: 4
      required: true
    - target: joint_6
      source: joint_states.position
      source_index: 5
      required: true
```

### Step 5: Install and Verify

```bash
# Install the adapter package
pip install .            # or pip install -e . for development

# Verify the adapter is discovered
cloudrobo r2c list-adapters
# Expected: "my_robot" appears in the list

# Validate the robot config
cloudrobo r2c validate-config --robot-config robot_my_robot_config.yaml

# Start the client
cloudrobo r2c client --bundle <path/to/cert_config_*.zip> --robot-config robot_my_robot_config.yaml
```

### Entry-Point Discovery Mechanism

The R2C SDK uses Python's `importlib.metadata.entry_points` to scan the `r2c_sdk.adapters`
group at runtime:

```text
pip install my-robot-r2c-adapter
  → AdapterRegistry._ensure_scanned()
    → entry_points(group="r2c_sdk.adapters")
      → finds "my_robot" = "my_robot_adapter:create_my_robot_adapter"
        → RobotFactory.get("my_robot")
          → loads factory function
            → factory(config) → MyRobotHardwareAdapter instance
```

The adapter is loaded lazily on first use — individual factories are only imported when
`RobotFactory.get(type_name)` is called.

## Path 2: CLI Override (Quick Prototyping) CLI 覆盖（快速原型）

For one-off custom adapters or local development, use `--hardware-class` on the CLI. No
entry-point registration or separate package needed.

### Implement the Adapter

```python
# my_pkg/my_adapter.py

from cloudrobo_r2c.core.interfaces import IRobotHardwareAdapter
import numpy as np

class MyRobotAdapter(IRobotHardwareAdapter):
    def __init__(self, config: dict):
        self._config = config
        self._robot = None
        self._joint_names = config.get("joint_names", [])
        self._image_specs = config.get("image_specs", {})

    def connect(self):
        """Connect to the robot."""
        import vendor_sdk
        ip = self._config["ip"]
        self._robot = vendor_sdk.Robot(ip)
        self._robot.connect()
        initial = self._config.get("initial_joint_positions")
        if initial:
            self._robot.move_joints(initial)

    def disconnect(self):
        if self._robot:
            self._robot.disconnect()
            self._robot = None

    def get_observation(self):
        """Read sensor state. Returns dict of field_name -> value."""
        obs = {}
        joints = self._robot.get_joint_positions()
        obs["joint_positions"] = joints
        for name, spec in self._image_specs.items():
            img = self._robot.capture_image(camera=name)
            obs[name] = np.array(img)
        obs["state"] = self._robot.get_state()
        return obs

    def send_action(self, action: dict):
        if "joint_positions" in action:
            self._robot.move_joints(action["joint_positions"])
```

### Configure and Run

Set `hardware.type: "custom"` and `hardware.class_path` in the robot config YAML:

```yaml
hardware:
  type: "custom"
  class_path: "my_pkg.my_adapter.MyRobotAdapter"
  config:
    ip: "192.168.1.100"
    joint_names: ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]
    initial_joint_positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

Or pass the class directly on the CLI:

```bash
cloudrobo r2c client --bundle <path/to/cert_config_*.zip> --robot-config config/my_robot_config.yaml --hardware-class my_pkg.my_adapter.MyRobotAdapter
```

## Path 3: VendorSDKHardwareAdapter (No Code) 厂商SDK适配器（无需编码）

For robots with a Python SDK that exposes joint read/write APIs, use the `raw_sdk` adapter
type with a config-driven approach. No custom class needed.

### Config Example

```yaml
hardware:
  type: "raw_sdk"
  config:
    # Vendor SDK initialization
    sdk_class: "vendor_sdk.Robot"       # dotted import path
    sdk_init_args:
      ip: "192.168.1.100"
      port: 8080

    # Joint configuration
    joint_names: ["joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "joint_6"]
    initial_joint_positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    # Observation: how to read from SDK
    observation:
      method: "get_joint_positions"     # SDK method to call
      result_key: "positions"           # key in returned dict

    # Action: how to write to SDK
    action:
      method: "set_joint_positions"     # SDK method to call
      args_key: "positions"             # parameter name in SDK method

    # Image capture (optional)
    image_specs:
      front:
        method: "capture_image"
        h: 480
        w: 640
        c: 3
```

### Translator Config

With `raw_sdk`, use `ConfigurableDeviceTranslator` to map SDK fields to R2C fields:

```yaml
translator:
  type: "configurable"

device_to_r2c:
  mappings:
    - target_key: "joint_states.position"
      source_path: "positions"         # key from get_observation() dict
    - target_key: "images.color.front"
      source_path: "front"             # key from image_specs
      transforms: ndarray_to_jpeg

r2c_to_device:
  mappings:
    - target: "positions"               # key expected by send_action()
      source: "joint_states.position"
      required: true
```

## IRobotHardwareAdapter Interface

All hardware adapters implement the `IRobotHardwareAdapter` interface:

```python
from cloudrobo_r2c.core.interfaces import IRobotHardwareAdapter

class MyHardwareAdapter(IRobotHardwareAdapter):
    def connect(self):
        """Establish connection to the physical robot."""
        ...

    def disconnect(self):
        """Safely disconnect from the robot."""
        ...

    def get_observation(self):
        """Read current sensor state from the robot.
        Returns a dict of field_name -> value (joints, images, etc.).
        Called at runtime.publish_hz frequency.
        """
        ...

    def send_action(self, action):
        """Execute an action on the robot.
        Receives a dict of field_name -> value translated from R2C Actions.
        Called when cloud actions are received.
        """
        ...
```

### Method Lifecycle

```text
connect() → [get_observation() → publish → wait action → send_action()] loop → disconnect()
```

1. `connect()` — Called once at startup. Establishes physical connection (TCP, serial, USB, etc.).
2. `get_observation()` — Called at `runtime.publish_hz` frequency. Returns a dict of sensor
   readings (joint positions, images, IMU data, etc.).
3. `send_action(action)` — Called when cloud actions are received. The `action` dict has been
   translated from R2C Action Protobuf by the device translator.
4. `disconnect()` — Called on shutdown (Ctrl+C or duration elapsed). Cleans up resources.

## Command System 命令系统

Adapters can register custom commands that are triggered via keyboard control or CLI.
Commands are instances of `AdapterCommand`:

```python
from cloudrobo_r2c.robots.commands.base import AdapterCommand

class MyRobotHomeCommand(AdapterCommand):
    """Send robot to home position via send_action."""

    def execute(self, **kwargs: Any) -> None:
        target = self.config.get("joints")
        if target is not None:
            self.adapter.send_action({"joint_target": list(target)})
```

### Registering Commands

Register commands in the adapter's `__post_init__`:

```python
def __post_init__(self) -> None:
    from my_robot_commands import MyRobotHomeCommand
    self.register_command_class("go_home", MyRobotHomeCommand)
```

### Command Config in Robot Config YAML

Commands are configured under `hardware.config.commands`:

```yaml
hardware:
  type: my_robot
  config:
    commands:
      go_home:
        type: go_home              # Matches the registered command class name
        joints: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

### Keyboard Control

Commands can be bound to keyboard keys:

```yaml
runtime:
  keyboard_control:
    enabled: true
    keymap:
      "j": go_home              # Press "j" to trigger go_home command
```

> Key mapping is case-sensitive. `self.adapter` in `AdapterCommand` refers to the adapter
> instance; `self.config` refers to the command config dict (e.g., `{"joints": [0,0,0,0,0,0]}`).

## ConfigurableDeviceTranslator

The `ConfigurableDeviceTranslator` is the default translator type. It uses the `device_to_r2c`
and `r2c_to_device` sections in the robot config YAML to map fields — no code required.

### device_to_r2c: Device Observation → R2C Observation

```yaml
device_to_r2c:
  task: "pick the pen into the box"    # Task context string
  mappings:
    # Direct array mapping
    - target_key: "joint_states.position"
      source_paths: ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos"]
      # Concatenates multiple source fields into one array

    # Single source mapping
    - target_key: "joint_states.names"
      default: ["joint_1", "joint_2", "joint_3"]
      # Uses default if source not available

    # Image with transform
    - target_key: "images.color.front"
      source_path: "front"
      transforms: ndarray_to_jpeg
      # Converts numpy ndarray to JPEG bytes

    # Extension field (custom data)
    - target: "extensions.language_goal"
      source_path: "task_instruction"
      extension:
        dtype: STRING
        shape: []                   # Empty shape = scalar
```

### r2c_to_device: R2C Action → Device Action

```yaml
r2c_to_device:
  mappings:
    # Array index mapping
    - target: "shoulder_pan.pos"
      source: "joint_states.position"
      source_index: 0              # Take element 0 from joint_states.position array
      required: true               # Error if source field missing

    - target: "shoulder_lift.pos"
      source: "joint_states.position"
      source_index: 1
      required: true

    # Direct mapping (whole array)
    - target: "gripper_position"
      source: "gripper.position"
      required: false              # Optional, skip if missing
```

### Available Transforms

| Transform | Description |
|-----------|-------------|
| `ndarray_to_jpeg` | Convert numpy ndarray to JPEG-encoded bytes |
| `jpeg_to_ndarray` | Convert JPEG bytes back to numpy ndarray |
| (custom) | Register custom transforms via entry points |

## Custom Translator (Alternative)

If `ConfigurableDeviceTranslator` is insufficient, implement a custom translator:

```python
# my_pkg/my_translator.py

from cloudrobo_r2c.core.interfaces import IDeviceTranslator
from cloudrobo_r2c.common.models import Observations, Actions

class MyTranslator(IDeviceTranslator):
    def __init__(self, config: dict):
        self._config = config

    def device_to_r2c(self, device_obs: dict) -> Observations:
        """Convert device observation dict to R2C Observations protobuf."""
        obs = Observations()
        obs.joint_states.position.extend(device_obs["joint_positions"])
        # ... custom mapping logic
        return obs

    def r2c_to_device(self, action: Actions) -> dict:
        """Convert R2C Actions protobuf to device action dict."""
        return {
            "joint_positions": list(action.joint_states.position),
        }
```

Use with `--translator-class`:

```bash
cloudrobo r2c client --bundle <path/to/cert_config_*.zip> --robot-config config/my_robot_config.yaml --hardware-class my_pkg.my_adapter.MyRobotAdapter --translator-class my_pkg.my_translator.MyTranslator
```

## Dry-Run Testing

Always test custom adapters with `dry_run: true` first:

### Step 1: Syntax Check

```bash
# Validate the config
cloudrobo r2c validate-config --robot-config config/my_robot_config.yaml
```

### Step 2: Dry-Run Test

Set `runtime.dry_run: true` in the robot config, then start the client:

```bash
cloudrobo r2c client --bundle <path/to/cert_config_*.zip> --robot-config config/my_robot_config.yaml --log-level DEBUG --duration 60
```

Verify:
- Client starts without errors
- Observations are published (check logs for "publish_observations")
- Hardware adapter connects and reads observations
- If cloud sends actions, they are logged but NOT executed (dry_run mode)

### Step 3: Subscribe to Observations (Verification)

On the cloud side (or another terminal), subscribe to the robot's observation topic to
verify data is flowing:

```python
# Quick verification script
from cloudrobo_r2c.client import R2CClient
session = R2CClient.connect("<bundle_path>")
session.subscribe_observations(
    callback=lambda obs: print(f"Received: {obs.id}"),
    target_device_id="<device_id>",
)
import time; time.sleep(60)
```

### Step 4: Publish Test Action

Send a test action to verify the translator and (in non-dry_run mode) hardware execution:

```python
from cloudrobo_r2c.client import R2CClient
from cloudrobo_r2c.common.models import Actions

session = R2CClient.connect("<bundle_path>")
action = Actions()
action.joint_states.position.extend([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
session.publish_actions(action)
```

### Step 5: Disable Dry-Run

Set `runtime.dry_run: false` and restart. Verify the robot moves correctly.

## Cloud Adapter Pattern

The cloud adapter (`r2c cloud-adapter`) subscribes to observations, calls OpenPI for
inference, and publishes actions. For custom cloud-side logic (non-OpenPI models), implement
a custom policy client:

```python
# my_cloud_adapter.py

from cloudrobo_r2c.inference.r2c_cloud_adapter import R2CCloudAdapter, R2CCloudAdapterConfig

class MyPolicyClient:
    def infer(self, policy_input):
        # Custom model inference
        return {"action": model_predict(policy_input)}

# Use custom policy client instead of OpenPI WebsocketClientPolicy
adapter = R2CCloudAdapter(
    session=session,
    config=R2CCloudAdapterConfig(openpi_host="", cloud_config_path="config/cloud_config.yaml"),
    policy_client=MyPolicyClient(),
)
adapter.start()
```

### Cloud Config (cloud_config.yaml)

```yaml
schema_version: "v2.2"
service_name: "r2c_policy_runtime"

runtime:
  backend: "openpi"          # openpi (websocket) or local (TorchScript)

openpi:
  host: "ws://127.0.0.1"
  port: 8000
  api_key: ""

model:
  type: "lerobot_act"
  policy_type: "act"
  pretrained_model:
    path: "/path/to/model"
  device: "cuda:0"
  fp16_inference: true
  use_pre_post_processors: true
  action_chunk_size: 50

# Up: Observations -> Model Input
r2c_to_model:
  mappings:
    - source_path: "images.color.front"
      target_key: "observation.images.front"
      transforms: ["jpeg_to_ndarray"]
      required: false
    - source_path: "joint_states.position"
      target_key: "observation.state"
      required: true
    - source_path: "task"
      target_key: "task"

# Down: Model Output -> Actions
model_to_r2c:
  mappings:
    - source_tensor: "action"
      target_key: "joint_states.position"
      slice_start: 0
      slice_end: 6
      dtype: "float32"
```

## Best Practices

- **Prefer entry-point registration for reusable adapters**: If the adapter will be used
  across projects or shared with other teams, register it as an entry point in `pyproject.toml`
  under `[project.entry-points."r2c_sdk.adapters"]`. Use `--hardware-class` for quick prototyping.
- **Start with dry_run**: Always test with `dry_run: true` to verify observation publishing
  without risking robot damage.
- **Use ConfigurableDeviceTranslator**: Prefer config-driven mapping over custom translator
  code. Only implement a custom translator when the mapping logic is too complex for YAML.
- **Validate config first**: Run `cloudrobo r2c validate-config` before starting the client
  to catch schema errors early.
- **Handle exceptions in get_observation/send_action**: The control loop calls these methods
  at high frequency; unhandled exceptions will crash the client.
- **Log adapter state**: Use Python `logging` for debug info; the client's `--log-level DEBUG`
  will surface adapter logs.
- **Clean up in disconnect**: Close TCP connections, release hardware resources, and move to
  a safe position in `disconnect()`.
- **Test with dummy adapter first**: Use `robot_dummy_config.yaml` to verify the full
  data-plane pipeline (client → Zenoh → cloud adapter) before connecting real hardware.
- **Use commands for reusable actions**: Register command classes via `register_command_class()`
  for actions that should be triggerable via keyboard or CLI (e.g., `go_home`, `get_state`).
