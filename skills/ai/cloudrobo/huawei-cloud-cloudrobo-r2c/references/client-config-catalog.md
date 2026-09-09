# Client Config Reference

## client_config.yaml

The client config YAML defines Zenoh connection parameters, QoS settings, and authentication.
It is used when `--bundle` is not provided (or as a fallback). When `--bundle` is provided,
the bundle's `zenoh.json` takes precedence.

```yaml
# Robot to Cloud SDK Client Configuration

# Tenant and device identity
project_id: "project-demo"
device_id: "so101"
client_id: "python-client-001"

# Zenoh connection configuration
endpoints: ["tcp/127.0.0.1:7447"]  # Recommended: Zenoh Router address

# Connection mode
# peer:   supports LAN P2P direct connection (recommended)
# client: routes through Zenoh Router only, suitable for strict firewalls or low-resource devices
mode: "client"

# Protocol selection (currently only zenoh supported)
protocol: "zenoh"

# Endpoint role: "connect" (active, default) or "listen" (passive)
endpoint_role: "connect"

# Publisher QoS configuration
publisher_reliability: "RELIABLE"               # RELIABLE / BEST_EFFORT
publisher_congestion_control: "DROP"            # BLOCK / DROP
publisher_priority: "REAL_TIME"                 # REAL_TIME / INTERACTIVE / DATA / BACKGROUND
publisher_reliability_by_message:
  observations: "RELIABLE"
  actions: "RELIABLE"
  joint_states: "BEST_EFFORT"
  end_effector_states: "BEST_EFFORT"
  localization_states: "BEST_EFFORT"
  imu_states: "BEST_EFFORT"
  heartbeats: "BEST_EFFORT"
publisher_congestion_control_by_message:
  observations: "DROP"
  actions: "DROP"

# Subscriber handler per message type. handler: callback (default) / fifo / ring.
# When fifo or ring is used, capacity must be set (>0).
subscriber_handler_by_message: {}
subscriber_handler_capacity_by_message: {}

# Predeclare key expressions for latency reduction
predeclare_keyexpr_enabled: false
predeclare_keyexpr_by_message: []

# Authentication configuration (optional)
# authentication:
#   method: "user_password"
#   credential_path: "/path/to/secret"

# TLS / mTLS configuration (used when not using a --bundle)
# tls:
#   enabled: true
#   root_ca_certificate: "ca.pem"          # or root_ca_certificate_base64
#   enable_mtls: true
#   connect_certificate: "server_cert.pem"   # or connect_certificate_base64
#   connect_private_key: "server_key.pem"  # or connect_private_key_base64
#   verify_name_on_connect: true
#   close_link_on_expiration: true

# Zenoh connect-specific runtime options
# connect:
#   endpoints: ["tls/127.0.0.1:7447"]      # takes precedence over top-level endpoints
#   exit_on_failure: true
#   timeout_ms: 5000
```

## Field Reference

### Identity Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `project_id` | string | Yes (if no bundle) | — | Project/tenant ID for topic namespacing |
| `device_id` | string | Yes (if no bundle) | — | Device/robot ID for topic namespacing |
| `client_id` | string | No | auto-generated | Client instance identifier; with a bundle defaults to `python-client-<device>-<host>`, with explicit params to `sync-robot-client` |

### Zenoh Connection Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `endpoints` | list[string] | No | `[]` | Zenoh router endpoints, e.g. `["tls/127.0.0.1:7447"]` |
| `mode` | string enum | No | `peer` | `peer` (P2P) or `client` (router-only) |
| `protocol` | string | No | `zenoh` | Transport protocol (only `zenoh` supported) |
| `endpoint_role` | string enum | No | `connect` | `connect` (active) or `listen` (passive) |

### QoS Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `publisher_reliability` | string | `RELIABLE` | Default reliability for all messages |
| `publisher_congestion_control` | string | `DROP` | Default congestion control for all messages |
| `publisher_priority` | string | `REAL_TIME` | Default Zenoh priority (`REAL_TIME`/`INTERACTIVE`/`DATA`/`BACKGROUND`) |
| `publisher_reliability_by_message` | dict | — | Per-message-type reliability override |
| `publisher_congestion_control_by_message` | dict | — | Per-message-type congestion control override |
| `publisher_priority_by_message` | dict | — | Per-message-type priority override (observations/actions=`REAL_TIME`, joint/ee/local/imu=`DATA`, heartbeats=`BACKGROUND`) |

### Subscriber Handler Fields (optional)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `subscriber_handler_by_message` | dict | `{}` | Per-message-type handler: `callback` (default) / `fifo` / `ring` |
| `subscriber_handler_capacity_by_message` | dict | `{}` | Per-message-type capacity; required (>0) when handler is `fifo`/`ring` |

### Predeclare Key Expression Fields (optional)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `predeclare_keyexpr_enabled` | bool | `false` | Enable predeclaration of key expressions (latency reduction) |
| `predeclare_keyexpr_by_message` | list[string] | `[]` | Message types whose key expressions are predeclared |

### connect (Zenoh runtime) — optional

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `connect.endpoints` | list[string] | `[]` | Connect endpoints; takes precedence over top-level `endpoints` |
| `connect.exit_on_failure` | bool | `None` | Exit if connection fails |
| `connect.timeout_ms` | int | `None` | Connection timeout in milliseconds (>=0) |

### tls (TLS/mTLS) — optional

| Field | Type | Description |
|-------|------|-------------|
| `tls.enabled` | bool | Enable TLS (must be true if `enable_mtls` is true) |
| `tls.root_ca_certificate` / `root_ca_certificate_base64` | string | CA cert file path or base64 content |
| `tls.enable_mtls` | bool | Enable mutual TLS (requires cert + private key) |
| `tls.connect_certificate` / `connect_certificate_base64` | string | Client cert (endpoint_role=`connect`) |
| `tls.connect_private_key` / `connect_private_key_base64` | string | Client private key (endpoint_role=`connect`) |
| `tls.listen_certificate` / `listen_certificate_base64` | string | Listener cert (endpoint_role=`listen`) |
| `tls.listen_private_key` / `listen_private_key_base64` | string | Listener private key (endpoint_role=`listen`) |
| `tls.verify_name_on_connect` | bool | Verify peer name on connect |
| `tls.close_link_on_expiration` | bool | Close link on certificate expiration |

> mTLS endpoints must use the `tls/` scheme. When using `--bundle`, all TLS material is taken
> from the bundle — the `tls` section is only for `--client-config` (no bundle) mode.

### Message Types for QoS

| Message Type | Default Reliability | Default Congestion Control | Description |
|--------------|---------------------|-----------------------------|-------------|
| `observations` | RELIABLE | DROP | Robot sensor observations (images, joint states) |
| `actions` | RELIABLE | DROP | Cloud-sent actions for robot execution |
| `joint_states` | BEST_EFFORT | — | Joint position/velocity states |
| `end_effector_states` | BEST_EFFORT | — | End effector pose states |
| `localization_states` | BEST_EFFORT | — | Robot localization/position states |
| `imu_states` | BEST_EFFORT | — | IMU sensor data |
| `heartbeats` | BEST_EFFORT | — | Connection health heartbeats |

### Authentication Fields (optional)

| Field | Type | Description |
|-------|------|-------------|
| `authentication.method` | string | Auth method (e.g., `user_password`) |
| `authentication.credential_path` | string | Path to credential file |

> When using `--bundle`, authentication is handled via mTLS certificates in the bundle. The
> `authentication` section in client_config.yaml is for alternative auth methods.

## Endpoint Format

Endpoints use the Zenoh endpoint format: `<protocol>/<host>:<port>`

| Protocol | Description | Example |
|----------|-------------|---------|
| `tcp` | Plain TCP | `tcp/127.0.0.1:7447` |
| `tls` | TLS encrypted (recommended) | `tls/cloudrobo-router.myhuaweicloud.com:7447` |

Multiple endpoints can be comma-separated on the CLI (`--endpoints tls/host1:7447,tls/host2:7447`)
or listed in YAML (`endpoints: ["tls/host1:7447", "tls/host2:7447"]`).

## Connection Mode Comparison

| Mode | Description | Use Case |
|------|-------------|----------|
| `peer` | P2P direct connection with LAN optimization | Recommended for most scenarios; supports direct peer discovery |
| `client` | Router-only mode; all traffic via Zenoh router | Strict firewalls, low-resource devices, or when P2P is not possible |

## Zenoh Topic Format

All R2C messages are published/subscribed on Zenoh topics with the format:

```text
{project_id}/{device_id}/{message_path}
```

| Message Path | Direction | Content |
|--------------|-----------|---------|
| `observations` | Robot → Cloud | Sensor observations (images, joint states, etc.) |
| `actions` | Cloud → Robot | Action commands for robot execution |
| `joint_states` | Robot → Cloud | Joint position/velocity data |
| `end_effector_states` | Robot → Cloud | End effector pose data |
| `localization_states` | Robot → Cloud | Robot localization data |
| `imu_states` | Robot → Cloud | IMU sensor readings |
| `heartbeats` | Robot → Cloud | Connection health heartbeat |

## CLI Override Behavior

When both `--client-config` and explicit CLI parameters are provided, CLI parameters override
config file values:

| CLI Parameter | Overrides Config Field |
|---------------|----------------------|
| `--project-id` | `project_id` |
| `--device-id` | `device_id` |
| `--client-id` | `client_id` |
| `--endpoints` | `endpoints` |
| `--mode` | `mode` |
| `--endpoint-role` | None — NOT forwarded to `--client-config`; it is only used in the no-bundle/no-config branch. The YAML `endpoint_role` field is read directly. To set the role with `--client-config`, set `endpoint_role` in the YAML |
