---
name: huawei-cloud-ascend-remote-connect
description: |
  Provides temporary SSH remote connection for Huawei Cloud Ascend devices with dynamic host/port/user/password input (in-memory only), disk management, NPU monitoring, container management, security auditing and log analysis; sensitive operations require user confirmation before execution
  Use this skillthis skill to remotely connect to Ascend servers, monitor NPU health, manage disks/LVM, or troubleshoot Ascend devices.
  Triggerer words: SSH, remote, Ascend, NPU, 远程连接, 昇腾, NPU监控
version: 1.0.0
tags: [huawei-cloud, ascend, npu, ssh, remote]
allowed-tools:
  - python3
  - bash
  - ssh
---

# Huawei Cloud Ascend Remote Connection

## Overview

Provides temporary SSH remote connection capability for Huawei Cloud Ascend devices. Supports simultaneous connection to multiple machines. All sensitive operations (delete, modify, move, etc.) require user confirmation before execution. Passwords are only stored in memory and destroyed after session ends.

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Interaction Layer                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Natural Language Commands / CLI Arguments                  │    │
│  │  (connect, execute, monitor, disconnect)                   │    │
│  └────────────────────────────┬────────────────────────────────┘    │
│                               │                                     │
│                               ▼                                     │
├────────────────────────────────┼─────────────────────────────────────┤
│                      Skill Core Components                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │ Session Manager │←→│ Command Executor│←→│   SSH Client    │      │
│  │  - Connection   │  │  - NL Parsing   │  │  - paramiko     │      │
│  │  - Pooling      │  │  - Validation   │  │  - ControlMaster│      │
│  │  - Timeout Mgmt │  │  - Execution    │  │  - Key/Cert Auth│      │
│  └─────────────────┘  └─────────────────┘  └────────┬────────┘      │
│         │                      │                     │               │
│         │                      │                     ▼               │
│         │                      │         ┌─────────────────┐        │
│         │                      │         │ Command Validator│        │
│         │                      │         │  - Blocked Cmds  │        │
│         │                      │         │  - Confirm Req   │        │
│         │                      │         └─────────────────┘        │
│         │                      │                                     │
│         ▼                      ▼                                     │
├────────────────────────────────┼─────────────────────────────────────┤
│                    Huawei Cloud Ascend Infrastructure               │
│                          (Remote Target Servers)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │   Ascend NPU    │  │    OS Services  │  │    Containers   │      │
│  │  - npu-smi      │  │  - systemctl    │  │  - docker       │      │
│  │  - Driver       │  │  - journalctl   │  │  - k8s          │      │
│  │  - FW Upgrade   │  │  - Network Mgmt │  │  - Pods         │      │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘      │
│                                                                      │
│  Data Flow: User → Skill → SSH Tunnel → Target Server → Response    │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Relationships

| Component | Responsibility | Key Features |
|-----------|----------------|--------------|
| **Session Manager** | Manage SSH connections | Connection pooling, timeout management, lifecycle control |
| **Command Executor** | Process user commands | Natural language parsing, command routing, result formatting |
| **SSH Client** | Establish secure tunnels | paramiko integration, ControlMaster, authentication |
| **Command Validator** | Security enforcement | Blocked commands list, confirmation requirements |

### Cloud Service Integration

- **Ascend NPU Management**: Direct access to npu-smi for monitoring and management
- **Huawei Cloud Infrastructure**: Secure SSH access to cloud servers and containers
- **Security Compliance**: Memory-only credential storage, session isolation

## Prerequisites

### System Requirements

- Python 3.8+
- paramiko >= 3.4.0

### Environment Check

> **Prerequisite check: Python3 + paramiko required**
> ```bash
> python3 --version  # Python3 >= 3.8
> python3 -c "import paramiko; print('OK')"  # SSH library
> ```
> If not installed: `pip3 install --user paramiko cryptography`

## Authentication

> **Security rules (must be followed):**
> - **Prohibited** from reading, echoing, or printing password values
> - **Prohibited** from asking the user to input passwords directly in the conversation
> - **Only allowed** to read credentials from command line arguments

## Parameter Confirmation

### Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| host | Yes | Target server IP address |
| port | No | SSH port (default: 22) |
| user | Yes | SSH username |
| password | Yes | SSH password |

### Parameter Validation

- IP address format: IPv4 (e.g., 192.168.1.100)
- Port range: 1-65535
- Username: alphanumeric and underscore
- Password: non-empty string

### Confirmation Requirements

The following operations require explicit user confirmation:
- Delete: rm, rmdir
- Format: mkfs, fdisk -d, parted rm
- Unmount: umount
- Reboot: reboot, shutdown, init 6
- Shutdown: poweroff, halt, init 0
- User delete: userdel, groupdel
- Permission change: chmod -R, chown -R

## IAM Permission Policies

Ensure the target server has SSH service enabled and the provided credentials have appropriate permissions.

**Minimum required permissions on target server:**
- SSH access (port 22 or custom)
- Sudo privileges for system management operations

## Core Workflow

### Task 1: Establish SSH Connection

```bash
python3 scripts/main.py --host <ascend-server-ip> --port 22 --user root --password <your-password> --command "npu-smi info"
```

### Task 2: Interactive Mode

```bash
python3 scripts/main.py
```

## Usage Instructions

### Connect to Ascend Server

```
SSH connect to 192.168.1.100 port 22 as root with password xxx
```

### Execute Commands

#### NPU Monitoring
```
npu-smi info
Check NPU status
NPU health check
```

#### System Management
```
Check CPU and memory
df -h
top -bn1
```

#### Connection Management
```
Show current connections
Switch to 192.168.1.101
Disconnect SSH
```

---

## Output Format

### Standard Response Format

All command outputs follow a structured format:

```
┌─────────────────────────────────────────┐
│ Target: <host>:<port>                   │
│ Command: <executed-command>             │
│ Exit Code: <0-success/non-zero-fail>    │
├─────────────────────────────────────────┤
│ STDOUT:                                │
│ <command-output>                        │
├─────────────────────────────────────────┤
│ STDERR:                                 │
│ <error-output>                          │
├─────────────────────────────────────────┤
│ Duration: <seconds>s                     │
└─────────────────────────────────────────┘
```

### Error Response Format

```
[ERROR] <error-code>
Message: <error-description>
Suggestion: <troubleshooting-tip>
```

### Success Indicators

- Exit Code: 0
- STDOUT: Contains expected output
- STDERR: Empty or contains only warnings

---

## Verification Method

### Basic Verification Steps

1. **Environment Check**
   ```bash
   python3 --version  # Verify Python 3.8+
   python3 -c "import paramiko"  # Verify paramiko installed
   ```

2. **Connection Test**
   ```bash
   python3 scripts/main.py --host <test-ip> --port 22 --user root --password <test-pwd> --command "echo test"
   ```

3. **NPU Monitoring Test**
   ```bash
   python3 scripts/main.py --host <ascend-ip> --user root --password <pwd> --command "npu-smi info"
   ```

### Expected Results

| Test Case | Expected Output |
|-----------|----------------|
| Environment check | Python version >= 3.8, paramiko import success |
| Connection test | Exit code 0, "test" in stdout |
| NPU info | NPU device information displayed |

See [references/verification-method.md](references/verification-method.md) for detailed verification procedures.

---

## Script Files

### Entry File

- **main.py**: Skill entry file (required)
  - Function: Provide interactive menu, unified entry point
  - Menu options:
    - Establish SSH connection
    - Execute commands
    - Disconnect

### Core Scripts

- **executor.py**: Command executor (main entry)
  - Function: Parse user input, dispatch commands to corresponding handlers
  - Core methods:
    - `handle_command(text)`: Command dispatch entry
    - `_connect(info)`: Establish SSH connection
    - `_detect_disks()`: Detect unmounted disks
    - `_handle_auto_mount(text)`: Configure auto-mount on boot
    - `_confirm_disk_merge(info)`: Disk merge confirmation

- **session_manager.py**: Session manager
  - Function: Manage multiple concurrent SSH sessions
  - Core methods:
    - `create_session(host, port, username, password)`: Create new session
    - `execute_command(command)`: Execute command in active session
    - `switch_session(host)`: Switch to specified host session
    - `close_session()`: Close current session
    - `get_session_info()`: Get all session information

- **ssh_client.py**: SSH client
  - Function: Low-level SSH connection implementation, supports password and key authentication
  - Core methods:
    - `connect()`: Establish SSH connection
    - `exec_command(command)`: Execute remote command
    - `close()`: Close connection

- **command_validator.py**: Command validator
  - Function: Security layer, filter dangerous commands
  - Validation rules:
    - Blocklist: Direct block (e.g., fork bomb)
    - Sensitive: Require confirmation (e.g., rm -rf, reboot)
    - Allowlist: Direct execution (e.g., ls, cat, df)

---

## Supported Features

### NPU Management
- NPU status monitoring (npu-smi)
- NPU health check
- NPU configuration viewing

### Disk Management
- Disk detection
- LVM merging
- Partition mounting
- Auto-mount on boot
- Disk health check
- Free space check

### System Management
- CPU/Memory/Disk monitoring
- System updates
- User/permission management
- Cron job management

### Network Management
- Port scanning
- Firewall configuration
- Route viewing
- Network interface configuration
- DNS troubleshooting

### Container Management
- Docker installation and management
- Image management
- Container management
- Log viewing
- Docker Compose operations

### Security Management
- Login auditing
- SSH key management
- High-risk command blocking

### Log Management
- System logs
- Application log analysis
- Error troubleshooting

### File Operations
- Upload/download
- Copy/transfer
- Change permissions
- Create/delete

---

## Connection Pool Management

### Features
- **Connection Reuse**: Reuse same connection for same target, avoid repeated handshakes
- **Auto Disconnect**: Auto disconnect after 10 minutes idle (configurable)
- **Thread Safe**: Support multi-thread concurrent access
- **Status Query**: View connection pool status and idle time

### Protection Mechanisms
- **Max Connections Limit**: Default 50, supports multi-target machines
- **Request Rate Limiting**: Default max 200 concurrent requests
- **Connection Timeout**: Default 10 seconds
- **Execute Timeout**: Default 60 seconds
- **Health Check**: Check connection status every 30 seconds, auto disconnect bad connections

```python
# Using connection pool
from ssh_client import get_pool

pool = get_pool()
result = pool.execute(conn_info, 'ls -la')

# View pool status (includes statistics)
status = pool.get_pool_status()
# {
#   'connections': [...],
#   'total_connections': 2,
#   'max_connections': 10,
#   'max_concurrent_requests': 5,
#   'statistics': {'total_requests': 100, 'failed_requests': 2, ...}
# }

# Configure protection parameters
pool.configure(
    max_connections=20,           # Max connections
    max_concurrent_requests=10,   # Max concurrent requests
    idle_timeout=300,             # Idle timeout (seconds)
    connect_timeout=15,           # Connection timeout (seconds)
    execute_timeout=120           # Execute timeout (seconds)
)
```

---

## Multi-Machine Connection

Support simultaneous connection to multiple machines, distinguished by IP address:

```
SSH connect to 192.168.1.100 port 22 as root with password xxx
SSH connect to 192.168.1.101 port 2222 as admin with password yyy
```

### Switch Target
```
Switch to 192.168.1.101
```

### View Current Connections
```
View current connections
```

---

## Security Mechanisms

### Sensitive Operation Confirmation
The following operations require user confirmation:
- Delete: rm, rmdir
- Format: mkfs, fdisk -d, parted rm
- Unmount: umount
- Reboot: reboot, shutdown, init 6
- Shutdown: poweroff, halt, init 0
- User delete: userdel, groupdel
- Permission change: chmod -R, chown -R

### High-Risk Command Blocking
The following commands are blocked by default:
- `:(){ :|:& };:` (fork bomb)
- Direct disk formatting commands

### Password Security
- Passwords only stored in memory
- Immediately cleared after session ends
- Not written to any configuration file or log

---

## Best Practices

### Connection Management

1. **Reuse Connections**: Connection pool automatically reuses existing connections
2. **Timeout Settings**: Adjust timeouts based on network conditions
3. **Idle Timeout**: Default 10 minutes; set shorter for frequent disconnects

### Security Recommendations

1. **Use Key Authentication**: Prefer SSH keys over passwords when possible
2. **Limit Permissions**: Grant minimum sudo privileges needed
3. **Monitor Sessions**: Regularly check active connections
4. **Log Auditing**: Review login logs periodically

### Performance Optimization

1. **Batch Commands**: Group related commands to reduce connection overhead
2. **Connection Pool Tuning**: Adjust pool size based on concurrent needs
3. **Command Timeout**: Set appropriate timeout values for long-running commands

---

## Notes

### Security Warnings

⚠️ **Credential Handling**:
- Never log or display passwords
- Clear credentials from memory after use
- Use SSH keys for production environments

⚠️ **High-Risk Operations**:
- Always confirm destructive operations (rm, mkfs, reboot)
- Blocked commands cannot be bypassed
- Review security mechanisms before deployment

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection timeout | Network/firewall | Check network connectivity |
| Authentication failed | Wrong credentials | Verify username/password |
| Command blocked | Security policy | Review command validator rules |
| Pool exhausted | Too many connections | Increase max_connections |

### Limitations

- SSH password authentication only (no interactive password prompt)
- Single-user session per connection
- Maximum 50 concurrent connections (configurable)

---

## Troubleshooting

### Connection Failed
- Check if IP address and port are correct
- Check if firewall allows the port
- Check if username and password are correct
- Check if SSH service is running on target host

### Command Execution Failed
- Check if command syntax is correct
- Check if there is an active connection
- Check if command is blocked by security policy

### Disk Merge Failed
- Check if disk is occupied by other processes
- Check if LVM tools are installed
- Check if disk is already mounted

---

## Directory Structure

```
huawei-cloud-ascend-remote-connect/
├── SKILL.md              # Skill definition entry file (required)
├── scripts/              # Scripts directory (required)
│   ├── __init__.py       # Module export
│   ├── main.py           # Skill entry script (required)
│   ├── executor.py       # Command executor
│   ├── session_manager.py # Session manager
│   ├── ssh_client.py     # SSH client implementation
│   └── command_validator.py # Command validator
└── references/           # Reference documentation directory
    ├── troubleshooting.md # Troubleshooting guide
    ├── verification-method.md # Verification steps
    └── iam-policies.md   # IAM policies
```

---

## References

| Document | Description |
|----------|-------------|
| [references/troubleshooting.md](references/troubleshooting.md) | Troubleshooting guide |
| [references/verification-method.md](references/verification-method.md) | Verification steps |
| [scripts/main.py](scripts/main.py) | Main entry script |

**Author**: huawei-cloud
