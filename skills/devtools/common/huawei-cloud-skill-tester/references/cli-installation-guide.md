# KooCLI Installation Guide

## Install KooCLI

```bash
# curl install (Linux/Mac)
curl -sSL https://apiexplorer.developer.huaweicloud.com/install/hcloud/install.sh | bash

# pip install
pip install huaweicloudcli

# verify
hcloud version
```

## Configure Credentials

```bash
hcloud configure set \
  --cli-profile=default \
  --cli-access-key=YOUR_ACCESS_KEY \
  --cli-secret-key=YOUR_SECRET_KEY
```

## Verify Configuration

```bash
hcloud ECS ListServers --cli-region=cn-north-4 --limit=1
```

## Environment Variables

The test framework also supports AK/SK via environment variables:

```bash
export HUAWEI_ACCESS_KEY=your_access_key
export HUAWEI_SECRET_KEY=your_secret_key
```
