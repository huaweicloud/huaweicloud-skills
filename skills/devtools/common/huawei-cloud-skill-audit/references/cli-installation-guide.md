# CLI Installation Guide

> **官方口径**: `skill-quality-cli` 只由 `scripts/ensure_cli.sh` 就绪(唯一安装入口, 幂等, 已装即跳过),
> 不提供任何独立安装脚本; 版本按平台最低支持版本保持(每次 run 自动对齐); 关闭上报统一用
> `SKILL_QUALITY_REPORT=0`。本 skill 内所有 `hcloud` 调用必须经 `scripts/hcloud-run.sh` 或
> `skill-quality-cli run --skill-name huawei-cloud-skill-audit -- ` 包裹, 禁止裸调。

<!-- BEGIN inject:cli-guide (managed, do not edit) -->

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | `bash scripts/ensure_cli.sh` (ensured idempotently if absent) |
| `hcloud` | Huawei Cloud KooCLI | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html) |

## Upgrade

The CLI stays up to date on each run (auto-upgrade enabled by default). To upgrade to the latest version manually, run:

```bash
skill-quality-cli upgrade
```

## Disable telemetry (optional)

Telemetry is automatic (opt-out). To disable reporting entirely (rare), set:

```bash
export SKILL_QUALITY_REPORT=0
```

## Manual cold-start (fallback)

If `ensure_cli.sh` is unavailable, request the platform package from the latest
endpoint and install it into `~/.local/bin/`, then verify with
`skill-quality-cli version`. Upgrade afterwards with `skill-quality-cli upgrade`.

<!-- END inject:cli-guide -->

## 本 skill 的调用方式

本 skill 安装目录记为 `AUDIT_DIR`(= huawei-cloud-skill-audit 的绝对安装路径, 见 SKILL.md Step 0),
所有命令用它拼绝对路径, 不在被审计目录内使用相对路径执行本 skill 的脚本:

```bash
bash "$AUDIT_DIR/scripts/ensure_cli.sh"          # 幂等就绪 CLI(已装即跳过)
bash "$AUDIT_DIR/scripts/hcloud-run.sh" ...      # 一切 hcloud 调用的唯一入口
```

`ensure_cli.sh` 是唯一的安装入口: CLI 缺失时它从平台 latest 接口取预签名包、校验 sha256 后安装到
`~/.local/bin/`, 不再落任何独立安装脚本。`hcloud-run.sh` 只认 `skill-quality-cli` 单一载体,
CLI 不可用时直接失败退出(exit 1), 不降级裸调 `hcloud`。