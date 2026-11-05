# Prerequisites Installation Guide - MaaS Tokens Usage

This skill requires Python 3.8+ and the Huawei Cloud SDK signing library (`huaweicloudsdkcore`) for AK/SK signing.

## Table of Contents

- [Python3 + huaweicloudsdkcore](#python3--huaweicloudsdkcore)
- [Credentials Configuration](#credentials-configuration)
  - [Method 1: Environment variables (recommended)](#method-1-environment-variables-recommended)
  - [Method 2: Credentials file](#method-2-credentials-file)
  - [Windows GUI Setup](#windows-gui-setup)
- [MaaS Service Regions](#maas-service-regions)
- [References](#references)

---

## Python3 + huaweicloudsdkcore

```bash
# Check Python3 version
python3 --version  # Requires >= 3.8

# Install SDK signing library + HTTP client
# Auto-use China mirror when system timezone is UTC+8 (faster in CN region; auto-detected via Python)
PIP_INDEX=$(python3 -c "import time;print('-i https://mirrors.huaweicloud.com/repository/pypi/simple' if -(time.timezone)//3600==8 else '')")
pip install $PIP_INDEX huaweicloudsdkcore requests

# Verify
python3 -c "import huaweicloudsdkcore; print('SDK OK')"
python3 -c "import requests; print('requests OK')"
```

---

## Credentials Configuration

### Method 1: Environment variables (recommended)

```bash
# Permanent AK/SK
export HW_ACCESS_KEY=<your-access-key-id>
export HW_SECRET_KEY=<your-access-key-secret>

# Temporary AK/SK + Security Token
export HW_ACCESS_KEY=<your-temp-access-key-id>
export HW_SECRET_KEY=<your-temp-access-key-secret>
export HW_SECURITY_TOKEN=<your-security-token>
```

Verify (values never printed):
```bash
python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");ok=bool(ak) and bool(sk);print("AK/SK configured OK" if ok else "ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set");sys.exit(0 if ok else 1)'
```

### Method 2: Credentials file

Create a file supporting three formats (`--credentials-file /path/to/aksk.txt`). All three support the temporary
security token:

| Format | Layout | Temporary credentials |
|--------|--------|-----------------------|
| One value per line | line 1 `<AK>`, line 2 `<SK>` | line 3 = `<HW_SECURITY_TOKEN>` |
| Comma-separated (CSV) | `<AK>,<SK>` | third column = `<HW_SECURITY_TOKEN>` |
| `KEY=VALUE` | `HW_ACCESS_KEY=<AK>`<br>`HW_SECRET_KEY=<SK>` | add `HW_SECURITY_TOKEN=<token>` |

```
# One value per line (temporary credentials: line 3 is the token; omit for permanent AK/SK)
<AK>
<SK>
<HW_SECURITY_TOKEN>

# Comma-separated (third column is the token; omit for permanent AK/SK)
<AK>,<SK>,<HW_SECURITY_TOKEN>

# KEY=VALUE format
HW_ACCESS_KEY=<AK>
HW_SECRET_KEY=<SK>
HW_SECURITY_TOKEN=<HW_SECURITY_TOKEN>
```

If the file does not exist, the script reports `Error: Credentials file not found: <path>` on stderr and exits with
code 1. The file must be a **readable UTF-8 text file**; if it exists but cannot be read (path is a directory,
permission denied, non-UTF-8/UTF-16 bytes), the script reports
`Error: Cannot read credentials file <path>: <msg>` and exits with code 1. Never commit a credentials file to version
control. See [security-guide.md](security-guide.md) for the full security rules and file-format details.

### Windows GUI Setup

**System environment variables (avoids `setx` command history leakage):**

1. Press `Win + R`, type `sysdm.cpl`, press Enter → opens System Properties
2. Switch to the **Advanced** tab → click **Environment Variables...**
3. In the **System variables** section (lower half) → click **New...**
4. Add `HW_ACCESS_KEY`:
   - Variable name: `HW_ACCESS_KEY`
   - Variable value: _<your Access Key ID>_
   - Click OK
5. Click **New...** again, add `HW_SECRET_KEY`:
   - Variable name: `HW_SECRET_KEY`
   - Variable value: _<your Secret Access Key>_
   - Click OK
6. (Optional, temporary credentials only) Add `HW_SECURITY_TOKEN` the same way
7. Click OK on all dialogs to close
8. **Restart your terminal / Python process** — system environment variables are loaded only at process startup
9. Re-run the verification command above

> **Why GUI instead of `setx`?** `setx HW_ACCESS_KEY=...` records the credential in command history (visible via `doskey /history` or PowerShell `Get-History`), risking leakage. The GUI keeps the value out of command history.

> **⚠️ Security rules:**
> - Never provide AK/SK directly in conversation
> - Never hardcode AK/SK in scripts
> - Never print the full AK/SK values
> - For temporary credentials, also set `HW_SECURITY_TOKEN`

---

## MaaS Service Regions

| Region | Region ID |
|--------|-----------|
| Southwest-Guiyang-1 | cn-southwest-2 |

> **⚠️ MaaS ShowStatistics API currently only supports Southwest-Guiyang-1 region.** Using other regions will fail.

---

## References

| Document | Description |
|----------|-------------|
| [SKILL.md](../SKILL.md) | Skill overview and core workflows |
| [task-query-tokens-usage.md](task-query-tokens-usage.md) | Task 1 detailed steps |
| [security-design.md](security-design.md) | Security design: credential lifecycle |
| [security-guide.md](security-guide.md) | Security rules, refusal template, credentials-file formats |
