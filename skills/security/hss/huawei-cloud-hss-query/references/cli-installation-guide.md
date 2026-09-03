# hcloud CLI Installation Guide

## Installation

### Linux / macOS

```bash
# Download and install hcloud CLI
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh
```

### Verification

```bash
hcloud --version
# Expected: KooCLI Version 7.x.x
```

## Authentication

### Option 1: Interactive Configuration

```bash
hcloud configure
# Follow prompts to enter AK/SK and region
```

### Option 2: Configure via hcloud configure set（推荐给脚本/CI 场景）

```bash
hcloud configure set --cli-region={your-region} --cli-access-key={your-ak} --cli-secret-key={your-sk}
```

> ⚠️ hcloud CLI **只读取** `~/.hcloud/config.json` 或 `--cli-access-key/--cli-secret-key` 参数，**不支持环境变量认证**（`HUAWEI_ACCESS_KEY`/`HW_ACCESS_KEY` 等均被忽略）。请勿使用环境变量方式。
> 请勿在对话中向 AI 提供 AK/SK——由用户在终端自行执行配置命令。

### Verify Authentication

```bash
hcloud configure list
# Check that a valid profile exists with AK/SK configured
```

## Security Notes

- **NEVER** hardcode AK/SK in scripts or configuration files committed to version control.
- **NEVER** print or echo AK/SK values in command output.
- Prefer environment variables or the interactive `hcloud configure` command.
- The CLI configuration file is stored at `~/.hcloud/` — treat as confidential.

## HSS Service Availability

HSS is available in most Huawei Cloud regions. Verify with:

```bash
hcloud HSS ListHostStatus --cli-region={your-region} --project_id={your-project-id} --limit=10
```

If the command returns results or an empty list (not an error), HSS is available in that region.
