---
name: huawei-cloud-devbox-sandbox
description: |
  Create and manage DevBox cloud sandboxes (isolated cloud Linux environments) via three official
  channels, in order of preference: (1) the `devbox` CLI for terminal/interactive work, (2) the
  JavaScript/TypeScript SDK (devbox-js-sdk) for Node.js integration, (3) the Python SDK (devbox-sdk)
  for scripts and automation.
  Based on devspace-devbox `dev` branch (CLI 0.1.x — release and internal test builds, e.g. `test1106.002`; SDKs 0.1.x) and API Key authentication.
  Use when the user wants to: (1) install and use the DevBox CLI, (2) create/connect/list
  sandboxes, (3) open an interactive sandbox terminal or run one-off commands, (4) manage sandbox
  lifecycle (timeout, refresh, pause, resume, kill), (5) list and select sandbox templates,
  (6) integrate sandboxes into Node.js code with the JS SDK, (7) integrate sandboxes into Python
  code with the Python SDK (commands, processes, files, PTY, Git, async).
  Triggers include: user mentions "DevBox", "devbox", "devbox cli", "devbox-sdk", "devbox-js-sdk",
  "devspace-devbox", "云沙箱", "云端沙箱", "沙箱", "cloud sandbox", "sandbox", "创建沙箱",
  "隔离开发环境", "code execution sandbox", "AI sandbox", "remote dev environment", "devbox sbx"
tags: [huawei-cloud, devbox, sandbox, cli, sdk]
---

# Huawei Cloud DevBox Cloud Sandbox (CLI → JS SDK → Python SDK)

Create and operate isolated cloud Linux sandboxes through three official channels. **Prefer the CLI for terminal and interactive work; use the SDKs when embedding sandbox operations into code** — JS first for Node.js projects, Python for scripts and automation.

## Overview

DevBox provides isolated cloud Linux sandboxes. Whatever runs your commands (CLI or SDK), the operations execute **inside the sandbox**; the local side only holds a control connection plus a per-sandbox data-plane credential.

### The Three Channels

| Channel | Binary / package | Best for | Interactive terminal | Automation |
|---------|-----------------|----------|----------------------|------------|
| **CLI** (use first) | `devbox` (Go, cobra) | humans in a terminal, quick checks, one-off commands | ✅ built-in (`sbx create`/`sbx cn`) | ✅ (`sbx ex`, `-f json`) |
| **JS SDK** | `devbox-js-sdk` (ESM) | Node.js / TypeScript applications | via `pty` API | ✅ |
| **Python SDK** | `devbox-sdk` (import `devbox`) | scripts, CI glue, AI agents | via `pty` API | ✅ (`AsyncSandbox`) |

All three implement the same Manager REST API + EnvD data-plane protocol (CLI naming/flags are cobra-style; SDKs are `snake_case` / `camelCase`).

### Architecture

```
Channel (CLI / JS SDK / Python SDK)      Huawei Cloud
┌──────────────────────────────┐
│  devbox CLI                  │  X-API-Key / auth login   ┌─────────────────────────┐
│  devbox-js-sdk               │ ────────────────────────► │  Manager (控制面)        │
│  devbox-sdk (python)         │   REST /sandboxes         │  templates / lifecycle  │
│         │                    │ ◄──────────────────────── └─────────────────────────┘
│         │                    │   connectToken
│         │                    │   Cookie: relay_token=... (数据面鉴权)
│         └────────────────────┼────────────────────────►  ┌─────────────────────────┐
└──────────────────────────────┘  EnvD protocol            │  Gateway → Sandbox      │
                                                           │  /process.Process/*     │
                                                           │  /filesystem.Filesystem │
                                                           └─────────────────────────┘
```

- **Manager (control plane)**: `https://devbox.developer.myhuaweicloud.com` — sandbox CRUD, templates, lifecycle. Authenticated with the API Key (`X-API-Key` header). Both the CLI (build-time injected) and the SDKs (default; override `DEVBOX_API_URL`) point at this production Manager.
- **Gateway (data plane)**: address returned by the Manager per sandbox. Authenticated with the per-sandbox `connectToken` (`Cookie: relay_token=<token>`), silently refreshed before expiry.

### Use Cases

- Disposable Linux workspaces for untrusted or experimental code
- Interactive remote terminals (`devbox sbx create` from any terminal)
- Cloud-based build/test/CI execution environments
- AI agents that need a sandbox workspace (CLI for quick ops, SDK for deep integration)
- Batch automation over many sandboxes (CLI `kill --all`, SDK list/kill loops)

### Typical User Expressions

- "帮我创建一个云沙箱并执行 hello world" → CLI fast path
- "开个沙箱终端" / "进交互式终端" → `devbox sbx create <templateID>`
- "用 DevBox JS SDK 写个 Node 服务,在沙箱里跑命令" → JS SDK path
- "用 DevBox Python SDK 写个脚本,在沙箱里跑命令、读写文件" → Python SDK path
- "把本地文件上传到沙箱,运行后再把结果下载回来" → CLI + scp-like `ex`, or SDK files API
- "暂停沙箱,明天继续用" / "列出所有运行中的沙箱" → both CLI and SDK

## Version Support

| Item | Requirement |
|------|-------------|
| CLI | `devbox` 0.1.x — **install from prebuilt artifacts via the official install script** (OBS/GitCode/GitHub; guide: huaweicloud.github.io/devspace-devbox/cli/install); source build (Go >= 1.26) is a fallback only |
| JS SDK | `devbox-js-sdk` 0.1.x — **Node.js >= 20.18.1**, ESM, ships its own TypeScript types |
| Python SDK | `devbox-sdk` 0.1.x — import name `devbox`, **Python >= 3.10** |
| Source | `github.com/huaweicloud/devspace-devbox` **`dev` branch** (`cli/`, `js-sdk/`, `python-sdk/`) |
| Authentication | **API Key** — CLI: `HW_DEVBOX_API_KEY` env or `auth login`; SDKs: `DEVBOX_API_KEY` env or constructor |
| Registries | CLI: install script (GitHub/GitCode/OBS releases) or `make build` (Go >= 1.26); Python SDK: `pip install devbox-sdk` (**on PyPI**, 0.1.0); JS SDK: `npm install devbox-js-sdk` (**on npm**, 0.1.0). Source builds (`pip install ./python-sdk`, `npm ci && npm run build` + `npm install ./js-sdk`) are the fallback for pinning a commit |

## Installing this skill

```bash
# from the published repository (once this skill is merged & pushed)
npx skills add huaweicloud/huaweicloud-skills --skill huawei-cloud-devbox-sandbox

# from a local checkout (works now)
npx skills add <path>/huaweicloud-skills/skills/devtools/devbox/huawei-cloud-devbox-sandbox

# GitCode private-repo fallback (npx cannot authenticate against GitCode):
git clone https://oauth2:<token>@gitcode.com/<org>/<repo>.git /tmp/repo
cp -r /tmp/repo/skills/devtools/devbox/huawei-cloud-devbox-sandbox ~/.agents/skills/
```

The installed directory is self-contained (references/scripts/examples/evals travel with it). After installing, run `python3 scripts/devbox_check.py` to set up the CLI.

## Prerequisites

> **CRITICAL — Do NOT ask the user for confirmation during environment setup.** Silently and automatically, in order: (1) verify/install the **CLI**, (2) verify auth (`devbox auth status`; API Key via `HW_DEVBOX_API_KEY` for CLI, `DEVBOX_API_KEY` for SDKs), (3) only then set up the SDK path the user asked for (default: none needed for CLI-only tasks). Only surface output if a check fails.

```bash
# 1) Environment check — CLI-first (installs the CLI when missing, verifies version + auth)
python3 scripts/devbox_check.py

# 2) API Key
export HW_DEVBOX_API_KEY="devbox_xxx"    # for the CLI
export DEVBOX_API_KEY="devbox_xxx"       # for the JS/Python SDKs
```

- API Key is issued by the DevBox management plane. Never hardcode it in code, scripts, or logs.
- CLI credential resolution order: command-line flag > `HW_DEVBOX_API_KEY` env > OS secure credential storage > `~/.huawei/devbox/config.json`.
- SDK overrides: `DEVBOX_API_URL` (default `https://devbox.developer.myhuaweicloud.com`), `DEVBOX_GATEWAY_URL` (rarely needed). SDK fallback env names: `E2B_API_KEY` / `E2B_API_URL`.
- CLI and SDKs target the same production Manager (`devbox.developer.myhuaweicloud.com`) — one API Key works for both. The CLI's address is fixed at build time; only the SDKs allow `DEVBOX_API_URL` overrides.

### Permission / Auth Failure Handling

When any command/API call fails with 401/403 (`AuthenticationError`, `PermissionDeniedError`, or CLI auth verify failure):

1. Confirm the env var is set and non-empty for the channel in use (`HW_DEVBOX_API_KEY` for CLI, `DEVBOX_API_KEY` for SDKs).
2. The key may be invalid, expired, or out of quota scope — re-issue an API Key from the DevBox management page and re-inject; for the CLI run `devbox auth login --api-key "$HW_DEVBOX_API_KEY"` again.
3. Read [references/iam-policies.md](references/iam-policies.md) for guidance.
4. Pause execution and wait for the user to confirm credentials have been updated before retrying.
5. **Do NOT** work around auth errors by disabling TLS verification.

### System Requirements

| Requirement | CLI | JS SDK | Python SDK |
|-------------|-----|--------|------------|
| Runtime | none (static binary) | Node.js 20.18.1+ | Python 3.10+ |
| Install | official `install.sh` (prebuilt artifact, no toolchain) → `~/.huawei/bin/devbox` | `npm install devbox-js-sdk` (source-build fallback: `npm ci && npm run build`, then `npm install ./js-sdk`) | `pip install devbox-sdk` (source fallback: `pip install ./python-sdk`) |
| Network | HTTPS to its build-time Manager + Gateway domains | HTTPS to `DEVBOX_API_URL` + Gateway | same |
| Extra | — | ESM (`"type": "module"`) | `httpx` (auto-installed) |

## Workflow

> **CRITICAL — Zero confirmation.** Execute the whole flow (check env → run task → verify → clean up) fully automatically. Do NOT ask the user to confirm default parameters.

### Default Parameters

| Parameter | CLI flag | JS SDK | Python SDK | Default |
|-----------|----------|--------|------------|---------|
| Template | 1st arg of `sbx create` | `template` (1st arg) | `template` (1st arg) | template ID/alias (CLI: e.g. `tpl-devbox-base-4g`) |
| Sandbox lifetime | `-t` (s) | `timeout` (s) | `timeout` (s) | `300` (range 10–86400) |
| Metadata | `-m key=value` (create/list/kill) | `metadata` object | `metadata` mapping | none |
| Lifecycle | `--lifecycle.ontimeout pause --lifecycle.autoresume` | `lifecycle` object | `lifecycle` (SandboxLifecycle) | kill on timeout |
| Command timeout | n/a (interactive) | `timeoutMs: 60000` | `timeout=60` | 60 s |
| Refresh duration | `sbx rf -d` (s) | `refresh(duration)` | `refresh(duration)` | 300 s |
| Output format | `-f pretty\|json` | objects | objects | pretty |

> **Unit pitfall**: lifetime and command `timeout` are in **seconds** everywhere; only the JS request/command options (`timeoutMs`, `requestTimeoutMs`) are **milliseconds**.

### Fast Path: CLI (use this first for terminal tasks)

```bash
devbox auth status                       # verify login (auto-reads HW_DEVBOX_API_KEY)
devbox tpl list                          # pick a template ID
SBX=$(devbox sbx create tpl-devbox-base-4g -d -t 600)   # -d: create detached, prints sandbox ID
devbox sbx ex "$SBX" -- printf 'hello from DevBox'      # one-off command
devbox sbx ex "$SBX" -- bash -lc 'cd /tmp && ls -la'    # any shell work
devbox sbx kl "$SBX"                     # cleanup (supports multiple IDs and --all)
```

- `sbx create` / `sbx cn` **without `-d` enter an interactive terminal** (your terminal becomes the sandbox shell; type `exit` to leave) — use `-d` for scripts.
- `sbx ex <id> -- <command...>` runs a one-off command; `-b/--background` (`sbx ex -b <id> -- <command>`) runs it in background and prints the PID to stderr. **DevBox options must precede the sandbox ID**: everything after the ID goes to the remote command (`SetInterspersed(false)`), so `sbx ex <id> -- long-job -b` sends `-b` to the remote command, not to `devbox`.
- Sandbox IDs are 36-char lowercase UUIDs; timeouts are 10–86400 s.
- Full command set: [references/cli-command-reference.md](references/cli-command-reference.md).

### JS SDK Path (Node.js integration)

```js
import { Sandbox } from "devbox-js-sdk";

const sandbox = await Sandbox.create("default", { timeout: 300 });
try {
  console.log("sandbox:", sandbox.sandboxId);
  const result = await sandbox.commands.run("printf 'hello from DevBox'");
  console.log(result.stdout);
} finally {
  await sandbox.kill();
  await sandbox.close();
}
```

Full API: [references/js-sdk-reference.md](references/js-sdk-reference.md).

### Python SDK Path (scripts & automation)

```python
from devbox import Sandbox

with Sandbox.create("default", timeout=300) as sandbox:   # leaving `with` deletes the sandbox
    print("sandbox:", sandbox.sandbox_id)
    result = sandbox.commands.run("printf 'hello from DevBox'")
    print(result.stdout)
```

Full API (commands/files/pty/git/async): [references/python-sdk-reference.md](references/python-sdk-reference.md).

### Full Workflow (any channel)

1. **Check environment**: `python3 scripts/devbox_check.py` (CLI-first; `--js`/`--python` for SDK paths; `--smoke` for end-to-end).
2. **Select template**: CLI `devbox tpl list` (`-f json` for parsing) or SDK `templates.list()`.
3. **Create & work**: CLI fast path above, or SDK code.
4. **Manage lifetime**: `devbox sbx to <id> -t 600` (reset TTL, may shorten) / `devbox sbx rf <id> -d 300` (extend-only) / `sbx ps` + `sbx rs -t 600` (pause/resume, 24 h retention). SDK equivalents: `set_timeout`/`refresh`/`pause`/`resume`.
5. **Cleanup**: `devbox sbx kl <id...>` (`--all` for bulk — destructive) or SDK `kill()`/`close()`.

> **`with` semantics (Python)**: `with Sandbox.create(...)` **deletes** the sandbox on exit. To keep it, create without `with` and call `close()`; reconnect later with `Sandbox.connect(id)`. JS has no context manager — `kill()`/`close()` in `finally`.

## Core Commands

Every command below is runnable as written once `devbox` is on `PATH` (see [sdk-installation-guide.md](references/sdk-installation-guide.md)); `<id>` is a sandbox ID printed by `sbx create -d`.

```bash
# auth + templates
devbox auth status                                  # login state (auto-reads HW_DEVBOX_API_KEY)
devbox auth login --api-key "$HW_DEVBOX_API_KEY"    # persist the key
devbox tpl list -f json                             # template IDs/aliases for `sbx create`

# sandbox lifecycle
devbox sbx create <tpl> -d -t 600                   # detached: print sandbox ID
devbox sbx create <tpl>                             # create + enter interactive terminal
devbox sbx cn <id> -c /tmp                          # reconnect a terminal
devbox sbx ls -s running -f json                    # list / filter
devbox sbx in <id> -f json                          # details
devbox sbx to <id> -t 600                           # reset TTL (may shorten)
devbox sbx rf <id> -d 300                           # extend (never shortens)
devbox sbx ps <id>                                  # pause
devbox sbx rs <id> -t 600                           # resume
devbox sbx kl <id>                                  # delete (accepts several IDs, or --all)

# run commands inside the sandbox (options BEFORE the ID; command after --)
devbox sbx ex <id> -- printf 'hello from DevBox'
devbox sbx ex -b <id> -- long-job                   # background, prints PID to stderr
```

SDK entry points (published packages — `pip install devbox-sdk` / `npm install devbox-js-sdk`):

```python
from devbox import Sandbox
with Sandbox.create("default", timeout=300) as sandbox:
    print(sandbox.commands.run("printf hi").stdout)
```

```js
import { Sandbox } from "devbox-js-sdk";
const sandbox = await Sandbox.create("default", { timeout: 300 });
try { console.log((await sandbox.commands.run("printf hi")).stdout); }
finally { await sandbox.kill(); await sandbox.close(); }
```

## Parameter Confirmation

`task.json`-style confirmation is not needed for DevBox calls: every parameter has a documented default and the workflow runs **without asking the user** (see the CRITICAL note under Workflow). Confirm a value only when the user supplied it.

| Parameter | Required | CLI | SDKs | Default / range |
|-----------|----------|-----|------|-----------------|
| Template | yes (1st arg) | `sbx create <tpl>` (ID or alias) | `Sandbox.create(template)` | alias `default`; list with `tpl list` |
| Sandbox lifetime | no | `-t <seconds>` | `timeout=` | `300` s, 10–86400 |
| Detach (scripts) | no | `-d` | n/a | interactive when omitted |
| Metadata | no | `-m key=value` (repeatable) | `metadata={}` | none |
| Lifecycle | no | `--lifecycle.ontimeout pause --lifecycle.autoresume` | `lifecycle=` | kill on timeout |
| Working dir / env | no | `-c <dir>` / `-e KEY=VAL` (repeatable) | `cwd=`, `envs={}` | sandbox default / none |
| Command timeout | no | n/a (foreground streams) | `timeout=60` / `timeoutMs: 60000` | 60 s (ms only for JS request options) |
| Refresh duration | no | `sbx rf -d <seconds>` | `refresh(duration)` | `300` s |
| List limit | no | `-l <n>` | `limit=` | 100 (0 = no limit, max 1000) |
| API Key | yes | `HW_DEVBOX_API_KEY` / `auth login` | `DEVBOX_API_KEY` | never hardcode |

Full flag table: [references/cli-command-reference.md](references/cli-command-reference.md). SDK signatures: [python](references/python-sdk-reference.md) / [js](references/js-sdk-reference.md).

## Core Capabilities

> CLI details: [references/cli-command-reference.md](references/cli-command-reference.md) · JS: [references/js-sdk-reference.md](references/js-sdk-reference.md) · Python: [references/python-sdk-reference.md](references/python-sdk-reference.md)

### Sandbox Lifecycle — CLI ⇄ SDK equivalence

| Operation | CLI | JS SDK | Python SDK |
|-----------|-----|--------|------------|
| Create (detached) | `sbx create <tpl> -d [-t 600]` | `Sandbox.create(tpl, {timeout})` | `Sandbox.create(tpl, timeout=300)` |
| Create + enter terminal | `sbx create <tpl>` | — | — |
| Reconnect terminal | `sbx cn <id> [-c /tmp]` | — | — |
| List / filter | `sbx ls [-s running -m k=v -t tpl]` | `sandboxes.list({states})` | `client.sandboxes.list(states=...)` |
| Details | `sbx in <id> [-f json]` | `getInfo()` / `get(id)` | `get_info()` / `client.sandboxes.get(id)` |
| One-off command | `sbx ex <id> -- <cmd>` | `commands.run(cmd)` | `commands.run(cmd)` |
| Background + PID | `sbx ex -b <id> -- <cmd>` | `commands.run(cmd, {background:true})` | `commands.run(cmd, background=True)` |
| Set TTL | `sbx to <id> -t 600` | `setTimeout(600)` | `set_timeout(600)` |
| Extend | `sbx rf <id> -d 300` | `refresh(300)` | `refresh(300)` |
| Pause / Resume | `sbx ps <id>` / `sbx rs <id> -t 600` | `pause()` / `resume({timeout})` | `pause()` / `resume(timeout=300)` |
| Kill | `sbx kl <id...>` / `kl --all [-s paused]` | `kill()` | `kill()` (idempotent) |
| Templates | `tpl list [-f json]` | `templates.list()` | `client.templates.list()` |
| Auth | `auth status/login/logout` | env only | env only |

### CLI specifics

- Interactive terminal: `sbx create <tpl>` / `sbx cn <id>` make the local terminal the sandbox shell; `-e KEY=VAL` sets **session-only** env vars (not persisted, gone after `exit`); `-c` sets the working directory.
- `sbx kill --all` deletes **all matching running sandboxes** (optionally filtered `-s paused -m "user=abc"`) — destructive, use deliberately.
- `-f json` on `sbx ls` / `sbx in` / `tpl list` prints raw API data for scripting.
- `DEVBOX_LANG=zh` switches CLI messages to Chinese; `-v` enables debug logs (credentials auto-masked).

### JS SDK specifics

- All network operations return `Promise`; background commands return a `CommandHandle` (`sendStdin`/`closeStdin`/`sendSignal`/`wait`); non-zero exit raises `CommandExitError` unless `{check: false}`.
- `files` API: `read/write/list/stat/exists/makeDir/move/remove/upload/download/watch` — absolute sandbox paths only.
- `envd` API: `getMetrics()` (realtime CPU/mem/disk + OOM kills), `getEnvs()`, `health()` (EnvD version probe).
- `pty.start()` for interactive terminals inside code; `git.*` for in-sandbox Git workflows.

### Python SDK specifics

- Same facets as JS: `sandbox.commands/files/pty/git/envd`; `AsyncSandbox` mirrors the sync API 1:1.
- `with Sandbox.create(...)` deletes the sandbox on exit (see Workflow note).
- Non-zero exit raises `CommandExitError` unless `check=False`; `user` switching is unsupported (`ConfigurationError`).

## Output & Errors

- Sandbox states: `running` · `paused` · `stopped` (transient states were trimmed in the 0.1.x `dev` branch).
- `printf` does not append a trailing newline — stdout contains exactly the printed bytes.
- CLI errors: non-zero exit + localized stderr; `-v` shows masked API traces.
- SDK errors: all derive from `DevBoxError` (`code`, `status_code`, `request_id`, `message`, `retry_after` on 429); `CommandExitError` carries `.result` (pass `check=False` to inspect instead of raise).

```python
try:
    sandbox = Sandbox.create("default")
except RateLimitError as e:
    print("retry after", e.retry_after)
except DevBoxError as e:
    print(e.code, e.status_code, e.request_id, e.message)
```

## Verification

```bash
python3 scripts/devbox_check.py              # CLI-first: install+version+auth
python3 scripts/devbox_check.py --python     # Python SDK path
python3 scripts/devbox_check.py --js         # JS SDK path
python3 examples/cli/quickstart.sh           # CLI end-to-end (needs auth+network)
```

Offline protocol-level eval (no API key / no network — runs every SDK example against the real SDK through an in-process mock of Manager and Gateway). Install the published SDK first, then run the eval:

```bash
pip install devbox-sdk                       # published on PyPI
python3 evals/run_evals.py
# pinning a source checkout instead: --sdk-path "<deps-dir>:<devspace-devbox-src>"
```

Detailed steps: [references/verification-method.md](references/verification-method.md).

## Best Practices

1. **CLI first, SDK when embedding** — terminal/interactive/quick checks: CLI; Node.js apps: JS SDK; scripts/automation/AI agents: Python SDK.
2. **`-d` for scripts, interactive for humans** — `sbx create` without `-d` takes over the terminal.
3. **Dispose or keep deliberately** — disposable: `with` (Python) / `try-finally` (JS) / `sbx kl`; keep: save the ID (`sbx ps` + `sbx rs`, or `pause()`/`close()` + `connect(id)`, 24 h paused retention).
4. **Shortest sufficient lifetime** — default 300 s; extend with `sbx rf`/`refresh()`; pin `build_id`/`-b` when reproducibility matters.
5. **Never hardcode API Keys** — `HW_DEVBOX_API_KEY` (CLI) / `DEVBOX_API_KEY` (SDKs), or `auth login` (secure credential storage).
6. **Backoff on `RateLimitError`** — honor `retry_after`; nothing retries rate limits for you. Write results to files — reconnected streams do not replay missed output.
7. **Absolute paths only** in SDK file APIs; `sbx ex` runs in the sandbox default cwd unless `-c`.
8. **`sbx kill --all` is destructive** — filter with `-s`/`-m` and verify with `sbx ls` first.

## References

- [CLI Command Reference](references/cli-command-reference.md) — full `devbox` command set with flags and semantics.
- [CLI & SDK Installation Guide](references/sdk-installation-guide.md) — installing the CLI (script/source) and both SDKs, in that order.
- [Python SDK Reference](references/python-sdk-reference.md) — complete Python API (sync + async).
- [JavaScript SDK Reference](references/js-sdk-reference.md) — complete JS/TS API.
- [API Key & Access](references/iam-policies.md) — CLI and SDK authentication, env vars, failure handling.
- [Verification Method](references/verification-method.md) — CLI-first step-by-step verification.
- [Acceptance Criteria](references/acceptance-criteria.md) — pass/fail criteria for skill testing.
- [Troubleshooting](references/troubleshooting.md) — CLI and SDK common issues.

## Notes

### Security

- **Never hardcode API Keys** in code, scripts, notebooks, or logs. CLI: `HW_DEVBOX_API_KEY` or `auth login` (secure-credential-storage-preferred). SDKs: `DEVBOX_API_KEY` or constructor parameter.
- The API Key is only sent to the **Manager**; the per-sandbox `connectToken` is only sent to the **Gateway** as a cookie. SDKs never persist credentials or follow redirects with them; the CLI stores the key in the OS secure credential storage when available (falls back to `~/.huawei/devbox/config.json`).
- Git credentials (SDK `GitCredentials`) are injected as process env vars inside the sandbox, never written to `.git/config`.
- `DEVBOX_GATEWAY_SKIP_TLS_VERIFY=true` (SDK debug env) disables Gateway certificate verification — **debug only**, never fixes auth errors; remove after debugging.
- Sandbox contents are disposable — do not store secrets in sandbox files expecting persistence.
- CLI `-v` debug logs include request/response bodies with API Keys **auto-masked** — still avoid pasting them into tickets unchecked.

### Limitations

- **CLI Manager address is build-time** (`https://devbox.developer.myhuaweicloud.com`, the production Manager, same as the SDK default) — not configurable at runtime; the SDKs can override via `DEVBOX_API_URL`.
- Sandbox lifetime max 24 h (86400 s); minimum positive timeout 10 s.
- Paused sandboxes retained 24 h, resume on the **original node only**.
- `user` switching not supported by EnvD (SDKs raise `ConfigurationError`).
- CLI `sbx create`/`sbx cn` `-e` env vars are **session-only** (terminal session, not persisted).
- Process reconnection does not replay output produced while disconnected.
- SDKs retry only connection-establishment failures (two short retries); never rate limits, server errors, or possibly-delivered writes.
- `list()` page size 1–100; pagination via `next_token` / `X-Next-Token`.
- Templates must include `git` for Git workflows (exit code 127 otherwise).

### Compatibility

- CLI: static binary for Linux/Darwin/Windows amd64/arm64; installs to `~/.huawei/bin`, state in `~/.huawei/devbox`; source build needs Go >= 1.26 (`cd cli && make build`).
- Python SDK: Python 3.10+; `httpx>=0.27,<1`; package `devbox-sdk`, import `devbox`.
- JS SDK: Node.js 20.18.1+; ESM only; ships TypeScript declarations.
- CLI naming: full `sandbox|sbx`, `template|tpl` subcommands with alias short forms (`cr/ls/in/kl/ps/rs/cn/to/rf/ex`, plus `tpl ls`) — all built in via cobra `Aliases` in `cli/cmd/sandbox.go`; SDK naming `snake_case` (Python) / `camelCase` (JS).
- Source of truth: `github.com/huaweicloud/devspace-devbox` `dev` branch (GitCode mirror empty). The `dev` branch is a **moving target** (alpha): pin a commit (`DEVBOX_SDK_REF`, `DEVBOX_SDK_COMMIT`) and re-run checks after upgrades.
