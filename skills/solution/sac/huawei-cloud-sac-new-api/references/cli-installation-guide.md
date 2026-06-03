# CLI Installation Guide

## Python 3.10+

Required for helper scripts (`scripts/*.py`).

### Install

Download from <https://www.python.org/downloads/> or Microsoft Store.
Ensure Python 3.10+ is added to PATH.

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

## Terraform 1.5+

Required for deploying the NewAPI LLM Gateway.

### Download URLs

| Platform | URL |
| ---------- | ----- |
| Linux amd64 | <https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_amd64.zip> |
| Linux arm64 | <https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_arm64.zip> |
| macOS amd64 | <https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_darwin_amd64.zip> |
| macOS arm64 | <https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_darwin_arm64.zip> |
| Windows amd64 | <https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_windows_amd64.zip> |

### Install — Linux / macOS

```bash
curl -fsSL -o <temp_dir>/terraform.zip "<URL_from_table_above>"
unzip -o <temp_dir>/terraform.zip -d /usr/local/bin/
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
