# CLI Installation Guide

## Installing hcloud CLI

### Linux (x86_64 / ARM64)

```bash
curl -O https://cn-south-1-cloud-res-model-sdk.obs.cn-south-1.myhuaweicloud.com/hcloud/hcloud.tar.gz
tar -xzf hcloud.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
hcloud version
```

### macOS

```bash
curl -O https://cn-south-1-cloud-res-model-sdk.obs.cn-south-1.myhuaweicloud.com/hcloud/hcloud.tar.gz
tar -xzf hcloud.tar.gz
chmod +x hcloud
sudo mv hcloud /usr/local/bin/
hcloud version
```

### Windows

Download from: https://cn-south-1-cloud-res-model-sdk.obs.cn-south-1.myhuaweicloud.com/hcloud/hcloud.tar.gz

Extract and add `hcloud.exe` to your PATH.

## Upgrading hcloud CLI

```bash
hcloud update -y
```

## Authentication Setup

### Method 1: Configure AK/SK Profile

```bash
hcloud configure set --cli-profile=default --access-key=YOUR_ACCESS_KEY --secret-key=YOUR_SECRET_KEY
hcloud configure set --cli-profile=default --cli-region=cn-north-4
```

### Method 2: Environment Variables

```bash
export HUAWEI_ACCESS_KEY=your-access-key
export HUAWEI_SECRET_KEY=your-secret-key
export HUAWEI_REGION=cn-north-4
```

## Verifying Authentication

```bash
# List DDS instances (read-only check)
hcloud DDS ListInstances --cli-region=cn-north-4

# List DCS instances (read-only check)
hcloud DCS ListInstances --cli-region=cn-north-4
```

## Python SDK Dependencies

For operations not supported by hcloud CLI, install SDK packages:

```bash
pip install huaweicloudsdkdcs huaweicloudsdkdds
```