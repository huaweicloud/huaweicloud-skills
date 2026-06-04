# Acceptance Criteria

## Functional Acceptance Criteria

### 1. Basic Device Query

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-1.1 | Should list all NPU devices | `NPU list` command |
| AC-1.2 | Should show device health status | `NPU health check` command |
| AC-1.3 | Should display temperature information | `NPU temperature` command |
| AC-1.4 | Should display memory information | `NPU memory` command |
| AC-1.5 | Should display power usage | `NPU power` command |
| AC-1.6 | Should display utilization | `NPU utilization` command |

### 2. Configuration Management

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-2.1 | Should get fan mode | `Fan mode` command |
| AC-2.2 | Should set fan mode (auto/manual) | `Set fan auto` / `Set fan manual` |
| AC-2.3 | Should get ECC status | `ECC status` command |
| AC-2.4 | Should enable/disable ECC | `Enable ECC` / `Disable ECC` |
| AC-2.5 | Should get performance mode | `Performance mode` command |
| AC-2.6 | Should set performance mode | `Set performance mode` command |

### 3. Firmware Management

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-3.1 | Should display firmware version | `Firmware version` command |
| AC-3.2 | Should check for firmware updates | `Check firmware update` command |

### 4. Virtualization Management

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-4.1 | Should list vNPUs | `List vNPUs` command |
| AC-4.2 | Should create vNPU | `Create vNPU` command |
| AC-4.3 | Should delete vNPU | `Delete vNPU` command |

### 5. Security Management

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-5.1 | Should display certificate status | `Certificate status` command |
| AC-5.2 | Should verify certificate | `Verify certificate` command |

### 6. SSH Remote Access

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-6.1 | Should connect via SSH with password | `--host --user --password` |
| AC-6.2 | Should execute commands remotely | Remote `NPU list` command |
| AC-6.3 | Should handle connection errors gracefully | Invalid host/password |

### 7. Safety Features

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-7.1 | Should prompt confirmation for sensitive operations | Try `Enable ECC` command |
| AC-7.2 | Should allow confirmation/cancellation | Reply `confirm` or `cancel` |
| AC-7.3 | Should display help information | `help` command |

## Non-Functional Acceptance Criteria

### 1. Performance

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-1.1 | Local command execution time | < 1 second |
| NAC-1.2 | Remote command execution time | < 5 seconds (depending on network) |
| NAC-1.3 | Multi-device query parallel execution | Yes |

### 2. Reliability

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-2.1 | Command success rate | > 99% |
| NAC-2.2 | Graceful error handling | No crashes |
| NAC-2.3 | Connection retry | Automatic retry on failure |

### 3. Usability

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-3.1 | Natural language command recognition | > 90% accuracy |
| NAC-3.2 | Command response clarity | Clear, human-readable output |
| NAC-3.3 | Error message clarity | Understandable error messages |

### 4. Compatibility

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-4.1 | Python version compatibility | Python 3.8+ |
| NAC-4.2 | OS compatibility | Linux (CentOS/Ubuntu) |
| NAC-4.3 | NPU chip compatibility | Ascend 910/310 series |

## Deployment Acceptance Criteria

### 1. Environment Requirements

| Criteria | Description |
|----------|-------------|
| DAC-1.1 | Python 3.8 or higher installed |
| DAC-1.2 | paramiko library installed (for SSH) |
| DAC-1.3 | npu-smi available in PATH (local mode) |

### 2. Installation

| Criteria | Description |
|----------|-------------|
| DAC-2.1 | No additional installation required |
| DAC-2.2 | Scripts run directly from source |
| DAC-2.3 | No external dependencies beyond standard library |

## Test Cases Summary

### Positive Test Cases

1. TC-001: Basic device query
2. TC-002: Health check
3. TC-003: Temperature monitoring
4. TC-004: Memory information
5. TC-005: Fan mode configuration
6. TC-006: ECC configuration
7. TC-007: Remote SSH access
8. TC-008: Help command
9. TC-009: Sensitive operation confirmation
10. TC-010: Virtual NPU management

### Negative Test Cases

1. TC-N01: Invalid command handling
2. TC-N02: SSH connection failure
3. TC-N03: Missing npu-smi binary
4. TC-N04: Permission denied handling
5. TC-N05: Invalid device ID
