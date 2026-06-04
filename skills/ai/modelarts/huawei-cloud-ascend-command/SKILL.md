---
name: huawei-cloud-ascend-command
description: |
  Huawei Ascend NPU natural language management skill, supporting both local direct connection and SSH remote modes. Provides comprehensive npu-smi command capabilities including device queries, configuration management, firmware upgrade, vNPU virtualization, certificate management, and compute power testing (FLOPS). Enables remote management and monitoring of Ascend NPU devices with real-time metrics tracking.
  Use this skill when the user wants to: (1) query NPU device status and health, (2) monitor temperature, power, memory/HBM utilization, (3) configure ECC settings and fan modes, (4) perform firmware upgrades, (5) manage vNPU virtualization, (6) run compute power tests, (7) check certificate information.
  Trigger: user mentionsnpu', 'ascend', 'NPU', 'Ascend', 'temperature', 'power', 'HBM', 'firmware', 'upgrade', 'vNPU', 'virtualization', 'certificate', 'FLOPS', 'compute', 'health', 'memory', 'utilization', 'ECC', 'fan', '昇腾', '昇腾卡', '昇腾状态', '显存', '算力', '设备查询', 'NPU监控'"
version: 1.0.0
tags: [huawei-cloud, ascend, npu, npu-smi, remote]
allowed-tools:
  - python3
  - bash
  - ssh
---
Provides Huawei Ascend NPU natural language command translation and execution. Supports full npu-smi commands: device queries, configuration management, firmware upgrade, vNPU virtualization, certificate management, and compute power testing.

## Overview

This skill provides natural language management for Huawei Ascend NPU devices via npu-smi commands. Supports both local direct execution and SSH remote modes.

**Related Skills**:
- `huawei-cloud-ascend-remote-connect` - General SSH remote operations (disk, Docker, logs, processes)
- `npu-smi-skill` - Alternative NPU management implementation
- `model-deploy-test-skill` - Model deployment and testing on Ascend DevServer

**Capabilities**:
- Device queries (health, temperature, power, HBM, ECC, topology)
- Configuration management (ECC, fan mode, fan speed)
- Firmware upgrade and status
- vNPU virtualization
- Certificate management
- Compute power testing (FLOPS)

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent Orchestration                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  1. Parse user intent → Match Trigger keywords                        │    │
│  │  2. Prepare params → host, user, password explicit                 │    │
│  │  3. Invoke Skill → skill exec --name ascend-command            │    │
│  │  4. Return result → User                                          │    │
│  └────────────────────────────┬────────────────────────────────┘    │
│                               │ Explicit param passing (Rule 1)                │
│                               ▼                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        User Interaction Layer                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Natural Language Commands / CLI Arguments                  │    │
│  │  (NPU health check, temperature, firmware upgrade)          │    │
│  └────────────────────────────┬────────────────────────────────┘    │
│                               │                                     │
│                               ▼                                     │
├─────────────────────────────────────────────────────────────────────┤
│                      Skill Core Components (Stateless (Rule 2))           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │ Command Executor│←→│   NPU Client    │←→│ Trend Recorder  │      │
│  │  - NL Parsing   │  │  - npu-smi cmd  │  │  - Metric Log   │      │
│  │  - Command Route│  │  - Local/SSH    │  │  - Trend Analysis│      │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘      │
│         │                      │                                     │
│         ▼                      ▼                                     │
├─────────────────────────────────────────────────────────────────────┤
│                    Huawei Cloud Ascend Infrastructure               │
│  Data Flow: Agent → Skill(host,user,pwd) → SSH → npu-smi → Response │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Orchestration Flow

```
User request: "Query NPU status on 116.204.23.145"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent parses intent                                               │
│   - Keyword "NPU" → Match ascend-command                       │
│   - IP address → SSH params needed                                  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent prepares params (explicit, Rule 1)                              │
│   --host 116.204.23.145                                      │
│   --user root                                                │
│   --password ***                                             │
│   --command "NPU list"                                       │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Skill executes (Stateless, Rule 2)                                    │
│   - NpuClient(host, user, password) explicit receive                 │
│   - Execute npu-smi command                                        │
│   - Return result                                                 │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
      Return to user
```

### Related Skills (Agent orchestrated, no direct call, Rule 3)

| Skill | Purpose | Orchestration Scenario |
|-------|------|----------|
| `huawei-cloud-ascend-remote-connect` | SSH remote ops | Agent selects when user needs disk/Docker/logs |
| `npu-smi-skill` | NPU management | Alternative impl, Agent selects by scenario |
| `model-deploy-test-skill` | Model deploy | Use ascend-command to monitor NPU after deploy |

**Note**: No direct calls between Skills, orchestrated by Agent based on user intent.

## Prerequisites

### System Requirements

- Python 3.8+
- Pure Python standard library implementation, no additional dependencies required

### Environment Check

> **Prerequisite check: Python3 required**
> ```bash
> python3 --version  # Python3 >= 3.8
> ```

## Authentication

> **Security rules (must be followed):**
> - **Prohibited** from reading, echoing, or printing password values
> - **Prohibited** from asking the user to input passwords directly in the conversation
> - **Only allowed** to read credentials from command line arguments

## Parameter Confirmation

### Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| command | Yes (one-shot) | Natural language command to execute |
| host | No | SSH remote host IP address |
| user | No | SSH username |
| password | No | SSH password |

### Confirmation Requirements

The following operations require explicit user confirmation:
- ECC enable/disable
- Fan mode changes
- Firmware upgrade
- vNPU creation/deletion
- Certificate management

## Core Workflow

### Task 1: One-Shot Command Execution

```bash
python3 scripts/main.py --command "NPU health check"
```

### Task 2: SSH Remote Execution

```bash
python3 scripts/main.py --command "NPU list" --host 192.168.1.100 --user root --password xxx
```

### Task 3: Interactive Mode

```bash
python3 scripts/main.py
```

## Usage Instructions

### Device Queries

```
List all NPU devices
NPU health check
Get NPU temperature
Get NPU power usage
Get NPU memory info
```

### Configuration Management

```
Set ECC mode
Set fan mode
```

### Firmware Upgrade

```
Query firmware version
Upgrade firmware
```

### Virtualization

```
Query vNPU info
Create vNPU
```

### FLOPS Test

```
Run FLOPS test
Run FP32 FLOPS test
Run multi-device FLOPS test
```

---

## Output Format

### Standard Response Format

All command outputs follow a structured format:

```json
{
  "status": "success",
  "command": "npu-smi info -l",
  "description": "List all NPU devices"
}
```

### Error Response Format

```
[ERROR] <error-code>
Message: <error-description>
Suggestion: <troubleshooting-tip>
```

---

## Verification Method

### Basic Verification Steps

1. **Environment Check**
   ```bash
   python3 --version  # Verify Python 3.8+
   ```

2. **Local Command Test**
   ```bash
   python3 scripts/main.py --command "NPU list"
   ```

3. **Remote Command Test**
   ```bash
   python3 scripts/main.py --host <ascend-ip> --user root --password <pwd> --command "NPU health check"
   ```

### Expected Results

| Test Case | Expected Output |
|-----------|----------------|
| Environment check | Python version >= 3.8 |
| Local command | NPU device information or "npu-smi not found" |
| Remote command | NPU status from remote server |

---

## Script Files

### Entry File

- **main.py**: Skill entry file (required)
  - Function: Provide interactive mode, one-shot mode, SSH remote mode
  - Supports: Command line arguments, interactive prompt

### Core Scripts

- **executor.py**: NPU command executor (main entry)
  - Function: Natural language parsing, command routing, sensitive operation confirmation
  - Supported commands: Device queries, configuration, firmware upgrade, virtualization, certificate management
  - Core methods: `handle_command(text)`, `confirm_sensitive()`

- **npu_client.py**: NPU client
  - Function: Wraps npu-smi command execution, supports local and SSH remote execution
  - Core methods: `list_devices()`, `get_health()`, `get_temperature()`, `get_power()`, `get_memory()`, `set_ecc_enable()`, `upgrade_query()`, `create_vnpu()`, `get_tls_cert()`
  - Optimization: SSH ControlMaster, batch execution, parallel FLOPS testing

---

## Command Translation Mapping

### Device Queries

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| List all NPU devices | `npu-smi info -l` | List all NPU devices |
| NPU card info | `npu-smi info -m` | Card and chip mapping |
| NPU info | `npu-smi info` | Full NPU information |

### Health Check

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| NPU health check | `npu-smi info -t health -i 0` | Check device health |
| Check NPU status | `npu-smi info -t health -i 0` | Check device health |

### Temperature/Power/Memory

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| NPU temperature | `npu-smi info -t temp -i 0 -c 0` | Get temperature |
| NPU power | `npu-smi info -t power -i 0 -c 0` | Get power usage |
| NPU memory | `npu-smi info -t memory -i 0 -c 0` | Get memory info |
| NPU utilization | `npu-smi info -t usages -i 0 -c 0` | Get utilization |

### Configuration

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| Set ECC | `npu-smi set -t ecc-enable -i 0 -c 0 -d 1` | Enable ECC (requires confirmation) |
| Set fan mode | `npu-smi set -t pwm-mode -d 0` | Set fan mode (requires confirmation) |

### Firmware Upgrade

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| Firmware version | `npu-smi upgrade -b mcu -i 0` | Query firmware version |
| Upgrade firmware | `npu-smi upgrade -t mcu -i 0 -f file.hpm` | Upload firmware (requires confirmation) |

### Virtualization

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| vNPU info | `npu-smi info -t info-vnpu -i 0 -c 0` | Query vNPU info |
| Template info | `npu-smi info -t template-info -i 0` | Query template info |
| Create vNPU | `npu-smi set -t create-vnpu -i 0 -c 0 -f vir04` | Create vNPU (requires confirmation) |

### Certificate Management

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| Certificate info | `npu-smi info -t tls-cert -i 0 -c 0` | View TLS certificate |
| Certificate expiration | `npu-smi info -t tls-cert-period -i 0 -c 0` | Query certificate expiration threshold |

### FLOPS Test (ascend-dmi)

**Default behavior: single device FP16, fast return (~2 seconds)**

| Natural Language | Command | Description |
|-----------------|---------|-------------|
| FLOPS test | `ascend-dmi -f -d 0 -t fp16 -q` | Default: NPU 0, FP16 |
| NPU FLOPS | `ascend-dmi -f -d 0 -t fp16 -q` | Same as above |
| NPU 3 FLOPS | `ascend-dmi -f -d 3 -t fp16 -q` | Specify NPU 3 |
| FP32 FLOPS | `ascend-dmi -f -d 0 -t fp32 -q` | FP32 precision |
| All devices FLOPS | 8 devices async parallel | All NPUs tested simultaneously |

**Execution strategy:**
- **Single device**: Direct execution, ~2 seconds return
- **Multi-device**: Async parallel execution, total ~2 seconds (not serial 16 seconds)
- **Precision**: Default fp16, supports fp32/bf16/int8/hf32

---

## Performance Optimization

| Optimization | Description | Effect |
|-------------|-------------|--------|
| SSH persistent connection | ControlMaster reuse | Connection time ~0.1s |
| Batch execution | `execute_batch()` for multiple commands | Reduce SSH round trips |
| Parallel query | `test_flops_parallel()` 8-device async test | 16s -> 2s |
| Single parse | `parse_full_info()` get all card info at once | O(N) -> O(1) |

---

## Troubleshooting

### Command Not Recognized
- Check if input contains supported keywords
- Try using more explicit commands

### SSH Connection Failed
- Verify SSH parameters are correct
- Ensure SSH service is running on target machine

### npu-smi Not Available
- Ensure CANN and npu-smi are installed on target machine
- Check LD_LIBRARY_PATH environment variable

---

## Notes

### Security Warnings

- Sensitive operations require user confirmation before execution
- Passwords are only stored in memory during session
- Blocked commands cannot be bypassed

### Limitations

- Requires npu-smi or ascend-dmi installed on target machine
- SSH password authentication only (no interactive password prompt)

---


## Best Practices

### Best Practices

1. **Connection Mode Selection**
   - Local direct: For NPU installed on local machine
   - SSH remote: For managing remote Ascend servers

2. **Command Execution Tips**
   - Sensitive ops (firmware upgrade, config change) require user confirmation
   - Test on single card before batch operations

3. **Performance Monitoring**
   - Regularly check NPU temperature and power
   - Monitor HBM usage to avoid OOM

4. **Troubleshooting**
   - First check NPU health: `npu-smi info`
   - View detailed error log: `npu-smi info -t board -i <npu_id>`
   - See [troubleshooting.md](references/troubleshooting.md)

5. **Trigger Keywords**
   - Chinese: NPU, 昇腾, 显存, 算力, 温度, 功耗, 固件, 虚拟化
   - English: npu, ascend, temperature, power, HBM, firmware, vNPU, FLOPS

## Directory Structure

```
huawei-cloud-ascend-command/
├── SKILL.md                    # Skill description (required)
├── scripts/                    # Scripts directory (required)
│   ├── __init__.py             # Module export
│   ├── main.py                 # Skill entry file (required)
│   ├── executor.py             # NPU command executor
│   └── npu_client.py           # NPU client
└── references/                 # Reference documentation
    ├── acceptance-criteria.md  # Acceptance criteria
    ├── verification-method.md  # Verification steps
    ├── troubleshooting.md      # Troubleshooting guide
    ├── device-queries.md       # Device queries reference
    ├── configuration.md        # Configuration reference
    ├── firmware-upgrade.md     # Firmware upgrade reference
    ├── virtualization.md       # Virtualization reference
    └── certificate-management.md # Certificate management
```

## References

| Document | Description |
|----------|-------------|
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria for skill validation |
| [verification-method.md](references/verification-method.md) | Verification steps and test methods |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting guide and common issues |
| [device-queries.md](references/device-queries.md) | Device queries command reference |
| [configuration.md](references/configuration.md) | Configuration management reference |
| [firmware-upgrade.md](references/firmware-upgrade.md) | Firmware upgrade reference |
| [virtualization.md](references/virtualization.md) | Virtualization management reference |
| [certificate-management.md](references/certificate-management.md) | Certificate management reference |

## Technical Support

- Ascend Official Documentation: https://www.hiascend.com/document
- npu-smi Command Reference: https://www.hiascend.com/document/detail/zh/Atlas%20200I%20A2/260RC1/re/npu/npusmi_007.html
