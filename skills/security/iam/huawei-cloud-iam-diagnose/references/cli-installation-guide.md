# CLI Installation & Credential Configuration Guide

This skill executes via the Python SDK (`huaweicloudsdkiam`), with credentials loaded from
**either** environment variables **or** a local hcloud CLI profile. `hcloud IAM` CLI commands are
also available for quick data fetches and for reference.

## 1. hcloud CLI (KooCLI) installation

Required only if you want the CLI commands or the local-profile credential mode.

```bash
# Linux x86_64 —— 官方离线包（下载 → 校验 SHA256 → 解压，不执行远程脚本）
# 1) 下载官方归档包与校验文件
curl -sSfL -o /tmp/hcloud.tar.gz https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz
curl -sSfL -o /tmp/hcloud.tar.gz.sha256 https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/huaweicloud-cli-linux-amd64.tar.gz.sha256
# 2) 校验一致性后再解压安装
echo "$(cat /tmp/hcloud.tar.gz.sha256)  /tmp/hcloud.tar.gz" | sha256sum -c -
tar -xzf /tmp/hcloud.tar.gz -C /usr/local/bin/
hcloud version            # >= 7.2.12
# macOS / ARM 版请在官方下载页选择对应归档包:
# https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
```

> 官方快速开始：<https://support.huaweicloud.com/qs-hcli/hcli_02_003.html>
> 推荐使用官方下载页提供的 `.sha256` 校验文件做版本一致性校验后解压安装，
> 归档均来自华为云 OBS 官方桶，不从网络流式执行远程脚本。

## 2. Configure credentials

### Option A — Local hcloud profile (recommended for CLI mode)

Run the hcloud CLI's interactive `configure` command yourself in a local terminal and follow its
prompts to enter your AK and SK:

```bash
hcloud configure
```

> Do not paste AK/SK values into an agent chat; enter them directly in your own shell.
> This writes `~/.hcloud/config.json`. The SDK scripts in this skill read that profile
> automatically when `HW_ACCESS_KEY` / `HW_SECRET_KEY` are not set. Use `HCLOUD_PROFILE` to
> select a non-default profile.

### Option B — Environment variables (recommended for SDK script mode)

```bash
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
export HW_REGION_NAME=cn-north-4        # optional, default cn-north-4
export HW_DOMAIN_ID=<your-domain-id>    # optional, used for domain/all-projects role queries
# temporary credentials (optional):
export HW_SECURITY_TOKEN=<token>
```

**Never ask users to paste AK/SK into a chat.** Ask them to export the variables in their shell
profile and re-run.

## 3. Verify

```bash
hcloud configure list                       # CLI mode
skill action=exec: bash skill://scripts/check_env.sh   # SDK mode: checks Python, deps, creds
```

## 4. Python dependency provisioning

The environment check (`check_env.sh` / `ensure_env.py`) installs the dependencies declared in
`requirements.txt` if the SDK is missing:

```
huaweicloudsdkcore>=3.1.140
huaweicloudsdkiam>=3.1.140
```

## 5. IAM CLI quick reference (for data fetching)

| Purpose | Command |
|---|---|
| List user attached policies | `hcloud IAM ListAttachedUserPoliciesV5 --user_id=<id> --cli-region=<region>` |
| List groups of user | `hcloud IAM KeystoneListGroupsForUser --user_id=<id> --cli-region=<region>` |
| List group attached policies | `hcloud IAM ListAttachedGroupPoliciesV5 --group_id=<id> --cli-region=<region>` |
| List agencies | `hcloud IAM ListAgenciesV5 --cli-region=<region>` |
| Get policy version doc | `hcloud IAM GetPolicyVersionV5 --policy_id=<id> --version_id=v1 --cli-region=<region>` |
| Show permission (role) | `hcloud IAM KeystoneShowPermission --role_id=<id> --cli-region=<region>` |
| Show custom policy | `hcloud IAM ShowCustomPolicy --role_id=<id> --cli-region=<region>` |

### CLI check-interface caveat (important)

The CLI check commands (`KeystoneCheckProjectPermissionForGroup`,
`KeystoneCheckDomainPermissionForGroup`, `CheckProjectPermissionForAgency`, ...) return an
indistinguishable empty result and **exit code 0 for both HTTP 204 (has permission) and HTTP 404
(no permission)**. Do not use the CLI alone for a real yes/no verification — use
`scripts/check_group_permission.py` / `scripts/check_agency_permission.py`, which report the
actual HTTP status through the Python SDK.