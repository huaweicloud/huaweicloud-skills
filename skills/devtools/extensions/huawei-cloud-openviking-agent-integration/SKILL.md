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
  version: 1.2.2
  license: MIT
  category: devtools
---

# Huawei Cloud Agent Integration (OpenViking Long-Term Memory)

Integrate / unbind OpenViking long-term memory for coding agents running in bwrap sandboxes (`/root/job-envs/sandboxes/`). Every agent uses its **native mechanism** (MCP, HTTP memory provider, TS extension hooks, settings.json), so integration survives agent upgrades. Writes are **template-level persistent**: config is injected into `/root/template/<agent>/start.sh`, so sandbox `stop + start` preserves the integration.

## Supported Agents

| Agent | Mechanism |
|-------|-----------|
| CodeArts CLI | `@openviking/opencode-plugin` → `.codeartsdoer/` |
| OpenCode | `@openviking/opencode-plugin` (npm mirror → GitHub fallback) |
| OpenClaw | `clawhub:@openviking/openclaw-plugin` + `contextEngine` slot (disables `session-memory` hook, denies `memory_search`) |
| Hermes | Built-in `memory.provider: openviking` (HTTP REST, no MCP) |
| WorkSwarm | Dual-channel: native provider + MCP (15 tools) + code-mode patch |
| KimiCode | hooks + MCP (session lifecycle) — `config.toml [[hooks]]` → `ov-kimi-hook.sh` + MCP via `mcp.json` |
| DeepSeek Harness | `@openviking/dsh-memory-plugin` bundle (on-demand from GitHub) |
| Prime Agent | `@openviking/pi-coding-agent-extension` (on-demand from GitHub) |

Per-agent config paths and details: [references/agent-configs.md](references/agent-configs.md).

## Prerequisites

- OpenViking server healthy: `curl -s http://127.0.0.1:1933/health` → `healthy`.
- Target sandbox exists under `/root/job-envs/sandboxes/`.
- Host tools: `curl`, `python3`, `bash`; `npm` for OpenCode/OpenClaw; `pip install --upgrade "mcp>=2.0"` for `verify_mcp.sh`.
- No Huawei Cloud IAM required — operates on local bwrap sandboxes only.

## 参数 (Parameters)

| Flag | Required | Meaning |
|------|----------|---------|
| `--agent <name>` | Yes (unless `--all`) | Target agent |
| `--all` | Yes (unless `--agent`) | Operate on all 8 agents |
| `--endpoint <url>` | No | OpenViking URL (default `http://127.0.0.1:1933`) |
| `--api-key <key>` | No | For auth-mode servers. Never echo in chat. Must be consumed by an agent config or `verify_mcp.sh`; an unconsumed `--api-key` is reported as a warning. |
| `--dry-run` | No | Show changes without applying |
| `--yes` / `-y` | No | Skip confirmation (automation only) |
| `--json` | No | `status.sh`: machine-readable output |

## 核心命令

| 功能 | 命令 |
|------|------|
| 查看状态 | `scripts/status.sh`（`--json` / `--agent <name>`） |
| 验证 MCP | `scripts/verify_mcp.sh` |
| 集成 | `scripts/integrate.sh --agent <name> [--endpoint URL] [--dry-run] [--yes]`（或 `--all`） |
| 解绑 | `scripts/unbind.sh --agent <name> [--dry-run] [--yes]`（或 `--all`） |

## Workflow

```bash
SKILL_DIR=/root/.agents/skills/huawei-cloud-openviking-agent-integration
$SKILL_DIR/scripts/status.sh          # per-agent: template+live / template only / live only / none
$SKILL_DIR/scripts/verify_mcp.sh      # full MCP handshake (initialize → tools/list → health)
$SKILL_DIR/scripts/integrate.sh --agent <name> [--yes]
$SKILL_DIR/scripts/unbind.sh  --agent <name> [--yes]
```

1. **Status first** — never claim integrated before `status.sh` confirms (do not fabricate state).
2. **Verify MCP** — `verify_mcp.sh` before integration.
3. **Integrate / Unbind** — each requires explicit `confirm` (or `--yes`); `--dry-run` previews safely.
4. States: `template + live` = active; `template only` = activates on restart; `live only` = **lost on restart** (warn user).

## Authorization & Safety

- `integrate.sh` / `unbind.sh` require explicit confirmation; never edit agent configs directly — go through the skill scripts.
- Every config modification creates `.bak.<timestamp>` (keep 5) for rollback.
- `--api-key` values must never appear in output.

## 能力边界（Cannot Do）

本技能只做"OpenViking 记忆 ↔ 编码 agent 的集成/解绑/状态/验证"。以下操作**明确不做**，遇到请改走对应路径或明确报错：

- 不直接读写 agent 配置文件、sandbox 内业务数据或用户代码——一律通过 `scripts/integrate.sh` / `unbind.sh` 等入口执行。
- 不删除、不修改用户自装的第三方包/目录/数据。卸载只清理 OpenViking 自身产物（`@openviking/*` 插件、注入的配置段、OV 专属目录）；`node_modules` 整目录删除等越界行为是缺陷，不执行。
- 服务器不可达/健康检查失败时**不报告成功**：`integrate.sh`、`unbind.sh`、`verify_mcp.sh` 均先做健康门禁，失败即失败（exit 非 0），绝不假成功。
- `--dry-run` 只预览改动，不写任何持久文件；预览后续真实执行仍需确认。
- `--api-key` 必须被某个 agent 配置或验证流程实际消费；若传入却无处消费，脚本会告警（而非静默忽略）。
- 不做 embedding 模型切换、向量库重建、服务器自身配置变更——那是 `huawei-cloud-openviking-embedding-switch` 等技能的范围。
- 不支持在集成/解绑过程中创建或修改 OpenViking 账号、用户、权限体系。
- 不承诺"查看 → 已集成"：一律以 `status.sh` 实测结果为准，禁止凭模板猜测 live 状态。

## References

| Document | When to read |
|----------|--------------|
| [agent-configs.md](references/agent-configs.md) | Per-agent config paths/formats, MCP tools, server info |
| [notes.md](references/notes.md) | Guardrails, env vars, sandbox restart, plugin sources, troubleshooting, adding a new agent |