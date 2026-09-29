#!/bin/bash
#
# Teradata 到 DWS 完整迁移示例脚本
#
# 使用前请修改以下变量为实际值
#

set -euo pipefail

# ============================================================
# 配置（请修改为实际值）
# ============================================================
TD_CONFIG="config/teradata_config.ini"
DWS_CONFIG="config/dws_config.ini"
SCHEMA="mydb"
OUTPUT_DIR="./output"
LOG_DIR="./logs"

# OBS 配置（大表迁移时使用）
OBS_CONFIG="config/obs_config.ini"
OBS_TEMP_DIR="migration/temp/mig"

# ============================================================
# 准备工作
# ============================================================
mkdir -p "$OUTPUT_DIR" "$LOG_DIR"

echo "============================================================"
echo "  Teradata → DWS 迁移开始"
echo "  时间: $(date)"
echo "  Schema: $SCHEMA"
echo "============================================================"

# ============================================================
# Step 1: 表结构迁移 (DDL)
# ============================================================
echo ""
echo "[Step 1] 表结构迁移..."
# 注意: 如 DWS 中已存在同名表，脚本会暂停等待用户确认
# 非交互模式可加 --force 自动删除重建
python3 scripts/migrate_schema.py \
    --td-config "$TD_CONFIG" \
    --dws-config "$DWS_CONFIG" \
    --schema "$SCHEMA" \
    --output-dir "$OUTPUT_DIR" \
    2>&1 | tee "$LOG_DIR/step1_schema.log"

echo "[Step 1] 表结构迁移完成"

# ============================================================
# Step 2: 表数据迁移 (DML)
# ============================================================
echo ""
echo "[Step 2] 表数据迁移..."
python3 scripts/migrate_data.py \
    --td-config "$TD_CONFIG" \
    --dws-config "$DWS_CONFIG" \
    --schema "$SCHEMA" \
    --method obs \
    --obs-config "$OBS_CONFIG" \
    --obs-temp-dir "$OBS_TEMP_DIR" \
    --output-dir "$OUTPUT_DIR" \
    2>&1 | tee "$LOG_DIR/step2_data.log"

echo "[Step 2] 表数据迁移完成"

# ============================================================
# Step 3: 校验与验证
# ============================================================
echo ""
echo "[Step 3] 校验与验证..."
python3 scripts/validate_migration.py \
    --td-config "$TD_CONFIG" \
    --dws-config "$DWS_CONFIG" \
    --schema "$SCHEMA" \
    --output-dir "$OUTPUT_DIR" \
    2>&1 | tee "$LOG_DIR/step3_validate.log"

echo "[Step 3] 校验完成"

# ============================================================
# 完成
# ============================================================
echo ""
echo "============================================================"
echo "  迁移完成！"
echo "  时间: $(date)"
echo "  输出目录: $OUTPUT_DIR"
echo "  日志目录: $LOG_DIR"
echo "  校验报告: $OUTPUT_DIR/${SCHEMA}_validation_report.json"
echo "============================================================"
