# CLI Installation Guide

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | Linux / macOS: `bash <SKILL_DIR>/scripts/ensure_cli.sh` (idempotent, skips if present). Windows (Git Bash): same command, but `python3` must be on `PATH` — see [Windows prerequisite](#windows-git-bash-prerequisite) |
| `hcloud` | Huawei Cloud KooCLI | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html). Scope commands with the global parameter `--cli-region`: `hcloud <Service> <Operation> --cli-region=<region>` |

### Windows (Git Bash) prerequisite

`ensure_cli.sh` bootstraps through `python3`. Git for Windows ships `python` and
`py` but not `python3`, so before running the installer make sure
`python3 --version` works in Git Bash (add a shim/alias on `PATH` if needed).
Without it the bootstrap degrades to `exit 0` and quality telemetry is skipped
silently while the business commands keep working.

## Upgrade

CLI no longer unconditionally auto-upgrades（合规 v1.7+）。`skill-quality-cli run`
only upgrades when the installed version is below the platform's minimum
supported version (disable that with `SKILL_QUALITY_NO_AUTO_UPGRADE=1`). For any
other version bump, upgrade manually:

```bash
skill-quality-cli upgrade
```

## Disable telemetry (optional)

Telemetry is automatic (opt-out). To disable reporting entirely (rare), set:

```bash
export SKILL_QUALITY_REPORT=0
```

## Manual cold-start (fallback)

Bootstrap requires a working `python3` in `PATH` and reachability of the latest
endpoint. When either is missing, the skill degrades safely: `ensure_cli.sh`
prints a warning, exits 0, and quality telemetry is skipped without blocking the
business commands. To restore telemetry:

1. provide `python3` on `PATH` and re-run `bash <SKILL_DIR>/scripts/ensure_cli.sh`; or
2. install `skill-quality-cli` through your organization's official distribution
   channel, then confirm `skill-quality-cli version` works.

`ensure_cli.sh` remains the only script-level installation entry (idempotent —
skips when already installed): the latest endpoint returns an OBS pre-signed
package URL, the script verifies its sha256 and installs `skill-quality-cli`
into `~/.local/bin/`. Re-running is safe. Upgrade afterwards with
`skill-quality-cli upgrade`.

## KooCLI command format

KooCLI commands follow `hcloud <Service> <Operation> [--param=value ...]` and
should carry the global region parameter:

```bash
hcloud ECS ListServers --cli-region=cn-north-4
```

In this skill every `hcloud` call goes through `scripts/hcloud-run.sh`, which
injects `--cli-region` automatically from the `HW_CLI_REGION` environment
variable when set (and the command does not already pass it).