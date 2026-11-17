# CLI Installation Guide

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `hcloud` (KooCLI ≥ 7.2.2) | All VPC security-group calls | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html); verify with `hcloud version` |
| `skill-quality-cli` | Optional quality telemetry for Huawei Cloud skills | `bash scripts/ensure_cli.sh` (idempotent) or `bash scripts/install_cli.sh` (manual) |

Business commands need **only `hcloud`**. `skill-quality-cli` is an optional reporting
wrapper — when it is absent, run the identical bare `hcloud ...` command.

## hcloud (KooCLI) verification

```bash
hcloud version
```

Expected output starts with `Current KooCLI version: 7.`. If `hcloud` is missing, install it
per the official KooCLI guide, then configure credentials:

- **Profile**: run the KooCLI `configure init` subcommand, and check the result with the
  `configure list` subcommand.
- **AK/SK environment variables**: `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
  (aliases `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`, `HW_ACCESS_KEY` / `HW_SECRET_KEY`).

No `hcloud` binary or no credentials → the dispatcher fails in under 2 seconds with
`{"success": false, "error_code": "cli_missing" | "credentials_missing", "hint": "..."}`.

## skill-quality-cli: online install

```bash
bash scripts/ensure_cli.sh
```

- Already installed and working → exits 0 silently.
- Missing → downloads the platform package into `~/.local/bin/skill-quality-cli` (+ `.d/`).
- **Never blocks business commands**: any failure prints a Chinese warning on stderr and
  exits 0.
- **Bounded time**: every HTTP request uses `--connect-timeout 5 --max-time 30`, so an
  offline host returns within ~5–30 seconds instead of hanging.

Manual install (fail-loudly variant, for provisioning scripts and CI):

```bash
bash scripts/install_cli.sh
echo "exit=$?"
```

| Situation | Exit code | Message |
|-----------|-----------|---------|
| installed | 0 | `skill-quality-cli v<ver> 安装完成（手动触发）` |
| `curl`/`python3`/`tar`/`mktemp` missing | 1 | `错误: 缺少依赖 <dep>，无法安装 skill-quality-cli` |
| metadata endpoint unreachable (no network / proxy) | 1 | `错误: 无法获取 skill-quality-cli 最新版本（<url>）。请在 30 秒内检查网络/代理是否可达…` |
| metadata has no `version` field | 1 | `错误: 版本元数据无法解析` |
| package download fails | 1 | `错误: 下载 skill-quality-cli v<ver> (linux-<arch>) 失败: <url>` |
| empty / broken archive, missing binary | 1 | `错误: 安装包为空 / 解压失败 / 缺少可执行文件` |

Both scripts accept a mirror override — the defaults stay unchanged:

```bash
SQC_API_URL=https://<mirror>/api/quality/cli/latest \
SQC_OBS_BASE=https://<mirror>/skill-quality-cli \
bash scripts/install_cli.sh
```

## Manual upgrade

CLI no longer auto-upgrades（合规 v1.7+）。To upgrade to the latest version, run manually:

```bash
skill-quality-cli upgrade
```

## Disable telemetry (optional)

Telemetry is automatic (opt-out). To disable reporting entirely (rare), set:

```bash
export SKILL_QUALITY_REPORT=0
```

## Wrapping rule

When `skill-quality-cli` works, prefix a direct CLI call with
`skill-quality-cli run --skill-name huawei-cloud-sg-manage -- `. Bare `hcloud` commands in
SKILL.md are the documented fallback and stay valid on hosts where the wrapper cannot be
installed; the dispatcher attaches reporting itself.