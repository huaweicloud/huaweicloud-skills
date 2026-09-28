# CLI Installation Guide

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | `bash "$AUDIT_DIR/scripts/ensure_cli.sh"` (ensured idempotently if absent; `AUDIT_DIR` = huawei-cloud-skill-audit 安装目录, 见 SKILL.md Core Commands) |
| `hcloud` | Huawei Cloud KooCLI | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html) |

## Manual upgrade

CLI no longer auto-upgrades（合规 v1.7+）。To upgrade to the latest version, run manually:

```bash
skill-quality-cli upgrade
```

## Disable telemetry (optional)

Telemetry is automatic (opt-out). To disable reporting entirely (rare), set:

```bash
export SKILL_QUALITY_DISABLE=1
```

## Manual cold-start (fallback)

If `ensure_cli.sh` is unavailable, install manually:

```bash
bash "$AUDIT_DIR/scripts/install_cli.sh"
```

The install script downloads the platform package, verifies it, and installs
`skill-quality-cli` into `~/.local/bin/`. Upgrade afterwards with
`skill-quality-cli upgrade`.

> 脚本关系: `ensure_cli.sh` 是**幂等自动入口**(已装即跳过, 供业务脚本/Step 0 调用);
> `install_cli.sh` 是**唯一 canonical 安装实现**(含 sha256 校验); `ensure_cli.sh` 在
> CLI 缺失时直接委托 `install_cli.sh` 完成安装, 不再各自维护一套下载/安装逻辑 —
> 修改安装逻辑只需改 `install_cli.sh` 一处。
