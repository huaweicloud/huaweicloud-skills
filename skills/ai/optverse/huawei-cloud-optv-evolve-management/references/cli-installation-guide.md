# KooCLI (hcloud) Installation Guide

> How to install the Huawei Cloud command-line interface `hcloud` (a.k.a. KooCLI), configure credentials, and verify network reachability. This guide is the **only** place the install / credentials commands live; the main `SKILL.md` cross-references this file.

## 1. KooCLI installation

KooCLI is the unified Huawei Cloud CLI; the OptVerse skill uses its `hcloud` wrapper. The expected version on first run is `当前KooCLI版本:7.2.12.1` (or later).

```bash
# Check whether hcloud is already installed
hcloud version
```

> If `hcloud` is not on `PATH`, see the platform-specific install notes below.

### 1.1 Linux / macOS

```bash
# Download the release binary (verify the URL against the official Huawei Cloud docs)
curl -L -o /tmp/hcloud.tar.gz "<official-hcloud-release-url>"
tar -xzf /tmp/hcloud.tar.gz -C /tmp
sudo mv /tmp/hcloud /usr/local/bin/hcloud
hcloud version
```

### 1.2 Windows

Two common options:

- **winget** (Windows 10/11): `winget install HuaweiCloud.HuaweiCloudCLI` (verify the package id on the official docs)
- **Manual download**: install the MSI from the official Huawei Cloud download page; the binary lands at `C:\Program Files\Huawei\hcloud\bin\hcloud.exe` and is added to `PATH` automatically

After install, open a **new** PowerShell and run `hcloud version` to confirm.

### 1.3 First-run interactive prompt

On the very first run, KooCLI prints license terms and waits for `y`:

```bash
# In non-interactive scripts, pipe y
printf "y\n" | hcloud version
```

---

## 2. Credentials (AK / SK)

> **⚠️ Security rules (must read)**:
> - Never put AK / SK in plaintext in conversations, scripts, or output
> - Verify credential presence only via `hcloud configure list`
> - Prefer environment variables or the profile mode

### 2.1 Environment variables (recommended for CI / agent flow)

```bash
# Linux / macOS / Git Bash
export HUAWEI_CLOUD_AK="<your-access-key-id>"
export HUAWEI_CLOUD_SK="<your-secret-access-key>"
export HUAWEI_CLOUD_REGION="<your-region-id>"  # e.g. "cn-north-1" — check `hcloud configure show`
```

```powershell
# PowerShell
$env:HUAWEI_CLOUD_AK = "<your-access-key-id>"
$env:HUAWEI_CLOUD_SK = "<your-secret-access-key>"
$env:HUAWEI_CLOUD_REGION = "<your-region-id>"  # e.g. "cn-north-1"
```

### 2.2 Interactive `hcloud configure init`

```bash
hcloud configure init
# Follow the prompts: enter AK, SK, region, project_id
```

### 2.3 Verify credentials

```bash
hcloud configure list
hcloud OptVerse ListBuckets --cli-region=$HUAWEI_CLOUD_REGION --cli-output=json
```

`ListBuckets` returning a JSON array confirms AK/SK + region + project_id are all valid.

---

## 3. Network and regions

### 3.1 Reachability

- Outbound HTTPS to the Apig address of your region must be allowed
- Verify with `hcloud OptVerse <Op> --help` — if the help page loads, the network is OK
- For internal networks, use the Apig address; ensure `HUAWEI_CLOUD_REGION` resolves to the matching Apig domain

### 3.2 Common regions

| Region | Region ID | Notes |
|---|---|---|
| North-Beijing-1 | `cn-north-1` | Default for some accounts |
| North-Beijing-4 | `cn-north-4` | Most accounts; check `hcloud configure show` |
| East-Shanghai-2 | `cn-east-4` | East |

> `hcloud configure show` lists the region you have configured. The OptVerse skill reads region from there (or from the `HUAWEI_CLOUD_REGION` env var) and passes it via `--cli-region` on every call.

---

## 4. Common install failures

| Symptom | Cause | Fix |
|---|---|---|
| `command not found: hcloud` | Binary not on `PATH` | Add the install dir to `PATH` and reopen the terminal |
| `当前KooCLI版本:` printed but `--help` errors | First-run prompt needs `y` | `printf "y\n" \| hcloud version` |
| `APIGW.0301` / 401 | AK/SK wrong or expired | Re-run `hcloud configure init` |
| `APIGW.0311` / 404 | Project ID wrong | Check `hcloud configure show` |
| `hcloud update` keeps appearing | New version available | Run the suggested `hcloud update` to self-upgrade |
| Windows: `hcloud` found but bash invokes a stub in `WindowsApps` | Git Bash / WSL stub intercepts | Use the absolute path to the real `hcloud.exe`, or set `HUAWEI_CLOUD_REGION` then call the real one explicitly |

---

## 5. References

| Document | Description |
|---|---|
| [SKILL.md](../SKILL.md) | Skill overview, main workflow, examples |
| [references/prerequisites.md](prerequisites.md) | Runtime / Python / IAM / agency overview (this file is the install-only deep-dive) |
| [references/iam-policies.md](iam-policies.md) | Required IAM actions for sub-accounts |
| [references/troubleshooting.md](troubleshooting.md) | Error-message-grouped troubleshooting |
