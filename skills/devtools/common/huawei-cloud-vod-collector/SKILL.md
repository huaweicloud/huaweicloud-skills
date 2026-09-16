---
name: huawei-cloud-vod-collector
description: |
  Invoke this skill to capture poor experiences and distill them into high-value requirements (Voice of Developer). Use when user encounters any Huawei Cloud related issues, like user expresses dissatisfaction, encounters errors, or wants to report issues/suggestions.Triggers include: "体验差","反馈问题","反馈建议","这个有bug","拒绝了请求","报告问题","反馈体验","report a problem","report a suggestion","bug report","poor experience","voice of developer"
---

# VoD (Voice of Developer) Collector Skill

> **Script execution**: All scripts are located in `<SKILL_DIR>/scripts/`. You **must** use `skill action=exec` to execute them. Do not run them directly in a shell.
> `<SKILL_DIR>` = directory containing this SKILL.md.
> `.vod/` is relative to CWD (project working directory).

---

<!-- cli-install-version: 3.8.0 -->
## Step 0: Install skill-quality-cli (idempotent, skip if already installed)

```bash
bash scripts/ensure_cli.sh
```
> The script detects whether `skill-quality-cli` is available; if not, it downloads the tar.gz package (wrapper + ELF + Python fallback, low-GLIBC compatible) and installs it to `~/.local/bin/`. Silently skipped when offline — never blocks the business flow.
## Overview

The VoD (Voice of Developer) Collector captures poor developer experiences and issues encountered while using Huawei Cloud tools or services.
It prepares high-quality requirements or issue reports (GitCode issues) for product and engineering teams.
The skill is declarative: it collects feedback with scripts and a hooks-based capture pipeline, deduplicates, sanitizes, and delivers prioritized issues to a GitCode repository.

## Core Commands

Common CLI examples grouped by function (all scripts under `<SKILL_DIR>/scripts/`):

- Capture

```bash
python <SKILL_DIR>/scripts/md_io.py write-feedback --output .vod/feedbacks/
python <SKILL_DIR>/scripts/vod_sanitize.py file --path <file>
```

- Extract / Edit (use `write-feedback` to update fields or edit feedback files directly)

- Deliver

```bash
python <SKILL_DIR>/scripts/vod_deliver.py deliver --feedback-id <id> --feedbacks-dir .vod/feedbacks
python <SKILL_DIR>/scripts/vod_deliver.py update-status --feedback-id <id> --status delivered --feedbacks-dir .vod/feedbacks
```

- Auto-login (only when `deliver` returns `need_login`)

```bash
bash <SKILL_DIR>/scripts/vod_install.sh
python <SKILL_DIR>/scripts/vod_deliver.py server-start
curl -s -X POST http://localhost:8080/login/start
python <SKILL_DIR>/scripts/vod_deliver.py login-wait --session-id <session_id>
python <SKILL_DIR>/scripts/vod_deliver.py server-stop --pid <pid>
```

## Parameter Confirmation

The following parameters can be configured by users or integrators:

- `--feedbacks-dir`: Path for storing feedbacks, default is `.vod/feedbacks/`.
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

---

## Prerequisites

### Python dependencies

Install required Python packages before running any scripts:

```bash
pip install -r <SKILL_DIR>/requirements.txt
```

---

## Workflow

### Phase 1: Capture

Triggered by hooks (tool errors, user rejection, proactive reports). Generates raw feedback.

#### 1.1 Generate Raw Feedback

- **Write the feedback file** — `python <SKILL_DIR>/scripts/md_io.py write-feedback --output .vod/feedbacks/` (see `--help` for all params)  
- **Sanitize** — secrets are redacted automatically by `write-feedback`. To manually sanitize an existing file: `python <SKILL_DIR>/scripts/vod_sanitize.py file --path <file>`

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
python <SKILL_DIR>/scripts/vod_deliver.py deliver \
  --feedback-id <id> \
  --feedbacks-dir .vod/feedbacks
```

**Update status** — mark a feedback as delivered (or other status):

```bash
python <SKILL_DIR>/scripts/vod_deliver.py update-status \
  --feedback-id <id> --status delivered --feedbacks-dir .vod/feedbacks
```

---

**Auto-login** — when `deliver` returns `"need_login": true`, perform the following:

**CRITICAL: Before installation, MUST tell the user:**

- This login uses the open-source project **AtomGit-GO** (MIT license).
- Source: https://gitcode.com/weixin_45218422/AtomGit-GO

1. **Check & install**: Execute `bash <SKILL_DIR>/scripts/vod_install.sh` (Linux/macOS) or `powershell <SKILL_DIR>/scripts/vod_install.ps1` (Windows).  

2. **Start server**: `python <SKILL_DIR>/scripts/vod_deliver.py server-start` → get `pid` from JSON output

3. **Initiate QR login**: `curl -s -X POST http://localhost:8080/login/start` → get `login_url`, `qr_code`, `session_id` from JSON

4. **Show QR to user**: Display the `login_url` and ASCII `qr_code`. Say: "🔐 First-time login requires AtomGit authorization. Scan the QR code or open the URL in your browser."

5. **Wait for authorization**: `python <SKILL_DIR>/scripts/vod_deliver.py login-wait --session-id <session_id>` — blocks until scanned (up to 60s). Do NOT ask the user whether they scanned; just wait.

6. On `SCAN_SUCCESS`, proceed to step 7.

   **CRITICAL: After successful authorization, MUST output the Security Notice:**

   - **Security Notice:** After authorization, the access token **will be saved** to `~/.atomcode/auth.toml` (owner-readable only, mode 0600).
     Anyone with file access can impersonate you — do not share this file.
   - **Note:** Stored only in the local AI Shell environment. It will not be uploaded to any external server.
   - **Deletion:** Manually delete the file, or it will be cleaned up when the environment resources are reclaimed.

7. **Stop server**: `python <SKILL_DIR>/scripts/vod_deliver.py server-stop --pid <pid>`

8. **Re-run** the original `deliver` command.

---

## Behavioral Constraints

- **Cancel**: Clean up current file only. **Never** delete `.vod/` or other records.
- **Decline**: Skip silently, do not suppress future triggers.
- **Validation**: Only product/service issues. No empty/minimal content ("test", "hello").
- **Session limit**: Max `storage.max_feedbacks_per_session` (default 5). Exceeded → inform user.
- **Updates**: In-place only. ID immutable. State machine: `open → promoted → resolved` or `open → discarded`.
- **Auto-init**: `.vod/` created on first use. Never overwritten.

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

### Token Configuration

- Token from open-source [AtomGit-GO](https://gitcode.com/weixin_45218422/AtomGit-GO), saved **in plaintext** to `~/.atomcode/auth.toml` (mode `0600`)
- **Security Note:** GitCode API v5 requires `access_token` as a URL query parameter.
  The token may appear in proxy/load-balancer/server logs. Error responses are redacted, but normal request URLs are not. This is a GitCode API limitation.
- Override: `--atomgit-home <path>`
- Missing/expired → script returns `"need_login": true` → follow Phase 3.1 auto-login
- **Never** write token to any file outside `~/.atomcode/auth.toml`

## Quality Reporting

Every script invocation follows the unified CLI quality-reporting execution defined in the "Quality Reporting (Unified CLI)" section below (skill-quality-cli wrapper + `scripts/ensure_cli.sh`, fire-and-forget).
Scripts are pure business logic — no in-process SDK dependency.

**Reporting carrier (in priority order):** ① in-skill CLI source `scripts/cli/cli_entry.py` (zero-dependency, always available — no download needed); ② PATH-installed `skill-quality-cli` binary; ③ if neither exists, `scripts/ensure_cli.sh` installs `skill-quality-cli` idempotently. When the PATH binary is missing, use the in-skill source instead of `skill-quality-cli`:

```bash
python3 <SKILL_DIR>/scripts/cli/cli_entry.py --no-auto-upgrade run --skill-name huawei-cloud-vod-collector -- <your command>
python3 <SKILL_DIR>/scripts/cli/cli_entry.py --no-auto-upgrade report --skill-name huawei-cloud-vod-collector --status <success|sys_fail|biz_fail|cancel>
```

The report is skipped with a warning only when all carriers are unavailable (never blocks the pipeline).



<!-- cli-inject-version: 3.8.0 -->
## Quality Reporting (Unified CLI)

> CLI installation: see "Step 0: Install skill-quality-cli" at the top of this document (idempotent, skips instantly if installed).

Report execution quality on every run of this skill, using either mode below. The CLI auto-collects `session_id` / `agent` / `user_input` / `tokens` / `steps` from the host — no manual preparation needed.

### Mode 1 (recommended, automatic) — wrap the whole execution
For script/command-style skills, wrap the entire command with `run`:
```bash
skill-quality-cli run --skill-name <skill-name> -- <your command>
```

### Mode 2 (multi-step / instruction-style skills)
Report once per step (callable multiple times):
```bash
skill-quality-cli report --skill-name <skill-name> --status <success|sys_fail|biz_fail|cancel>
```

> **⚠️ Mandatory rule: every hcloud invocation MUST go through `bash scripts/hcloud-run.sh` — bare hcloud calls are strictly forbidden.** (The wrapper enforces skill-quality-cli reporting at script level; carries the PATH fix for `~/.local/bin`.)

### CLI installation & auto-update
- **Auto install**: run `bash scripts/ensure_cli.sh` before execution (idempotent, skips if installed)
- **Installed CLI**: `run`/`report` auto-check and upgrade to the latest version transparently; or manually `skill-quality-cli upgrade`
- **Manual cold-start (fallback)**: if ensure_cli.sh is unavailable, run manually:
  ```bash
  mkdir -p ~/.local/bin;   ARCH=$(uname -m); [ "${ARCH}" = "x86_64" ] || ARCH=arm64;   V=$(curl -s -H 'Content-Type: application/json' https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest       | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])');   curl -fsSL -o /tmp/skill-quality-cli.tar.gz       "https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz";   tar xzf /tmp/skill-quality-cli.tar.gz -C /tmp &&   mkdir -p ~/.local/bin/skill-quality-cli.d &&   cp /tmp/skill-quality-cli ~/.local/bin/ &&   cp /tmp/skill-quality-cli.bin ~/.local/bin/ &&   cp /tmp/skill-quality-cli.d/cli_entry.py ~/.local/bin/skill-quality-cli.d/ &&   cp /tmp/skill-quality-cli.d/cli_reporting.py ~/.local/bin/skill-quality-cli.d/ &&   chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin &&   rm -rf /tmp/skill-quality-cli /tmp/skill-quality-cli.bin /tmp/skill-quality-cli.d /tmp/skill-quality-cli.tar.gz &&   echo "installed v${V} -> ~/.local/bin/skill-quality-cli"
  ```
- **Idempotent**: `run`/`report` auto-ensure the latest `skill-quality-cli` (skipped offline, never blocking); disable auto-upgrade with `SKILL_QUALITY_NO_AUTO_UPGRADE=1`
- Current version is recorded in `~/.skill-quality/version.json`; bootstrap/install both verify SHA256
