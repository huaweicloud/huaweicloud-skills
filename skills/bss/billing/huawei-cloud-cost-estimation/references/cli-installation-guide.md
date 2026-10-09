# KooCLI Installation & Authentication Guide

This guide is for users who lack a working Huawei Cloud CLI. The skill never
installs or configures credentials on the user's behalf — relay this guide only.

## 1. Install hcloud (KooCLI)

Requirement: **hcloud (KooCLI) >= 7.2.2**.

```bash
# Direct download on Linux
curl -O https://cn-north-4-hwc-cloud.s3.cn-north-4.myhuaweicloud.com/cli/current/hcloud-linux-amd64.tar.gz
tar -xzf hcloud-linux-amd64.tar.gz
chmod +x hcloud
./hcloud version
```

Latest version check / upgrade:

```bash
hcloud update -y
hcloud version
```

Windows/macOS installers and more detail:
https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

## 2. Enable the BSS / IAM / ECS metadata

If `hcloud BSS ...` reports `Unsupported service`, download the offline metadata
package once (BSS/IAM are included):

```bash
echo y | hcloud meta download
hcloud BSS ListServiceTypes --cli-region=cn-north-1 --cli-output=json --limit=1
```

## 3. Configure authentication (AK/SK)

```bash
hcloud configure set --cli-mode=AKSK \
  --cli-access-key=<your_access_key_id> \
  --cli-secret-key=<your_secret_access_key>
```

Or set environment variables used by the CLI/runtime:

```bash
export HUAWEICLOUD_SDK_AK=<your_access_key_id>
export HUAWEICLOUD_SDK_SK=<your_secret_access_key>
```

Verify:

```bash
hcloud configure list
hcloud IAM KeystoneListAuthProjects --cli-region=cn-north-1 --cli-output=json
```

## 4. Credentials safety

- NEVER paste AK/SK/token into a chat; configure them locally.
- Never commit credentials to source control.
- For temporary/rotation tokens use `--cli-security-token` or switch profile:
  `hcloud configure set --cli-new-title=<name>`.

## 5. Region note

All `hcloud BSS` pricing commands run with `--cli-region=cn-north-1` (fixed endpoint).
The resource deploy region is passed inside each quote line's `region` field.