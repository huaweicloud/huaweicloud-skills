# CLI Installation Guide

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | `bash <SKILL_DIR>/scripts/ensure_cli.sh` (ensured idempotently if absent) |
| `hcloud` | Huawei Cloud KooCLI | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html). Scope commands with the global parameter `--cli-region`: `hcloud <Service> <Operation> --cli-region=<region>` |

## Manual upgrade

CLI no longer auto-upgrades（合规 v1.7+）。To upgrade to the latest version, run manually:

```bash
skill-quality-cli upgrade
```

## Disable telemetry (optional)

Telemetry is automatic (opt-out). To disable reporting entirely (rare), set:

```bash
export SKILL_QUALITY_REPORT=0
```

## Manual cold-start (fallback)

If `ensure_cli.sh` is unavailable, install manually:

```bash
bash <SKILL_DIR>/scripts/install_cli.sh
```

The install script downloads the platform package, verifies it, and installs
`skill-quality-cli` into `~/.local/bin/`. Upgrade afterwards with
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
