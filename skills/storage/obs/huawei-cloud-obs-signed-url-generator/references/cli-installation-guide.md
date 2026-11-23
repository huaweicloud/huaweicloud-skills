# CLI Installation Guide

## KooCLI Installation

### Install KooCLI

Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

KooCLI is used for Huawei Cloud API operations. For this skill, KooCLI is optional — the primary tool is the Python SDK.

### Configure KooCLI Credentials

```bash
# Non-interactive verification (read-only, no secrets echoed)
hcloud configure list
```

If no valid profile exists, configure credentials out-of-band:

```bash
export HUAWEICLOUD_SDK_AK="<your-access-key-id>"
read -rs HUAWEICLOUD_SDK_SK; export HUAWEICLOUD_SDK_SK
export HUAWEICLOUD_SDK_REGION="cn-north-4"
```

## Python SDK Installation

### Install esdk-obs-python

```bash
pip install esdk-obs-python
```

### Verify Installation

```bash
python3 -c "from obs import ObsClient; print('OBS SDK available')"
```

## skill-quality-cli

### Ensure CLI is Ready

```bash
bash scripts/ensure_cli.sh
```

This script is idempotent — it silently exits if `skill-quality-cli` is already installed and working. If the CLI is missing, it downloads the latest version with SHA256 verification.

### Manual Installation

If `ensure_cli.sh` fails (network or platform issues), run the manual installer:

```bash
bash scripts/install_cli.sh
```

### Upgrade

```bash
skill-quality-cli upgrade
```

Upgrades are manual — no auto-upgrade is performed.

### Disable Telemetry

```bash
export SKILL_QUALITY_REPORT=0
```

Set this environment variable to disable quality telemetry reporting.
