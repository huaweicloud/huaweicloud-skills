#!/bin/bash
#
# eip_audit_log.sh - EIP 操作审计日志
#
# 功能:
#   - 记录所有 EIP 操作历史
#   - 支持 JSON 格式审计日志
#   - 支持审计日志查询和导出
#   - 符合等保合规要求
#
# 使用方法:
#   ./eip_audit_log.sh --action release --eip-id eip-xxx --operator admin
#   ./eip_audit_log.sh --query --days 30
#   ./eip_audit_log.sh --export --format csv
#
# 环境变量:
#   EIP_AUDIT_LOG_DIR - 审计日志目录（默认：~/.eip-audit-logs）
#

set -e

# 默认配置
AUDIT_LOG_DIR="${EIP_AUDIT_LOG_DIR:-$HOME/.eip-audit-logs}"
AUDIT_LOG_FILE="$AUDIT_LOG_DIR/audit_$(date +%Y%m).jsonl"

# 创建审计日志目录
mkdir -p "$AUDIT_LOG_DIR"

# 解析参数
ACTION=""
EIP_ID=""
OPERATOR="${USER:-admin}"
DETAILS=""
QUERY_MODE=false
QUERY_DAYS=30
EXPORT_MODE=false
EXPORT_FORMAT="json"

while [[ $# -gt 0 ]]; do
    case $1 in
        --action)
            ACTION="$2"
            shift 2
            ;;
        --eip-id)
            EIP_ID="$2"
            shift 2
            ;;
        --operator)
            OPERATOR="$2"
            shift 2
            ;;
        --details)
            DETAILS="$2"
            shift 2
            ;;
        --query)
            QUERY_MODE=true
            shift
            ;;
        --days)
            QUERY_DAYS="$2"
            shift 2
            ;;
        --export)
            EXPORT_MODE=true
            shift
            ;;
        --format)
            EXPORT_FORMAT="$2"
            shift 2
            ;;
        --log-dir)
            AUDIT_LOG_DIR="$2"
            AUDIT_LOG_FILE="$AUDIT_LOG_DIR/audit_$(date +%Y%m).jsonl"
            shift 2
            ;;
        --help)
            echo "用法：$0 [选项]"
            echo ""
            echo "记录操作:"
            echo "  --action ACTION      操作类型 (release, create, update_bandwidth, bind, unbind)"
            echo "  --eip-id EIP_ID      EIP ID"
            echo "  --operator OPERATOR  操作人员"
            echo "  --details DETAILS    操作详情（JSON 格式）"
            echo ""
            echo "查询模式:"
            echo "  --query              查询审计日志"
            echo "  --days DAYS          查询最近 N 天的日志（默认：30）"
            echo ""
            echo "导出模式:"
            echo "  --export             导出审计日志"
            echo "  --format FORMAT      导出格式：json, csv, html（默认：json）"
            echo ""
            echo "其他选项:"
            echo "  --log-dir DIR        审计日志目录"
            echo "  --help               显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知选项：$1"
            exit 1
            ;;
    esac
done

# 查询模式
if [ "$QUERY_MODE" = true ]; then
    echo "🔍 查询最近 $QUERY_DAYS 天的审计日志..."
    echo ""
    
    if [ ! -f "$AUDIT_LOG_FILE" ] && [ -z "$(ls -A $AUDIT_LOG_DIR/*.jsonl 2>/dev/null)" ]; then
        echo "ℹ️  暂无审计日志记录"
        exit 0
    fi
    
    # 计算日期阈值
    THRESHOLD_DATE=$(date -d "$QUERY_DAYS days ago" +%Y%m%d 2>/dev/null || date -v-${QUERY_DAYS}d +%Y%m%d 2>/dev/null || echo "0")
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "%-20s %-15s %-20s %-15s\n" "时间" "操作类型" "EIP ID" "操作人员"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 遍历所有日志文件
    for LOG_FILE in "$AUDIT_LOG_DIR"/audit_*.jsonl; do
        [ -f "$LOG_FILE" ] || continue
        
        # 使用 jq 读取所有 JSON 对象（支持多行格式）
        jq -c '.' "$LOG_FILE" 2>/dev/null | while IFS= read -r LINE; do
            TIMESTAMP=$(echo "$LINE" | jq -r '.timestamp' 2>/dev/null)
            FILE_DATE=$(echo "$TIMESTAMP" | cut -d'T' -f1 | tr -d '-')
            
            # 只显示指定天数内的日志
            if [ "$FILE_DATE" -ge "$THRESHOLD_DATE" ] 2>/dev/null; then
                printf "%-20s %-15s %-20s %-15s\n" \
                    "$(echo "$TIMESTAMP" | cut -d'T' -f1) $(echo "$TIMESTAMP" | cut -d'T' -f2 | cut -d'.' -f1)" \
                    "$(echo "$LINE" | jq -r '.operation' 2>/dev/null)" \
                    "$(echo "$LINE" | jq -r '.eip_id' 2>/dev/null)" \
                    "$(echo "$LINE" | jq -r '.operator' 2>/dev/null)"
            fi
        done
    done
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    exit 0
fi

# 导出模式
if [ "$EXPORT_MODE" = true ]; then
    echo "📊 导出审计日志（格式：$EXPORT_FORMAT）..."
    echo ""
    
    EXPORT_FILE="$AUDIT_LOG_DIR/export_$(date +%Y%m%d_%H%M%S).$EXPORT_FORMAT"
    
    case $EXPORT_FORMAT in
        json)
            echo "[" > "$EXPORT_FILE"
            FIRST=true
            for LOG_FILE in "$AUDIT_LOG_DIR"/audit_*.jsonl; do
                [ -f "$LOG_FILE" ] || continue
                while IFS= read -r LINE; do
                    if [ "$FIRST" = true ]; then
                        FIRST=false
                    else
                        echo "," >> "$EXPORT_FILE"
                    fi
                    echo "$LINE" >> "$EXPORT_FILE"
                done < "$LOG_FILE"
            done
            echo "]" >> "$EXPORT_FILE"
            ;;
        
        csv)
            echo "timestamp,operation,eip_id,operator,details" > "$EXPORT_FILE"
            for LOG_FILE in "$AUDIT_LOG_DIR"/audit_*.jsonl; do
                [ -f "$LOG_FILE" ] || continue
                while IFS= read -r LINE; do
                    TIMESTAMP=$(echo "$LINE" | jq -r '.timestamp' 2>/dev/null)
                    OPERATION=$(echo "$LINE" | jq -r '.operation' 2>/dev/null)
                    EIP_ID_VAL=$(echo "$LINE" | jq -r '.eip_id' 2>/dev/null)
                    OPERATOR_VAL=$(echo "$LINE" | jq -r '.operator' 2>/dev/null)
                    DETAILS_VAL=$(echo "$LINE" | jq -r '.details' 2>/dev/null | tr ',' ';' | tr '"' "'")
                    echo "$TIMESTAMP,$OPERATION,$EIP_ID_VAL,$OPERATOR_VAL,\"$DETAILS_VAL\"" >> "$EXPORT_FILE"
                done < "$LOG_FILE"
            done
            ;;
        
        html)
            cat > "$EXPORT_FILE" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>EIP 审计日志</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>📋 EIP 操作审计日志</h1>
    <p>导出时间：EOF
            echo "$(date '+%Y-%m-%d %H:%M:%S')" >> "$EXPORT_FILE"
            cat >> "$EXPORT_FILE" << 'EOF'
</p>
    <table>
        <tr>
            <th>时间</th>
            <th>操作类型</th>
            <th>EIP ID</th>
            <th>操作人员</th>
            <th>详情</th>
        </tr>
EOF
            for LOG_FILE in "$AUDIT_LOG_DIR"/audit_*.jsonl; do
                [ -f "$LOG_FILE" ] || continue
                while IFS= read -r LINE; do
                    TIMESTAMP=$(echo "$LINE" | jq -r '.timestamp' 2>/dev/null)
                    OPERATION=$(echo "$LINE" | jq -r '.operation' 2>/dev/null)
                    EIP_ID_VAL=$(echo "$LINE" | jq -r '.eip_id' 2>/dev/null)
                    OPERATOR_VAL=$(echo "$LINE" | jq -r '.operator' 2>/dev/null)
                    DETAILS_VAL=$(echo "$LINE" | jq -r '.details' 2>/dev/null | tr '"' "'")
                    echo "        <tr><td>$TIMESTAMP</td><td>$OPERATION</td><td>$EIP_ID_VAL</td><td>$OPERATOR_VAL</td><td>$DETAILS_VAL</td></tr>" >> "$EXPORT_FILE"
                done < "$LOG_FILE"
            done
            cat >> "$EXPORT_FILE" << 'EOF'
    </table>
</body>
</html>
EOF
            ;;
        
        *)
            echo "不支持的导出格式：$EXPORT_FORMAT"
            exit 1
            ;;
    esac
    
    echo "✓ 导出成功：$EXPORT_FILE"
    exit 0
fi

# 记录审计日志模式
if [ -n "$ACTION" ] && [ -n "$EIP_ID" ]; then
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # 构建审计日志条目
    if [ -n "$DETAILS" ]; then
        # 如果 details 已经是 JSON 对象（以{开头），直接使用；否则作为字符串处理
        if [[ "$DETAILS" == "{"* ]]; then
            DETAILS_JSON="$DETAILS"
        else
            DETAILS_JSON="\"$DETAILS\""
        fi
    else
        DETAILS_JSON="{}"
    fi
    
    AUDIT_ENTRY=$(cat << EOF
{
  "timestamp": "$TIMESTAMP",
  "operation": "$ACTION",
  "eip_id": "$EIP_ID",
  "operator": "$OPERATOR",
  "region": "${HW_REGION:-cn-north-4}",
  "details": $DETAILS_JSON
}
EOF
)
    
    # 追加到审计日志文件
    echo "$AUDIT_ENTRY" >> "$AUDIT_LOG_FILE"
    
    echo "✓ 审计日志已记录"
    echo "  操作：$ACTION"
    echo "  EIP ID: $EIP_ID"
    echo "  操作人员：$OPERATOR"
    echo "  时间：$TIMESTAMP"
    echo "  日志文件：$AUDIT_LOG_FILE"
    
    exit 0
else
    echo "⚠️  请提供 --action 和 --eip-id 参数，或使用 --query/--export 模式"
    echo ""
    echo "示例:"
    echo "  # 记录释放操作"
    echo "  $0 --action release --eip-id eip-xxx --operator admin"
    echo ""
    echo "  # 查询最近 30 天日志"
    echo "  $0 --query --days 30"
    echo ""
    echo "  # 导出 CSV 格式日志"
    echo "  $0 --export --format csv"
    
    exit 1
fi
