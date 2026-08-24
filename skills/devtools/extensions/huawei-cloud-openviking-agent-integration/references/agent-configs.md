# Agent Configuration Reference

Detailed documentation of each agent's config file location, format, persistence mechanism, and integration/unbinding specifics.

## Persistence Patterns Summary

| Pattern | Agents | Why |
|---------|--------|-----|
| **Template-level** | OpenCode, Hermes, KimiCode, DeepSeek Harness | `start.sh` recreates config from scratch, wiping additions |
| **Sandbox file (preserved)** | CodeArts | `start.sh` uses `json.load()` → modify → `json.dump()`, preserves extra keys |
| **Sandbox file (first-copy)** | JiuwenSwarm | `start.sh` only copies config on first start, never overwrites |
| **Sandbox (bwrap, ephemeral)** | OpenClaw | Official plugin installed in template `start.sh` (ClawHub primary, Huawei npm mirror fallback) + `openviking setup --json` contract. Gateway runs in bwrap sandbox with ephemeral `OPENCLAW_STATE_DIR=/tmp/.openclaw`. Plugin install runs inside bwrap on every start (idempotent). Must sync `start.sh` to sandbox workspace after template update. |

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
- **Integration:** Official `@openviking/opencode-plugin` (installed on demand: npm Huawei Cloud mirror first, on-demand GitHub raw mirror fallback; deployed to `$RUNTIME/opencode/openviking-plugin/` → sandbox `node_modules/@openviking/opencode-plugin`) + `@opencode-ai/plugin` SDK via npm (domestic-first registry) + `openviking-config.json`. No install needed for the plugin itself at boot beyond `npm install` (pure .mjs, zero deps).
- **Sandbox env:** `env.yaml` updated to add `/usr/local/nodejs` to `readablePaths` and `PATH` to `extraEnv` (npm/node must be accessible inside bwrap). npm install is non-fatal — opencode starts even if npm is unavailable.
- **Persistence:** **Template-level** (dual-write)
- **Restart required:** Yes

### Official-Equivalent Approach

Installs `@openviking/opencode-plugin` on demand (npm Huawei Cloud mirror first; on-demand runtime copy fallback — pure .mjs, zero runtime deps), pre-installs `@opencode-ai/plugin` SDK via npm:

1. **On-demand plugin** — `npm install` via domestic-first registry into the sandbox, copied from `$RUNTIME/opencode/openviking-plugin/` to `node_modules/@openviking/opencode-plugin/` as the offline fallback on each boot
2. **Plugin SDK** — `@opencode-ai/plugin` installed via npm (Huawei Cloud mirror first, peer dep from OpenCode ecosystem)
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

Aligned with the official `@openviking/opencode-plugin` fields (`examples/opencode-plugin/lib/config.mjs`, commit `592c0fe`). `recallLimit` / `recallMaxContentChars` are the official top-level aliases that scale the server-side recall budget — the plugin does **not** read a `recall.quotas` object.

```json
{
  "enabled": true,
  "timeoutMs": 30000,
  "repoContext": { "enabled": true, "cacheTtlMs": 60000 },
  "autoRecall": {
    "enabled": true,
    "limit": 10,
    "scoreThreshold": 0.35,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recallLimit": 15,
  "recallMaxContentChars": 20000,
  "commitTokenThreshold": 20000,
  "commitKeepRecentCount": 10,
  "profileTokenBudget": 10000,
  "resumeContextBudget": 32000
}
```

#### Recall budget (official fields)

The plugin derives per-type quotas server-side from `autoRecall.limit` (official `recall-core.mjs`: coding weights `events/entities/preferences/experiences/resources/skills`). `recallLimit` is the legacy top-level alias for the same knob; `recallMaxContentChars` scales the character budget. The skill sets `recallLimit: 15` + `recallMaxContentChars: 20000` to favor preference recall — an intentional increase over the plugin's default (`limit: 10`), expressed through the fields the plugin actually reads.

| Field | Official default | Skill value | Why |
|-------|-----------------|-------------|-----|
| `autoRecall.limit` | 10 | 10 (default) | Keep official default for coding-allocation balance |
| `recallLimit` | 10 | **15** | Scale the total retrieval budget so preferences keep more slots |
| `recallMaxContentChars` | (derived from limit) | **20000** | Allow more preference content to be returned |

**Symptom of a too-small budget**: `recall`/auto-recall returns only 1 preference (e.g. just `obs_bucket_name`) instead of all stored preferences. Fix via `recallLimit` / `recallMaxContentChars` — never via a `recall.quotas` object, which the official plugin ignores.

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
- **Integration:** Official `clawhub:@openviking/openclaw-plugin` (ClawHub primary → domestic npm mirror fallback → on-demand source build fallback from `/root/runtime/openclaw/openviking-plugin-source`) + `openviking setup --json` contract + `contextEngine` slot. On-demand source installed to `$RUNTIME/openclaw/openviking-plugin-source/` for offline build fallback.
- **Persistence:** Template-level injection in `start.sh` (re-installs on every gateway start, idempotent)
- **Restart required:** Yes (gateway restart)

### Approach

Follows the official **INSTALL-AGENT.md** contract:
```
openclaw plugins install clawhub:@openviking/openclaw-plugin   # primary source
openclaw openviking setup --base-url ... [--api-key ...] --json  # write config, machine-readable
openclaw gateway restart
openclaw openviking status --json                                 # verify: configured + slotActive
```
ClawHub is the primary plugin source; if it is unreachable/rate-limited the skill falls back to the Huawei Cloud npm mirror (`plugins install @openviking/openclaw-plugin --acknowledge-clawhub-risk`). The install runs **inside** the gateway's bwrap sandbox (via `start.sh` injection), so plugin files land in `$OPENCLAW_STATE_DIR/npm/projects/` — idempotent, and re-run on every boot because bwrap /tmp is ephemeral.

### Integration steps
1. Inject an install block into template `start.sh` (before gateway start)
2. The block:
   - Tries `openclaw plugins install clawhub:@openviking/openclaw-plugin`, falls back to npm mirror
   - Exports `OPENVIKING_BASE_URL` / `OPENVIKING_API_KEY` / `OPENVIKING_ENDPOINT` env vars
   - Runs `openclaw openviking setup --base-url ... --json` and branches per the official JSON contract:
     - `success: true` → done
     - `action: "slot_blocked"` → only retries with `--force-slot` if the user approved at integrate time
     - `action: "error"` → report, do not treat as success
     - `health.ok: false` → only writes with `--allow-offline` if approved
     - root-key (`keyProbe.keyType: root_key`) → report that `--account-id`/`--user-id` are required
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

- **Plugin source:** official ClawHub (`clawhub:@openviking/openclaw-plugin`) primary; Huawei Cloud npm mirror as fallback
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
- **Integration:** Dual-channel — native memory provider (`memory.engine: both` + `memory.external.provider: openviking`) **+ MCP server** (`mcp.servers` with `streamable-http` transport) + `auto_memory_enabled: true`
- **Persistence:** Sandbox file — `start.sh` only copies config on first start, never overwrites. Template `start.sh` exports env vars + re-applies config defaults if missing.
- **Restart required:** Yes
- **Protocol:** HTTP REST (native external memory system) + Streamable HTTP MCP (full 13-tool access)

### Design: dual-channel (native memory provider + MCP)

JiuwenSwarm has a built-in external memory system that natively supports OpenViking via HTTP REST,
providing auto-recall and auto-store. However, the native `OpenVikingMemoryProvider` only exposes
5 tools (`viking_search`, `viking_read`, `viking_browse`, `viking_remember`, `viking_add_resource`)
and its `prefetch()` is limited (top_k=5, only memories+resources types, no score threshold,
no token budget, no type-quota recall).

The MCP server injection adds the remaining 8 tools — critically `search` (with `mode="context"`
for token-budgeted cross-type digest) and `recall` (type-quota across events/entities/preferences/
experiences) — bringing the total to 13 tools, matching what other agents (OpenCode, KimiCode,
CodeArts, Hermes) get via MCP.

| Channel | Mechanism | Role | When |
|---------|-----------|------|------|
| **Native** | `memory.engine: both` + `memory.external.provider: openviking` | Auto-recall at conversation start, auto-store after exchanges | Automatic — no agent action needed |
| **MCP** | `mcp.servers` entry (`streamable-http` transport) | Full 13-tool access: `search`, `recall`, `find`, `read`, `remember`, `add_resource`, `grep`, `glob`, `forget`, `health`, `list`, `list_watches`, `cancel_watch` | Explicit, targeted operations — especially `search` with `mode="context"` and `recall` for type-quota retrieval |
| **Auto-memory** | `auto_memory_enabled: true` | Automatic memory extraction after exchanges | Background — fire-and-forget |

### Config changes
```yaml
auto_memory_enabled: true                    # Changed from false — enables auto-capture
memory:
  engine: ${MEMORY_ENGINE:-both}              # Changed from builtin (env var override: MEMORY_ENGINE=both)
  external:
    provider: ${MEMORY_EXTERNAL_PROVIDER:-openviking}  # Changed from empty (env var override)
    openviking:
      endpoint: ${OPENVIKING_ENDPOINT:-http://127.0.0.1:1933}
      api_key: ${OPENVIKING_API_KEY:-}
      account: ${OPENVIKING_ACCOUNT:-root}
      user: ${OPENVIKING_USER:-default}
mcp:
  servers:
    - name: openviking                       # Added — MCP server for full 13-tool access
      transport: streamable-http
      url: http://127.0.0.1:1933/mcp
      enabled: true
```

### Engine modes
| engine | provider | Effect |
|--------|----------|--------|
| builtin | * | Only built-in memory (default) |
| external | openviking | Only OpenViking memory |
| both | openviking | Built-in + OpenViking simultaneously |
| none | * | All memory disabled |

### Why MCP was added (native provider limitations)

The native `OpenVikingMemoryProvider` (in `openjiuwen.core.memory.external.openviking_memory_provider`)
has these limitations that the MCP server resolves:

| Capability | Native provider | MCP server |
|------------|----------------|------------|
| `search` with `mode="context"` | ❌ (only `viking_search` → `/api/v1/search/find`) | ✅ Cross-type token-budgeted digest |
| `recall` (type-quota) | ❌ | ✅ Events/entities/preferences/experiences quotas |
| `find` (fast semantic) | ❌ (weak version via `viking_search`) | ✅ |
| `grep` / `glob` | ❌ | ✅ Exact text/filename matching |
| `forget` (delete memory) | ❌ | ✅ |
| `health` (server check) | ❌ | ✅ |
| `list` / `list_watches` / `cancel_watch` | ❌ | ✅ |
| `prefetch()` quality | top_k=5, only memories+resources, no threshold | N/A (MCP tools used explicitly) |
| Auto-recall + auto-store | ✅ (native engine) | N/A (MCP is on-demand) |

### Status detection

`status.sh` checks for both native memory provider and MCP server, reporting granular state:
- `native memory provider + MCP (template + live)` — fully integrated (dual-channel)
- `native memory provider only (MCP missing — re-integrate to add MCP)` — needs re-integrate to add MCP
- `MCP only (native provider not configured)` — partial, needs re-integrate
- `partial` — live only, will be lost on restart (template missing)
- `not_integrated` — no OpenViking integration found

Native provider detection: `memory.engine` contains `both`/`external` AND (`memory.external.provider` contains `openviking` OR template exports `MEMORY_EXTERNAL_PROVIDER=openviking`).
MCP detection: `mcp.servers` contains an entry with `name: openviking`.

### Not used

- **openviking-config.json** — not created. That file is for the `@openviking/opencode-plugin`, which JiuwenSwarm does not use. Recall budget tuning for JiuwenSwarm is handled by the MCP server's built-in defaults.

### Backward compatibility

Unbinding removes both the MCP server entry and native memory provider config, and reverts `auto_memory_enabled` to `false`. The `has_sandbox` detection checks for `name: openviking` (MCP), `MEMORY_ENGINE:-both` / `MEMORY_EXTERNAL_PROVIDER:-openviking` (native provider), and `auto_memory_enabled: true`.

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
- **Profiles:** `web` (HTTP UI, port 13079) and `dsh-tui` (terminal TUI)
- **Integration:** Official OpenViking bundle — `@openviking/dsh-memory-plugin` (source under `examples/dsh-memory-plugin` in the OpenViking repo; not on npm) — installed on demand to `$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin` (`integrate.sh` checks the upstream `volcengine/OpenViking` commit each run and downloads only changed files via the domestic GitHub raw mirror list, each byte-verified against the official blob SHA) with self-contained peer deps for `@deepseek-ai/dsh-llm` + `@deepseek-ai/dsh-tools`. It is installed as a **real package** into each profile's `node_modules/@openviking/dsh-memory-plugin` and registered in `dsh.profile.bundles`; dsh profile-boot composes the plugin's `cordis.patch.yml` (`openviking-memory` group, `group: true`, `isolate.openvikingMemory: true`).
- **No pnpm needed:** direct directory copy + `dsh.profile.bundles` registration (no `link:` dependency — pnpm creates broken relative symlinks from sandbox paths; the real dir in `node_modules` + bundles registration is sufficient and survives `undeploy→deploy` via runtime seed profiles).
- **Plugin behavior (native hooks, no MCP):**
  - `agent/session-start` → inject startup profile
  - `agent/pre-step` → append per-step recall context
  - tools → `viking_search`, `viking_read`, `viking_browse`, `viking_remember`, `viking_forget`, `viking_add_resource`, `viking_archive_expand`
  - auto-capture (`captureMode: semantic`, `captureMaxLength: 24000`), `profileTokenBudget: 10000`, `recallTokenBudget: 2000`, `requestTimeoutMs: 10000`
  - default endpoint `http://127.0.0.1:1933`; server base URL passed via `OPENVIKING_URL` env (overridable by the plugin's env `OPENVIKING_BASE_URL`, `OPENVIKING_BEARER_TOKEN`/`OPENVIKING_API_KEY`, etc. read from `~/.openviking/ovcli.conf`/`ov.conf`)
- **Persistence:** **Template-level** — the boot-time install block lives in `/root/template/deepseek-harness/start.sh` (before the web launch), so every boot (re)applies the bundle to the regenerated `.dsh`.
- **Restart required:** Yes. Profile bundles are composed at process boot; changes apply after restarting `dsh web` / `dsh-tui` (sandbox `stop + start` re-runs `start.sh`).

### Boot-time install (injected into template start.sh)

```bash
if [ -d "$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin" ]; then
  export OPENVIKING_URL="${OPENVIKING_URL:-http://127.0.0.1:1933}"
  python3 - "$DSH_HOME" "$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin" "$OPENVIKING_URL" <<'OVDSPY'
  # per profile (web, dsh-tui):
  #   remove broken symlink if present, copy src -> $DSH_HOME/profiles/<p>/node_modules/@openviking/dsh-memory-plugin  (real dir, if missing)
  #   package.json: NO link: dependency (pnpm creates broken relative symlinks from sandbox paths)
  #                 dsh.profile.bundles += "@openviking/dsh-memory-plugin"           (idempotent)
OVDSPY
fi
```

### Profile package.json (after integration)

```json
{
  "name": "dsh-profile-web",
  "private": true,
  "dependencies": {
    "@gausszhou/dsh-web-search-local": "0.1.0",
    "dshmarket": "1.12.2",
  },
  "dsh": {
    "profile": {
      "bundles": [
        "@deepseek-ai/dsh-base",
        "@deepseek-ai/dsh-web-app",
        "dshmarket",
        "@openviking/dsh-memory-plugin"
      ]
    }
  }
}
```

### File locations
| File | Path | Persistent? |
|------|------|-------------|
| Template start.sh | `/root/template/deepseek-harness/start.sh` | ✅ Yes (contains the OV boot-install block) |
| On-demand plugin (runtime) | `/root/runtime/deepseek-harness/plugins/@openviking/dsh-memory-plugin/` | ✅ Yes (installed from upstream `volcengine/OpenViking` on demand, bind-mounted into sandbox) |
| Runtime seed profiles | `/root/runtime/deepseek-harness/home/profiles/{web,dsh-tui}/` (package.json bundles + node_modules real dir) | ✅ Yes (deploy-resilient: survives undeploy→deploy) |
| Live profile installs | `<sandbox>/.dsh/profiles/{web,dsh-tui}/node_modules/@openviking/dsh-memory-plugin` + `package.json` | ❌ Recreated by start.sh on boot |

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
