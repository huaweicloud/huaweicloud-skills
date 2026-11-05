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
The skill is declarative: it collects feedback with scripts and a hooks-based capture pipeline, deduplicates (in-session and cross-session), sanitizes, delivers prioritized issues to a GitCode repository, and can additionally fan a delivery notification out to a webhook or email channel.

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `<SKILL_DIR>/scripts/ensure_cli.sh` if absent; on Windows use `<SKILL_DIR>/scripts/ensure_cli.ps1`).

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
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py deliver --feedback-id <id> --feedbacks-dir .vod/feedbacks --force
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py update-status --feedback-id <id> --status delivered --feedbacks-dir .vod/feedbacks
```

- Cross-session dedup / notification

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py dedup-scan --feedbacks-dir .vod/feedbacks --feedback-id <id> --lookback 10 --json
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py notify --feedbacks-dir .vod/feedbacks --feedback-id <id> --channel auto --json
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

- `--feedbacks-dir` / `--output`: Feedback storage directory. `md_io.py write-feedback` writes via `--output`; `vod_deliver.py` (deliver/update-status/dedup-scan/notify) reads via `--feedbacks-dir`. Both are usually passed as `.vod/feedbacks/` — neither script defines a default, so each must be given explicitly (equivalent per-command naming).
- `--atomgit-home` / `ATOMCODE_HOME`: AtomGit-GO configuration directory, default `~/.atomcode`.
- `VOD_ATOMGIT_TOKEN`: Environment-variable token override. When set to a non-empty value it takes precedence over `${ATOMCODE_HOME:-$HOME/.atomcode}/auth.toml`, so no credential has to be persisted to disk.
- `delivery.channels.gitcode.repo_url`: Target repository URL — read only from `assets/config.yaml`.
- `capture.dedup_window_sec`: In-session deduplication window in seconds.
- `storage.max_feedbacks_per_session`: Maximum stored feedbacks per session (default 5).
- `--lookback <N>`: `dedup-scan` scan depth — the N most recently modified feedbacks (default 10).
- `--force` / `--skip-dedup`: `deliver` duplicate-gate controls. `--force` delivers even when a strong cross-session duplicate candidate is found (and is also required to re-deliver a feedback whose `delivery_status` is already `delivered`, which otherwise returns `already_delivered`); `--skip-dedup` skips the pre-delivery duplicate scan entirely.
- `--channel webhook|email|auto`: `notify` transport override (default `auto` → `delivery.channels.notification.type`).
- `--dry-run`: `notify` lists the payloads that would be sent without sending anything.
- Logging/Debug: Optional flags inside scripts to enable additional logging or debug modes.

Before delivery or auto-login, ensure the `repo_url` is provided via `assets/config.yaml` and is not inferred from `git remote`.

## References

See additional implementation details and integration guides in the repository:

- [references/hooks-setup.md](references/hooks-setup.md)
- [references/openclaw-integration.md](references/openclaw-integration.md)
- [references/cli-installation-guide.md](references/cli-installation-guide.md)
- [references/dedup-and-notify.md](references/dedup-and-notify.md)
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

### Windows support

Windows is a supported platform (`scripts/vod_install.ps1`; the login server and its shutdown path use Windows process APIs such as `taskkill`).

- The POSIX ownership/permission checks on `auth.toml` (owner uid via `st_uid` / `os.getuid()`, group/other write bits) are skipped when `os.name == "nt"` — on Windows the file is protected by the directory ACL instead. Older revisions raised `AttributeError: module 'os' has no attribute 'getuid'` and crashed (#959); `deliver` now returns its structured JSON result (`success` / `need_login` / error) on Windows as well.
- **Quality CLI install entry (#929):** the official `install_cli.sh` maps only `linux-x86_64` / `linux-arm64` and the official manifest currently publishes only a `linux-arm64` package, so Windows x86_64 had no supported entry. This skill adds a **local** cross-platform entry — `scripts/install_cli.py` plus `scripts/ensure_cli.ps1`, and a Windows branch in `ensure_cli.sh` — which installs the pure-Python fallback from the SHA256-verified official package when no native package exists. Always run it with `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` (the entry scripts set both): the official `cli_entry.py` uses `subprocess.run(..., text=True)` without `encoding`, so Chinese Windows would decode child output as GBK and raise `UnicodeDecodeError`. See [references/cli-installation-guide.md](references/cli-installation-guide.md).

---
- **`skill-quality-cli`** — ensured by `bash <SKILL_DIR>/scripts/ensure_cli.sh` (Linux/macOS, and Git Bash on Windows) or `powershell -NoProfile -ExecutionPolicy Bypass -File <SKILL_DIR>\scripts\ensure_cli.ps1` (Windows PowerShell); idempotent, skips if present. Both export `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8`, which is required on Chinese Windows (#929) — see [references/cli-installation-guide.md](references/cli-installation-guide.md).
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

> **⚠️ Mandatory: every script execution in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- ` (e.g. `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/md_io.py write-feedback ...`) — bare invocations of `python` / `md_io.py` / `vod_sanitize.py` / `vod_deliver.py` / `vod_install.*` / `curl` are strictly forbidden. Disable telemetry (opt-out): `SKILL_QUALITY_REPORT=0`. **Bootstrapping exception**: the installers themselves — `ensure_cli.sh` / `install_cli.sh` / `ensure_cli.ps1` / `install_cli.py` — may be executed bare (unwrapped) when `skill-quality-cli` is not yet installed; all other script executions must be wrapped once the CLI exists.

## Workflow

### Phase 1: Capture

Triggered by hooks (tool errors, user rejection, proactive reports). Generates raw feedback.

#### 1.1 Generate Raw Feedback

- **Write the feedback file** — `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/md_io.py write-feedback --output .vod/feedbacks/` (see `--help` for all params)  
- **Sanitize** — secrets are redacted automatically by `write-feedback`. To manually sanitize an existing file: `skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_sanitize.py file --path <file>`

#### 1.2 Deduplication

- **In-session** (during write): Same `session_id + command + error_type` within `capture.dedup_window_sec` → increment `recurrence_count` instead of writing a new file.
- **Cross-session** (before Phase 3 delivery): scan the 10 most recent feedbacks and let the Agent (LLM) judge duplicates. Run:

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py dedup-scan --feedbacks-dir .vod/feedbacks --feedback-id <id> --lookback 10 --json
```

The command takes the most recently modified feedbacks (mtime, descending, `--lookback` default 10) and, for the given `--feedback-id`, reports the duplicate candidates: `{"success":..., "scanned":N, "target":{...}, "candidates":[{id, file, session_id, feedback_type, error_type, status, delivery_status, recurrence_count, title, signature, signature_match, score, reason, is_strong_duplicate}], "strong_duplicates":[...], "should_deliver":true|false, "llm_prompt":"..."}`. A candidate from a **different `session_id`** is reported when the normalized error-text `signature` matches **or** `score` ≥ 0.6; only signature-matching candidates whose peer is already closed out can block delivery. The Agent makes the final semantic call. On a match, do **not** deliver — merge into the existing feedback instead. See [references/dedup-and-notify.md](references/dedup-and-notify.md).

---

### Phase 2: Extract

> **Note:** This phase is executed by the Agent (LLM) directly — there is **no** independent extraction script (`scripts/` intentionally contains no `vod_extract.py` or equivalent). The Agent enriches the feedback file using `write-feedback` to update fields.

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

**Step 0 — cross-session dedup gate (required before delivering):**

1. Run `dedup-scan` for the target feedback (see Phase 1.2) and inspect `candidates` + `should_deliver`.
2. If a candidate is the same problem (different session, and either a matching normalized error-text `signature` or `score` ≥ 0.6, semantically equivalent), **do not deliver** — update the existing feedback instead.
3. Otherwise deliver normally. `deliver` re-checks this gate: without `--force` it returns `{"success":false,"error":"duplicate_suspected","duplicate_of":"<ID>","candidates":[...]}` when a **strong** candidate exists — `signature_match == true`, a different session, and a peer already closed out (peer `delivery_status == "delivered"`, or peer `status` in `promoted`/`resolved`; the status enum has no `delivered` value) — and no issue is created. Score-only candidates (`signature_match == false`) never block delivery. Re-run with `--force` only after the LLM has confirmed the candidate is a different problem; `--skip-dedup` skips the gate.

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

## Notification Channels (`notify`)

Optional fan-out of pending feedbacks to a webhook or an email recipient, in addition to the GitCode issue. Configure `delivery.channels.notification` in `assets/config.yaml` (ships `enabled: false`; enable it explicitly before use), then run:

```bash
skill-quality-cli run --skill-name huawei-cloud-vod-collector -- python <SKILL_DIR>/scripts/vod_deliver.py notify --feedbacks-dir .vod/feedbacks --feedback-id <id> --channel auto --json
```

- `--channel webhook|email|auto` (optional, default `auto` → `delivery.channels.notification.type`); `--feedback-id` limits the run to one feedback. `--dry-run` lists the payloads without sending.
- **Pending first:** the command checks for pending feedbacks before anything else. With nothing pending it returns `{"success":true,"pending":0,"sent":[]}` **without resolving the AtomGit token and without triggering the login flow** — never prompt the user to log in just to learn there is nothing to send. Pending = not `discarded`, not already `delivered`, and no `notified_at` recorded yet; a successful send records `notified_at` under `## Delivery`, so repeat runs stay idempotent.
- `webhook`: HTTP `POST` with a JSON body to `webhook.url`, using `webhook.headers`. `email`: SMTP with TLS via `email.smtp_host` / `email.smtp_port` / `email.recipients`. Both honor `retry_policy` (`max_retries`, `backoff_base_sec`, `backoff_max_sec`).
- Full JSON contract and configuration reference: [references/dedup-and-notify.md](references/dedup-and-notify.md).

---

## Behavioral Constraints

- **Cancel**: Clean up current file only. **Never** delete `.vod/` or other records.
- **Decline**: Skip silently, do not suppress future triggers.
- **Validation**: Only product/service issues. No empty/minimal content ("test", "hello").
- **Cross-session dedup**: run `dedup-scan` before `deliver` and skip delivery when the Agent judges a candidate to be the same problem; use `deliver --force` only after that judgment, and `--skip-dedup` only when the gate has deliberately been bypassed.
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
| `--feedback-id <id>` | Feedback ID to deliver/update, or the target of `dedup-scan` / `notify` |
| `--feedbacks-dir <path>` | Path to `.vod/feedbacks/` |
| `--lookback <N>` | `dedup-scan`: number of most recent feedbacks to scan (default 10) |
| `--json` | Reserved for compatibility only — the code never reads it; `dedup-scan` / `notify` always print JSON |
| `--force` | `deliver`: deliver despite a strong cross-session duplicate candidate, or re-deliver an already delivered feedback |
| `--skip-dedup` | `deliver`: skip the pre-delivery duplicate scan |
| `--channel <webhook\|email\|auto>` | `notify`: transport override (default `auto`) |
| `--dry-run` | `notify`: list the payloads that would be sent without sending |

### KooCLI region

KooCLI invocations accept the global parameter `--cli-region=<region>`
(e.g. `hcloud ECS ListServers --cli-region=cn-north-4`). In this skill all
`hcloud` calls go through `scripts/hcloud-run.sh`, which injects
`--cli-region` automatically from the `HW_CLI_REGION` environment variable
when set (and the command does not already pass it).

### Token Configuration

- Token source, in priority order:
  1. **`VOD_ATOMGIT_TOKEN`** environment variable — used directly when set to a non-empty value; `auth.toml` is not read and the token is never persisted to disk.
  2. Token from open-source [AtomGit-GO](https://gitcode.com/weixin_45218422/AtomGit-GO), saved **in plaintext** to `${ATOMCODE_HOME:-$HOME/.atomcode}/auth.toml`.
- **Plaintext storage is upstream behavior (#114 问题 9).** This skill cannot change how AtomGit-GO writes `auth.toml`; its mitigations are:
  - **POSIX**: the parent directory must be owned by the current user and not group/other-writable; symlinks and non-regular files are refused; the file mode is tightened to `0600` **before** the token is read, and reading is refused when it cannot be tightened.
  - **Windows** (`os.name == "nt"`): POSIX ownership/mode checks are skipped and the file is protected by the directory ACL instead.
  - `VOD_ATOMGIT_TOKEN` avoids writing a credential to disk, which is a real improvement on shared hosts and containers — but on POSIX a **same-uid** process (including a child process) can still read the variable from `/proc/<pid>/environ`, so it is not a strict win; use a short-lived token when stronger isolation is required. Use `--atomgit-home <path>` to relocate `auth.toml` when it must be persisted.
  - Anyone with read access to the file can impersonate you — do not share it.
- **Security Note (#114 问题 7):** GitCode API v5 requires `access_token` as a URL query parameter, so the token may appear in proxy/load-balancer/server logs even though error responses are redacted. This is a GitCode API limitation this skill cannot work around, and `VOD_ATOMGIT_TOKEN` does not change it (the token still travels in the URL). Prefer short-lived tokens and a trusted egress path; migrate to a GitCode API version with header-based authentication when one is available.
- Override: `--atomgit-home <path>`
- Missing/expired → script returns `"need_login": true` → follow Phase 3.1 auto-login
- **Never** write token to any file outside `$ATOMCODE_HOME/auth.toml` (or use `VOD_ATOMGIT_TOKEN` and write nothing at all)

