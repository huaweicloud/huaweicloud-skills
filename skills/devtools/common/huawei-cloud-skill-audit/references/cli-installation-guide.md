# CLI Installation Guide

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | `bash scripts/ensure_cli.sh` (auto-installs if absent) |
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
mkdir -p ~/.local/bin
ARCH=$(uname -m); [ "${ARCH}" = "x86_64" ] || ARCH=arm64
V=$(curl -s https://skillsapi.developer.myhuaweicloud.com/api/quality/cli/latest \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)["version"])')
curl -fsSL -o /tmp/skill-quality-cli.tar.gz \
    "https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli/v${V}/skill-quality-cli-v${V}-linux-${ARCH}.tar.gz"
tar xzf /tmp/skill-quality-cli.tar.gz -C /tmp
mkdir -p ~/.local/bin/skill-quality-cli.d
cp /tmp/skill-quality-cli ~/.local/bin/
cp /tmp/skill-quality-cli.bin ~/.local/bin/
cp /tmp/skill-quality-cli.d/cli_entry.py ~/.local/bin/skill-quality-cli.d/
cp /tmp/skill-quality-cli.d/cli_reporting.py ~/.local/bin/skill-quality-cli.d/
chmod +x ~/.local/bin/skill-quality-cli ~/.local/bin/skill-quality-cli.bin
rm -rf /tmp/skill-quality-cli /tmp/skill-quality-cli.bin /tmp/skill-quality-cli.d /tmp/skill-quality-cli.tar.gz
echo "installed v${V} -> ~/.local/bin/skill-quality-cli"
```
