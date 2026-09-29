# CLI Installation Guide

This skill executes all cloud operations through the **hcloud (KooCLI)** CLI — no Python
SDK is used.

## 1. Install hcloud (KooCLI)

```bash
# Via curl (official installer)
curl -sSL https://hwcloudcli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o /tmp/hcloud_install.sh
bash /tmp/hcloud_install.sh

# Verify
hcloud version          # e.g. 当前KooCLI版本:7.2.12
hcloud VPC --help       # security-group operations must be listed
```

## 2. Authentication — two supported modes

### Mode A: AK/SK environment variables

```bash
export HUAWEICLOUD_SDK_AK="<your-access-key-id>"
export HUAWEICLOUD_SDK_SK="<your-secret-access-key>"
export HUAWEI_REGION="cn-north-4"          # optional default region
```

Other accepted aliases: `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` / `HW_ACCESS_KEY` /
`HW_SECRET_KEY`. Temporary credentials additionally require
`HUAWEICLOUD_SDK_SECURITY_TOKEN`. **Never type AK/SK values into chat or command lines —
always set them via your environment.**

### Mode B: local hcloud profile

```bash
hcloud configure            # interactive wizard — enter AK/SK + region
hcloud configure list       # verify: shows a profile with mode AKSK
hcloud configure set --cli-region=cn-north-4
```

The dispatcher uses the profile automatically when one exists; AK/SK env vars are only
passed explicitly when no profile is present.

## 3. Verify connectivity

```bash
# Read-only probe — must return JSON, not an auth error
hcloud VPC ListSecurityGroups/v3 --cli-region=cn-north-4 --limit=1
```

Expected failure modes:

| Output | Meaning | Fix |
| ------ | ------- | --- |
| `APIGW.0301 Incorrect IAM authentication information: Unauthorized` | Invalid/expired credentials | Refresh AK/SK or re-run `hcloud configure` |
| `缺少必填参数:project_id` | Profile can't auto-resolve project | Pass `--project_id={id}` |

## 4. skill-quality-cli (quality telemetry)

The skill reports usage telemetry automatically via `skill-quality-cli`.

```bash
export PATH="$HOME/.local/bin:$PATH"
bash scripts/ensure_cli.sh        # idempotent — installs only if absent
skill-quality-cli version
```

- Upgrade manually: `skill-quality-cli upgrade` (no auto-upgrade)
- Opt out per-run: `SKILL_QUALITY_REPORT=0` (command still executes, no report)
- Every `hcloud` command in this skill MUST be wrapped as
  `skill-quality-cli run --skill-name huawei-cloud-sg-manage -- hcloud ...`