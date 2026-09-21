---
name: huawei-cloud-vod-collector
description: |
  Invoke this skill to capture poor experiences and distill them into high-value requirements (Voice of Developer). Use when user encounters any Huawei Cloud related issues, like user expresses dissatisfaction, encounters errors, or wants to report issues/suggestions.Triggers include: "体验差","反馈问题","反馈建议","这个有bug","拒绝了请求","报告问题","反馈体验","report a problem","report a suggestion","bug report","poor experience","voice of developer"
---

# VoD (Voice of Developer) Collector Skill

> **Script execution**: All scripts are located in `<SKILL_DIR>/scripts/`. You **must** wrap every script execution with `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- ` (Mandatory mandate below); never run them bare.
> `<SKILL_DIR>` = directory containing this SKILL.md.
> `.vod/` is relative to CWD (project working directory).

---

## Overview

The VoD (Voice of Developer) Collector captures poor developer experiences and issues encountered while using Huawei Cloud tools or services.
It prepares high-quality requirements or issue reports (GitCode issues) for product and engineering teams.
The skill is declarative: it collects feedback with scripts and a hooks-based capture pipeline, deduplicates, sanitizes, and delivers prioritized issues to a GitCode repository.

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `<SKILL_DIR>/scripts/ensure_cli.sh` if absent).

## Core Commands

Common CLI examples grouped by function (all scripts under `<SKILL_DIR>/scripts/`):

- Capture

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/md_io.py write-feedback --output .vod/feedbacks/
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_sanitize.py file --path <file>
```

- Extract / Edit (use `write-feedback` to update fields or edit feedback files directly)

- Deliver

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py deliver --feedback-id <id> --feedbacks-dir .vod/feedbacks
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py update-status --feedback-id <id> --status delivered --feedbacks-dir .vod/feedbacks
```

- Auto-login (only when `deliver` returns `need_login`)

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- bash <SKILL_DIR>/scripts/vod_install.sh
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py server-start
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- curl -s -X POST http://localhost:8080/login/start
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py login-wait --session-id <session_id>
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py server-stop --pid <pid>
```

## Parameter Confirmation

The following parameters can be configured by users or integrators:

- `--feedbacks-dir` / `--output`: Feedback storage directory. `md_io.py write-feedback` writes via `--output`; `vod_deliver.py` (deliver/update-status) reads via `--feedbacks-dir`. Both default to `.vod/feedbacks/` and accept the same value (equivalent per-command naming).
- `--atomgit-home` / `ATOMCODE_HOME`: AtomGit-GO configuration directory, default `~/.atomcode`.
- `delivery.channels.gitcode.repo_url`: Target repository URL — read only from `assets/config.yaml`.
- `capture.dedup_window_sec`: In-session deduplication window in seconds.
- `storage.max_feedbacks_per_session`: Maximum stored feedbacks per session (default 5).
- Logging/Debug: Optional flags inside scripts to enable additional logging or debug modes.

Before delivery or auto-login, ensure the `repo_url` is provided via `assets/config.yaml` and is not inferred from `git remote`.

## References

See additional implementation details and integration guides in the repository:

- [references/hooks-setup.md](references/hooks-setup.md)
- [references/openclaw-integration.md](references/openclaw-integration.md)
- [assets/VOD_FEEDBACKS.md](assets/VOD_FEEDBACKS.md)
- [assets/VOD_ISSUE.md](assets/VOD_ISSUE.md)
- [references/acceptance-criteria.md](references/acceptance-criteria.md)
- [references/verification-method.md](references/verification-method.md)

---

## Prerequisites

### Python dependencies

Install required Python packages before running any scripts:

```bash
pip install -r <SKILL_DIR>/requirements.txt
```

---
- **`skill-quality-cli`** — ensured by `bash <SKILL_DIR>/scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

> **⚠️ Mandatory: every script execution in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- ` (e.g. `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/md_io.py write-feedback ...`) — bare invocations of `python` / `md_io.py` / `vod_sanitize.py` / `vod_deliver.py` / `vod_install.*` / `curl` are strictly forbidden. Disable telemetry (opt-out): `SKILL_QUALITY_REPORT=0`. **Bootstrapping exception**: `ensure_cli.sh` / `install_cli.sh` are the installers themselves, so they may be executed bare (unwrapped) when `skill-quality-cli` is not yet installed; all other script executions must be wrapped once the CLI exists.

## Workflow

### Phase 1: Capture

Triggered by hooks (tool errors, user rejection, proactive reports). Generates raw feedback.

#### 1.1 Generate Raw Feedback

- **Write the feedback file** — `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/md_io.py write-feedback --output .vod/feedbacks/` (see `--help` for all params)  
- **Sanitize** — secrets are redacted automatically by `write-feedback`. To manually sanitize an existing file: `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_sanitize.py file --path <file>`

#### 1.2 Deduplication

- **In-session** (during write): Same `session_id + command + error_type` within `capture.dedup_window_sec` → increment `recurrence_count` instead of writing a new file.
- **Cross-session** (before Phase 3 delivery): Scan 10 recent feedbacks via LLM for duplicates.

---

### Phase 2: Extract

> **Note:** This phase is executed by the Agent (LLM) directly — there is no independent extraction script. The Agent enriches the feedback file using `write-feedback` to update fields.

Enrich feedback with context using LLM, then write all fields directly into the feedback file.

Each field maps to a specific section in the markdown file:

- **`error_stack`** — Extract traceback/exit code from error context → `## Error Information → error_stack`
- **`user_intent`** — What the user wanted to do (e.g. "create OBS bucket"), NOT how → `## Context → user_intent`
- **`scenario`** — Reconstruct what the user was doing → `## User Report → scenario`
- **`expected_behavior`** — What the user expected. From dialog if explicit, otherwise infer from error → `## User Report → expected_behavior`
- **`product_name`** — Priority: annotation > agent_action > error_message → Title prefix `【Product】`
- **`environment`** — Platform, OS, session ID, Python version → `## Context → environment`
- **`dialog_context`** — 3-5 key turns around the problem point, preserve original language → `## Context → dialog_context`

Use `write-feedback` again to update fields, or edit the markdown file directly.

---

### Phase 3: Deliver

#### 3.1 Sync to GitCode Issue

> ⚠️ `repo_url` comes **only** from `assets/config.yaml` → `delivery.channels.gitcode.repo_url`. Never use `git remote`, never ask the user.

**Single delivery** — submit one feedback as a GitCode Issue:

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py deliver \
  --feedback-id <id> \
  --feedbacks-dir .vod/feedbacks
```

**Update status** — mark a feedback as delivered (or other status):

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py update-status \
  --feedback-id <id> --status delivered --feedbacks-dir .vod/feedbacks
```

---

**Auto-login** — when `deliver` returns `"need_login": true`, perform the following:

> **Pre-check (MCP shortcut — try first):** Before starting the QR-code login flow below, check whether the `devspace-connector` MCP server exposes a `gitcode_create_issue` (or `create_issue`) tool. If the tool exists AND is callable, use it to create the issue directly — the `deliver` response now carries `repo_url`, `issue_title`, and `issue_body` for this purpose. After the MCP tool creates the issue, run `update-status --status delivered` and skip the QR-code login steps 1–8 below.
>
> **If the connector is unavailable — for ANY reason (server not connected, not configured, tool absent, or call fails):** **directly** fall back to the QR-code login flow below. **Do NOT ask the user** whether to connect the MCP server or present any choice — proceed silently to step 1 of the fallback. Any attempt to "enable/connect the connector" is out of scope here and must NOT be offered as an option.

**CRITICAL: Before installation, MUST tell the user:**

- This login uses the open-source project **AtomGit-GO** (MIT license).
- Source: https://gitcode.com/weixin_45218422/AtomGit-GO

1. **Check & install**: Execute `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- bash <SKILL_DIR>/scripts/vod_install.sh` (Linux/macOS) or `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- powershell <SKILL_DIR>/scripts/vod_install.ps1` (Windows).  

2. **Start server**: `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py server-start` → get `pid` from JSON output

3. **Initiate QR login**: `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- curl -s -X POST http://localhost:8080/login/start` → get `login_url`, `qr_code`, `session_id` from JSON

4. **Show QR to user**: Display the `login_url` and ASCII `qr_code`. Say: "🔐 First-time login requires AtomGit authorization. Scan the QR code or open the URL in your browser."

5. **Wait for authorization**: `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py login-wait --session-id <session_id>` — blocks until scanned (up to 60s). Do NOT ask the user whether they scanned; just wait.

6. On `SCAN_SUCCESS`, proceed to step 7.

   **CRITICAL: After successful authorization, MUST output the Security Notice:**

   - **Security Notice:** The AtomGit-GO login flow persists the token only to `${ATOMCODE_HOME:-$HOME/.atomcode}/auth.toml` (owner-readable only, mode 0600).
     Anyone with file access can impersonate you — do not share this file.
   - **Note:** Stored only in the local AI Shell environment. It will not be uploaded to any external server.
   - **Deletion:** Manually delete the file, or it will be cleaned up when the environment resources are reclaimed.

7. **Stop server**: `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py server-stop --pid <pid>`

8. **Re-run** the original `deliver` command.

---

## Behavioral Constraints

- **Cancel**: Clean up current file only. **Never** delete `.vod/` or other records.
- **Decline**: Skip silently, do not suppress future triggers.
- **Validation**: Only product/service issues. No empty/minimal content ("test", "hello").
- **Session limit**: Max `storage.max_feedbacks_per_session` (default 5). Exceeded → inform user.
- **Updates**: In-place only. ID immutable. State machine: `open → delivered → promoted → resolved` or `open → delivered → discarded` (`delivered` is the post-delivery state written by `update-status --status delivered`).
- **Auto-init**: `.vod/` created on first use. Never overwritten.
- **Quality telemetry (mandatory)**: every script/command execution is wrapped with `skill-quality-cli run --skill-name huawei-cloud-vod-collector --`; disable via `SKILL_QUALITY_REPORT=0` (opt-out).

---

## Storage

- **Path**: `<CWD>/.vod/feedbacks/`
- **Format**: `VOD-YYYYMMDD-NNNN.md`

---

## CLI Reference

| Parameter | Description |
| ----------- | ------------- |
| `--atomgit-home <path>` | AtomGit-GO config dir (default: `~/.atomcode` or `$ATOMCODE_HOME`) |
| `--feedback-id <id>` | Feedback ID to deliver/update |
| `--feedbacks-dir <path>` | Path to `.vod/feedbacks/` |

### KooCLI region

KooCLI invocations accept the global parameter `--cli-region=<region>`
(e.g. `hcloud ECS ListServers --cli-region=cn-north-4`). In this skill all
`hcloud` calls go through `scripts/hcloud-run.sh`, which injects
`--cli-region` automatically from the `HW_CLI_REGION` environment variable
when set (and the command does not already pass it).

### Token Configuration

- Token from open-source [AtomGit-GO](https://gitcode.com/weixin_45218422/AtomGit-GO), saved **in plaintext** to `~/.atomcode/auth.toml` (mode `0600`)
- **Security Note:** GitCode API v5 requires `access_token` as a URL query parameter.
  The token may appear in proxy/load-balancer/server logs. Error responses are redacted, but normal request URLs are not. This is a GitCode API limitation.
- Override: `--atomgit-home <path>`
- Missing/expired → script returns `"need_login": true` → follow Phase 3.1 auto-login
- **Never** write token to any file outside `~/.atomcode/auth.toml`
