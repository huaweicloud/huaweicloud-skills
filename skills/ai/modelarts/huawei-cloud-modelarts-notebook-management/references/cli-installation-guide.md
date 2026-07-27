# CLI Installation Guide

## Install hcloud CLI

### Linux/macOS

```bash
curl -sSL https://support.huaweicloud.com/qs-hcli/hcli_02_003.html | bash
```

Or download from: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

### Verify Installation

```bash
hcloud --version
```

## Configure Authentication

### Method 1: Interactive Configuration

```bash
hcloud configure set
```

Follow the prompts to enter:
- AK (Access Key ID)
- SK (Secret Access Key)
- Default region

### Method 2: Environment Variables

Set the following environment variables (do not hardcode in scripts):

```bash
export HUAWEICLOUD_SDK_AK={your_ak}
export HUAWEICLOUD_SDK_SK={your_sk}
```

### Verify Authentication

```bash
hcloud ModelArts ListNotebooks --cli-region=cn-north-4 --limit=1
```

## hcloud CLI Reference

- Documentation: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
- ModelArts API Explorer: https://console.huaweicloud.com/apiexplorer/#/openapi/ModelArts
