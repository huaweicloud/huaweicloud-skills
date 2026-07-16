#!/bin/bash
# list_eips.sh - 列出所有 EIP 及其详细信息
# 基于 hcloud CLI（KooCLI），替代 Python SDK 方式
#
# Usage:
#   bash list_eips.sh --region cn-north-4
#   bash list_eips.sh --status DOWN
#   bash list_eips.sh --idle-only
#   bash list_eips.sh --summary
#   bash list_eips.sh --format json
#   bash list_eips.sh --publicip-id <EIP_ID>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# ── 参数解析 ──────────────────────────────────────────────────────
REGION=""
STATUS_FILTER=""
IDLE_ONLY=false
SUMMARY=false
FORMAT="text"
PUBLICIP_ID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --region)       REGION="$2"; shift 2 ;;
        --status)       STATUS_FILTER="$2"; shift 2 ;;
        --idle-only)    IDLE_ONLY=true; shift ;;
        --summary)      SUMMARY=true; shift ;;
        --format)       FORMAT="$2"; shift 2 ;;
        --publicip-id)  PUBLICIP_ID="$2"; shift 2 ;;
        --help|-h)
            echo "用法: $0 [--region REGION] [--status STATUS] [--idle-only] [--summary] [--format text|json] [--publicip-id EIP_ID]"
            echo "  --region       区域（默认：HW_REGION_NAME 或 cn-north-4）"
            echo "  --status       状态过滤（BINDING, DOWN, ELB 等）"
            echo "  --idle-only    仅显示闲置 EIP"
            echo "  --summary      仅输出统计数据（CSV：总数,闲置数,总带宽）"
            echo "  --format       输出格式：text（默认）、json"
            echo "  --publicip-id  按指定 EIP ID 查询单个 EIP 详情"
            exit 0 ;;
        *) echo "未知选项: $1" >&2; exit 1 ;;
    esac
done

# 校验 --format
case "$FORMAT" in
    text|json) ;;
    *) echo "❌ 不支持的格式: '$FORMAT'（仅支持 text / json）" >&2; exit 1 ;;
esac

# 区域优先级：命令行 > 环境变量 > 默认值
if [ -n "$REGION" ]; then
    HW_REGION="$REGION"
fi

# ── 查询单个 EIP（按 ID）──────────────────────────────────────────
fetch_single_eip() {
    local eip_id="$1"
    local raw_json
    raw_json=$(run_hcloud EIP ShowPublicip/v2 --publicip_id="$eip_id" 2>/dev/null) || {
        color_print "$RED" "❌ 查询 EIP ${eip_id} 失败（ID 无效或凭证错误）"
        exit 1
    }

    if [ -z "$raw_json" ] || ! echo "$raw_json" | jq -e '.publicip' >/dev/null 2>&1; then
        color_print "$RED" "❌ 未找到 EIP: ${eip_id}"
        exit 1
    fi

    echo "$raw_json"
}

# ── 查询 EIP 列表 ────────────────────────────────────────────────
fetch_eip_list() {
    local raw_json
    raw_json=$(run_hcloud EIP ListPublicips/v2 --limit=1000 2>/dev/null) || {
        color_print "$RED" "❌ 查询 EIP 列表失败（区域 ${HW_REGION} 可能无效或凭证错误）"
        exit 1
    }

    if [ -z "$raw_json" ] || ! echo "$raw_json" | jq -e '.publicips' >/dev/null 2>&1; then
        color_print "$RED" "❌ API 返回异常，请检查区域 ${HW_REGION} 是否有效"
        exit 1
    fi

    echo "$raw_json"
}

# ── 主逻辑 ────────────────────────────────────────────────────────
main() {
    # ── 按 EIP ID 查询单个 EIP ──────────────────────────────────────
    if [ -n "$PUBLICIP_ID" ]; then
        local raw_json
        raw_json=$(fetch_single_eip "$PUBLICIP_ID")

        local eip_json
        eip_json=$(echo "$raw_json" | jq -c '.publicip')

        local eip_id ip status bw_size charge_mode port_id create_time
        eip_id=$(echo "$eip_json" | jq -r '.id // "N/A"')
        ip=$(echo "$eip_json" | jq -r '.public_ip_address // "N/A"')
        status=$(echo "$eip_json" | jq -r '.status // "UNKNOWN"')
        bw_size=$(echo "$eip_json" | jq -r '.bandwidth_size // 0')
        charge_mode=$(echo "$eip_json" | jq -r '.bandwidth_charge_mode // "N/A"')
        port_id=$(echo "$eip_json" | jq -r '.port_id // ""')
        create_time=$(echo "$eip_json" | jq -r '.create_time // "N/A"')

        local is_idle=false
        if [ "$status" = "DOWN" ] || [ "$status" = "ELB" ] || [ -z "$port_id" ]; then
            is_idle=true
        fi

        if [ "$FORMAT" = "json" ]; then
            echo "$eip_json" | jq -c '{
                id: .id,
                public_ip_address: .public_ip_address,
                status: .status,
                bandwidth_size: .bandwidth_size,
                bandwidth_id: .bandwidth_id,
                bandwidth_name: .bandwidth_name,
                bandwidth_share_type: .bandwidth_share_type,
                port_id: .port_id,
                create_time: .create_time,
                idle: (if (.status == "DOWN" or .status == "ELB" or (.port_id | not) or (.port_id == "")) then true else false end)
            }' | jq .
        else
            color_print "$BLUE" "============================================================"
            color_print "$BLUE" "  EIP 详情（区域：${HW_REGION}）"
            color_print "$BLUE" "============================================================"
            echo ""

            printf "  ${BOLD}%s${RESET}\n" "$ip"
            echo "    EIP ID:      ${eip_id}"
            local status_color="$GREEN" status_text="$status"
            if [ "$is_idle" = true ]; then
                status_color="$RED"; status_text="IDLE"
            fi
            printf "    状态：       ${status_color}%s${RESET}\n" "$status_text"
            echo "    带宽大小：   ${bw_size} Mbps"
            echo "    计费模式：   ${charge_mode}"
            if [ -n "$port_id" ]; then
                echo "    绑定资源：   ${port_id}"
            else
                printf "    绑定资源：   ${YELLOW}未绑定${RESET}\n"
            fi
            if [ "$create_time" != "N/A" ]; then
                echo "    创建时间：   ${create_time}"
            fi
            echo ""
            color_print "$BLUE" "------------------------------------------------------------"
        fi
        exit 0
    fi

    # ── 列表查询 ────────────────────────────────────────────────────
    local raw_json
    raw_json=$(fetch_eip_list)

    # 提取 publicips 数组
    local eips_json
    eips_json=$(echo "$raw_json" | jq -c '.publicips // []')

    local total_count
    total_count=$(echo "$eips_json" | jq 'length')

    if [ "$total_count" -eq 0 ]; then
        if [ "$SUMMARY" = true ]; then
            echo "0,0,0"
        else
            color_print "$YELLOW" "⚠️  当前区域没有找到 EIP 资源"
        fi
        exit 0
    fi

    # ── Summary 模式 ──────────────────────────────────────────────
    if [ "$SUMMARY" = true ]; then
        local idle_count total_bw
        idle_count=$(echo "$eips_json" | jq '[.[] | select(.status == "DOWN" or .status == "ELB")] | length')
        total_bw=$(echo "$eips_json" | jq '[.[].bandwidth_size // 0] | add // 0')
        echo "${total_count},${idle_count},${total_bw}"
        exit 0
    fi

    # ── 详细列表模式 ──────────────────────────────────────────────
    # 收集所有 EIP 信息到 JSON 数组（供 JSON 输出使用）
    local eip_results='[]'

    if [ "$FORMAT" = "text" ]; then
        color_print "$BLUE" "============================================================"
        color_print "$BLUE" "  EIP 列表查询（区域：${HW_REGION}）"
        color_print "$BLUE" "============================================================"
        echo ""
    fi

    local idx=0
    local idle_count=0
    local binding_count=0
    local total_bw=0

    # 遍历每个 EIP（使用进程替换避免子 shell 变量丢失）
    while IFS= read -r row; do
        local eip_id ip status bw_size charge_mode port_id create_time

        eip_id=$(echo "$row" | jq -r '.id // "N/A"')
        ip=$(echo "$row" | jq -r '.public_ip_address // "N/A"')
        status=$(echo "$row" | jq -r '.status // "UNKNOWN"')
        bw_size=$(echo "$row" | jq -r '.bandwidth_size // 0')
        charge_mode=$(echo "$row" | jq -r '.bandwidth_charge_mode // "N/A"')
        port_id=$(echo "$row" | jq -r '.port_id // ""')
        create_time=$(echo "$row" | jq -r '.create_time // "N/A"')

        # 状态过滤
        if [ -n "$STATUS_FILTER" ] && [ "$status" != "$STATUS_FILTER" ]; then
            continue
        fi

        # 闲置判断：status 为 DOWN 或 ELB，或 port_id 为空
        local is_idle=false
        if [ "$status" = "DOWN" ] || [ "$status" = "ELB" ] || [ -z "$port_id" ]; then
            is_idle=true
        fi

        # 闲置过滤
        if [ "$IDLE_ONLY" = true ] && [ "$is_idle" = false ]; then
            continue
        fi

        idx=$((idx + 1))

        # 统计（仅统计过滤后的）
        if [ "$is_idle" = true ]; then
            idle_count=$((idle_count + 1))
        else
            binding_count=$((binding_count + 1))
        fi
        total_bw=$((total_bw + bw_size))

        # 收集到 JSON 数组
        local result_row
        result_row=$(echo "$row" | jq -c --argjson idle_bool "$( [ "$is_idle" = true ] && echo true || echo false )" '. + {idle: $idle_bool}')
        eip_results=$(echo "$eip_results" | jq --argjson r "$result_row" '. + [$r]')

        # 文本输出
        if [ "$FORMAT" = "text" ]; then
            local status_color="$GREEN" status_text="$status"
            if [ "$is_idle" = true ]; then
                status_color="$RED"
                status_text="IDLE"
            fi

            printf "[%d] ${BOLD}%s${RESET}\n" "$idx" "$ip"
            echo "    EIP ID:      ${eip_id}"
            printf "    状态：       ${status_color}%s${RESET}\n" "$status_text"
            echo "    带宽大小：   ${bw_size} Mbps"
            echo "    计费模式：   ${charge_mode}"

            if [ -n "$port_id" ]; then
                echo "    绑定资源：   ${port_id}"
            else
                printf "    绑定资源：   ${YELLOW}未绑定${RESET}\n"
            fi

            if [ "$create_time" != "N/A" ]; then
                echo "    创建时间：   ${create_time}"
            fi
            echo ""
        fi
    done < <(echo "$eips_json" | jq -c '.[]')

    # ── 输出结果 ──────────────────────────────────────────────────
    if [ "$FORMAT" = "json" ]; then
        local ts
        ts=$(date '+%Y-%m-%dT%H:%M:%S+08:00')
        jq -n -c \
            --arg region "$HW_REGION" \
            --arg timestamp "$ts" \
            --argjson total "$idx" \
            --argjson idle "$idle_count" \
            --argjson bound "$binding_count" \
            --argjson bw "$total_bw" \
            --argjson details "$eip_results" \
            '{
                region: $region,
                timestamp: $timestamp,
                summary: {
                    total_eips: $total,
                    idle_eips: $idle,
                    bound_eips: $bound,
                    total_bandwidth_mbps: $bw
                },
                details: $details
            }' | jq .
    else
        color_print "$BLUE" "------------------------------------------------------------"
        color_print "$BOLD" "📈 汇总统计:"
        echo "  总 EIP 数：     ${idx}"
        printf "  闲置 EIP:      ${RED}%d${RESET}\n" "$idle_count"
        printf "  使用中 EIP:    ${GREEN}%d${RESET}\n" "$binding_count"
        echo "  总带宽：       ${total_bw} Mbps"
        color_print "$BLUE" "------------------------------------------------------------"
    fi
}

main
