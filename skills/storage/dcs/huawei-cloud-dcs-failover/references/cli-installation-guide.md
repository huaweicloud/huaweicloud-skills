# hcloud (KooCLI) Installation and Authentication Guide

This skill depends on the Huawei Cloud CLI tool **hcloud (KooCLI)** for cloud operations.

## Installation

### Option 1: One-Click Install Script

```bash
# Linux / macOS
curl -sSL https://cn-north-4-hwc-cloudsite.obs.cn-north-4.myhuaweicloud.com/hcli/install.sh | bash

# Windows (PowerShell admin)
Invoke-WebRequest -Uri https://cn-north-4-hwc-cloudsite.obs.cn-north-4.myhuaweicloud.com/hcli/install.ps1 -OutFile install.ps1
.\install.ps1
```

### Option 2: Manual Download

Download the binary for your platform from the Huawei Cloud KooCLI download page, extract it, and add `hcloud` to PATH.

## Authentication Configuration

### Using AK/SK

```bash
hcloud configure init
# Follow prompts to enter:
#   Access Key ID
#   Secret Access Key
#   Region (e.g. cn-south-1)
#   Project ID (optional)
```

### Using Command-Line Parameters

```bash
hcloud DCS ListInstances --cli-region=cn-south-1 \
  --cli-access-key=AK --cli-secret-key=SK
```

> ⚠️ **Security reminder**: never write AK/SK into scripts or commit them to repos. Using `hcloud configure init` is recommended.

## Verification

```bash
hcloud version
hcloud DCS ListInstances --cli-region=cn-south-1
```

If the above commands produce normal output, hcloud is installed and authenticated.

## Permission Requirements for This Skill

Running the DCS master-slave failover drill requires at least the following permissions (full policy see `references/iam-policies.md`):

| Permission | Usage |
|------------|-------|
| `dcs:instance:list` / `dcs:instance:get` | Query instances |
| `dcs:instance:getNodes` | Query master-slave nodes |
| `dcs:instance:modify` | Execute master-slave failover (ChangeMasterStandby) |
| `dcs:backup:list` | Query backups (risk assessment) |
| `ces:metricData:get` | Query monitoring metrics (risk assessment/report) |
