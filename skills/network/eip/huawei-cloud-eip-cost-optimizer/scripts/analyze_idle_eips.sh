#!/bin/bash
# analyze_idle_eips.sh - 查找闲置 EIP 并生成分析报告（仅分析，不执行释放操作）
# 基于 hcloud CLI（KooCLI），替代 Python SDK 方式
#
# Usage:
#   bash analyze_idle_eips.sh [--region cn-north-4] [--idle-days 7] [--json]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# ── 参数解析 ──────────────────────────────────────────────────────
REGION=""
MIN_IDLE_DAYS=0
JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --region)         REGION="$2"; shift 2 ;;
        --idle-days)      MIN_IDLE_DAYS="$2"; shift 2 ;;    # 统一参数名
        --min-idle-days)  MIN_IDLE_DAYS="$2"; shift 2 ;;    # 向后兼容
        --json)           JSON_OUTPUT=true; shift ;;
        --help|-h)
            echo "用法: $0 [--region REGION] [--idle-days N] [--min-idle-days N] [--json]"
            echo "  --region       华为云区域 ID（默认从环境变量读取）"
            echo "  --idle-days    最小闲置天数阈值（默认：0，即所有未绑定 EIP）"
            echo "  --min-idle-days  --idle-days 的旧名（向后兼容）"
            echo "  --json         输出 JSON 格式报告"
            exit 0 ;;
        *) echo "未知选项: $1" >&2; exit 1 ;;
    esac
done

if [ -n "$REGION" ]; then
    HW_REGION="$REGION"
fi

# ── 工具函数 ──────────────────────────────────────────────────────
# 计算闲置天数（从创建时间到现在），使用 date 命令确保时区一致
calculate_idle_days() {
    local create_time="$1"
    if [ -z "$create_time" ] || [ "$create_time" = "null" ] || [ "$create_time" = "N/A" ]; then
        echo "-1"
        return
    fi

    # 将 ISO 时间转为 epoch（兼容 GNU date 和 BSD date）
    local create_epoch
    create_epoch=$(date -d "${create_time}" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${create_time:0:19}" +%s 2>/dev/null)

    if [ -z "$create_epoch" ]; then
        echo "-1"
        return
    fi

    local now_epoch
    now_epoch=$(date +%s)

    local diff_days=$(( (now_epoch - create_epoch) / 86400 ))
    echo "$diff_days"
}

# bc 计算结果添加前导零 (e.g. ".02" -> "0.02")
format_cost() {
    local val="$1"
    if [[ "$val" == .* ]]; then
        echo "0${val}"
    else
        echo "$val"
    fi
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

# ── 打印 EIP 表格 ────────────────────────────────────────────────
print_eip_table() {
    local eips_json="$1"
    local title="$2"
    local threshold="$3"

    echo ""
    echo "========================================================================================================================"
    echo "${title} (区域：${HW_REGION}, 闲置阈值：≥${threshold}天)"
    echo "========================================================================================================================"
    printf "%-40s %-16s %-20s %-10s %-12s %-20s %s\n" "EIP ID" "IP 地址" "带宽 ID" "状态" "端口绑定" "创建时间" "闲置天数"
    echo "------------------------------------------------------------------------------------------------------------------------"

    local idle_in_table=0
    while IFS= read -r row; do
        local eip_id ip bw_id status port_id create_time
        eip_id=$(echo "$row" | jq -r '.id // "N/A"')
        ip=$(echo "$row" | jq -r '.public_ip_address // "N/A"')
        bw_id=$(echo "$row" | jq -r '.bandwidth_id // "N/A"')
        status=$(echo "$row" | jq -r '.status // "N/A"')
        port_id=$(echo "$row" | jq -r '.port_id // ""')
        create_time=$(echo "$row" | jq -r '.create_time // "N/A"')

        # 截断长字段
        eip_id_short="${eip_id:0:36}"
        bw_id_short="${bw_id:0:16}"
        create_time_short="${create_time:0:19}"

        # 闲置判断
        local is_idle=false
        if [ -z "$port_id" ] || [ "$port_id" = "null" ]; then
            is_idle=true
        fi

        local port_status="已绑定"
        local marker=""
        if [ "$is_idle" = true ]; then
            port_status="未绑定"
            marker=" ⚠️ 闲置"
            idle_in_table=$((idle_in_table + 1))
        else
            port_status="已绑定 (${port_id:0:8}...)"
        fi

        # 闲置天数
        local idle_days=0 idle_days_str="0 天"
        if [ "$is_idle" = true ]; then
            idle_days=$(calculate_idle_days "$create_time")
            if [ "$idle_days" -ge 0 ]; then
                idle_days_str="${idle_days} 天"
            else
                idle_days_str="未知"
            fi
        fi

        printf "%-40s %-16s %-20s %-10s %-12s %-20s %s%s\n" \
            "$eip_id_short" "$ip" "$bw_id_short" "$status" "$port_status" "$create_time_short" "$idle_days_str" "$marker"
    done < <(echo "$eips_json" | jq -c '.[]')

    echo "------------------------------------------------------------------------------------------------------------------------"
    local total_in_table
    total_in_table=$(echo "$eips_json" | jq 'length')
    echo "总计：${total_in_table} 个 EIP, 闲置：${idle_in_table} 个 (阈值：≥${threshold}天)"
    echo "========================================================================================================================"
    echo ""
}

# ── 生成分析报告 ──────────────────────────────────────────────────
generate_report() {
    local all_count="$1"
    local idle_count="$2"
    local idle_eips_json="$3"

    echo ""
    echo "========================================================================================================================"
    echo "📊 闲置 EIP 分析报告 (闲置阈值：≥${MIN_IDLE_DAYS}天)"
    echo "========================================================================================================================"

    # 成本估算 - 按带宽计费: 约 3 元/Mbps/月 (华为云按需按带宽)
    local estimated_monthly_cost
    estimated_monthly_cost=$(echo "scale=2; $idle_count * 3" | bc 2>/dev/null || echo "0")
    estimated_monthly_cost=$(format_cost "$estimated_monthly_cost")

    # 每小时成本
    local estimated_hourly_cost
    estimated_hourly_cost=$(echo "scale=4; $idle_count * 3 / 720" | bc 2>/dev/null || echo "0")
    estimated_hourly_cost=$(format_cost "$estimated_hourly_cost")

    echo ""
    echo "📈 资源概览:"
    echo "  - EIP 总数：${all_count} 个"
    echo "  - 闲置 EIP 数量：${idle_count} 个"

    if [ "$all_count" -gt 0 ]; then
        local idle_rate
        idle_rate=$(echo "scale=1; $idle_count * 100 / $all_count" | bc 2>/dev/null || echo "0")
        echo "  - 闲置率：${idle_rate}%"
    else
        echo "  - 闲置率：N/A"
    fi

    echo ""
    echo "💰 成本估算（按带宽计费，参考 cn-north-4 按需价格 ≈ 3元/Mbps/月）:"
    echo "  - 当前每小时成本：约 ¥${estimated_hourly_cost}/小时"
    echo "  - 当前每月成本：约 ¥${estimated_monthly_cost}/月"
    echo "  - 潜在节省：100%（如释放所有闲置 EIP）"

    echo ""
    echo "⚠️  风险提示:"
    echo "  - EIP 释放是不可逆操作，IP 地址将被回收且无法恢复"
    echo "  - 建议先确认闲置 EIP 是否用于备用、灾备或临时业务"
    echo "  - 释放前请通知相关业务负责人"

    echo ""
    echo "💡 优化建议:"
    if [ "$idle_count" -eq 0 ]; then
        echo "  ✅ 所有 EIP 都在使用中，无需优化"
    else
        echo "  1. 【立即行动】确认闲置 EIP 的业务用途，联系负责人核实"
        echo "  2. 【降低成本】对确认不用的 EIP，手动在控制台释放"
        echo "  3. 【保留备用】对可能需要但暂时闲置的 EIP，可调整为最低带宽（1 Mbps）"
        echo "  4. 【定期审计】建议每周运行此脚本，持续监控闲置资源"
        echo "  5. 【标签管理】为 EIP 添加用途标签，便于后续识别和管理"
    fi

    # 详细清单
    if [ "$idle_count" -gt 0 ]; then
        echo ""
        echo "📋 闲置 EIP 详细清单:"
        local i=0
        while IFS= read -r row; do
            i=$((i + 1))
            local eip_id ip create_time idle_days idle_days_str
            eip_id=$(echo "$row" | jq -r '.id // "N/A"')
            ip=$(echo "$row" | jq -r '.public_ip_address // "N/A"')
            create_time=$(echo "$row" | jq -r '.create_time // "N/A"')
            create_time_short="${create_time:0:19}"

            idle_days=$(calculate_idle_days "$create_time")
            if [ "$idle_days" -ge 0 ]; then
                idle_days_str="${idle_days} 天"
            else
                idle_days_str="未知"
            fi

            echo ""
            echo "  [${i}] EIP: ${ip}"
            echo "      ID: ${eip_id}"
            echo "      创建时间：${create_time_short}"
            echo "      闲置时长：${idle_days_str}"
            if [ "$idle_days" -gt 30 ]; then
                echo "      建议操作：立即释放"
            else
                echo "      建议操作：确认用途后决定"
            fi
        done < <(echo "$idle_eips_json" | jq -c '.[]')
    fi

    echo ""
    echo "========================================================================================================================"
    echo "📝 报告生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================================================================================================"
    echo ""
}

# ── 主逻辑 ────────────────────────────────────────────────────────
main() {
    [[ "$JSON_OUTPUT" != "true" ]] && color_print "$BLUE" "🔍 正在查询区域 ${HW_REGION} 的 EIP... (闲置阈值：≥${MIN_IDLE_DAYS}天)"

    local raw_json
    raw_json=$(fetch_eip_list)

    local eips_json
    eips_json=$(echo "$raw_json" | jq -c '.publicips // []')

    local all_count
    all_count=$(echo "$eips_json" | jq 'length')

    if [ "$all_count" -eq 0 ]; then
        if [ "$JSON_OUTPUT" = "true" ]; then
            local ts
            ts=$(date '+%Y-%m-%dT%H:%M:%S+08:00')
            jq -n \
                --arg region "$REGION" \
                --arg ts "$ts" \
                '{
                    region: $region,
                    timestamp: $ts,
                    summary: { total_eips: 0, idle_eips: 0, idle_rate: "0.0%", estimated_monthly_cost_cny: 0, pricing_model: "bandwidth: 3 CNY/Mbps/month + IP retain: 0.02 CNY/hour (API charge_mode unavailable)" },
                    idle_eip_details: [],
                    recommendations: ["当前区域无 EIP 资源"]
                }'
        else
            color_print "$YELLOW" "ℹ️  未找到任何 EIP"
        fi
        exit 0
    fi

    # 打印所有 EIP 表格
    [[ "$JSON_OUTPUT" != "true" ]] && print_eip_table "$eips_json" "所有 EIP" "$MIN_IDLE_DAYS"

    # 筛选闲置 EIP（port_id 为空/null 且闲置天数 >= 阈值）
    # 使用 date 命令计算天数（保持时区一致）
    local idle_eips_json='[]'
    local idle_count=0

    while IFS= read -r row; do
        local port_id create_time is_idle
        port_id=$(echo "$row" | jq -r '.port_id // ""')
        create_time=$(echo "$row" | jq -r '.create_time // "N/A"')

        # 仅筛选未绑定的
        [ -z "$port_id" ] || [ "$port_id" = "null" ] || continue

        # 计算闲置天数
        local idle_days
        idle_days=$(calculate_idle_days "$create_time")

        # 过滤阈值
        if [ "$idle_days" -ge "$MIN_IDLE_DAYS" ] || [ "$idle_days" -eq -1 ]; then
            # 添加 idle_days_calculated 字段
            local enriched_row
            enriched_row=$(echo "$row" | jq --argjson d "$idle_days" '. + {idle_days_calculated: $d}')
            idle_eips_json=$(echo "$idle_eips_json" | jq --argjson r "$enriched_row" '. + [$r]')
            idle_count=$((idle_count + 1))
        fi
    done < <(echo "$eips_json" | jq -c '.[]')

    if [ "$idle_count" -eq 0 ]; then
        color_print "$GREEN" "✅ 未发现闲置超过 ${MIN_IDLE_DAYS} 天的 EIP，所有 EIP 都在使用中或闲置时间不足"
        exit 0
    fi

    # 打印闲置 EIP 表格
    [[ "$JSON_OUTPUT" != "true" ]] && print_eip_table "$idle_eips_json" "⚠️  闲置 EIP 列表" "$MIN_IDLE_DAYS"

    # 生成分析报告（仅非 JSON 模式输出文本）
    [[ "$JSON_OUTPUT" != "true" ]] && generate_report "$all_count" "$idle_count" "$idle_eips_json"

    # JSON 格式报告（可选）
    if [ "$JSON_OUTPUT" = true ]; then
        local idle_rate
        if [ "$all_count" -gt 0 ]; then
            idle_rate=$(echo "scale=1; $idle_count * 100 / $all_count" | bc 2>/dev/null || echo "0")
        else
            idle_rate=0
        fi
        local estimated_monthly_cost
        estimated_monthly_cost=$(echo "scale=2; $idle_count * 3" | bc 2>/dev/null || echo "0")

        local report_json
        report_json=$(jq -n -c \
            --arg region "$HW_REGION" \
            --arg timestamp "$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(+[0-9]\{2\}\)\([0-9]\{2\}\)/\1:\2/')" \
            --argjson total "$all_count" \
            --argjson idle "$idle_count" \
            --argjson rate "$idle_rate" \
            --argjson cost "$estimated_monthly_cost" \
            '{
                region: $region,
                timestamp: $timestamp,
                summary: {
                    total_eips: $total,
                    idle_eips: $idle,
                    idle_rate: ($rate | tostring + "%"),
                    estimated_monthly_cost_cny: $cost,
                    pricing_model: "bandwidth (≈3 CNY/Mbps/month)"
                }
            }')

        # 添加闲置 EIP 详情
        local idle_details
        idle_details=$(echo "$idle_eips_json" | jq -c '[ .[] | {
            eip_id: .id,
            public_ip: .public_ip_address,
            bandwidth_id: .bandwidth_id,
            create_time: .create_time,
            idle_days: .idle_days_calculated
        }]')

        report_json=$(echo "$report_json" | jq --argjson details "$idle_details" '. + {idle_eip_details: $details}')

        # 添加建议
        report_json=$(echo "$report_json" | jq '. + {recommendations: [
            "确认闲置 EIP 的业务用途，联系负责人核实",
            "对确认不用的 EIP，手动在控制台释放",
            "对可能需要但暂时闲置的 EIP，可调整为最低带宽（1 Mbps）",
            "定期审计，建议每周运行此脚本",
            "为 EIP 添加用途标签，便于后续识别和管理"
        ]}')

        echo "$report_json" | jq .
    fi
}

main
