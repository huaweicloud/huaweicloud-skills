# hcloud CLI Installation Guide

> KooCLI / hcloud 是华为云的官方 CLI。Phase 2（tech-research）和 Phase 4（test-execution）
> 需要它来执行 `executor=cli` 的命令。SDK 模式（`executor=sdk`）也需要先装 Python SDK。

## Install hcloud (KooCLI)

```bash
# curl install (Linux/Mac)
curl -sSL https://apiexplorer.developer.huaweicloud.com/install/hcloud/install.sh | bash

# pip install (cross-platform)
pip install huaweicloudcli

# Windows (PowerShell)
Invoke-WebRequest -UseBasicParsing -OutFile install.ps1 https://apiexplorer.developer.huaweicloud.com/install/hcloud/install.ps1
.\install.ps1

# verify
hcloud version
```

## Configure Credentials

> **NEVER** pass AK/SK to the tester through any in-session secret-entry form —
> the tester, the Skill Creator, and the opencode pipeline plugin are all
> designed to read AK/SK only from environment variables (or an existing
> `~/.hcloud/config.json` profile that you set up interactively out-of-session).
> The tester never writes credentials for you: it only runs the read-only
> existence check below and, when no profile exists, asks you to initialize one
> yourself.

### Recommended — set environment variables out-of-band

The tester reads AK/SK from any environment variable prefixed `HUAWEI*` / `HW*` /
`HWC*` whose name contains `ACCESS_KEY` / `_AK` / `SECRET_KEY` / `_SK`. Set them
in your shell profile (NEVER inline in the test command line — that risks the
value ending up in shell history, process listings, or chat logs).

```bash
# Linux / Mac — in ~/.bashrc, runtime-inject from a secrets file (never inline the literal)
# gitleaks:ignore — runtime injection from secrets file, no literal secret
read -r HUAWEI_ACCESS_KEY < ~/.secrets/hw_ak 2>/dev/null
read -r HUAWEI_SECRET_KEY < ~/.secrets/hw_sk 2>/dev/null
export HUAWEI_ACCESS_KEY HUAWEI_SECRET_KEY

# Windows PowerShell — persist to your $PROFILE:
[System.Environment]::SetEnvironmentVariable('HUAWEI_ACCESS_KEY', '<your-access-key-id>', 'User')
[System.Environment]::SetEnvironmentVariable('HUAWEI_SECRET_KEY', '<your-secret-access-key>', 'User')
```

After setting, **re-open your terminal** (or `source ~/.bashrc`) so the new
variables are inherited by the test process.

### Optional alternative — user-managed hcloud profile (out-of-session)

If you prefer the on-disk hcloud profile path, set it up yourself **in your own
terminal**: run the interactive command there — it prompts for AK/SK inside the
hcloud tool, not the tester, and writes them to `~/.hcloud/config.json` (mode
`AKSK`). The tester will pick them up automatically.

```bash
hcloud configure list      # read-only existence check — the tester runs only this
hcloud configure init      # interactive only — run it YOURSELF if configure list shows no profile
```

The tester never runs the interactive init for you and never writes credentials
on your behalf. It checks `hcloud configure list`; when no profile is listed it
prompts you to run `hcloud configure init` yourself. Do NOT pass the keys as
flags on any `hcloud configure` invocation; the goal is to keep AK/SK out of any
command line that might end up in a transcript or log.

### Resolution order used by `lib/utils.sh: ensure_ak_sk()`

1. Environment variables (any `HUAWEI*` / `HW*` / `HWC*` prefix matching
   `*_AK` / `*_SK` / `*_ACCESS_KEY` / `*_SECRET_KEY`)
2. hcloud CLI config file (`~/.hcloud/config.json` profile)
3. **No interactive prompt.** If neither source yields credentials, the
   framework emits the env-var setup template to stderr and exits 77.

## Verify Configuration

```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=1
```

期望：返回 ECS 实例列表（即使为空 `{"servers": [], "total_count": 0}` 也算成功）。

## Verify Python SDK (可选，Phase 2/4 SDK mode)

```bash
pip install huaweicloudsdkcore huaweicloudsdkrds   # 替换成对应服务

python3 -c "from huaweicloudsdkrds.v2 import *; print('SDK OK')"
```

## Common Issues

| 现象 | 原因 | 解决 |
|------|------|------|
| `hcloud: command not found` | PATH 没设 | `export PATH="$HOME/.hcloud/bin:$PATH"`（按 install 输出） |
| `AK/SK 凭证缺失（exit 77）` | 环境无凭证 + hcloud profile 也没有 | 在 shell profile 里 `export HUAWEI_ACCESS_KEY` + `HUAWEI_SECRET_KEY` 后重开终端重跑；框架不会向 agent 或终端索要 AK/SK 明文 |
| `[USE_ERROR] cli-region的值不支持` | region 不在白名单 | 用 `HUAWEI_REGION=cn-north-4`（默认）或换被测 skill 的真实 region |
| Python3 找不到（Windows） | WindowsApps alias 冲突 | 用 shim 或 `python3` 实际安装路径（自动探测：`shutil.which('python3')` / `Get-Command python3`） |

完整的环境变量 / 参数说明见 `SKILL.md` § Parameters / § Environment Variables。
