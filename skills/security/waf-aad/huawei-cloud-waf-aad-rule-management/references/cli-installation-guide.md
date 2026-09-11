# KooCLI (hcloud) Installation & Configuration Guide

This guide covers installing KooCLI (`hcloud`) and configuring authentication for the
`huawei-cloud-waf-aad-rule-management` skill. All CLI facts below were verified with **KooCLI 7.2.12**.

## 1. Install KooCLI

Official doc: <https://support.huaweicloud.com/qs-hcli/hcli_02_003.html>

```bash
# Linux / macOS / Windows (curl install script)
curl -sSL https://cn-north-4-hcli-cloud.s3.cn-north-4.myhuaweicloud.com/install.sh | bash

# Verify
hcloud version
# Expected: Current KooCLI version: 7.2.12 (or newer)
```

## 2. Authentication (two supported modes)

This skill supports both standard Huawei Cloud authentication modes:

### Mode A — AK/SK environment variables

| Variable | Description |
|----------|-------------|
| `HUAWEICLOUD_SDK_AK` | Access Key ID |
| `HUAWEICLOUD_SDK_SK` | Secret Access Key |
| `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` | Aliases also auto-detected by hcloud |

Export them before running any command:

```bash
export HUAWEICLOUD_SDK_AK="your-access-key"
export HUAWEICLOUD_SDK_SK="your-secret-key"
hcloud WAF ListPolicy --cli-region=cn-north-4 --project_id=<project_id>
```

### Mode B — local hcloud profile

```bash
hcloud configure set --cli-access-key=<your-access-key> --cli-secret-key=<your-secret-key>   # example only — never commit real keys
hcloud configure set --cli-region=cn-north-4
hcloud configure list   # verify
```

> Security note: never hardcode AK/SK in skill files, scripts, or PR descriptions. Prefer
> environment variables. `hcloud configure set` stores credentials in the local user profile only.

## 3. Region & Project ID

- **`--cli-region`** selects the region (e.g. `cn-north-4`, `ap-southeast-1`). AAD is available in
  select regions — check with `hcloud AAD ListInstance --cli-region=<region>`.
- **`--project_id`** (required for every `hcloud WAF` call) is obtained from the console:
  *click username → My Credentials → Projects*, or automatically used from the profile via
  `--cli-project-id`.

## 4. Health checks after install

```bash
hcloud WAF --help                 # shows Available Operations list
hcloud AAD --help                 # shows Available Operations list
hcloud WAF ListPolicy --cli-region=cn-north-4 --project_id=<project_id>   # live query
```
