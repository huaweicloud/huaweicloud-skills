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

Required for extracting solution info and estimated price from the SAC detail page.

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

### arm64 / no Google Chrome environments (Linux aarch64, Kunpeng, container)

On arm64 (and other machines without Google Chrome), `playwright-cli install-browser`
cannot install the `chrome` channel (`ERROR: not supported on Linux Arm64`) and
the extract step would fail with `Chromium distribution 'chrome' is not found`. Use
an equivalent **chromium** build instead:

1. Install chromium (any of the following):

   ```bash
   # Option A: install via Playwright itself (chromium is supported on Linux arm64)
   npx playwright install chromium
   # Option B: system package
   apt-get install -y chromium-browser   # or: yum install -y chromium
   ```

2. Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to the installed binary so the skill
   launches chromium instead of Google Chrome:

   ```bash
   # find the binary, e.g.:
   which chromium chromium-browser 2>/dev/null
   export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="$(which chromium || which chromium-browser)"
   ```

   The skill's `playwright_utils.py` reads this variable and hands the path to the
   Playwright daemon (`PLAYWRIGHT_MCP_BROWSER=chromium` +
   `PLAYWRIGHT_MCP_EXECUTABLE_PATH`), so everything downstream — `open`, `run-code`,
   price/solution extraction — runs on chromium.

### Verify

```bash
playwright-cli --version
```

## Terraform 1.15.4+

Required for deploying the Dify platform with Terraform (`init/plan/apply`).

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
