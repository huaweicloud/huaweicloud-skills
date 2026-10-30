#!/usr/bin/env bash
# ============================================================
# host-migration 运行包装脚本
#
# 设计原则（遵循工具现有架构，零硬编码）：
#   - 本脚本不含任何 IP / AK / SK / 密码 / 域名等运行时值
#   - 所有运行时值只来自 config/migrate.yaml（配置层）
#   - 只编排工具既有的两个 CLI 入口，不改动任何核心模块
#
# 用法:
#   ./run_migration.sh                          # 清理 + 迁移（默认 public）
#   ./run_migration.sh --skip-cleanup           # 跳过清理，直接迁移（重试用）
#   ./run_migration.sh --config config/migrate.yaml --scenario public
#   ./run_migration.sh --json                   # 结构化输出
#   ./run_migration.sh --precheck               # 只做前置检查，不执行迁移
#
# 退出码: 与 unified_migrate.py 一致（0=成功 1=失败 2=配置错误 130=中断）
# ============================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$PROJECT_DIR/config/migrate.yaml"
SCENARIO="public"
JSON_FLAG=""
DO_CLEANUP=1
DO_PRECHECK=0

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)     CONFIG="$2"; shift 2 ;;
        --scenario)   SCENARIO="$2"; shift 2 ;;
        --json)       JSON_FLAG="--json"; shift ;;
        --skip-cleanup) DO_CLEANUP=0; shift ;;
        --precheck)   DO_PRECHECK=1; shift ;;
        -h|--help)    usage ;;
        *) echo "未知参数: $1"; usage ;;
    esac
done

cd "$PROJECT_DIR"

# ---- 前置检查（只读） ----
if [[ ! -f "$CONFIG" ]]; then
    echo "错误: 配置文件不存在: $CONFIG"; exit 2
fi

python3 - <<'PYEOF' "$CONFIG"
import sys
try:
    import winrm, yaml, paramiko  # noqa: F401
except ImportError as e:
    print(f"依赖缺失: {e}，请先 pip install pywinrm requests-ntlm pyspnego pyyaml paramiko")
    sys.exit(2)
from core.config import ConfigLoader
cfg = ConfigLoader.load(sys.argv[1])
req = ["source.host", "source.username", "source.password", "obs.ak", "obs.sk",
       "sms_agent.ak", "sms_agent.sk", "sms_agent.domain_id", "download.packages"]
for field in req:
    if field == "download.packages" and not cfg.download.packages:
        print("配置错误: download.packages 为空"); sys.exit(2)
print(f"配置加载成功: scenario={cfg.scenario} source={cfg.source.host}:{cfg.source.winrm_port} "
      f"agent={cfg.sms_agent.agent_version}/{cfg.sms_agent.configure_mode}")
PYEOF

if [[ "$DO_PRECHECK" == "1" ]]; then
    echo "[precheck] 前置检查通过。未执行任何变更操作。"
    exit 0
fi

# ---- 可选：源端清理（迁移前必做，幂等） ----
if [[ "$DO_CLEANUP" == "1" ]]; then
    echo "==================== [1/2] 清理源端残留 ===================="
    python3 cleanup_windows.py "$CONFIG"
fi

# ---- 执行迁移 ----
echo "==================== [2/2] 执行迁移 ===================="
python3 unified_migrate.py --scenario "$SCENARIO" --config "$CONFIG" $JSON_FLAG