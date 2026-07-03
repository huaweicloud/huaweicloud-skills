---
name: huawei-cloud-vod-collector
description: |
  Invoke this skill to capture poor experiences and distill them into high-value requirements (Voice of Developer). Use when user encounters any Huawei Cloud related issues, like user expresses dissatisfaction, encounters errors, or wants to report issues/suggestions.Triggers include: "体验差","反馈问题","反馈建议","这个有bug","拒绝了请求","报告问题","反馈体验","report a problem","report a suggestion","bug report","poor experience","voice of developer"
---

# VoD (Voice of Developer) Collector Skill

> **Script execution**: All scripts are located in `<SKILL_DIR>/scripts/`. You **must** use `skill action=exec` to execute them. Do not run them directly in a shell. `<SKILL_DIR>` = directory containing this SKILL.md. `.vod/` is relative to CWD (project working directory).

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

> ⚠️ `repo_url` comes **only** from `assets/config.yaml.template` → `delivery.channels.gitcode.repo_url`. Never use `git remote`, never ask the user.

**Single delivery** — submit one feedback as a GitCode Issue:

```bash
python <SKILL_DIR>/scripts/vod_deliver.py deliver \
  --feedback-id <id> \
  --feedbacks-dir .vod/feedbacks
```

**Batch notification** — scan undelivered feedbacks and submit as a single merged issue:

```bash
python <SKILL_DIR>/scripts/vod_deliver.py notify \
  --feedbacks-dir .vod/feedbacks
```

**Update status** — mark a feedback as delivered (or other status):

```bash
python <SKILL_DIR>/scripts/vod_deliver.py update-status \
  --feedback-id <id> --status delivered --feedbacks-dir .vod/feedbacks
```

---

**Auto-login** — when `deliver` or `notify` returns `"need_login": true`, perform the following:

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

   - **Security Notice:** After authorization, the access token **will be saved** to `~/.atomcode/auth.toml` (owner-readable only, mode 0600). Anyone with file access can impersonate you — do not share this file.
   - **Note:** Stored only in the local AI Shell environment. It will not be uploaded to any external server.
   - **Deletion:** Manually delete the file, or it will be cleaned up when the environment resources are reclaimed.

7. **Stop server**: `python <SKILL_DIR>/scripts/vod_deliver.py server-stop --pid <pid>`

8. **Re-run** the original `deliver` or `notify` command.

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
|-----------|-------------|
| `--atomgit-home <path>` | AtomGit-GO config dir (default: `~/.atomcode` or `$ATOMCODE_HOME`) |
| `--feedback-id <id>` | Feedback ID to deliver/update |
| `--feedbacks-dir <path>` | Path to `.vod/feedbacks/` |

### Token Configuration

- Token from open-source [AtomGit-GO](https://gitcode.com/weixin_45218422/AtomGit-GO), saved **in plaintext** to `~/.atomcode/auth.toml` (mode `0600`)
- Override: `--atomgit-home <path>`
- Missing/expired → script returns `"need_login": true` → follow Phase 3.1 auto-login
- **Never** write token to any file outside `~/.atomcode/auth.toml`