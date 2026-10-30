#!/usr/bin/env bash
# ============================================================
# SMS 控制面任务编排包装脚本（步骤二~五）
#
# 设计原则（与 run_migration.sh 一致）：
#   - 不含任何 IP / AK / SK / 任务 ID 等运行时值，全部来自 config/migrate.yaml
#   - 只调用 sms_task.py 现有 CLI，不改动核心模块
#   - 可编排：支持单步或 --steps 串联
#
# 用法:
#   ./run_sms_task.sh discover                    # 步骤二前：发现源端（只读）
#   ./run_sms_task.sh ecs-list                    # 目的端候选 ECS（只读）
#   ./run_sms_task.sh create                      # 步骤二：设置目的端（交互确认）
#   ./run_sms_task.sh create --yes                # 自动确认
#   ./run_sms_task.sh start --yes                 # 步骤三：开始全量复制
#   ./run_sms_task.sh wait --target-state SYNCING --timeout 14400
#   ./run_sms_task.sh sync --yes                  # 步骤四：增量同步
#   ./run_sms_task.sh cutover --yes               # 步骤四：启动目的端（割接）
#   ./run_sms_task.sh cleanup --yes               # 步骤五：清理快照（不可逆）
#   ./run_sms_task.sh pipeline --steps discover,create,start,wait --yes
# ============================================================
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [[ ! -x "$PROJECT_DIR/sms_task.py" ]]; then
    echo "错误: sms_task.py 不存在或不可执行"; exit 2
fi

exec python3 sms_task.py "$@"