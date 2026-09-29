# CLI Installation Guide — Huawei Cloud OBS Lifecycle Management

This skill requires two CLI tools: **hcloud (KooCLI)** and **obsutil**. The `hcloud obs` module is a 1:1 passthrough of obsutil commands.

## Table of Contents

- [hcloud CLI Installation](#hcloud-cli-installation)
- [obsutil Installation](#obsutil-installation)
- [Credential Configuration](#credential-configuration)
- [Verify Installation](#verify-installation)
- [skill-quality-cli (quality telemetry)](#skill-quality-cli-quality-telemetry)
- [Troubleshooting](#troubleshooting)

---

## hcloud CLI Installation

Use the **official package repository** when available (per
https://support.huaweicloud.com/qs-hcli/hcli_02_003.html):

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y hcloud
# openEuler/CentOS
sudo yum install -y hcloud
```

If a repository package is unavailable in your distro, download the official
hcloudcli tarball and **verify its SHA-256 checksum** before unpacking (never
pipe a remote script straight into `bash`):

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-amd64.tar.gz
sha256sum hcloudcli-linux-amd64.tar.gz   # compare against the official published SHA-256
tar -xzf hcloudcli-linux-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-linux-arm64.tar.gz
sha256sum hcloudcli-linux-arm64.tar.gz   # compare against the official published SHA-256
tar -xzf hcloudcli-linux-arm64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### macOS

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-macos-amd64.tar.gz
sha256sum hcloudcli-macos-amd64.tar.gz   # compare against the official published SHA-256
tar -xzf hcloudcli-macos-amd64.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
```

### Windows

```powershell
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/hcloudcli/latest/hcloudcli-windows-amd64.zip" -OutFile "hcloudcli.zip"
Expand-Archive hcloudcli.zip
# Add hcloud.exe to PATH
```

Update KooCLI to the latest version:

```bash
hcloud update -y
hcloud version
```

---

## obsutil Installation

obsutil is the official OBS command-line tool. The `hcloud obs` module requires it (>= 5.5.0).

### Linux (x86_64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_amd64.tar.gz
sha256sum obsutil_linux_amd64.tar.gz   # compare against the official published SHA-256
tar -xzf obsutil_linux_amd64.tar.gz
chmod +x obsutil_linux_amd64_*/obsutil
sudo mv obsutil_linux_amd64_*/obsutil /usr/local/bin/
```

### Linux (ARM64)

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_linux_arm64.tar.gz
sha256sum obsutil_linux_arm64.tar.gz   # compare against the official published SHA-256
tar -xzf obsutil_linux_arm64.tar.gz
chmod +x obsutil_linux_arm64_*/obsutil
sudo mv obsutil_linux_arm64_*/obsutil /usr/local/bin/
```

### macOS

```bash
curl -O https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_darwin_amd64.tar.gz
sha256sum obsutil_darwin_amd64.tar.gz   # compare against the official published SHA-256
tar -xzf obsutil_darwin_amd64.tar.gz
chmod +x obsutil_darwin_amd64_*/obsutil
sudo mv obsutil_darwin_amd64_*/obsutil /usr/local/bin/
```

### Windows

```powershell
Invoke-WebRequest -Uri "https://obs-community-tool.obs.cn-north-1.myhuaweicloud.com/obsutil/current/obsutil_windows_amd64.zip" -OutFile "obsutil.zip"
Expand-Archive obsutil.zip
# Add obsutil.exe to PATH
```

Verify obsutil version:

```bash
obsutil version
```

---

## Credential Configuration

> **Security rule:** never type or paste AK/SK into the chat. Configure credentials out-of-band (obsutil config / shell profile), then re-run the skill. This skill never hardcodes credentials.

### Step 1: Configure the hcloud CLI profile (for non-OBS services)

```bash
hcloud configure set --cli-profile=default --cli-region=cn-south-1
# Provide AK/SK interactively via: hcloud configure
```

### Step 2: Configure obsutil credentials (used by `hcloud obs`)

The region is part of the endpoint: `obs.{region}.myhuaweicloud.com`.

```bash
# Interactive (recommended) — hcloud prompts for AK/SK/endpoint and stores
# them in ~/.obsutilconfig; no plaintext -i/-k arguments on the command line
hcloud obs config -e=obs.{region}.myhuaweicloud.com

# or directly via obsutil (also interactive)
obsutil config -e=obs.{region}.myhuaweicloud.com
```

Example for cn-south-1:

```bash
hcloud obs config -e=obs.cn-south-1.myhuaweicloud.com
```

**Environment variable alternative** — obsutil also supports credentials via environment:

```bash
export OBS_ACCESS_KEY_ID={ak}
export OBS_SECRET_ACCESS_KEY={sk}
```

> ⚠️ Never pass AK/SK as plaintext CLI args (`-i={ak} -k={sk}`) — they leak via
> shell history / process list. Prefer interactive config or env vars, and run
> only in a trusted local environment.

---

## Verify Installation

```bash
hcloud version                # KooCLI >= 3.2.0
obsutil version               # obsutil >= 5.5.0
hcloud obs ls -limit=1        # list buckets — verifies credentials + endpoint
hcloud obs lifecycle obs://{bucket} -method=get   # read lifecycle rules
```

A successful bucket listing proves the endpoint and credentials are correct. A `Please set ak, sk and endpoint` error means obsutil credentials are not configured — repeat Step 2.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Please set ak, sk and endpoint` | obsutil not configured | Run `hcloud obs config -e=obs.{region}.myhuaweicloud.com` interactively (or set `OBS_ACCESS_KEY_ID` / `OBS_SECRET_ACCESS_KEY` env vars) |
| `The endpoint is not recognized` | Wrong region in endpoint | Use the bucket's real region, e.g. `obs.cn-south-1.myhuaweicloud.com` |
| `AccessDenied` on lifecycle get | Missing IAM permission | Grant `obs:bucket:GetLifecycleConfiguration` (see `iam-policies.md`) |
| `AccessDenied` on lifecycle put | Missing IAM permission | Grant `obs:bucket:PutLifecycleConfiguration` |
| `Bucket not found` | Wrong bucket name / region | Confirm bucket name and that the endpoint region matches the bucket |
| `UnsupportedOperation` | obsutil version too old | Upgrade obsutil to >= 5.5.0 |
| Objects never expire | Lifecycle rule issue, not CLI issue | Run `huawei_diagnose_obs_lifecycle` for root-cause analysis |

---

## skill-quality-cli (quality telemetry)

Quality telemetry is collected automatically via `skill-quality-cli`:

```bash
bash scripts/ensure_cli.sh   # idempotent: installs only if absent (no auto-upgrade)
export PATH="$HOME/.local/bin:$PATH"
skill-quality-cli version    # verify it works
```

- Every `hcloud` command in this skill MUST be invoked through the
  `skill-quality-cli run --skill-name huawei-cloud-obs-lifecycle-management -- ...`
  wrapper, which attaches one quality report per run (bare `hcloud` calls are
  strictly forbidden).
- Ensure step installs the CLI only when missing; **no auto-upgrade** — upgrade
  manually with `skill-quality-cli upgrade`.
- Disable telemetry: `export SKILL_QUALITY_REPORT=0`.
- If the CLI cannot be installed (e.g. offline), the skill degrades silently —
  the business commands still run, only telemetry is skipped.