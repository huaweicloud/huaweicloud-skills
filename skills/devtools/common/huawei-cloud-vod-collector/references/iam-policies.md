# IAM Policies — huawei-cloud-vod-collector

## Summary

This skill does **not** require any Huawei Cloud IAM credentials or policies.

## Reason

The VoD (Voice of Developer) Collector is a **local script skill**. It captures
poor developer experiences into local markdown feedback files (`.vod/feedbacks/`),
sanitizes them, and delivers them as GitCode issues. It does **not** call any
Huawei Cloud service APIs, so it does not need any Huawei Cloud
account authorization setup.

The only authorization artifact involved is handled entirely by the external
AtomGit-GO login flow and stored in the file `auth.toml` inside the
directory selected by the integration's `atomgit-home` option
(default `~/.atomcode`; owner-only, mode `0600`).

## Permissions Needed

- **None.** No IAM policy, agency, or role needs to be attached to the agent
  runtime for this skill to work.

## Security Notes

- The business scripts (`md_io.py` / `vod_sanitize.py`) only read/write files
  under the project working directory (`.vod/`) and perform HTTPS requests to
  `gitcode.com` for issue delivery. `vod_deliver.py` additionally reads the
  `auth.toml` token file under the directory selected by the `atomgit-home`
  option (default `~/.atomcode`) to authenticate GitCode API requests.
- The quality-CLI installer scripts (`ensure_cli.sh` / `install_cli.sh`) write
  to `~/.local/bin` (and `~/.local/bin/skill-quality-cli.d/`) and download the
  CLI package from `skillsapi.developer.myhuaweicloud.com` and
  `obs-skills-repository.obs.cn-north-4.myhuaweicloud.com`.
- No Huawei Cloud resources are created, modified, or deleted.
- The login-flow artifact is written only to the `auth.toml` file inside the
  directory selected by the `atomgit-home` option (mode `0600`) and is never logged.
- Confidential material of any kind is redacted automatically by
  `scripts/vod_sanitize.py` before being persisted in feedback files.
- The skill does not reference any credential-bearing `HUAWEI_*` / `HW_*`
  environment variables (credentials are handled out-of-band). `HW_CLI_REGION`
  is an optional, non-sensitive region selector consumed only by
  `scripts/hcloud-run.sh` when injecting KooCLI's `--cli-region`.

## Network Requirements

Ensure the Agent runtime has network access to:

| Endpoint | Protocol | Purpose |
|----------|----------|---------|
| `gitcode.com` | HTTPS (443) | Issue delivery (`delivery.channels.gitcode.repo_url`) |
| `skillsapi.developer.myhuaweicloud.com` | HTTPS (443) | Quality CLI manifest (`/api/quality/cli/latest`) + report endpoints |
| `obs-skills-repository.obs.cn-north-4.myhuaweicloud.com` | HTTPS (443) | Quality CLI package download |
| `localhost:8080` | HTTP | AtomGit-GO login server (transient, started on demand) |

If the runtime is behind a firewall, allow HTTPS (443) egress to `gitcode.com`,
`skillsapi.developer.myhuaweicloud.com`, and
`obs-skills-repository.obs.cn-north-4.myhuaweicloud.com`.