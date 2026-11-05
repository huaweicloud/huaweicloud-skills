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
| AC-1.7 | Chinese trigger words should route (ISSUE-003) | `查看NPU温度` must return temperature output, not `Unknown command` |
| AC-1.8 | Direct `npu-smi` commands must pass through unchanged (B115-2) | `npu-smi info -l` executes verbatim; `-l` is not dropped by NL routing |

### 2. Configuration Management

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-2.1 | Should get fan mode | `Fan mode` command |
| AC-2.2 | Should set fan mode (auto/manual) | `Set fan auto` / `Set fan manual` |
| AC-2.3 | Should get ECC status | `ECC status` command |
| AC-2.4 | Should enable/disable ECC | `Enable ECC` / `Disable ECC` |
| AC-2.5 | Should get performance mode | `Performance mode` command |
| AC-2.6 | Should set performance mode | `Set performance mode` command |
| AC-2.7 | Fan mode maps to `pwm-mode` (ISSUE-001) | `Set fan auto` shows `Set fan to auto mode`; after `confirm` dispatches `npu-smi set -t pwm-mode -d 1`; `Set fan manual` → `-d 0` |
| AC-2.8 | Fan speed maps to `pwm-duty-ratio` | `Set fan speed 70` → gate `Set fan speed to 70%`; after `confirm` dispatches `npu-smi set -t pwm-duty-ratio -d 70` |
| AC-2.9 | `set fan` without direction or number must clarify (ISSUE-001) | `set fan` returns a clarification request (`auto` / `manual` or 0-100) and arms no confirmation gate — it must **not** default to 50% |
| AC-2.10 | `set ECC` without direction must clarify (ISSUE-004) | `set ECC` returns `Please specify direction: 'enable ECC' or 'disable ECC'`; must **not** silently default to disable |

### 3. Firmware Management

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-3.1 | Should display firmware version | `Firmware version` command |
| AC-3.2 | Should check for firmware updates | `Upgrade status` / `Check firmware update` command |
| AC-3.3 | Should support firmware rollback with confirmation (ISSUE-006) | `rollback firmware` returns a rollback confirmation gate (warning rollback is not supported on all devices); after `confirm` dispatches `npu-smi upgrade -a rollback -i <npu_id>` |
| AC-3.4 | Should accept `activate upgrade` as an activation synonym (B115-6) | `activate upgrade mcu NPU0` enters the same activation confirmation gate as `activate firmware mcu NPU0` |

### 4. Virtualization Management

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-4.1 | Should list vNPUs | `List vNPUs` command |
| AC-4.2 | Should create vNPU | `Create vNPU` command |
| AC-4.3 | Should delete vNPU | `Delete vNPU` command |
| AC-4.4 | Create vNPU must not be intercepted by the template branch (B115-3) | `create vNPU NPU0 Chip0 template vir04` returns the create-vNPU confirmation gate, not template info |
| AC-4.5 | vNPU sub-command spelling (ISSUE-005) | After `confirm`, the dispatched command contains `set -t create-vnpu ...` / `set -t destroy-vnpu ...`; `create-vnru` / `destroy-vnru` must never appear |

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
| AC-6.3 | Should handle connection errors gracefully (ISSUE-002) | Invalid host/password |
| AC-6.3.1 | Authentication failure must be distinguishable | `--command "NPU health check" --host 127.0.0.1 --user root --password x` (no SSH server or bad credentials) reports `[ERROR] NPU-SSH-AUTH` or `[ERROR] NPU-SSH-UNREACHABLE` |
| AC-6.3.2 | Connection failure must never be reported as an empty device list | The output must **not** be `No NPU devices found` for an auth/unreachable failure |
| AC-6.3.3 | Error output follows the three-line contract | `[ERROR] <CODE>` / `Message: ...` / `Suggestion: ...`, no traceback, non-zero exit for one-shot CLI |
| AC-6.4 | Remote failures must not hang silently | Wait is bounded by the single retry (~2 × 10s SSH connect timeout) |

### 7. Safety Features

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-7.1 | Should prompt confirmation for sensitive operations | Try `Enable ECC` command |
| AC-7.2 | Should allow confirmation/cancellation | Reply `confirm` or `cancel` (Chinese `确认` / `取消` also accepted) |
| AC-7.3 | Should display help information | `help` command |
| AC-7.4 | Empty / non-string / `None` input must not crash (B115-4) | `handle_command(None)` returns the help JSON (`status: "help"`) |

### 8. Error Contract and Robustness

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-8.1 | Local mode without `npu-smi` degrades gracefully | `python3 scripts/main.py --command "NPU list"` on a machine with no `npu-smi` prints `[ERROR] NPU-CMD-NOT-FOUND` with a suggestion and no traceback |
| AC-8.2 | Missing `ascend-dmi` does not crash FLOPS tests (B115-5) | `python3 scripts/main.py --command "Run FLOPS test"` prints `❌ ascend-dmi not found ...` instead of raising `FileNotFoundError` |
| AC-8.3 | All six `NPU-*` codes are reachable and documented | `NPU-SSH-AUTH`, `NPU-SSH-UNREACHABLE`, `NPU-SSH-ERROR`, `NPU-CMD-NOT-FOUND`, `NPU-CMD-FAILED`, `NPU-TIMEOUT` |
| AC-8.4 | Parsers never swallow errors | `parse_full_info()` / `get_health()` let `NpuCommandError` propagate; no `"SSH Error: ..."` / `"Error (exit N): ..."` strings are produced |

### 9. Issue Traceability (#178 / #115 / #88)

| Finding | Acceptance criteria |
|---------|---------------------|
| #178 ISSUE-001 — `set fan auto` mis-routed to 50% speed | AC-2.2, AC-2.7, AC-2.9 |
| #178 ISSUE-002 — SSH failure swallowed into "No NPU devices found" | AC-6.3, AC-6.3.1, AC-6.3.2, AC-6.3.3, AC-8.4 |
| #178 ISSUE-003 — Chinese trigger `温度` not routed | AC-1.7 |
| #178 ISSUE-004 — `set ECC` silently defaulted to disable | AC-2.4, AC-2.10 |
| #178 ISSUE-005 — `create-vnru` / `destroy-vnru` misspelling | AC-4.5 |
| #178 ISSUE-006 — `rollback firmware` documented but not routed | AC-3.3 |
| #178 AC-6.3 — graceful connection-error handling | AC-6.3.1, AC-6.3.2, AC-6.3.3 |
| #115 B115-2 — `npu-smi info -l` swallowed by NL routing | AC-1.8 |
| #115 B115-3 — `template` intercepts `create vNPU` | AC-4.4 |
| #115 B115-4 — `handle_command(None)` raises | AC-7.4 |
| #115 B115-5 — FLOPS `FileNotFoundError` | AC-8.2 |
| #115 B115-6 — `activate upgrade` not matched | AC-3.4 |
| #88 I88-4 — no graceful degradation without a local NPU | AC-8.1, AC-8.3 |

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
