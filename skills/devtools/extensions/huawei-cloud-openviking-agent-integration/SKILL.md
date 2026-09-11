---
name: huawei-cloud-openviking-agent-integration
description: |
  Integrate and unbind OpenViking long-term memory with coding agents. Supports 8 agents (CodeArts CLI, OpenCode, OpenClaw, Hermes, WorkSwarm, KimiCode, DeepSeek Harness, Prime Agent) via their native mechanism — MCP, HTTP memory provider, TypeScript extension hooks, or settings.json config. Both integration and unbinding require explicit user authorization.
  Use this skill when the user wants to: (1) integrate OpenViking memory into a coding agent, (2) unbind OpenViking from a coding agent, (3) check the integration status of all agents, (4) verify the OpenViking MCP endpoint, (5) rebuild the OpenClaw sandbox to apply template changes.
  Trigger words: "OpenViking integration", "agent memory binding", "MCP setup", "OpenViking MCP", "integrate OpenViking", "unbind OpenViking", "记忆集成", "记忆解绑", "OpenViking 集成", "OpenViking 解绑", "agent long-term memory", "context database".
tags:
  - openviking
  - database
  - agent
metadata:
  version: 1.2.1
  license: MIT
  category: devtools
---

# Huawei Cloud Agent Integration (OpenViking Long-Term Memory)

## Overview

Integrate and unbind OpenViking long-term memory with coding agents. Agents run in bwrap sandboxes under `/root/job-envs/sandboxes/` and use their **native mechanism** — MCP (`mcp__openviking__*` tools) or HTTP memory provider — so integration survives agent upgrades.

Integration writes are **template-level persistent**: config is injected into the agent's `start.sh` / config templates under `/root/template/<agent>/`, so sandbox `stop + start` preserves the integration.

## Supported Agents

| Agent | Mechanism | Persistence |
|-------|-----------|-------------|
| CodeArts CLI | `@openviking/opencode-plugin` → `.codeartsdoer/node_modules/` | Template + live |
| OpenCode | `@openviking/opencode-plugin` (npm mirror → GitHub fallback) | Template start.sh |
| OpenClaw | `clawhub:@openviking/openclaw-plugin` + `contextEngine` slot | Template start.sh |
| | ↳ **Optimization**: disables `session-memory` hook + denies `memory_search` tool (OpenViking handles recall; local memory degrades quality) |
| Hermes | Built-in `memory.provider: openviking` (HTTP REST, no MCP) | Template + live |
| WorkSwarm | Dual-channel: native provider + MCP (13 tools) + code-mode patch | Template + live + runtime patch |
| KimiCode | MCP via `mcp.json` | Template + live |
| DeepSeek Harness | `@openviking/dsh-memory-plugin` bundle (on-demand from GitHub) | Template start.sh |
| Prime Agent | `@openviking/pi-coding-agent-extension` (on-demand from GitHub) | Template start.sh |

Per-agent config details: [references/agent-configs.md](references/agent-configs.md).

## Prerequisites

- OpenViking server running at `http://127.0.0.1:1933` (`curl -s http://127.0.0.1:1933/health`).
- Agent sandboxes exist under `/root/job-envs/sandboxes/` (managed by job-env-manager).
- Host tools: `curl`, `python3`, `bash`. OpenCode/OpenClaw additionally need `npm`.
- No Huawei Cloud IAM policies required — this skill operates on local bwrap sandboxes only.

## 参数确认 (Required Inputs)

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--agent <name>` | Yes (unless `--all`) | Target agent (see table above) | `--agent opencode` |
| `--all` | Yes (unless `--agent`) | Operate on all 8 agents | `--all` |
| `--endpoint <url>` | No | OpenViking server URL (default `http://127.0.0.1:1933`) | `--endpoint http://192.168.1.100:1933` |
| `--api-key <key>` | No | OpenViking API key (dev mode needs none). Never echo in chat | `--api-key sk-xxx` |
| `--dry-run` | No | Show changes without applying | `--dry-run` |
| `--yes` / `-y` | No | Skip authorization prompt (automation only) | `--yes` |
| `--json` | No | `status.sh`: machine-readable output | `--json` |

## 核心命令

| 功能 | 命令 |
|------|------|
| 查看集成状态 | `scripts/status.sh`（`--json` 机器可读，`--agent <name>` 指定） |
| 验证 MCP 端点 | `scripts/verify_mcp.sh` |
| 集成单个 Agent | `scripts/integrate.sh --agent <name> [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]` |
| 集成全部 Agent | `scripts/integrate.sh --all` |
| 解绑单个 Agent | `scripts/unbind.sh --agent <name> [--dry-run] [--yes]` |
| 解绑全部 Agent | `scripts/unbind.sh --all` |

## Workflow

```bash
SKILL_DIR=/root/.agents/skills/huawei-cloud-openviking-agent-integration
```

1. **Check status**: `$SKILL_DIR/scripts/status.sh` — per-agent state: `template + live` (active), `template only` (activates on restart), `live only` (lost on restart).
2. **Verify MCP**: `$SKILL_DIR/scripts/verify_mcp.sh` — full MCP handshake (initialize → tools/list → health).
3. **Integrate**: `$SKILL_DIR/scripts/integrate.sh --agent <name>` (or `--all`).
4. **Unbind**: `$SKILL_DIR/scripts/unbind.sh --agent <name>` (or `--all`).
5. **Rebuild OpenClaw**: `stop + start` via job-env-manager API re-runs `start.sh`. Scripts: [references/related-commands.md](references/related-commands.md).

## Authorization & Safety

- **Authorization is mandatory** — `integrate.sh` and `unbind.sh` require explicit `confirm` (or `--yes` for automation). `--dry-run` previews without authorization.
- **Do not fabricate integration state** — always run `status.sh` to verify before reporting.
- **Never edit agent configs directly** — all changes go through the skill scripts.
- **No API keys in logs** — `--api-key` values must never appear in output.
- Every config modification creates a `.bak.<timestamp>` backup for rollback.

Full rules: [references/guardrails.md](references/guardrails.md). Troubleshooting: [references/troubleshooting.md](references/troubleshooting.md).

## Plugin Sources

The skill ships **no plugin code** — plugins are installed on demand at integrate time via domestic-first mirrors (Huawei Cloud npm → npmmirror → npmjs; GitHub raw mirrors for non-npm plugins). All downloads are byte-verified against GitHub blob SHA. Installed copies under `/root/runtime/` are reused if upstream is unreachable (3-tier cache: sandbox `node_modules` → runtime cache → online).

## References

| Document | Description |
|----------|-------------|
| [agent-configs.md](references/agent-configs.md) | Per-agent config details, MCP tools, server info |
| [guardrails.md](references/guardrails.md) | Safety, authorization, access permissions |
| [troubleshooting.md](references/troubleshooting.md) | Failure scenarios and fixes |
| [verification.md](references/verification.md) | Verification methods and acceptance criteria |
| [related-commands.md](references/related-commands.md) | Restart/rebuild scripts, env vars |

## Scripts (OO Architecture)

Base class (`lib/base.sh`) + registry (`lib/registry.sh`) + per-agent subclasses (`agents/*.sh`). Entry points (`integrate/unbind/status.sh`) are thin CLI parsers. All scripts are idempotent with `.bak.<timestamp>` backups. Adding a new agent = one file in `agents/`.
