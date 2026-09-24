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