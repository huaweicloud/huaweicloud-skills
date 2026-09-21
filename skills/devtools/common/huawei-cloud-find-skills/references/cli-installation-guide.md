# CLI Installation Guide

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | **MANDATORY Step 0.1**: `bash scripts/ensure_cli.sh` (idempotent; MUST be triggered on every skill execution) |
| `hcloud` | Huawei Cloud KooCLI | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html) |

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
bash scripts/install_cli.sh
```

The install script downloads the platform package, verifies it, and installs
`skill-quality-cli` into `~/.local/bin/`. Upgrade afterwards with
`skill-quality-cli upgrade`.
