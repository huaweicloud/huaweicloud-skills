---
name: huawei-cloud-terraform-installer
description: >-
  Installs Terraform CLI cross-platform with Huawei Cloud mirror support. Use
  this skill whenever the user mentions installing Terraform, setting up
  Terraform environment, or when IaC tasks detect missing Terraform. Trigger:
  install terraform, setup terraform, terraform environment, huaweicloud
  provider.

compatibility:
  network: true
  allowed_hosts:
    - releases.hashicorp.com
    - mirrors.huaweicloud.com
    - api.github.com
---

# Huawei Cloud Terraform Installer

Cross-platform Terraform CLI installation with **Huawei Cloud mirror** by default
(avoids GitHub network issues).

## Prerequisites

- **Python 3.6+** (required for installation script)
- Network access to:
  - `releases.hashicorp.com` (Terraform binary)
  - `mirrors.huaweicloud.com` (HuaweiCloud Provider)

## Platform Support

| Platform | Method | Notes |
|----------|--------|-------|
| **Linux** | Binary | Direct binary download |
| **Windows** | Binary | Direct download |

**Why use binary download only?**

- Simpler and more reliable across all platforms
- No dependency on package manager availability
- Consistent behavior for troubleshooting

**Note:** macOS is not currently supported.

### Windows Special Notes

**Provider installation method:**

- Use `filesystem_mirror` (local file mirror)
- Download zip from Huawei Cloud mirror, extract to local
- Configure `terraform.rc` to point to local directory

**Unsupported methods:**

- ❌ `direct` (Registry → GitHub): GitHub timeout
- ❌ `network_mirror`: Huawei Cloud mirror directory structure incompatible

## Quick Start

### Basic Installation

```bash
# Auto-install (default to Huawei Cloud mirror)
python scripts/install_terraform.py

# Install + Initialize
python scripts/install_terraform.py --init

# Install + Test
python scripts/install_terraform.py --test
```

### Specify Version

```bash
# Install specific version
python scripts/install_terraform.py --version 1.15.4
```

### Other Operations

```bash
# Check status only
python scripts/install_terraform.py --check

# Uninstall
python scripts/install_terraform.py --uninstall
```

## Mirror Strategy

| Resource | Source | Notes |
|----------|--------|-------|
| Terraform binary | HashiCorp Releases | Official source |
| Provider | Huawei Cloud Mirror (default) | Avoid GitHub network issues |

**Huawei Cloud Mirror:** `https://mirrors.huaweicloud.com/terraform/`

## Troubleshooting

### Issue 1: Windows PATH Not Effective

**Solution:** Reopen terminal (PowerShell/CMD)

### Issue 2: Permission Denied

```text
[ERROR] Permission denied, please run with administrator privileges
```

**Solution:**

- Windows: Right-click → Run as administrator
- Linux: `sudo python3 install_terraform.py`

### Issue 3: Network Timeout

**Solution:** Default uses Huawei Cloud mirror, should not encounter this issue
