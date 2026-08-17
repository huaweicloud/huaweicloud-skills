# Agent Configuration Reference

Detailed documentation of each agent's config file location, format, persistence mechanism, and integration/unbinding specifics.

## Persistence Patterns Summary

| Pattern | Agents | Why |
|---------|--------|-----|
| **Template-level** | OpenCode, Hermes, KimiCode, DeepSeek Harness | `start.sh` recreates config from scratch, wiping additions |
| **Sandbox file (preserved)** | CodeArts | `start.sh` uses `json.load()` → modify → `json.dump()`, preserves extra keys |
| **Sandbox file (first-copy)** | JiuwenSwarm | `start.sh` only copies config on first start, never overwrites |
| **Sandbox (bwrap, ephemeral)** | OpenClaw | Official plugin installed via npm (Huawei Cloud mirror) in template `start.sh`. Gateway runs in bwrap sandbox with ephemeral `OPENCLAW_STATE_DIR=/tmp/.openclaw`. Plugin install runs inside bwrap on every start (idempotent). Must sync `start.sh` to sandbox workspace after template update. |

---

## 1. CodeArts CLI

- **Sandbox pattern:** `codearts-*`
- **Config file:** `<sandbox>/.codeartsdoer/codearts_cli.json`
- **Format:** JSON (OpenCode-compatible schema)
- **Integration:** Add `mcp.openviking` object
- **Persistence:** Sandbox file — `start.sh` reads existing config with `json.load()`, only overwrites model field, then `json.dump()`. MCP additions preserved.
- **Restart required:** Yes

### Config structure
```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "openai-MaaS/glm-5.2",
  "mcp": {
    "openviking": {
      "type": "remote",
      "url": "http://127.0.0.1:1933/mcp",
      "enabled": true,
      "oauth": false,
      "timeout": 30000
    }
  }
}
```

---

## 2. OpenCode

- **Sandbox pattern:** `opencode-*`
- **Config file:** `<sandbox>/.config/opencode/opencode.json`
- **Format:** JSON
- **Integration:** Official `@openviking/opencode-plugin` via npm (Huawei Cloud mirror) + `openviking-config.json`. Plugin SDK pre-installed during integration to avoid startup delay.
- **Sandbox env:** `env.yaml` updated to add `/usr/local/nodejs` to `readablePaths` and `PATH` to `extraEnv` (npm/node must be accessible inside bwrap). npm install is non-fatal — opencode starts even if npm is unavailable.
- **Persistence:** **Template-level** (dual-write)
- **Restart required:** Yes

### Official-Equivalent Approach

Installs `@openviking/opencode-plugin` via npm (Huawei Cloud mirror), pre-installs plugin SDK during integration:

1. **MCP server** — remote MCP at `http://127.0.0.1:1933/mcp`
2. **Enhanced system prompt** — `agent.build.prompt` encodes auto-recall + auto-capture + repo context behavior
3. **`openviking-config.json`** — mirrors official plugin defaults at `~/.config/opencode/openviking-config.json`

### ⚠️ Persistence: Template-Level

`start.sh` recreates `opencode.json` from scratch on every start:
```python
cfg = {"$schema": "...", "provider": {...}, "model": f"jobmodel/{model}"}
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
```

This wipes MCP. Fix: inject re-injection block into template `start.sh`.

### Template injection (in `/root/template/opencode/start.sh`)

The injection block:
1. Re-injects MCP server config into `opencode.json`
2. Re-injects enhanced agent prompt (auto-recall + auto-capture + repo context protocols)
3. Creates `openviking-config.json` with official plugin defaults

### openviking-config.json

```json
{
  "enabled": true,
  "timeoutMs": 30000,
  "repoContext": { "enabled": true, "cacheTtlMs": 60000 },
  "autoRecall": {
    "enabled": true,
    "limit": 15,
    "scoreThreshold": 0.05,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recall": {
    "quotas": { "preferences": 10, "events": 3, "entities": 5 },
    "maxChars": 20000
  },
  "commitTokenThreshold": 20000,
  "commitKeepRecentCount": 10,
  "profileTokenBudget": 10000,
  "resumeContextBudget": 32000
}
```

#### Recall Quotas (critical for preference retrieval)

The `recall` tool uses **type quotas** — per-type result limits that control how many memories of each type are returned. Without explicit quotas, defaults give `preferences` only 1 slot, and `maxChars` defaults to 6500 (events + entities fill the budget, preferences get truncated).

| Field | Default (broken) | Skill default (fixed) | Why |
|-------|-----------------|----------------------|-----|
| `quotas.preferences` | 1 | **10** | Users have many preferences; 1 slot misses most |
| `quotas.events` | unlimited | **3** | Events are verbose; cap to leave room for preferences |
| `quotas.entities` | unlimited | **5** | Entities are verbose; cap to leave room for preferences |
| `maxChars` | 6500 | **20000** | With more preferences returned, need larger char budget |

**Symptom of missing quotas**: `recall` returns only 1 preference (e.g. just `obs_bucket_name`) instead of all stored preferences. Other agents can't find user preferences like region, flavor, billing preferences, etc.

### File locations
| File | Path | Persistent? |
|------|------|-------------|
| Template start.sh | `/root/template/opencode/start.sh` | ✅ Yes |
| Sandbox config | `<sandbox>/.config/opencode/opencode.json` | ❌ Overwritten on start |
| openviking-config.json | `<sandbox>/.config/opencode/openviking-config.json` | ✅ Created by injection if missing |

## 3. OpenClaw

- **Sandbox pattern:** `openclaw-*`
- **Config file:** Template `start.sh` injection (installs plugin inside gateway bwrap). Config lives at `/tmp/.openclaw/openclaw.json` inside bwrap sandbox (ephemeral).
- **Format:** JSON (managed by `openclaw` CLI)
- **Integration:** Official `@openviking/openclaw-plugin` via npm (Huawei Cloud mirror)
- **Persistence:** Template-level injection in `start.sh` (re-installs on every gateway start, idempotent)
- **Restart required:** Yes (gateway restart)

### Approach

Installs the official `@openviking/openclaw-plugin` from npm using the Huawei Cloud mirror (`https://mirrors.huaweicloud.com/repository/npm/`). The plugin is available on both the official npm registry and the Huawei Cloud mirror; the mirror is preferred for faster downloads in Huawei Cloud environments.

The install command runs **inside** the gateway's bwrap sandbox (via `start.sh` injection), so the plugin files land in `$OPENCLAW_STATE_DIR/npm/projects/` directory. The install is idempotent — always runs (bwrap /tmp is ephemeral, plugin is lost on every restart).

### Integration steps
1. Inject an install block into template `start.sh` (before gateway start)
2. The block:
   - Sets `NPM_CONFIG_REGISTRY` to the Huawei Cloud npm mirror
   - Runs `openclaw plugins install @openviking/openclaw-plugin --acknowledge-clawhub-risk`
   - Exports `OPENVIKING_BASE_URL` / `OPENVIKING_API_KEY` / `OPENVIKING_ENDPOINT` env vars
   - Sets `plugins.entries.openviking.baseUrl` / `apiKey` via `config set`
   - Runs `openclaw plugins enable openviking` (sets enabled=true + contextEngine slot)
   - Sets `plugins.allow: ["openviking"]` to explicitly trust the non-bundled plugin
   - Creates supplementary `AGENTS.md` in workspace for explicit tool usage guidance
3. Sync updated `start.sh` to sandbox workspace
4. Clean up any legacy direct-config-write or MCP injection (backward compatibility)

### Plugin behavior

The plugin registers as the `contextEngine` slot, providing:
- **Auto-recall**: Automatically recalls relevant context before each response
- **Auto-capture**: Automatically captures important information after exchanges
- **MCP tools**: Exposes OpenViking MCP tools (search, recall, remember, read, etc.)

### File locations
| File | Path | Persistent? |
|------|------|-------------|
| Template start.sh | `/root/template/openclaw/start.sh` | ✅ Yes |
| Plugin code | `$OPENCLAW_STATE_DIR/npm/projects/openviking-*` | ❌ Ephemeral (re-installed on every start) |
| Plugin config | `$OPENCLAW_STATE_DIR/openclaw.json` → `plugins.entries.openviking` | ❌ Ephemeral (re-set on every start) |
| Plugin trust | `$OPENCLAW_STATE_DIR/openclaw.json` → `plugins.allow` | ❌ Ephemeral (re-set on every start) |
| Env vars | `OPENVIKING_BASE_URL` / `OPENVIKING_API_KEY` / `OPENVIKING_ENDPOINT` | ❌ Ephemeral (re-exported on every start) |
| AGENTS.md | `$OPENCLAW_STATE_DIR/workspace/AGENTS.md` | ❌ Ephemeral (re-created on every start) |

- **npm source:** `@openviking/openclaw-plugin` from `https://mirrors.huaweicloud.com/repository/npm/`
- **Plugin slot:** `contextEngine` (full lifecycle: auto-recall + auto-capture)
- **Version requirements:** Node.js >= 22, OpenClaw >= 2026.5.27

---

## 4. Hermes

- **Sandbox pattern:** `hermes-*`
- **Config file:** `<sandbox>/.hermes/config.yaml`
- **Format:** YAML
- **Integration:** Add `memory.provider: openviking` via template-level injection
- **Persistence:** **Template-level** (dual-write)
- **Restart required:** Yes
- **Protocol:** HTTP REST API (not MCP) — Hermes has built-in OpenViking memory provider

### ⚠️ Persistence: Template-Level

Startup chain:
```
/root/template/hermes/start.sh ──copy──▶ sandbox/process_dir/start.sh ──exec──▶ $HOME/.hermes/config.yaml
```

The template `start.sh` overwrites `config.yaml` every time with `echo "model: ..." > config.yaml`. Writing to sandbox-internal `config.yaml` is lost on restart.

### Template injection (in `/root/template/hermes/start.sh`)
```bash
# ── OpenViking memory provider (added by huawei-cloud-openviking-agent-integration skill) ──
if ! grep -q "openviking" "$HOME/.hermes/config.yaml" 2>/dev/null; then
  cat >> "$HOME/.hermes/config.yaml" << 'OVYAML'

# OpenViking memory provider
memory:
  provider: openviking
  openviking:
    endpoint: http://127.0.0.1:1933
OVYAML
fi
export OPENVIKING_ENDPOINT=http://127.0.0.1:1933
```

### Resulting config.yaml (after Hermes start)
```yaml
model: glm-5.2

# OpenViking memory provider
memory:
  provider: openviking
  openviking:
    endpoint: http://127.0.0.1:1933
```

### File locations
| File | Path | Persistent? |
|------|------|-------------|
| Template start.sh | `/root/template/hermes/start.sh` | ✅ Yes |
| Sandbox config | `<sandbox>/.hermes/config.yaml` | ❌ Ephemeral |

---

## 5. JiuwenSwarm

- **Sandbox pattern:** `jiuwenswarm-*`
- **Config file:** `<sandbox>/.jiuwenswarm/config/config.yaml`
- **Format:** YAML with environment variable defaults
- **Integration:** Change `memory.engine` and `memory.external.provider` defaults
- **Persistence:** Sandbox file — `start.sh` only copies config on first start, never overwrites
- **Restart required:** Yes
- **Protocol:** HTTP REST API (not MCP) — native external memory system

### Config changes
```yaml
memory:
  engine: ${MEMORY_ENGINE:-external}          # Changed from builtin
  external:
    provider: ${MEMORY_EXTERNAL_PROVIDER:-openviking}  # Changed from empty
    openviking:
      endpoint: ${OPENVIKING_ENDPOINT:-http://127.0.0.1:1933}
      api_key: ${OPENVIKING_API_KEY:-}
      account: ${OPENVIKING_ACCOUNT:-root}
      user: ${OPENVIKING_USER:-default}
```

### Engine modes
| engine | provider | Effect |
|--------|----------|--------|
| builtin | * | Only built-in memory (default) |
| external | openviking | Only OpenViking memory |
| both | openviking | Built-in + OpenViking simultaneously |
| none | * | All memory disabled |

---

## 6. KimiCode

- **Sandbox pattern:** `kimicode-*`
- **Config file:** `/root/runtime/kimicode/data/config.toml`
- **Format:** TOML
- **Integration:** Add `[mcp_servers.openviking]` section via template-level injection
- **Persistence:** **Template-level** (dual-write)
- **Restart required:** Yes

### ⚠️ Persistence: Template-Level

`start.sh` recreates `config.toml` from scratch on every start (writes model/provider/models sections via Python), wiping any MCP server config. Fix: inject re-injection block into template `start.sh`.

### Template injection (in `/root/template/kimicode/start.sh`)
```bash
# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──
if [[ -f "$CONFIG_FILE" ]]; then
  cat >> "$CONFIG_FILE" << 'MCPEOF'

[mcp_servers.openviking]
type = "http"
url = "http://127.0.0.1:1933/mcp"
MCPEOF
fi
```

### Resulting config.toml (after KimiCode start)
```toml
# Managed by job-env-manager start.sh — MaaS provider config
default_model = "glm-5.2"

[providers.maas]
type = "openai"
base_url = "https://tokenhub.developer.huaweicloud.com/v2"
api_key = "..."

[models."glm-5.2"]
provider = "maas"
model = "glm-5.2"
max_context_size = 262144

[mcp_servers.openviking]
type = "http"
url = "http://127.0.0.1:1933/mcp"
```

### File locations
| File | Path | Persistent? |
|------|------|-------------|
| Template start.sh | `/root/template/kimicode/start.sh` | ✅ Yes |
| Runtime config | `/root/runtime/kimicode/data/config.toml` | ❌ Overwritten on start |

---

## 7. DeepSeek Harness (dsh)

- **Sandbox pattern:** `deepseek-harness-*`
- **Config home:** `<sandbox>/.dsh` (generated by `start.sh` on boot)
- **Profiles:** `web` (HTTP UI, port 13079) and `cc-tui` (terminal TUI)
- **Integration:** Native MCP client — `@deepseek-ai/dsh-mcp-client` (bundled with dsh core) connected to the OpenViking streamable-HTTP endpoint. No official OpenViking plugin exists (official list: Claude Code / Trae / Cursor / ChatGPT / Codex / OpenCode / Manus / Claude.ai).
- **MCP entry (per profile):** `serverName: openviking`, `transport: streamable-http`, `url: http://127.0.0.1:1933/mcp`. Tools surface to the model as `mcp__openviking__<name>`.
- **Persistence:** **Template-level** — `.dsh` is (re)generated by `start.sh` on boot, so the integration block lives in `/root/template/deepseek-harness/start.sh`.
- **Restart required:** Yes. dsh web profile has `hmr.disabled: true` — config changes only apply on process restart. Template changes apply after sandbox `stop + start` (re-runs `start.sh`).

### Strategy (mirrors official plugin lifecycle)

dsh has no hook runtime (official plugins hook `chat.message` / `session.created` / `session.compacting` / `stop`). The strategy maps those lifecycle hooks to **model-driven protocols** delivered through every channel dsh supports:

| Official plugin hook | dsh equivalent |
|---|---|
| session.created → profile + memory index injection | SKILL/AGENTS: `recall` preferences/events/entities quotas (10/3/5, maxChars 20000) at session start; `add_resource` on repo path (cacheTtlMs 60000) |
| chat.message / UserPromptSubmit → auto-recall | SKILL/AGENTS: `recall`/`search` before responding — minQueryLength 3, scoreThreshold 0.35, tokenBudget 2000, maxContentChars 500, preferAbstract |
| repoContext.refreshRepos → repo context in system prompt | `add_resource` repo path at session start + `search` prior work |
| auto-capture after each turn | `remember` durable facts after meaningful exchanges (~commitTokenThreshold 20000 semantics, keep ~10 highlights) |
| session.compacting / stop → commit | `remember` compact summary before compaction / session end; rebuild via `recall` on resume |
| viking-uri-guard (block local reads of viking://) | SKILL/AGENTS rule: never read viking:// via local fs tools — use `read`/`glob`/`grep`/`search` |

Behavior knobs live in `$DSH_HOME/openviking-config.json` (mirrors official plugin defaults: autoRecall limit 10, quotas preferences 10/events 3/entities 5, commitTokenThreshold 20000, profileTokenBudget 10000, resumeContextBudget 32000).

### Delivery channels (why web guidance works)

| Channel | File | web | cc-tui |
|---|---|---|---|
| MCP tools | patch `mcp-openviking` insert | ✅ | ✅ |
| Persona directive | patch `system-prompt.persona` (mentions mcp__openviking__*) | ✅ | ✅ |
| Skill protocol | `.dsh/skills/openviking/SKILL.md` | ✅ re-enabled `skill-filesystem` | ✅ |
| AGENTS.md | `.dsh/AGENTS.md` | ✅ re-enabled `agent-instructions` | ✅ |

> ⚠️ dsh-web-app ships `agent-instructions.disabled: true` and `skill-filesystem.disabled: true` for the web profile. The patch re-enables both with `disabled: false` entries (verified via `dsh --profile web --dump-config`), so the protocol reaches the web model too — otherwise web had MCP tools but no guidance on when to use them.

### Profile patch (in `.dsh/profiles/{web,cc-tui}/cordis.patch.yml`)
```yaml
- insert:
    - id: mcp-openviking
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: openviking
        transport: streamable-http
        url: http://127.0.0.1:1933/mcp

- id: system-prompt
  config:
    persona: >-
      You are a coding agent powered by the {{model}} model. Your working
      directory is {{cwd}}. You have OpenViking long-term memory via
      mcp__openviking__* tools: recall relevant past context before
      answering, save durable outcomes after meaningful work, and index
      repo context at session start (follow the openviking skill protocol).
```
Web only additionally: `- id: agent-instructions` / `- id: skill-filesystem` with `disabled: false`.

> Note: dsh auto-generates an empty `[]` body in the web patch — the injection replaces it, keeping the header comment. Files are refreshed unconditionally on every boot; patches are idempotent merges.

### File locations
| File | Path | Persistent? |
|------|------|-------------|
| Template start.sh | `/root/template/deepseek-harness/start.sh` | ✅ Yes (contains the OV injection block) |
| Behavior knobs | `<sandbox>/.dsh/openviking-config.json` | ❌ Recreated by start.sh on boot |
| Live profiles | `<sandbox>/.dsh/profiles/{web,cc-tui}/cordis.patch.yml` | ❌ Recreated by start.sh on boot |
| Live skill + AGENTS.md | `<sandbox>/.dsh/skills/openviking/SKILL.md`, `<sandbox>/.dsh/AGENTS.md` | ❌ Recreated by start.sh on boot |

---

## Available MCP Tools

When integrated via MCP, OpenViking exposes 13 tools:

| Tool | Description |
|------|-------------|
| `find` | Fast semantic retrieval without session context |
| `search` | Deep semantic retrieval with session context and intent analysis |
| `recall` | Type-quota memory recall (events, entities, preferences, experiences) |
| `read` | Read content from viking:// URIs |
| `list` | List files under viking:// directory |
| `remember` | Store information to long-term memory |
| `add_resource` | Add local file or URL as resource |
| `list_watches` | List auto-refresh subscriptions |
| `cancel_watch` | Cancel a watch task by URI |
| `grep` | Regex content search in viking:// files |
| `glob` | Glob pattern file matching |
| `forget` | Permanently delete a viking:// URI |
| `health` | Check OpenViking server health |

---

## OpenViking Server

- **Sandbox:** `openviking-*`
- **Config:** `<sandbox>/process_dir/ov.conf`
- **Endpoint:** `http://127.0.0.1:1933`
- **MCP endpoint:** `http://127.0.0.1:1933/mcp`
- **Auth mode:** `dev` (no API key required for localhost)
- **Version:** 0.4.12 (server), 1.29.0 (MCP)
- **Protocol:** Streamable HTTP (JSON-RPC 2.0 over SSE)
- **Embedding:** Local bge-small-zh-v1.5 via llama-server on port 18200

### Health check
```bash
curl http://127.0.0.1:1933/health
# {"status":"ok","healthy":true,"version":"0.4.12","auth_mode":"dev"}
```
