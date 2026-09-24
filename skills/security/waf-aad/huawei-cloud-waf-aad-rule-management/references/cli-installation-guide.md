# KooCLI (hcloud) Installation & Configuration Guide

This guide covers installing KooCLI (`hcloud`) and configuring authentication for the
`huawei-cloud-waf-aad-rule-management` skill. All CLI facts below were verified with **KooCLI 7.2.12**.

## 1. Install KooCLI

Official doc: <https://support.huaweicloud.com/qs-hcli/hcli_02_003.html>

```bash
# Linux / macOS / Windows — 官方安装脚本：下载到本地文件并核对 SHA256 后再执行
# （禁止未做校验就把下载内容直接交给解释器执行的安装方式）
curl -fsSL -o /tmp/hcloud-install.sh \
  https://cn-north-4-hcli-cloud.s3.cn-north-4.myhuaweicloud.com/install.sh

# 固定版本校验：比对官方文档页公布的 SHA256（https://support.huaweicloud.com/qs-hcli/hcli_02_003.html）
sha256sum /tmp/hcloud-install.sh
# 确认与官方公布值一致后，再执行安装：
# bash /tmp/hcloud-install.sh

# Verify
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud version
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
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ListPolicy --cli-region=cn-north-4   # project_id auto-resolved from profile
```

### Mode B — local hcloud profile (user-managed, 由用户自行配置)

The skill/agent **never** writes credentials for you — it only checks whether a local profile already exists:

```bash
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud configure list   # 存在性检查：显示当前已配置的 profile / region
```

- 若 `hcloud configure list` 没有输出（未配置 profile），请**用户自行**执行：

  ```bash
  skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud configure init    # 交互式引导，输入 AK/SK 与 region（由用户自己完成）
  ```

  然后再次用 `hcloud configure list` 确认配置生效。
- 安全边界：skill 与脚本**禁止**代用户执行 `hcloud configure set` 写入 AK/SK——凭据配置属于用户职责域；
  也可以直接用 Mode A 的环境变量方式认证，无需配置本地 profile。

> Security note: never hardcode AK/SK in skill files, scripts, or PR descriptions. Prefer
> environment variables. Local profile credentials are written only by the user's own
> `hcloud configure init`.

## 3. Region & Project ID

- **`--cli-region`** selects the region (e.g. `cn-north-4`, `ap-southeast-1`). AAD is available in
  select regions — check with `hcloud AAD ListInstance --cli-region=<region>`.
- **`--project_id`** (WAF path parameter) is obtained from the console:
  *click username → My Credentials → Projects*. KooCLI 7.2.12 automatically uses the default
  project of the authenticated profile when it is omitted (verified), so the examples in this
  skill omit it; multi-project accounts may append `--project_id=<project_id>` explicitly.

## 4. Health checks after install

```bash
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF --help                 # shows Available Operations list
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud AAD --help                 # shows Available Operations list
skill-quality-cli run --skill-name huawei-cloud-waf-aad-rule-management -- hcloud WAF ListPolicy --cli-region=cn-north-4   # live query (project_id auto-resolved)
```

## 5. Install skill-quality-cli (固定版本 v1.1.6，SHA256 校验)

质量上报 CLI（`skill-quality-cli`）由 `scripts/ensure_cli.sh` 做存在性检查；未安装时按本步骤**手动安装一次**（固定版本 + SHA256 校验；禁止动态拉取"最新版"，也禁止未做校验就把下载内容直接交给解释器执行）：

```bash
# 固定版本 v1.1.6（SHA256 校验值见下方参考，随版本发布固定）
ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] || ARCH=arm64
TARBALL="https://obs-skills-repository.obs.cn-north-4.myhuaweicloud.com/skill-quality-cli/v1.1.6/skill-quality-cli-v1.1.6-linux-${ARCH}.tar.gz"

TMP_DIR=$(mktemp -d)
curl -fsSL -o "$TMP_DIR/skill-quality-cli.tar.gz" "$TARBALL"

# 固定版本校验：SHA256 不匹配则拒绝安装（核对通过前禁止解压/执行）
sha256sum "$TMP_DIR/skill-quality-cli.tar.gz"
# 参考值（linux-arm64 / v1.1.6，2026-09-16 发布）:
#   9bff9966e2e07f21b674e68d90889b6377f415663cc9b14ef95f4c5d708e125b
# linux-x86_64 的校验值以官方发布渠道公布的为准，务必比对一致后再继续。

# 校验一致后再解压安装
mkdir -p "$HOME/.local/bin/skill-quality-cli.d"
tar xzf "$TMP_DIR/skill-quality-cli.tar.gz" -C "$TMP_DIR"
cp "$TMP_DIR/skill-quality-cli" "$TMP_DIR/skill-quality-cli.bin" "$HOME/.local/bin/" 2>/dev/null
cp "$TMP_DIR/skill-quality-cli.d/cli_entry.py" "$TMP_DIR/skill-quality-cli.d/cli_reporting.py" \
   "$HOME/.local/bin/skill-quality-cli.d/" 2>/dev/null
chmod +x "$HOME/.local/bin/skill-quality-cli" "$HOME/.local/bin/skill-quality-cli.bin"
rm -rf "$TMP_DIR"

skill-quality-cli version   # 验证安装
```

> 说明：质量上报为可选项——CLI 缺失或离线时跳过上报，不阻塞本 skill 的业务执行。
