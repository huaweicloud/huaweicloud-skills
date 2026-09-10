# IAM Policies — huawei-cloud-vod-collector

## Summary

This skill does **not** require any Huawei Cloud IAM credentials or policies.

## Reason

The VoD (Voice of Developer) Collector is a **local script skill**. It captures
poor developer experiences into local markdown feedback files (`.vod/feedbacks/`),
sanitizes them, and delivers them as GitCode issues. It does **not** call any
Huawei Cloud service APIs, so it does not need:

- AK/SK (Access Key / Secret Key)
- IAM tokens or session credentials
- Any Huawei Cloud agency, role, or policy attachment

The only credential involved is the **GitCode access token** obtained through the
open-source AtomGit-GO login flow, which is stored locally at
`~/.atomcode/auth.toml` (owner-only, mode `0600`).

## Permissions Needed

- **None.** No IAM policy, agency, or role needs to be attached to the agent
  runtime for this skill to work.

## Security Notes

- The scripts only read/write local files under the project working directory
  (`.vod/`) and perform HTTP requests to `gitcode.com` for issue delivery.
- No Huawei Cloud resources are created, modified, or deleted.
- The GitCode access token is written only to `~/.atomcode/auth.toml` (mode
  `0600`) and is never logged.
- Sensitive content (tokens, passwords, AK/SK, bare `AKIA`/`sk-`/`LTAI` secret
  strings) is redacted automatically by `scripts/vod_sanitize.py` before being
  persisted in feedback files.
- The skill does not reference any `HUAWEI_*` / `HW_*` environment variables
  (except `SKILL_QUALITY_*` used to configure non-blocking quality reporting,
  which is optional).

## Network Requirements

Ensure the Agent runtime has network access to:

| Endpoint | Protocol | Purpose |
|----------|----------|---------|
| `gitcode.com` | HTTPS (443) | Issue delivery (`delivery.channels.gitcode.repo_url`) |
| `localhost:8080` | HTTP | AtomGit-GO login server (transient, started on demand) |

If the runtime is behind a firewall, allow HTTPS (443) egress to `gitcode.com`.