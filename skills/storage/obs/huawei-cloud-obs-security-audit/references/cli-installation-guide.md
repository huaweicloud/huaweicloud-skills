# CLI Installation Guide

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | `bash scripts/ensure_cli.sh` (ensured idempotently if absent) |
| `hcloud` | Huawei Cloud KooCLI | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html) |
| `obsutil` | OBS command-line tool (mapped via hcloud obs) | Bundled with KooCLI >= 3.2.0 |

## Prerequisites

- **hcloud CLI >= 3.2.0** — verify with `hcloud version`
- **obsutil >= 5.5.0** — verify with `obsutil version`
- **Python 3.8+** — required for `scripts/obs_security_auditor.py`

## Credential Configuration

### Option 1: Interactive (recommended for first-time setup)

```bash
# Configure obsutil credentials interactively (prompts for AK/SK/endpoint)
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs config -e=obs.{region}.myhuaweicloud.com

# Verify connectivity
skill-quality-cli run --skill-name huawei-cloud-obs-security-audit -- hcloud obs ls -limit=1
```

### Option 2: Environment variables (recommended for scripts/automation)

```bash
export HUAWEICLOUD_SDK_AK="<your-access-key-id>"
export HUAWEICLOUD_SDK_SK="<your-secret-key>"
export HUAWEICLOUD_SDK_REGION="cn-north-4"
```

> **Security rule:** never type or paste AK/SK into the chat. Configure credentials out-of-band.

## Manual upgrade

CLI no longer auto-upgrades (compliance v1.7+). To upgrade to the latest version, run manually:

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

The install script downloads the platform package, verifies it, and installs `skill-quality-cli` into `~/.local/bin/`. Upgrade afterwards with `skill-quality-cli upgrade`.
