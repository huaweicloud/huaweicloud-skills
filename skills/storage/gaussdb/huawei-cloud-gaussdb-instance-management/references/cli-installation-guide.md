# KooCLI (hcloud) Installation & Authentication Guide

## Install KooCLI

Requirements: Linux/macOS/Windows, Python 3.6+ (optional but recommended).

```bash
# One-line install (Linux/macOS)
curl -sSL https://hwcloudcli.obs.cn-north-1.myhuaweicloud.com/cli/latest/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh

# Verify
hcloud version

# Keep it current — the GaussDB service metadata is refreshed with each release
hcloud update -y
```

## Authentication — Mode A: hcloud profile (recommended)

```bash
hcloud configure
# Interactive prompts:
#   Secret Access Key: ****************
#   Access Key ID:     ****************
#   Region:            cn-north-4
#   Project ID:        (optional — fallback for --project_id)
#   Mode:              AKSK
```

Verify:

```bash
hcloud configure list
# current profile shows mode=AKSK, region=cn-north-4

# Real read-only smoke test for GaussDB
hcloud GaussDB ListGaussMySqlInstances --cli-region=cn-north-4 --limit=1
hcloud gaussdbforopengauss ListInstances --cli-region=cn-north-4 --limit=1
```

## Authentication — Mode B: AK/SK environment variables

KooCLI reads these environment variables when no profile is used (or as an override):

```bash
export HUAWEICLOUD_SDK_AK="your-access-key-id"
export HUAWEICLOUD_SDK_SK="your-secret-access-key"
export HUAWEICLOUD_SDK_PROJECT_ID="your-project-id"   # optional
```

Alternative variable names also honoured by the SDK layer: `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`.

> **Security:** Never commit AK/SK into SKILL.md, scripts, or git. Prefer `hcloud configure` (encrypted local storage) over environment variables for interactive sessions.

## Service availability check

```bash
hcloud GaussDB --help                 # MySQL-compatible product (TaurusDB API)
hcloud gaussdbforopengauss --help     # openGauss distributed product
```

If `gaussdbforopengauss` is missing, run `hcloud update -y` and re-check.

## Region endpoints

| Product | Endpoint pattern |
|---------|------------------|
| GaussDB for MySQL (compatible) | `gaussdbformysql.<region>.myhuaweicloud.com` |
| GaussDB for openGauss (distributed) | `gaussdb-opengauss.<region>.myhuaweicloud.com` |