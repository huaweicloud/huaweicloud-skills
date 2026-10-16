# CLI Installation Guide

## hcloud (Huawei Cloud KooCLI)

The `hcloud` CLI is the primary command-line tool for interacting with Huawei Cloud services.

### Installation

Download and install from the official documentation:

> https://support.huaweicloud.com/qs-hcli/hcli_02.html

**Linux / macOS:**

```bash
# Download and run the official installation script
curl -O https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh
bash hcloud_install.sh
# Verify
hcloud --version
```

**Windows:**

Download the `.exe` from the KooCLI documentation page and add it to system PATH.

### Configuration

Initialize the CLI with your AK/SK credentials:

```bash
hcloud configure set --cli-access-key=YOUR_AK --cli-secret-key=YOUR_SK --cli-region=cn-north-4
```

Verify the configuration:

```bash
hcloud configure list
```

### Upgrade

```bash
hcloud version --upgrade
```

## Python Dependencies

This skill requires the following Python packages (see [requirements.txt](../requirements.txt)):

```bash
pip install -r requirements.txt
```

Key dependencies:
- `openpyxl` — Excel (.xlsx) report generation
- `et_xmlfile` — Low-level XML support for openpyxl
