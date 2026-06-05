# CLI Installation Guide

## Python 3.8+

Required for helper scripts (`scripts/*.py`).

### Install

Download from <https://www.python.org/downloads/> or Microsoft Store.
Ensure Python 3.8+ is added to PATH.

### Verify

```bash
python --version
```

## Playwright CLI

Required for extracting solution info and price from the detail page.

### Install

```bash
npm install -g @playwright/cli@latest
```

### Install browser — Linux / macOS

```bash
playwright-cli install-browser --with-deps
```

### Install browser — Windows

```bash
playwright-cli install-browser
```

### Verify

```bash
playwright-cli --version
```

## Terraform 1.15.4+

Required for deploying the YOLO training platform.

### Download URLs

| Platform | URL |
| ---------- | ----- |
| Linux amd64 | <https://releases.hashicorp.com/terraform/1.15.4/terraform_1.15.4_linux_amd64.zip> |
| Linux arm64 | <https://releases.hashicorp.com/terraform/1.15.4/terraform_1.15.4_linux_arm64.zip> |
| macOS amd64 | <https://releases.hashicorp.com/terraform/1.15.4/terraform_1.15.4_darwin_amd64.zip> |
| macOS arm64 | <https://releases.hashicorp.com/terraform/1.15.4/terraform_1.15.4_darwin_arm64.zip> |
| Windows amd64 | <https://releases.hashicorp.com/terraform/1.15.4/terraform_1.15.4_windows_amd64.zip> |

### Install — Linux / macOS

```bash
curl -fsSL -o /tmp/terraform.zip "<URL_from_table_above>"
unzip -o /tmp/terraform.zip -d /usr/local/bin/
```

### Install — Windows PowerShell

```powershell
Invoke-WebRequest -Uri "<URL_from_table_above>" -OutFile "$env:TEMP\terraform.zip"
Expand-Archive -Path "$env:TEMP\terraform.zip" `
  -DestinationPath "$env:SystemRoot\system32" -Force
```

### Verify Installation

```bash
terraform version
```
