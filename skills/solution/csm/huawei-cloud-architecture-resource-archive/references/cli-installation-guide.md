# CLI Installation Guide - huawei-cloud-architecture-resource-archive

## Overview

This document explains how to install, configure, and verify Huawei Cloud KooCLI (`hcloud`), as well as how to install the Python dependencies required by this skill.

## KooCLI Installation

### Auto Installation (recommended)

Running `check_koocli.py` automatically detects and installs KooCLI:

```bash
python scripts/check_koocli.py
```

### Manual Installation

```bash
# Download KooCLI
curl -LO https://obs.cn-north-4.myhuaweicloud.com/hcloud/cli/latest/hcloud.zip
unzip hcloud.zip
chmod +x hcloud
./hcloud version
```

### First Run

You must accept the privacy statement on first run:

```bash
printf "y\n" | hcloud version
```

> ⚠️ `hcloud --version` does not work; the correct command is `hcloud version`.

## KooCLI Configuration

### Setting AK/SK

```bash
# Via environment variables (recommended)
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>

# Or via KooCLI config (AK/SK must be set together)
hcloud configure set --cli-access-key=<AK> --cli-secret-key=<SK>
hcloud configure set --cli-region=cn-north-4
```

✅ Correct: AK/SK set together
❌ Wrong: setting AK/SK separately reports an error

```bash
# hcloud configure set --cli-access-key=<AK>  # errors
# hcloud configure set --cli-secret-key=<SK>  # errors
```

### Verifying Configuration

```bash
# Show current configuration
hcloud configure list

# Test an API call
hcloud ECS ListServersDetails --cli-region=cn-north-4
```

## Python Dependencies

```bash
# Marker table generation dependency
pip install openpyxl

# CCE K8s sub-resource query dependency (auto-installed in Step 1)
pip install kubernetes

# CCE proxy fallback dependency (optional)
pip install huaweicloudsdkcore huaweicloudsdkcce
```

## Verification Checklist

| Check item | Command | Expected result |
|------------|---------|-----------------|
| KooCLI installed | `hcloud version` | Version >= 7.2.2 |
| AK/SK configured | `hcloud configure list` | Shows valid configuration |
| Region accessible | `hcloud ECS ListServersDetails --cli-region=cn-north-4` | Returns instance list |
| Python version | `python3 --version` | >= 3.8 |
| openpyxl | `python3 -c "import openpyxl"` | No error |
| kubernetes | `python3 -c "import kubernetes"` | No error |
