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

### Method 1: Detect/Configure AK/SK Profile

> ⚠️ 安全约束(Q003): 技能/脚本禁止代用户通过 `configure set` 写入 AK/SK 凭据。本 skill 仅做**存在性检查**；若未配置，引导用户自行执行交互式 `hcloud configure init`。

```bash
# ① 存在性检查（只读，不写入任何凭据；`hcloud configure list` 无 `-a` 短参数，
#    KooCLI 7.2.12 参数为 --cli-output/--cli-query 等，已本机验证）
hcloud configure list                                # 查看当前 profile 是否已有配置
hcloud configure list --cli-query=profiles           # 可选：只返回已配置的 profile 数组
hcloud configure show --cli-profile=default 2>/dev/null || echo "default profile not configured"

# ② 未配置时引导用户自行交互式配置（由用户本人输入 AK/SK, 不落盘到技能侧，交互式仅终端手动执行）:
hcloud configure init

# ③ 仅当仅需切换区域时可设置区域(非凭据)：
hcloud configure set --cli-profile=default --cli-region=cn-north-4
```

### Method 2: Environment Variables

```bash
export HUAWEI_ACCESS_KEY=your-access-key
export HUAWEI_SECRET_KEY=your-secret-key
export HUAWEI_REGION=cn-north-4
```

## Python SDK credentials

> SDK authentication is **separate** from hcloud CLI authentication (issue #496-5).
> The SDK fallback paths (for example `show_nodes_information`,
> `list_config_templates`, `create_instance`, `create_custom_template`) fail with an
> authentication error when the variables below are not set — even when `hcloud`
> itself is already configured and working.

`hcloud configure init` stores the AK/SK in `~/.hcloud/config.json` in **encrypted**
form. The Huawei Cloud Python SDK does not read that file, so the CLI credentials
cannot be reused by the SDK. Configure SDK credentials separately through environment
variables:

```bash
# Required for every SDK call. Use placeholders only — never commit real credentials.
export HUAWEICLOUD_SDK_AK={your_ak}
export HUAWEICLOUD_SDK_SK={your_sk}
export HUAWEICLOUD_SDK_REGION={your_region}          # e.g. cn-north-4

# Only when temporary (STS / agency) credentials are used:
export HUAWEICLOUD_SDK_SECURITY_TOKEN={your_security_token}
```

| Variable | Required | Description |
|----------|----------|-------------|
| `HUAWEICLOUD_SDK_AK` | Yes (SDK path) | Access key ID read by the Python SDK |
| `HUAWEICLOUD_SDK_SK` | Yes (SDK path) | Secret access key read by the Python SDK |
| `HUAWEICLOUD_SDK_REGION` | Yes (SDK path) | Region of the target endpoint, e.g. `cn-north-4` |
| `HUAWEICLOUD_SDK_SECURITY_TOKEN` | No | Security token, only for temporary credentials |

Check the SDK credentials before running an SDK fallback:

```bash
python3 -c "import os; print('AK set:', bool(os.environ.get('HUAWEICLOUD_SDK_AK')), 'SK set:', bool(os.environ.get('HUAWEICLOUD_SDK_SK')), 'region:', os.environ.get('HUAWEICLOUD_SDK_REGION'))"
```

> Prefer the CLI for every operation the CLI exposes and treat the SDK as a fallback
> only (issue #496-4).

## Verifying Authentication

```bash
# List DDS instances (read-only check)
hcloud DDS ListInstances --cli-region=cn-north-4
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DDS ListInstances --cli-region=cn-north-4

# List DCS instances (read-only check)
hcloud DCS ListInstances --cli-region=cn-north-4
#   skill-quality-cli run --skill-name huawei-cloud-dds-dcs-instance-management -- hcloud DCS ListInstances --cli-region=cn-north-4
```

## Python SDK Dependencies

For operations not supported by hcloud CLI, install SDK packages:

```bash
pip install huaweicloudsdkdcs huaweicloudsdkdds
```

## Quality reporting environment variables

Moved here from `SKILL.md`; the quality-reporting wrapper reads these variables.

| Variable | Required | Description |
|----------|----------|-------------|
| `SKILL_QUALITY_ENDPOINT` | No | Report endpoint (default: skillsapi.developer.myhuaweicloud.com) |
| `SKILL_QUALITY_DISABLE` | No | Set `1` to disable (local debugging) |
| `SKILL_QUALITY_REPORT` | No | v1.1.8 opt-out: set `0` to skip reporting (command still runs) |
| `SKILL_QUALITY_SESSION_ID` | No | Session ID override (v1.1.8 precedence: `--session-id` > env > qcfg > host) |
| `SKILL_QUALITY_TIMEOUT` | No | Timeout seconds (default 3) |
