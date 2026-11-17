# CLI Installation Guide

<!-- BEGIN inject:cli-guide (managed, do not edit) -->

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | `bash scripts/ensure_cli.sh` (ensured idempotently if absent) |
| `hcloud` | Huawei Cloud KooCLI | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html) |

## Upgrade

The CLI stays up to date on each run (auto-upgrade enabled by default). To upgrade to the latest version manually, run:

```bash
skill-quality-cli upgrade
```

## Disable telemetry (optional)

Telemetry is automatic (opt-out). To disable reporting entirely (rare), set:

```bash
export SKILL_QUALITY_REPORT=0
```

## Manual cold-start (fallback)

If `ensure_cli.sh` is unavailable, request the platform package from the latest
endpoint and install it into `~/.local/bin/`, then verify with
`skill-quality-cli version`. Upgrade afterwards with `skill-quality-cli upgrade`.

<!-- END inject:cli-guide -->
