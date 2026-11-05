# CLI Installation Guide

## Install hcloud (KooCLI)

### Linux / macOS

```bash
bash <(curl -s https://cli-hk.obs.myhuaweicloud.com/install.sh)   # or follow the official guide
hcloud version
```

Official guide: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

### Windows

Download the installer for your platform from the official guide above and follow the wizard. Add the install directory to `PATH` if prompted.

## Configure Authentication

Run `hcloud configure set` interactively (`hcloud configure set --help`) to register an AK/SK profile. The credential values are typed interactively and never written by this skill. Then verify with:

```bash
hcloud configure list --cli-lang=en
hcloud configure set --cli-read-timeout=30
```

> Only set the project/region when the tenant uses project-level resources; WAF operations take `--project_id` as a path parameter which defaults to the profile value.

## Install skill-quality-cli (for CLI quality reporting)

This skill's `scripts/ensure_cli.sh` is idempotent and prepares `skill-quality-cli` when it is missing. For a pinned manual install:

```bash
# example pinned version + SHA256 verification (version may be upgraded over time)
wget -q -O /tmp/skill-quality-cli https://release.example/skill-quality-cli-v1.1.6
echo "<sha256-of-archive>  /tmp/skill-quality-cli" | sha256sum -c - && install -m 0755 /tmp/skill-quality-cli ~/.local/bin/skill-quality-cli
export PATH="$HOME/.local/bin:$PATH"
skill-quality-cli --version
```

> Use PATCH-level fixed versions and verify the SHA256 before installing. If the CLI or network is unavailable, business execution still proceeds; only quality telemetry is skipped.

## Verify Readiness

```bash
hcloud version
hcloud configure list
hcloud WAF ListEvent --cli-region=cn-north-4 --help
```
