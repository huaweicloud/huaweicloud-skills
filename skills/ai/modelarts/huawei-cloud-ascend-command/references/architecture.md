# Architecture and Orchestration Reference

Expanded architecture reference for `huawei-cloud-ascend-command`. `SKILL.md`
keeps only the summary; this document carries the full diagrams, orchestration
rules, script inventory, and directory structure that used to live in
`SKILL.md` (moved here so the main document stays under the token baseline).

## System Architecture Diagram

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

**Layer responsibilities**

| Layer | Responsibility |
|-------|----------------|
| Agent Orchestration | Parse intent, match trigger keywords, pass SSH params explicitly, invoke the skill, return the result |
| User Interaction Layer | Accept natural language commands or CLI arguments |
| Skill Core Components | `executor.py` parses/routes, `npu_client.py` executes npu-smi/ascend-dmi locally or over SSH |
| Ascend Infrastructure | Target machine with CANN + npu-smi, or the local NPU host |

**Two contract rules carried by the diagram**

- **Rule 1 — Explicit parameter passing**: the Agent passes `host` / `user` /
  `password` explicitly; the skill never guesses or stores credentials.
- **Rule 2 — Stateless**: no cross-invocation state is kept. Multi-turn
  behavior relies only on the in-process `pending_confirmation` slot.

## Agent Orchestration Flow

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

**Step-by-step**

1. **Intent parsing** — the Agent matches trigger keywords (`NPU`, `ascend`,
   `温度`, `固件`, …) and detects whether an IP/host was given.
2. **Parameter preparation** — `--host`, `--user`, `--password`, `--command`
   are assembled explicitly. Passwords are never echoed.
3. **Skill execution** — `NpuClient` receives the parameters, then executes the
   routed npu-smi/ascend-dmi command over SSH (remote mode) or locally.
4. **Result return** — the formatted output or the three-line
   `[ERROR] NPU-*` contract is returned to the user.

Sensitive steps in this flow insert a **confirmation gate**: the skill returns
the operation summary plus `Please reply 'confirm' or 'cancel'` and only
executes after `confirm` is received on a later turn.

## Related Skills (Agent orchestrated, no direct call, Rule 3)

| Skill Role | Purpose | Orchestration Scenario |
|------------|---------|------------------------|
| A general-purpose SSH remote operations skill | SSH remote ops (disk, Docker, logs, processes) | The Agent selects it when the user needs disk / Docker / log / process inspection on the same host; it complements — but is never invoked by — this skill |
| An alternative NPU management skill | NPU management | Alternative NPU command implementation; the Agent chooses one implementation per scenario |
| A model deployment and testing skill | Model deployment and testing on Ascend DevServer | Use `huawei-cloud-ascend-command` to monitor NPU health after that skill completes a deployment |

**Note**: No direct calls between skills. Orchestration is decided entirely by
the Agent based on user intent (Rule 3).

## Script Files

### Entry File

- **main.py**: Skill entry file (required)
  - Function: Provide interactive mode, one-shot mode, SSH remote mode
  - Supports: Command line arguments, interactive prompt
  - CLI flags: `--command/-c`, `--npu-smi`, `--npu-version/-V`, `--host`,
    `--port`, `--user`, `--password`
  - Errors: `run_one_shot()` / `run_npu_smi_direct()` catch `NpuCommandError`
    and print the `[ERROR] NPU-*` contract followed by `sys.exit(1)`; they never
    print a traceback.

### Core Scripts

- **executor.py**: NPU command executor (main entry)
  - Function: Natural language parsing, command routing, sensitive operation confirmation
  - Supported commands: Device queries, configuration, firmware upgrade, virtualization, certificate management
  - Core methods: `handle_command(text)`, `_route_nl(text)`, `_normalize_zh(text)`, `_execute_confirmed(cmd)`
  - Entry defense: `None` / non-`str` / empty input returns the help JSON instead of raising
  - Direct passthrough: input starting with `npu-smi` (case-insensitive) is
    executed verbatim **before** natural-language routing
  - Unified error handling: `NpuCommandError` → `format_npu_error(e)`;
    any other exception → three-line `[ERROR] NPU-UNEXPECTED` message

- **npu_client.py**: NPU client
  - Function: Wraps npu-smi command execution, supports local and SSH remote execution
  - Core methods: `list_devices()`, `get_health()`, `get_temperature()`, `get_power()`, `get_memory()`, `set_ecc_enable()`, `set_fan_mode()`, `set_fan_speed()`, `upgrade_query()`, `rollback_firmware()`, `create_vnpu()`, `destroy_vnpu()`, `get_tls_cert()`
  - Error contract: `NpuCommandError(kind, message, suggestion)` with
    `NPU_ERROR_CODES` and `format_npu_error()`; SSH failures raise, they never
    return an `"SSH Error: ..."` string
  - Optimization: SSH ControlMaster, batch execution, parallel FLOPS testing

- **__init__.py**: Module export for `scripts` package imports.

## Performance Optimization

| Optimization | Description | Effect |
|-------------|-------------|--------|
| SSH persistent connection | ControlMaster reuse | Connection time ~0.1s |
| Batch execution | `execute_batch()` for multiple commands | Reduce SSH round trips |
| Parallel query | `test_flops_parallel()` multi-device async test | 16s → 2s |
| Single parse | `parse_full_info()` gets all card info in one call | O(N) → O(1) |

## Reliability-Oriented Design

| Concern | Implementation |
|---------|----------------|
| Local command missing | `FileNotFoundError` → `NPU-CMD-NOT-FOUND` with install/PATH suggestion |
| Remote auth failure | `paramiko.AuthenticationException` → `NPU-SSH-AUTH` |
| Remote host unreachable | `NoValidConnectionsError` / `socket.timeout` / `ConnectionRefusedError` → `NPU-SSH-UNREACHABLE` |
| Command failure | non-zero exit or stderr-only output → `NPU-CMD-FAILED` (includes exit code + stderr summary) |
| Slow / hung command | SSH connect timeout 10s (default), per-command timeout 60s → `NPU-TIMEOUT` |
| Ambiguous intent | `set ECC` without direction, `set fan` without mode/number → clarification prompt, nothing dispatched |
| Unexpected exception | `[ERROR] NPU-UNEXPECTED` three-line contract, no traceback |

## Directory Structure

```
huawei-cloud-ascend-command/
├── SKILL.md                    # Skill description (required)
├── requirements.txt            # SSH mode dependency (paramiko)
├── scripts/                    # Scripts directory (required)
│   ├── __init__.py             # Module export
│   ├── main.py                 # Skill entry file (required)
│   ├── executor.py             # NPU command executor
│   └── npu_client.py           # NPU client
└── references/                 # Reference documentation
    ├── architecture.md         # Architecture, orchestration, scripts, layout
    ├── command-mapping.md      # Full natural language → npu-smi command map
    ├── acceptance-criteria.md  # Acceptance criteria
    ├── verification-method.md  # Verification steps
    ├── troubleshooting.md      # Troubleshooting guide and error codes
    ├── device-queries.md       # Device queries reference
    ├── configuration.md        # Configuration reference
    ├── firmware-upgrade.md     # Firmware upgrade reference
    ├── virtualization.md       # Virtualization reference
    └── certificate-management.md # Certificate management
```

## See Also

- [SKILL.md](../SKILL.md) — trigger keywords, core workflow, error handling summary
- [command-mapping.md](command-mapping.md) — every natural language → command mapping
- [configuration.md](configuration.md) — fan / ECC configuration details
- [troubleshooting.md](troubleshooting.md) — `NPU-*` error code reference
