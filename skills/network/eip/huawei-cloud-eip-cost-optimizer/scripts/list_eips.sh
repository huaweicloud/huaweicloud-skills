#!/bin/bash
# list_eips.sh - 列出所有 EIP 及其详细信息
# 基于 hcloud CLI（KooCLI），替代 Python SDK 方式
#
# Usage:
#   bash list_eips.sh --region cn-north-4
#   bash list_eips.sh --region cn-north-4,cn-east-3,cn-south-1   # 多区域
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
            echo "用法: $0 [--region REGION[,REGION...]] [--status STATUS] [--idle-only] [--summary] [--format text|json] [--publicip-id EIP_ID]"
            echo "  --region       区域（可逗号分隔多个，默认：HW_REGION_NAME 或 cn-north-4）"
            echo "  --status       状态过滤（BINDING, DOWN, ELB 等）"
            echo "  --idle-only    仅显示闲置 EIP"
            echo "  --summary      仅输出统计数据（CSV：总数,闲置数,总带宽）"
            echo "  --format       输出格式：text（默认）、json"
            echo "  --publicip-id  按指定 EIP ID 查询单个 EIP 详情（仅单区域有效）"
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
# 支持逗号分隔多区域: --region cn-north-4,cn-east-3
if [ -n "$REGION" ]; then
    HW_REGION="$REGION"
fi
IFS=',' read -ra REGIONS <<< "$HW_REGION"
# 去重保留顺序
declare -a UNIQ_REGIONS=()
declare -A SEEN_REGION=()
for r in "${REGIONS[@]}"; do
    r="${r// /}"  # 去除可能的空格
    [ -z "$r" ] && continue
    if [ -z "${SEEN_REGION[$r]:-}" ]; then
        SEEN_REGION[$r]=1
        UNIQ_REGIONS+=("$r")
    fi
done

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

# ── 查询 EIP 列表（按指定区域）────────────────────────────────────
# 参数: $1 = 区域；$2 = 临时覆盖变量名(可选)
fetch_eip_list() {
    local target_region="$1"
    local raw_json
    # 用子shell覆盖 HW_REGION，避免污染全局
    raw_json=$(HW_REGION="$target_region" run_hcloud EIP ListPublicips/v2 --limit=1000 2>/dev/null) || {
        color_print "$RED" "❌ 查询 EIP 列表失败（区域 ${target_region} 可能无效或凭证错误）"
        return 1
    }

    if [ -z "$raw_json" ] || ! echo "$raw_json" | jq -e '.publicips' >/dev/null 2>&1; then
        color_print "$RED" "❌ API 返回异常，请检查区域 ${target_region} 是否有效"
        return 1
    fi

    echo "$raw_json"
}

# ── 单个区域列表查询 + 输出 ──────────────────────────────────────
# 参数: $1 = 区域
# 输出(通过全局变量汇总): 累加结果到 stdout, 返回 0
query_region() {
    local region="$1"
    local raw_json
    raw_json=$(fetch_eip_list "$region") || return 1

    local eips_json
    eips_json=$(echo "$raw_json" | jq -c '.publicips // []')

    local total_count
    total_count=$(echo "$eips_json" | jq 'length')

    if [ "$total_count" -eq 0 ]; then
        if [ "$SUMMARY" = true ]; then
            # summary 由外部汇总, 此处不输出单区域空行
            return 0
        elif [ "$FORMAT" = "json" ]; then
            # JSON 模式: 输出空区域对象供外部合并
            local ts_empty
            ts_empty=$(date '+%Y-%m-%dT%H:%M:%S+08:00')
            jq -n -c \
                --arg region "$region" \
                --arg timestamp "$ts_empty" \
                '{
                    region: $region,
                    timestamp: $timestamp,
                    summary: {total_eips: 0, idle_eips: 0, bound_eips: 0, total_bandwidth_mbps: 0},
                    details: []
                }'
            return 0
        else
            color_print "$YELLOW" "⚠️  区域 ${region} 没有找到 EIP 资源"
            return 0
        fi
    fi

    # ── Summary 模式: 输出 "区域,total,idle,bw" 供外部汇总 ─────
    # 统计口径与详细模式完全一致(应用 status 过滤 + idle-only 过滤)
    if [ "$SUMMARY" = true ]; then
        local status_jq idle_jq
        # status 过滤
        if [ -n "$STATUS_FILTER" ]; then
            status_jq="select(.status == \"$STATUS_FILTER\") |"
        else
            status_jq=""
        fi
        # idle-only 过滤: 仅保留闲置EIP
        if [ "$IDLE_ONLY" = true ]; then
            idle_jq="select(.status == \"DOWN\" or .status == \"ELB\" or (.port_id == \"\" or .port_id == null)) |"
        else
            idle_jq=""
        fi
        local filtered
        filtered=$(echo "$eips_json" | jq -c "[.[] | ${status_jq} ${idle_jq} .]")
        local f_total f_idle f_bw
        f_total=$(echo "$filtered" | jq 'length')
        f_idle=$(echo "$filtered" | jq '[.[] | select(.status == "DOWN" or .status == "ELB" or (.port_id == "" or .port_id == null))] | length')
        f_bw=$(echo "$filtered" | jq '[.[].bandwidth_size // 0] | add // 0')
        echo "${region},${f_total},${f_idle},${f_bw}"
        return 0
    fi

    # ── 详细列表模式 ──────────────────────────────────────────────
    local eip_results='[]'

    if [ "$FORMAT" = "text" ]; then
        color_print "$BLUE" "============================================================"
        color_print "$BLUE" "  EIP 列表查询（区域：${region}）"
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
        result_row=$(echo "$row" | jq -c --argjson idle_bool "$( [ "$is_idle" = true ] && echo true || echo false )" '. + {idle: $idle_bool, region: $region}' --arg region "$region")
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

    # JSON 模式: 输出单区域 JSON 对象到临时文件由外部合并
    if [ "$FORMAT" = "json" ]; then
        local ts
        ts=$(date '+%Y-%m-%dT%H:%M:%S+08:00')
        jq -n -c \
            --arg region "$region" \
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
            }'
    else
        color_print "$BLUE" "------------------------------------------------------------"
        color_print "$BOLD" "📈 区域 ${region} 汇总统计:"
        echo "  总 EIP 数：     ${idx}"
        printf "  闲置 EIP:      ${RED}%d${RESET}\n" "$idle_count"
        printf "  使用中 EIP:    ${GREEN}%d${RESET}\n" "$binding_count"
        echo "  总带宽：       ${total_bw} Mbps"
        color_print "$BLUE" "------------------------------------------------------------"
        echo ""
    fi
    return 0
}

# ── 主逻辑 ────────────────────────────────────────────────────────
main() {
    # ── 按 EIP ID 查询单个 EIP（仅支持单区域）────────────────────
    if [ -n "$PUBLICIP_ID" ]; then
        if [ "${#UNIQ_REGIONS[@]}" -gt 1 ]; then
            color_print "$YELLOW" "⚠️  --publicip-id 仅支持单区域查询，将使用第一个区域 ${UNIQ_REGIONS[0]}"
        fi
        local raw_json
        raw_json=$(HW_REGION="${UNIQ_REGIONS[0]}" run_hcloud EIP ShowPublicip/v2 --publicip_id="$PUBLICIP_ID" 2>/dev/null) || {
            color_print "$RED" "❌ 查询 EIP ${PUBLICIP_ID} 失败（ID 无效或凭证错误）"
            exit 1
        }
        if [ -z "$raw_json" ] || ! echo "$raw_json" | jq -e '.publicip' >/dev/null 2>&1; then
            color_print "$RED" "❌ 未找到 EIP: ${PUBLICIP_ID}"
            exit 1
        fi
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
            color_print "$BLUE" "  EIP 详情（区域：${UNIQ_REGIONS[0]}）"
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

    # ── 多区域/单区域列表查询 ────────────────────────────────────
    local multi="${#UNIQ_REGIONS[@]}"

    if [ "$SUMMARY" = true ]; then
        # Summary 模式：逐区域汇总，输出 CSV "region,total,idle,bw"
        # 保持向后兼容：单区域输出 "total,idle,bw"（不带头区域）
        if [ "$multi" -le 1 ]; then
            local sline
            sline=$(query_region "${UNIQ_REGIONS[0]}") || exit 1
            # 单区域去掉首字段
            echo "$sline" | awk -F',' '{print $2","$3","$4}'
        else
            local grand_total=0 grand_idle=0 grand_bw=0
            for region in "${UNIQ_REGIONS[@]}"; do
                local sline
                sline=$(query_region "$region") || continue
                IFS=',' read -r _ t i b <<< "$sline"
                grand_total=$((grand_total + t))
                grand_idle=$((grand_idle + i))
                grand_bw=$((grand_bw + b))
            done
            echo "${grand_total},${grand_idle},${grand_bw}"
        fi
        exit 0
    fi

    if [ "$FORMAT" = "json" ]; then
        # JSON 模式：单区域输出对象（保持向后兼容），多区域输出数组
        local combined='[]'
        for region in "${UNIQ_REGIONS[@]}"; do
            local rj
            rj=$(query_region "$region") || continue
            combined=$(printf '%s' "$combined" | jq -c --argjson r "$rj" '. + [$r]')
        done
        if [ "${#UNIQ_REGIONS[@]}" -le 1 ]; then
            # 单区域：输出对象（向后兼容原行为）
            echo "$combined" | jq '.[0]'
        else
            # 多区域：输出数组
            echo "$combined" | jq .
        fi
        exit 0
    fi

    # text 多区域/单区域
    local region_has_data=false
    for region in "${UNIQ_REGIONS[@]}"; do
        query_region "$region" && region_has_data=true || true
    done
    if [ "$region_has_data" = false ]; then
        color_print "$YELLOW" "⚠️  所有区域均未找到 EIP 资源"
    fi
}

# 退出时自动记录审计日志（覆盖 main 内所有 exit 分支）
audit_on_exit() {
    local rc=$?
    if [ "$rc" -eq 0 ]; then
        log_audit "list" "EIP list/query for region ${HW_REGION}"
    else
        log_audit "list" "EIP list/query FAILED for region ${HW_REGION}"
    fi
    exit "$rc"
}
trap audit_on_exit EXIT
main
