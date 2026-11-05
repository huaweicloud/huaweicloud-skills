---
name: huawei-cloud-ascend-command
description: |
  Huawei Ascend NPU natural language management skill, supporting both local direct connection and SSH remote modes. Provides comprehensive npu-smi command capabilities including device queries, configuration management, firmware upgrade, vNPU virtualization, certificate management, and compute power testing (FLOPS). Enables remote management and monitoring of Ascend NPU devices with real-time metrics tracking.
  Use this skill when the user wants to: (1) query NPU device status and health, (2) monitor temperature, power, memory/HBM utilization, (3) configure ECC settings and fan modes, (4) perform firmware upgrades or rollbacks, (5) manage vNPU virtualization, (6) run compute power tests, (7) check certificate information.
  Trigger: user mentions 'npu', 'ascend', 'NPU', 'Ascend', 'temperature', 'power', 'HBM', 'firmware', 'upgrade', 'vNPU', 'virtualization', 'certificate', 'FLOPS', 'compute', 'health', 'memory', 'utilization', 'ECC', 'fan', '昇腾', '昇腾卡', '昇腾状态', '显存', '算力', '设备查询', 'NPU监控'
category: operational
tags: [huawei-cloud, ascend, npu, npu-smi, remote]
allowed-tools:
  - python3
  - bash
  - ssh
---
Natural language command translation and execution for Huawei Ascend NPU devices: device queries, configuration management, firmware upgrade, vNPU virtualization, certificate management, and compute power testing.

## Overview

Translates natural language requests into `npu-smi` / `ascend-dmi` commands on Huawei Ascend NPU devices, over either a local direct connection or an SSH remote session. This is a **stateless, operational** skill: it stores no credentials, device state or conversation history between invocations.

**Capabilities**: device queries (health, temperature, power, HBM, ECC, topology) · configuration (ECC, fan mode/speed) · firmware version / upgrade / activate / rollback · vNPU virtualization · TLS certificate management · FLOPS testing.

**Orchestration**: the Agent invokes this skill alongside others when a task needs them — for example a general-purpose SSH remote-operations skill (disk, Docker, logs, processes) or a model-deployment skill whose NPU state is monitored after deploy. Skills never call each other directly; the Agent selects and chains them from user intent. See [references/architecture.md](references/architecture.md).

## Prerequisites

| Requirement | Detail |
|-------------|--------|
| Python | 3.8+ (`python3 --version`) |
| Local mode | `npu-smi` (CANN) on the local machine; `ascend-dmi` additionally for FLOPS tests |
| SSH remote mode | `paramiko` — install with `pip install -r requirements.txt` (`paramiko>=2.11,<4`) |
| Target host | Reachable network, running `sshd`, password authentication enabled |

- Local mode needs **no** Python package beyond the standard library.
- SSH mode needs `paramiko`; it is imported lazily, so local mode still works when it is absent.
- The target machine must have CANN/`npu-smi` installed — run `npu-smi info` there once to confirm.
- **Security**: never read, echo or print password values; never ask the user to paste a password into the conversation; read credentials only from the `--password` command-line argument.

## Core Workflow

1. Parse the user intent and normalize Chinese trigger words (触发词: 温度 / 功耗 / 显存 / 算力 / 固件 / 虚拟化 / 风扇 / 启用 / 禁用 …) to English.
2. **Direct passthrough first**: if the input starts with `npu-smi`, execute it verbatim — this precedes natural-language routing, so `npu-smi info -l` keeps its `-l`.
3. Route the natural-language request to a handler and resolve the device target (`NPU0 Chip0`), defaulting to NPU 0 / Chip 0.
4. Read-only queries execute immediately and are formatted for the user.
5. Write operations print a confirmation gate and wait for `confirm` / `确认` (or `cancel` / `取消`) before executing — see [Parameter Confirmation](#parameter-confirmation).
6. Any failure returns a structured `[ERROR] NPU-*` response; a Python traceback is never shown.

```bash
python3 scripts/main.py --command "NPU health check"                                   # one-shot
python3 scripts/main.py --command "查看NPU温度"                                          # Chinese trigger words
python3 scripts/main.py --command "NPU list" --host <ip> --user root --password <pwd>  # SSH remote
python3 scripts/main.py                                                                # interactive
```

## Core Commands

| Intent | Example input | Underlying command |
|--------|---------------|--------------------|
| List devices | `NPU list` | `npu-smi info -l` |
| Full / card info | `NPU info` | `npu-smi info` (full NPU information) |
| Card / chip mapping | `NPU chip mapping`, `chip list` | `npu-smi info -m` (card-to-chip mapping) |
| Direct passthrough | any input starting with `npu-smi`, e.g. `npu-smi info -t board` | executed verbatim, exactly as typed — passthrough takes precedence over natural-language routing |
| Health check | `NPU health check` | `npu-smi info -t health -i 0` |
| Temperature / power / memory / usage | `NPU temperature`, `功耗`, `显存` | `npu-smi info -t temp \| power \| memory \| usages -i 0 -c 0` |
| ECC direction (mandatory) | `set ECC enable`, `disable ECC` | `npu-smi set -t ecc-enable -i 0 -c 0 -d 1 \| 0` (confirmation) |
| Fan mode | `set fan auto`, `set fan manual` | `npu-smi set -t pwm-mode -d 1 \| 0` (confirmation) |
| Fan speed | `set fan speed 70` | `npu-smi set -t pwm-duty-ratio -d 70` (confirmation) |
| Firmware version / upload | `firmware version`, `upgrade firmware` | `npu-smi upgrade -b mcu -i 0` / `upgrade -t mcu -i 0 -f <file>.hpm` (confirmation) |
| Firmware activate | `activate firmware`, `activate upgrade mcu NPU0` | `npu-smi upgrade -a <component> -i 0` (confirmation) |
| Firmware rollback | `rollback firmware` | `npu-smi upgrade -a rollback -i <npu_id>` (confirmation) |
| vNPU | `vNPU info`, `template info`, `create vNPU`, `destroy vNPU` | `npu-smi info -t info-vnpu \| template-info …`, `set -t create-vnpu \| destroy-vnpu …` (confirmation) |
| Certificate | `certificate info`, `cert expiration` | `npu-smi info -t tls-cert \| tls-cert-period -i 0 -c 0` |
| FLOPS | `FLOPS test`, `FP32 FLOPS`, `all devices FLOPS` | `ascend-dmi -f -d <n> -t <fp16\|fp32\|bf16\|int8\|hf32> -q`; multi-device runs async in parallel |

The complete natural-language → command mapping lives in [references/command-mapping.md](references/command-mapping.md).

## Parameter Confirmation

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--command` | Yes (one-shot) | Natural language request, or a direct `npu-smi` command |
| `--host` | SSH mode | Remote host IP address / hostname |
| `--user`, `--password` | SSH mode | SSH credentials (password authentication only) |

Read-only queries never prompt. These write operations always print their exact effect and wait for `confirm` / `确认` before executing:

- **ECC enable/disable** — the direction (`enable` / `disable`) is mandatory; `set ECC` with no direction is answered with a clarification question and nothing is executed.
- **Fan mode / fan speed** — `set fan` with neither `auto` / `manual` nor a speed value is answered with a clarification question; it never defaults to a speed.
- **Firmware upload / activate / rollback** — rollback may be unsupported by some devices.
- **vNPU create / destroy.**
- **Certificate management.**

## Output Format

Query results are human-readable text, optionally followed by the structured JSON envelope:

```json
{"status": "success", "command": "npu-smi info -l", "description": "List all NPU devices"}
```

Errors use exactly three lines, with `CODE` taken from the error-code contract below:

```
[ERROR] <CODE>
Message: <error-description>
Suggestion: <troubleshooting-tip>
```

## Error Handling & Stability

**Error-code contract.** One code per failure class, so "wrong credentials", "wrong host" and "the remote host really has no NPU" stay distinguishable:

| Code | Meaning | Typical suggestion |
|------|---------|--------------------|
| `NPU-SSH-AUTH` | SSH authentication failed | check `--user` / `--password`, account lockout, password login allowed |
| `NPU-SSH-UNREACHABLE` | host unreachable, port refused or connect timeout | check host, port 22, network, security group, `sshd` |
| `NPU-SSH-ERROR` | other SSH-level failure | retry once, then inspect `sshd` logs on the target |
| `NPU-CMD-NOT-FOUND` | `npu-smi` / `ascend-dmi` not installed or not on `PATH` | install CANN/npu-smi on the target, or use `--host` for SSH mode |
| `NPU-CMD-FAILED` | command ran but exited non-zero | inspect the reported exit code and stderr summary |
| `NPU-TIMEOUT` | command exceeded its timeout | check device load, retry once if the condition was transient |
| `NPU-UNEXPECTED` | unclassified fallback | check the command and environment, then retry |

**Retry policy.** Only transient failures are retried: a failing SSH connect/execute is retried **once** after the connection is closed, i.e. at most **2 attempts** in total (worst-case wait ≈ 2 × connect timeout). Authentication failures, `command_not_found`, non-zero exits and timeouts are not retried blindly. Retries are always bounded and never fan out (no retry storm); a failed write is never silently re-sent.

**Timeouts.** SSH connection timeout **10s**; a single local/remote command **60s**; FLOPS tests up to **120s**. Exceeding a timeout returns `[ERROR] NPU-TIMEOUT` with a suggestion instead of hanging.

**Degradation.** Every layer degrades to a friendly message rather than a traceback: missing `npu-smi` → `NPU-CMD-NOT-FOUND`; missing `ascend-dmi` → "ascend-dmi not found" for that FLOPS test only; missing `paramiko` or a failed SSH connection → a connection error, **never** "No NPU devices found". `handle_command(None)`, non-string and empty input return the help listing instead of raising. See [references/troubleshooting.md](references/troubleshooting.md).

**Idempotency.** Queries (`list`, `info`, `health`, `temperature`, …) are read-only and safe to repeat. Writes (ECC, fan, firmware, vNPU, certificate) always pass the confirmation gate, execute exactly once, and are never auto-replayed after a failure — re-issue them explicitly if needed.

**Boundary conditions.**

- No NPU hardware / no `npu-smi` locally → friendly `NPU-CMD-NOT-FOUND`, not a stack trace.
- SSH authentication failure, unreachable host, and a reachable host with genuinely zero devices must remain **three distinct** outcomes; a connection error is never parsed as an empty device list.
- Empty command output → an explicit "no data / no devices" message, never a crash.
- Chinese input (for example `查看NPU温度`) is normalized to English before routing.
- Multi-turn state is limited to the pending confirmation of the current invocation; nothing is persisted, so every invocation starts clean.

**Dependencies.** Local mode: `npu-smi` (CANN), plus `ascend-dmi` for FLOPS only — no Python package required. SSH mode: `paramiko` (`pip install -r requirements.txt`). When a dependency is missing, report its error code and suggestion; never invent a fallback command.

## Verification Method

1. `python3 --version` → 3.8+.
2. `python3 scripts/main.py --command "NPU list"` → a device table, or a friendly `NPU-CMD-NOT-FOUND` when `npu-smi` is absent (never a traceback).
3. `python3 scripts/main.py --host <ascend-ip> --user root --password <pwd> --command "NPU health check"` → remote status; a wrong host or password must yield `NPU-SSH-*`, not "No NPU devices found".

The full reproducible matrix (Chinese inputs, direct `npu-smi` passthrough, confirmation gates, rollback) is in [references/verification-method.md](references/verification-method.md).

## Troubleshooting

- **Command not recognized** → use a supported keyword; Chinese trigger words are normalized, but unsupported wording returns the help listing.
- **SSH connection failed** → follow the `[ERROR] NPU-*` code: credentials and account state for `NPU-SSH-AUTH`, host / port / network / `sshd` for `NPU-SSH-UNREACHABLE`.
- **`npu-smi` not available** → install CANN/`npu-smi` on the target machine and check `LD_LIBRARY_PATH`.

Error codes and per-code diagnosis steps: [references/troubleshooting.md](references/troubleshooting.md).

## Notes & Limitations

- Sensitive operations always require confirmation; blocked commands cannot be bypassed; passwords are held in memory for the session only.
- Requires `npu-smi` (or `ascend-dmi` for FLOPS) on the target machine; SSH uses password authentication only (no interactive prompt).
- Verify a single card before batch operations, and watch temperature / HBM usage to avoid OOM.
- Architecture, Agent orchestration flow, script files and directory layout: [references/architecture.md](references/architecture.md).

## References

| Document | Description |
|----------|-------------|
| [architecture.md](references/architecture.md) | System architecture, Agent orchestration flow, stateless rules, script files and directory layout |
| [command-mapping.md](references/command-mapping.md) | Complete natural-language → `npu-smi` / `ascend-dmi` command mapping, including fan mode/speed and firmware rollback |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria for skill validation |
| [verification-method.md](references/verification-method.md) | Reproducible verification steps and test methods |
| [troubleshooting.md](references/troubleshooting.md) | Error codes and troubleshooting guide |
| [device-queries.md](references/device-queries.md) | Device queries command reference |
| [configuration.md](references/configuration.md) | ECC and fan configuration reference |
| [firmware-upgrade.md](references/firmware-upgrade.md) | Firmware version, upgrade, activate and rollback reference |
| [virtualization.md](references/virtualization.md) | vNPU virtualization reference |
| [certificate-management.md](references/certificate-management.md) | Certificate management reference |
| [iam-policies.md](references/iam-policies.md) | IAM permission policy requirements (none — local/SSH operational skill) |

## Technical Support

- Ascend official documentation: https://www.hiascend.com/document
- npu-smi command reference: https://www.hiascend.com/document/detail/zh/Atlas%20200I%20A2/260RC1/re/npu/npusmi_007.html
