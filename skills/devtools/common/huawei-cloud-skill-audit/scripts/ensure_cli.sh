#!/bin/bash
# ensure_cli.sh — 确保 skill-quality-cli 就绪。
# 行为: 已装可用 → 静默退出; 未装 → 委托 install_cli.sh 执行安装(唯一 canonical 实现, 含 sha256 校验)。
# 升级: 不自动升级, 需手动 `skill-quality-cli upgrade`。
# 由 huawei-cloud-skill-quality-cli-inject v3.0.0 生成，请勿手动修改

# 1. 已安装且可用 → 退出
if command -v skill-quality-cli &>/dev/null && skill-quality-cli version &>/dev/null 2>&1; then
    exit 0
fi

# 2. 未安装 → 委托 install_cli.sh（唯一 canonical 安装实现; 失败不阻塞业务, 警告输出到 stderr）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/install_cli.sh" || true
exit 0