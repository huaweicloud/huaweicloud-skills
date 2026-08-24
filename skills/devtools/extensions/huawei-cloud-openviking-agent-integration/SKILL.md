---
name: huawei-cloud-openviking-agent-integration
description: |
  Integrate and unbind OpenViking long-term memory with coding agents. Supports 8 agents (CodeArts CLI, OpenCode, OpenClaw, Hermes, JiuwenSwarm, KimiCode, DeepSeek Harness, Prime Agent) via their native mechanism — MCP, HTTP memory provider, TypeScript extension hooks, or settings.json config. Both integration and unbinding require explicit user authorization.
  Use this skill when the user wants to: (1) integrate OpenViking memory into a coding agent, (2) unbind OpenViking from a coding agent, (3) check the integration status of all agents, (4) verify the OpenViking MCP endpoint, (5) rebuild the OpenClaw sandbox to apply template changes.
  Trigger words: "OpenViking integration", "agent memory binding", "MCP setup", "OpenViking MCP", "integrate OpenViking", "unbind OpenViking", "记忆集成", "记忆解绑", "OpenViking 集成", "OpenViking 解绑", "agent long-term memory", "context database".
tags:
  - openviking
  - database
  - agent
metadata:
  version: 1.2.0
  license: MIT
  category: devtools
---

# Huawei Cloud Agent Integration (OpenViking Long-Term Memory)

## Overview

Integrate and unbind OpenViking long-term memory with coding agents. Most agents run in bwrap sandboxes under `/root/job-envs/sandboxes/` and use their **native mechanism** — MCP (`mcp__openviking__*` tools) or the HTTP memory provider — so the integration survives agent upgrades and matches how each agent natively consumes memory.


Integration writes are **template-level persistent** for sandbox agents: config is injected into the agent's `start.sh` / config templates under `/root/template/<agent>/`, so a sandbox `stop + start` (which re-runs `start.sh`) preserves the integration.


## What Good Looks Like

- `scripts/status.sh` reports all 8 agents as `✓` (template + live).
- `scripts/verify_mcp.sh` passes the full MCP handshake (initialize → tools/list → health) against `http://127.0.0.1:1933/mcp`.
- Restarting a sandbox does **not** lose the integration (template-level persistence, not live-only).
- Agents surface OpenViking tools natively: `mcp__openviking__*` for MCP-based agents, dual-channel (MCP + native viking_*) for JiuwenSwarm.
- Unbinding removes every trace: template blocks, live config, skills/AGENTS.md, config backups, and openviking keys in settings.json.
- User authorization (`confirm`) is required for every mutation — nothing changes silently.

## Supported Agents

| Agent | Native mechanism | Persistence |
|-------|------------------|-------------|
| CodeArts CLI | MCP in `.codeartsdoer/codearts_cli.json` + 4-section prompt (aligned with official `openviking-memory` skill semantics) | Template start.sh + live sandbox |
| OpenCode | Official `@openviking/opencode-plugin` (installed on demand: npm domestic mirror first, on-demand GitHub raw mirror fallback; deployed from `$RUNTIME/opencode/openviking-plugin/`; `@opencode-ai/plugin` SDK via npm) + official `openviking-config.json` fields | Template start.sh (on-demand plugin install) |
| OpenClaw | Official `clawhub:@openviking/openclaw-plugin` + `openviking setup --json` contract (domestic npm mirror fallback → on-demand source build fallback) + `contextEngine` slot | Template start.sh |
| Hermes | Official built-in memory provider (`memory.provider: openviking`, no MCP SDK) | Template start.sh + live sandbox |
| JiuwenSwarm | Dual-channel: native memory provider (`memory.engine: both` + `memory.external.provider: openviking`, HTTP REST) **+ MCP server** (`streamable-http`, 13 tools incl. `search`/`recall`/`find`) + `auto_memory_enabled: true` | Template start.sh + live config.yaml |
| KimiCode | MCP via `mcp.json` | Template start.sh + live mcp.json |
| DeepSeek Harness (dsh) | Official `@openviking/dsh-memory-plugin` bundle (installed on demand from `volcengine/OpenViking` via the domestic GitHub raw mirror list; self-contained peers + ESM-safe peer dep sync) installed into `web`/`dsh-tui` profile node_modules + `dsh.profile.bundles` | Template start.sh |
| Prime Agent | Official `@openviking/pi-coding-agent-extension` (installed on demand from `volcengine/OpenViking` via the domestic GitHub raw mirror list, incl. tests/) | Template start.sh + live extensions dir |

Per-agent config files, injection blocks, and recall quotas: [references/agent-configs.md](references/agent-configs.md).

## Prerequisites

- OpenViking server running and accessible (default `http://127.0.0.1:1933`):
  ```bash
  curl -s http://127.0.0.1:1933/health
  # {"status":"ok","healthy":true,"version":"0.4.x","auth_mode":"dev"}
  ```
- Agent sandboxes exist under `/root/job-envs/sandboxes/` (managed by job-env-manager).
- Host tools: `curl`, `python3`, `bash`. OpenCode/OpenClaw additionally need `npm` (domestic-first registry configured by the skill).
- This skill operates on local bwrap sandboxes and the local hwcloud config only — no Huawei Cloud IAM policies required (see [references/iam-policies.md](references/iam-policies.md)).

## 参数确认 (Required Inputs)

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--agent <name>` | Yes (unless `--all`) | Target agent: `codearts`, `opencode`, `openclaw`, `hermes`, `jiuwenswarm`, `kimicode`, `deepseek-harness`, `prime-agent` | `--agent opencode` |
| `--all` | Yes (unless `--agent`) | Operate on all 8 agents | `--all` |
| `--endpoint <url>` | No | OpenViking server URL (default `http://127.0.0.1:1933`) | `--endpoint http://192.168.1.100:1933` |
| `--api-key <key>` | No | OpenViking API key (dev mode needs none). Never echo in chat or logs | `--api-key sk-xxx` |
| `--dry-run` | No | Show changes without applying them | `--dry-run` |
| `--yes` / `-y` | No | Skip authorization prompt (automation only) | `--yes` |
| `--json` | No | `status.sh`: machine-readable output | `--json` |

## Dependencies

- **OpenViking server** ≥ 0.4.x on `127.0.0.1:1933` (MCP endpoint `/mcp`, streamable HTTP).
- **npm** (domestic-first registries: `mirrors.huaweicloud.com/repository/npm/` → `registry.npmmirror.com` → `registry.npmjs.org`) for OpenCode `@opencode-ai/plugin` SDK + `@openviking/opencode-plugin`, and OpenClaw plugin installs (ClawHub primary, npm mirrors as fallback, on-demand source build as third fallback).
- **No MCP SDK needed for Hermes** — Hermes has a built-in OpenViking memory provider over HTTP REST (official `05-hermes.md`).
- **openclaw CLI inside sandbox** for `openclaw openviking setup/status` (official JSON contract).
- **dsh CLI** (`/root/runtime/deepseek-harness/bin/dsh`) for DeepSeek Harness, plus the official `@openviking/dsh-memory-plugin` bundle installed on demand from `volcengine/OpenViking` (domestic GitHub raw mirror list first; self-contained peer deps for `@deepseek-ai/dsh-llm`/`dsh-tools` plus all transitive `@deepseek-ai/*` packages synced as ESM-safe real copies (not symlinks — Node.js v22 ESM resolver does not follow symlinks for bare specifier imports)) — installed into `web`/`dsh-tui` profile `node_modules` + `dsh.profile.bundles`, no pnpm needed.
- API script conventions are Bash + `curl` + `python3` only.

## Plugin Sources (on-demand, domestic-first)

The skill ships **no plugin code** — industry convention is to install dependent plugins at
integrate time from the ecosystem registry. Every `integrate.sh` run provisions the plugins
it needs on demand (see `scripts/common.sh`):

1. **npm-published plugins** (`@openviking/opencode-plugin`, `@openviking/openclaw-plugin`)
   are installed via `npm install` using the **domestic-first registry list**
   (`mirrors.huaweicloud.com/repository/npm/` → `registry.npmmirror.com` →
   `registry.npmjs.org`); the first reachable registry wins.
2. **GitHub-only plugins** (`@openviking/dsh-memory-plugin`,
   `@openviking/pi-coding-agent-extension` — not yet on npm) are fetched from the official
   `volcengine/OpenViking` repo through the **domestic-first raw mirror list**
   (`ghfast.top` → `gh-proxy.com` → `raw.githubusercontent.com`), with the GitHub API used
   only for commit/tree metadata (domestic proxies 403 on the API).
3. **Source check is retained** — every downloaded file is verified **byte-for-byte against
   the authoritative GitHub blob SHA** from the official tree, so content is only accepted
   if it matches upstream regardless of which mirror served the bytes.
4. **Changed-files-only download** — the GitHub tree API is used to diff the previously
   installed commit vs upstream; only changed/new files are downloaded
   (with retry/backoff). If nothing under the plugin dir changed, only the recorded
   `.openviking-sync` commit is bumped — no download.
5. **Offline resilience** — installed copies live under `/root/runtime/` (outside the
   skill). If upstream is unreachable, the existing installed copy is reused as-is (warn),
   so integration never breaks on network hiccups.
6. **Fallthrough for OpenCode/OpenClaw** — plugin runtime installs sit at
   `/root/runtime/opencode/openviking-plugin` and `/root/runtime/openclaw/openviking-plugin-source`
   respectively, giving each agent `npm first → on-demand runtime copy` semantics.
7. **Cache-first on sandbox restart** (stop+start / undeploy+deploy) — template
   `start.sh` blocks use a 3-tier cache strategy to avoid re-downloading plugins on
   every boot:
   - **Tier 1 (already installed)**: Plugin already in sandbox `node_modules` → skip
     entirely (survives stop+start). Logs `cache hit`.
   - **Tier 2 (runtime cache)**: Copy from `/root/runtime/<agent>/...` persistent
     cache → no network call (survives undeploy+deploy, since `/root/runtime/` is
     outside the sandbox lifecycle).
   - **Tier 3 (online fallback)**: `npm install` / ClawHub → only on first integrate
     or cache miss. Logs `Cache miss`.
   - **DeepSeek Harness peer deps**: The 193-package `@deepseek-ai/*` sync loop is
     guarded by a `.openviking-peers-synced` marker file — if present, the entire
     copy loop is skipped. Marker is written after first sync completes.
   - **Prime Agent**: Already optimized via `diff -q` check (no change needed).

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

## Scripts (OO Architecture)

The scripts use an **object-oriented design** with a base class, registry pattern,
and per-agent subclasses. Adding a new agent = create one file in `agents/`.

```
scripts/
  lib/                        ── Framework (shared infrastructure)
    ui.sh                     Logging, authorization, dry-run, i18n
    json.sh                   JSON read/write/has/remove helpers
    plugins.sh                Plugin provisioning (npm + GitHub, SHA-1 verified)
    base.sh                   Agent base class: sandbox discovery, backup, confirm,
                              template injection, health check, default interface
    registry.sh               Agent registry: auto-discover, list, validate, dispatch
  agents/                     ── Agent subclasses (one file per agent)
    codearts.sh               CodeArts CLI — MCP in codearts_cli.json
    opencode.sh               OpenCode — plugin + openviking-config.json
    openclaw.sh               OpenClaw — ClawHub plugin + contextEngine
    hermes.sh                 Hermes — built-in memory provider
    jiuwenswarm.sh            JiuwenSwarm — dual-channel (provider + MCP)
    kimicode.sh               KimiCode — MCP via mcp.json
    deepseek_harness.sh       DeepSeek Harness — dsh-memory-plugin bundle
    prime_agent.sh            Prime Agent — pi-coding-agent-extension
  integrate.sh                Thin entry point → registry dispatch (80 lines, was 1919)
  unbind.sh                   Thin entry point → registry dispatch (74 lines, was 1084)
  status.sh                   Thin entry point → registry dispatch (122 lines, was 345)
  unset.sh                    Alias for unbind.sh
  verify_mcp.sh               MCP protocol handshake (unchanged)
  common.sh                   Backward-compat shim → sources lib/*.sh
```

### OO Design

- **Base class** (`lib/base.sh`): defines `agent::discover_sandbox`, `agent::backup_config`,
  `agent::confirm`, `agent::has_injection`, `check_ov_health`, `create_ov_config`, and
  default interface stubs (`agent::default_integrate/unbind/status`).
- **Agent metadata** via associative array `AGENT_META[name, sandbox_pattern, template_path, mechanism, ...]`,
  populated by each subclass's `agent_<name>_register()`.
- **Registry** (`lib/registry.sh`): `registry_discover()` auto-sources all `agents/*.sh`,
  `registry_dispatch(agent, method)` calls `agent_<name>_<method>()` with fallback to base.
- **Subclass override**: each `agents/<name>.sh` defines `agent_<name>_integrate/unbind/status`,
  calling base class methods for shared operations (backup, confirm, sandbox lookup).
- **Entry points** (integrate/unbind/status.sh): parse CLI args → discover agents → dispatch.
  No agent-specific logic in entry points — all in subclasses.

All scripts are idempotent and create `.bak.<timestamp>` backups before each modification.
