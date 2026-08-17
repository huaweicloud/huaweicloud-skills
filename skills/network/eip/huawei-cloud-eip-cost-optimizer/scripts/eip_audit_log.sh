#!/bin/bash
# eip_audit_log.sh - EIP 操作审计日志
# 基于 hcloud CLI（KooCLI），替代 Python SDK 方式
#
# Usage:
#   bash eip_audit_log.sh [--region cn-north-4] [--action list|query|analyze|monitor|report] \
#     [--detail TEXT] [--export csv|json] [--log-dir PATH]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# ── 参数解析 ──────────────────────────────────────────────────────
REGION=""
ACTION="list"
DETAIL=""
EXPORT=""
LOG_DIR=""
QUERY_DAYS=1   # query-log 查询天数，默认仅当日

while [[ $# -gt 0 ]]; do
    case $1 in
        --region)   REGION="$2"; shift 2 ;;
        --action)   ACTION="$2"; shift 2 ;;
        --detail)   DETAIL="$2"; shift 2 ;;
        --export)   EXPORT="$2"; shift 2 ;;
        --log-dir)  LOG_DIR="$2"; shift 2 ;;
        --days)     QUERY_DAYS="$2"; shift 2 ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo "  --region      华为云区域 ID（默认从环境变量读取）"
            echo "  --action      操作类型：list|query|analyze|monitor|report|query-log"
            echo "  --detail      操作详情描述"
            echo "  --export      导出格式：csv|json（默认仅显示）"
            echo "  --log-dir     日志目录路径（默认：./eip_audit_logs）"
            echo "  --days N      query-log 查询最近 N 天（默认：1=当日）"
            exit 0 ;;
        *) echo "未知选项: $1" >&2; exit 1 ;;
    esac
done

if [ -n "$REGION" ]; then
    HW_REGION="$REGION"
fi

# 默认日志目录
DEFAULT_LOG_DIR="${SCRIPT_DIR}/../eip_audit_logs"
if [ -z "$LOG_DIR" ]; then
    LOG_DIR="$DEFAULT_LOG_DIR"
fi

# ── 路径安全验证: 拒绝危险路径 + 保护系统目录 ────────────────────
# 保护列表: 系统关键目录一律拒绝写入
case "$LOG_DIR" in
    /etc/*|/usr/*|/var/*|/boot/*|/proc/*|/sys/*|/bin/*|/sbin/*|/lib/*)
        echo "❌ 拒绝写入系统目录: $LOG_DIR" >&2; exit 1 ;;
esac

# 若目录不存在则创建（创建后仍属当前用户）
mkdir -p "$LOG_DIR" 2>/dev/null || {
    echo "❌ 无法创建日志目录: $LOG_DIR（权限不足）" >&2
    exit 1
}

# 规范化路径用于后续检查
LOG_DIR=$(cd "$LOG_DIR" && pwd) || {
    echo "❌ 无法访问日志目录: $LOG_DIR" >&2
    exit 1
}

# 属主校验: 仅当目录属主是当前用户时才 chmod 700（避免 root 篡改系统目录权限）
if [ "$(stat -c %U "$LOG_DIR" 2>/dev/null || echo 'unknown')" = "$(whoami 2>/dev/null || echo 'unknown')" ]; then
    chmod 700 "$LOG_DIR" 2>/dev/null || true
fi

# ── 审计日志文件 ──────────────────────────────────────────────────
AUDIT_JSONL="${LOG_DIR}/audit_$(date '+%Y%m%d').jsonl"
AUDIT_CSV="${LOG_DIR}/audit_$(date '+%Y%m%d').csv"

# ── 时区感知时间戳 ────────────────────────────────────────────────
# 使用本地时间 + 显式标注时区偏移（而非误导性的 Z 后缀）
get_timestamp() {
    local tz_offset
    tz_offset=$(date +%z 2>/dev/null || echo "+0000")
    # 格式: 2024-01-15T10:30:00+08:00
    date "+%Y-%m-%dT%H:%M:%S${tz_offset:0:3}:${tz_offset:3:2}"
}

# ── 文件锁（防止并发写入冲突）────────────────────────────────────
acquire_lock() {
    local lock_file="$1"
    local max_wait=10
    local waited=0

    # 原子操作: 使用 set -C (noclobber) 确保排他创建, 避免 check-then-write 竞态条件
    while ! (set -C; echo $$ > "$lock_file") 2>/dev/null; do
        sleep 1
        waited=$((waited + 1))
        if [ "$waited" -ge "$max_wait" ]; then
            color_print "$YELLOW" "⚠️  等待文件锁超时，强制继续"
            # 超时后强制覆盖（旧锁可能残留）
            echo $$ > "$lock_file"
            break
        fi
    done
}

release_lock() {
    local lock_file="$1"
    rm -f "$lock_file" 2>/dev/null || true
}

LOCK_FILE="${LOG_DIR}/.audit.lock"

# ── 记录审计日志 ──────────────────────────────────────────────────
record_audit() {
    local action="$1"
    local detail="${2:-}"
    local timestamp
    timestamp=$(get_timestamp)

    # JSONL 格式追加（每行一条 JSON）
    local jsonl_entry
    jsonl_entry=$(jq -n -c \
        --arg timestamp "$timestamp" \
        --arg region "$HW_REGION" \
        --arg action "$action" \
        --arg detail "$detail" \
        --arg user "$(whoami 2>/dev/null || echo 'unknown')" \
        '{
            timestamp: $timestamp,
            region: $region,
            action: $action,
            detail: $detail,
            user: $user
        }')

    acquire_lock "$LOCK_FILE"
    echo "$jsonl_entry" >> "$AUDIT_JSONL"
    release_lock "$LOCK_FILE"
}

# ── 查询审计日志 ──────────────────────────────────────────────────
# 支持跨文件查询：合并最近 N 天的 audit_YYYYMMDD.jsonl
query_audit() {
    local filter_action="${1:-}"
    local filter_region="${2:-}"
    local days="${3:-1}"

    # 收集最近 N 天的日志文件
    local files=()
    for i in $(seq 0 $((days - 1))); do
        local fdate
        fdate=$(date -d "-${i} days" '+%Y%m%d' 2>/dev/null || date -v-${i}d '+%Y%m%d' 2>/dev/null)
        [ -z "$fdate" ] && continue
        local f="${LOG_DIR}/audit_${fdate}.jsonl"
        [ -f "$f" ] && [ -s "$f" ] && files+=("$f")
    done

    if [ "${#files[@]}" -eq 0 ]; then
        if [ "$days" -le 1 ]; then
            color_print "$YELLOW" "ℹ️  今日暂无审计记录"
        else
            color_print "$YELLOW" "ℹ️  最近 ${days} 天暂无审计记录"
        fi
        return
    fi

    # 合并所有文件并按时间排序
    local filtered
    filtered=$(cat "${files[@]}")

    if [ -n "$filter_action" ]; then
        filtered=$(echo "$filtered" | jq -c "select(.action == \"$filter_action\")")
    fi

    if [ -n "$filter_region" ]; then
        filtered=$(echo "$filtered" | jq -c "select(.region == \"$filter_region\")")
    fi

    if [ -z "$filtered" ] || [ "$filtered" = "" ]; then
        color_print "$YELLOW" "ℹ️  未找到匹配的审计记录"
        return
    fi

    echo "$filtered" | jq -r -s 'sort_by(.timestamp) | .[] | "\(.timestamp) | \(.region) | \(.action) | \(.detail) | \(.user)"'
}

# ── 导出 CSV ──────────────────────────────────────────────────────
# 修复：仅写入一次 header（检查文件是否为空/新文件）
export_csv() {
    local output_file="$1"
    local data="$2"

    # 仅在文件为空或不存在时写入 header
    if [ ! -f "$output_file" ] || [ ! -s "$output_file" ]; then
        echo "timestamp,region,action,detail,user" > "$output_file"
    fi

    echo "$data" | jq -r '. | [.timestamp, .region, .action, .detail, .user] | @csv' >> "$output_file"
}

# ── 导出 JSON ─────────────────────────────────────────────────────
export_json() {
    local output_file="$1"
    local data="$2"

    echo "$data" | jq -s '.' > "$output_file"
}

# ── 主逻辑 ────────────────────────────────────────────────────────
main() {
    case "$ACTION" in
        list|query|analyze|monitor|report)
            # 记录审计日志
            record_audit "$ACTION" "$DETAIL"
            color_print "$GREEN" "✅ 审计记录已写入: ${AUDIT_JSONL}"
            ;;
        query-log)
            # 查询审计日志（支持最近 N 天）
            color_print "$BLUE" "📋 审计日志查询（最近 ${QUERY_DAYS} 天）"
            query_audit "" "" "$QUERY_DAYS"
            ;;
        *)
            color_print "$RED" "❌ 未知操作: $ACTION"
            echo "支持的操作: list, query, analyze, monitor, report, query-log" >&2
            exit 1
            ;;
    esac

    # 导出
    if [ -n "$EXPORT" ]; then
        case "$EXPORT" in
            csv)
                if [ -f "$AUDIT_JSONL" ] && [ -s "$AUDIT_JSONL" ]; then
                    acquire_lock "$LOCK_FILE"
                    export_csv "$AUDIT_CSV" "$(cat "$AUDIT_JSONL")"
                    release_lock "$LOCK_FILE"
                    color_print "$GREEN" "✅ 已导出 CSV: ${AUDIT_CSV}"
                else
                    color_print "$YELLOW" "⚠️  无数据可导出"
                fi
                ;;
            json)
                if [ -f "$AUDIT_JSONL" ] && [ -s "$AUDIT_JSONL" ]; then
                    local json_output="${AUDIT_CSV%.csv}.json"
                    export_json "$json_output" "$(cat "$AUDIT_JSONL")"
                    color_print "$GREEN" "✅ 已导出 JSON: ${json_output}"
                else
                    color_print "$YELLOW" "⚠️  无数据可导出"
                fi
                ;;
            *)
                color_print "$RED" "❌ 不支持的导出格式: $EXPORT（仅支持 csv / json）" >&2
                exit 1
                ;;
        esac
    fi

    # 显示最近记录
    if [ -f "$AUDIT_JSONL" ] && [ -s "$AUDIT_JSONL" ]; then
        echo ""
        echo "最近 5 条审计记录:"
        tail -5 "$AUDIT_JSONL" | jq -r '. | "  \(.timestamp) [\(.region)] \(.action): \(.detail) (by \(.user))"'
    fi
}

main
