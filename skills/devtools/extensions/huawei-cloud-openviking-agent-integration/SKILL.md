---
name: huawei-cloud-openviking-agent-integration
description: |
  Integrate and unbind OpenViking long-term memory with coding agents running in bwrap sandboxes. Supports 7 agents (CodeArts CLI, OpenCode, OpenClaw, Hermes, JiuwenSwarm, KimiCode, DeepSeek Harness) via their native mechanism — MCP or HTTP memory provider. Both integration and unbinding require explicit user authorization.
  Use this skill when the user wants to: (1) integrate OpenViking memory into a coding agent, (2) unbind OpenViking from a coding agent, (3) check the integration status of all agents, (4) verify the OpenViking MCP endpoint, (5) rebuild the OpenClaw sandbox to apply template changes.
  Trigger words: "OpenViking integration", "agent memory binding", "MCP setup", "OpenViking MCP", "integrate OpenViking", "unbind OpenViking", "记忆集成", "记忆解绑", "OpenViking 集成", "OpenViking 解绑", "agent long-term memory", "context database".
tags:
  - openviking
  - mcp
  - agent-integration
  - memory
  - binding
  - unbinding
  - codearts
  - opencode
  - openclaw
  - hermes
  - jiuwenswarm
  - kimicode
  - deepseek-harness
  - dsh
  - mcp-client
metadata:
  version: 1.0.0
  license: MIT
  category: devtools
---

# Huawei Cloud Agent Integration (OpenViking Long-Term Memory)

## Overview

Integrate and unbind OpenViking long-term memory with coding agents running in bwrap sandboxes under `/root/job-envs/sandboxes/`. Each agent uses its **native mechanism** — MCP (`mcp__openviking__*` tools) or the HTTP memory provider — so the integration survives agent upgrades and matches how each agent natively consumes memory.

Integration writes are **template-level persistent**: config is injected into the agent's `start.sh` / config templates under `/root/template/<agent>/`, so a sandbox `stop + start` (which re-runs `start.sh`) preserves the integration.

## What Good Looks Like

- `scripts/status.sh` reports all 7 agents as `✓` (template + live).
- `scripts/verify_mcp.sh` passes the full MCP handshake (initialize → tools/list → health) against `http://127.0.0.1:1933/mcp`.
- Restarting a sandbox does **not** lose the integration (template-level persistence, not live-only).
- Agents surface OpenViking tools natively: `mcp__openviking__*` for MCP-based agents, memory provider for JiuwenSwarm.
- Unbinding removes every trace: template blocks, live config, skills/AGENTS.md, and config backups.
- User authorization (`confirm`) is required for every mutation — nothing changes silently.

## Supported Agents

| Agent | Native mechanism | Persistence |
|-------|------------------|-------------|
| CodeArts CLI | MCP in `.codeartsdoer/codearts_cli.json` + 4-section prompt | Template start.sh + live sandbox |
| OpenCode | Official `@openviking/opencode-plugin` (npm, Huawei Cloud mirror) | Template start.sh (plugin install) |
| OpenClaw | Official OpenViking plugin (npm) + `contextEngine` slot | Template start.sh |
| Hermes | MCP + MCP SDK (`pip install mcp`) | Template start.sh + live sandbox |
| JiuwenSwarm | MCP + native memory provider | Template start.sh + live config.yaml |
| KimiCode | MCP via `mcp.json` | Template start.sh + live mcp.json |
| DeepSeek Harness (dsh) | Built-in `@deepseek-ai/dsh-mcp-client` + profile patches (web/cc-tui) + skill/AGENTS protocol | Template start.sh |

Per-agent config files, injection blocks, and recall quotas: [references/agent-configs.md](references/agent-configs.md).

## Prerequisites

- OpenViking server running and accessible (default `http://127.0.0.1:1933`):
  ```bash
  curl -s http://127.0.0.1:1933/health
  # {"status":"ok","healthy":true,"version":"0.4.x","auth_mode":"dev"}
  ```
- Agent sandboxes exist under `/root/job-envs/sandboxes/` (managed by job-env-manager).
- Host tools: `curl`, `python3`, `bash`. OpenCode/OpenClaw additionally need `npm` (Huawei Cloud mirror configured by the skill).
- This skill operates on local bwrap sandboxes only — no Huawei Cloud IAM policies required (see [references/iam-policies.md](references/iam-policies.md)).

## 参数确认 (Required Inputs)

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--agent <name>` | Yes (unless `--all`) | Target agent: `codearts`, `opencode`, `openclaw`, `hermes`, `jiuwenswarm`, `kimicode`, `deepseek-harness` | `--agent opencode` |
| `--all` | Yes (unless `--agent`) | Operate on all 7 agents | `--all` |
| `--endpoint <url>` | No | OpenViking server URL (default `http://127.0.0.1:1933`) | `--endpoint http://192.168.1.100:1933` |
| `--api-key <key>` | No | OpenViking API key (dev mode needs none). Never echo in chat or logs | `--api-key sk-xxx` |
| `--dry-run` | No | Show changes without applying them | `--dry-run` |
| `--yes` / `-y` | No | Skip authorization prompt (automation only) | `--yes` |
| `--json` | No | `status.sh`: machine-readable output | `--json` |

## Dependencies

- **OpenViking server** ≥ 0.4.x on `127.0.0.1:1933` (MCP endpoint `/mcp`, streamable HTTP).
- **npm + Huawei Cloud mirror** (`registry.npmmirror.com` or equivalent) for OpenCode / OpenClaw plugin installs.
- **Python MCP SDK** (`mcp==1.29.0`) injected by the skill for Hermes — not in the base template image.
- **dsh CLI** (`/root/runtime/deepseek-harness/bin/dsh`) for DeepSeek Harness profile patches (`--dump-config` verification).
- API script conventions are Bash + `curl` + `python3` only.

## 核心命令

| 功能 | 命令 |
|------|------|
| 查看集成状态 | `scripts/status.sh`（`--json` 机器可读，`--agent <name>` 指定 Agent） |
| 验证 MCP 端点 | `scripts/verify_mcp.sh` |
| 集成单个 Agent | `scripts/integrate.sh --agent <name> [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]` |
| 集成全部 Agent | `scripts/integrate.sh --all` |
| 解绑单个 Agent | `scripts/unbind.sh --agent <name> [--dry-run] [--yes]` |
| 解绑全部 Agent | `scripts/unbind.sh --all` |

## Workflow

### Task 1: Check Integration Status

```bash
SKILL_DIR=/root/.agents/skills/huawei-cloud-openviking-agent-integration
$SKILL_DIR/scripts/status.sh          # human-readable
$SKILL_DIR/scripts/status.sh --json   # machine-readable
```

Status values per agent:
- `template + live` — fully integrated and active
- `template only` — will activate on next restart
- `live only` — will be **lost on restart** (needs template fix)

### Task 2: Verify MCP Endpoint

```bash
$SKILL_DIR/scripts/verify_mcp.sh
```

Performs the full MCP protocol handshake (initialize → notifications/initialized → tools/list → tools/call health) and lists the OpenViking tools (find, search, recall, read, list, remember, add_resource, …).

### Task 3: Integrate a Single Agent

```bash
$SKILL_DIR/scripts/integrate.sh --agent opencode                       # interactive (asks for confirmation)
$SKILL_DIR/scripts/integrate.sh --agent opencode --endpoint URL --api-key KEY
$SKILL_DIR/scripts/integrate.sh --agent opencode --dry-run             # preview only
$SKILL_DIR/scripts/integrate.sh --agent opencode --yes                 # automation only
```

### Task 4: Integrate All Agents

```bash
$SKILL_DIR/scripts/integrate.sh --all
```

### Task 5: Unbind a Single Agent

```bash
$SKILL_DIR/scripts/unbind.sh --agent opencode
$SKILL_DIR/scripts/unbind.sh --agent opencode --dry-run
$SKILL_DIR/scripts/unbind.sh --agent opencode --yes
```

### Task 6: Unbind All Agents

```bash
$SKILL_DIR/scripts/unbind.sh --all
```

### Task 7: Rebuild OpenClaw Sandbox (Apply Template Changes)

OpenClaw's gateway runs in an ephemeral bwrap; `stop + start` re-runs `start.sh`, which reinstalls the plugin and applies endpoint config. Do:

1. `curl -s -X POST $BASE/envs/openclaw/stop` (poll until `stopped`)
2. `curl -s -X POST $BASE/envs/openclaw/start` (poll until `running`)
3. Verify: `scripts/integrate.sh --agent openclaw --dry-run` reports endpoint configured

Full restart/rebuild scripts (including the `stop → delete → create → deploy` fallback) and live-config verification from outside bwrap: [references/related-commands.md](references/related-commands.md).

## Authorization Model

Both `integrate.sh` and `unbind.sh` require explicit user confirmation before modifying any agent configuration:

```
━━━ Authorization Required ━━━
  Action:   Integrate OpenViking MCP
  Agent:    opencode
  Details:  Add OpenViking MCP to OpenCode template start.sh (persistent across restarts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Type 'confirm' to proceed:
```

- The user must type exactly `confirm`; any other input aborts.
- `--yes` / `-y` skips the prompt (for automation only).
- `--dry-run` shows what would happen without requiring authorization.
- Never integrate or unbind without explicit user confirmation — see [references/guardrails.md](references/guardrails.md) for the full rules.

## Safety Rules

- **Authorization is mandatory** — never integrate or unbind without explicit user confirmation.
- **Do not fabricate integration state** — always run `status.sh` to verify before reporting.
- **Never edit agent configs directly on the host** — all changes go through the skill scripts.
- **No API keys in logs** — `--api-key` values must never appear in output or logs.
- **Dry-run first** for unfamiliar targets.
- **Slow responses are not an integration bug** — check model API TTFB before blaming MCP (see [references/troubleshooting.md](references/troubleshooting.md)).

## Validation Rules

Quick verification after any integration or unbinding:

```bash
$SKILL_DIR/scripts/status.sh          # all agents green
$SKILL_DIR/scripts/verify_mcp.sh      # MCP handshake passes
```

Acceptance criteria for each workflow (integrate/unbind per agent): [references/acceptance-criteria.md](references/acceptance-criteria.md).
Step-by-step verification methods: [references/verification-method.md](references/verification-method.md).

## References

| Document | Description |
|----------|-------------|
| [agent-configs.md](references/agent-configs.md) | Per-agent config files, injection blocks, persistence patterns, recall quotas, MCP tools |
| [guardrails.md](references/guardrails.md) | Safety and authorization rules |
| [troubleshooting.md](references/troubleshooting.md) | Common failure scenarios, slow-response diagnostics (model TTFB vs network vs MCP), and fixed unbind cleanup issues |
| [iam-policies.md](references/iam-policies.md) | Equivalent access controls (no Huawei Cloud IAM needed) |
| [verification-method.md](references/verification-method.md) | Step-by-step verification for each workflow |
| [related-commands.md](references/related-commands.md) | Restart/rebuild scripts, inspection commands, live-config verification |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria for integration/unbinding |
| [demo/example-input.json](demo/example-input.json) | Example input for the integration workflow |

## Scripts

```
scripts/status.sh       Check integration status for all agents (--agent, --json)
scripts/verify_mcp.sh   Verify MCP endpoint via full protocol handshake
scripts/integrate.sh    Integrate single agent or all agents (--agent/--all, --dry-run, --yes)
scripts/unbind.sh       Unbind single agent or all agents (--agent/--all, --dry-run, --yes)
scripts/unset.sh        Alias for unbind.sh (backward-compatibility wrapper)
scripts/common.sh       Shared helpers (logging, confirmation, backups) — sourced by the others
```

All scripts are idempotent and create `.bak.<timestamp>` backups before each modification.
