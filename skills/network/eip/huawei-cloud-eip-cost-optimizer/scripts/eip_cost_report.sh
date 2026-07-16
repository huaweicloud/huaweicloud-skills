#!/bin/bash
# eip_cost_report.sh - EIP 成本分析报告（HTML / JSON / 文本）
# 基于 hcloud CLI（KooCLI），替代 Python SDK 方式
#
# Usage:
#   bash eip_cost_report.sh [--region cn-north-4] [--format html|json|text] [--output FILE]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# ── 参数解析 ──────────────────────────────────────────────────────
REGION=""
FORMAT="text"
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --region)   REGION="$2"; shift 2 ;;
        --format)   FORMAT="$2"; shift 2 ;;
        --output)   OUTPUT_FILE="$2"; shift 2 ;;
        --help|-h)
            echo "用法: $0 [--region REGION] [--format html|json|text] [--output FILE]"
            echo "  --region   华为云区域 ID（默认从环境变量读取）"
            echo "  --format   输出格式：text（默认）、html、json"
            echo "  --output   输出文件路径（默认输出到 stdout）"
            exit 0 ;;
        *) echo "未知选项: $1" >&2; exit 1 ;;
    esac
done

if [ -n "$REGION" ]; then
    HW_REGION="$REGION"
fi

# 校验 --format
case "$FORMAT" in
    text|html|json) ;;
    *) echo "❌ 不支持的格式: '$FORMAT'（仅支持 text / html / json）" >&2; exit 1 ;;
esac

# ── 工具函数 ──────────────────────────────────────────────────────
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

# ── 成本计算 ──────────────────────────────────────────────────────
# 华为云 EIP 按需计费（按带宽）：
#   - 带宽费：≈ 3 元/Mbps/月 (cn-north-4 参考价)
#   - IP 保有费：≈ 0.02 元/小时（仅未绑定时收取）
# 注：API 不返回 charge_mode，默认按带宽计费模型估算

BANDWIDTH_MONTHLY_RATE=3        # 元/Mbps/月
IP_RETAIN_HOURLY_RATE=0.02     # 元/小时（未绑定 EIP 保有费）

# ── 生成文本报告 ──────────────────────────────────────────────────
generate_text_report() {
    local eips_json="$1"
    local count="$2"
    local idle_count="$3"
    local bound_count="$4"
    local total_bw="$5"
    local total_monthly="$6"
    local total_hourly="$7"

    echo ""
    echo "================================================================"
    echo "📊 EIP 成本分析报告"
    echo "================================================================"
    echo "区域：${HW_REGION}"
    echo "报告时间：$(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "────────────────────────────────────────────────────────────────"
    echo "📈 资源概览"
    echo "────────────────────────────────────────────────────────────────"
    echo "  EIP 总数：        ${count} 个"
    echo "  已绑定：          ${bound_count} 个"
    echo "  未绑定（闲置）：  ${idle_count} 个"
    echo "  总带宽：          ${total_bw} Mbps"
    echo ""
    echo "────────────────────────────────────────────────────────────────"
    echo "💰 成本估算（按带宽计费模型）"
    echo "────────────────────────────────────────────────────────────────"
    echo "  带宽费：          ≈ ¥${total_monthly}/月（${BANDWIDTH_MONTHLY_RATE} 元/Mbps/月 × ${total_bw} Mbps）"

    local ip_retain_monthly
    ip_retain_monthly=$(echo "scale=2; $idle_count * $IP_RETAIN_HOURLY_RATE * 720" | bc 2>/dev/null || echo "0")
    ip_retain_monthly=$(format_cost "$ip_retain_monthly")
    echo "  IP 保有费：       ≈ ¥${ip_retain_monthly}/月（${idle_count} 个未绑定 × ${IP_RETAIN_HOURLY_RATE} 元/小时 × 720 小时）"

    local grand_total
    grand_total=$(echo "scale=2; $total_monthly + $ip_retain_monthly" | bc 2>/dev/null || echo "0")
    grand_total=$(format_cost "$grand_total")
    echo "  ─────────────────"
    echo "  合计：            ≈ ¥${grand_total}/月"
    echo ""
    echo "  每小时成本：      ≈ ¥${total_hourly}/小时"
    echo ""

    echo "────────────────────────────────────────────────────────────────"
    echo "📋 EIP 明细"
    echo "────────────────────────────────────────────────────────────────"
    printf "%-18s %-12s %-10s %-10s %-10s %-10s\n" "IP 地址" "带宽(Mbps)" "状态" "绑定" "月费(¥)" "类型"
    echo "----------------------------------------------------------------"

    while IFS= read -r row; do
        local ip bw_size status port_id monthly_cost eip_type
        ip=$(echo "$row" | jq -r '.public_ip_address // "N/A"')
        bw_size=$(echo "$row" | jq -r '.bandwidth_size // 0')
        status=$(echo "$row" | jq -r '.status // "N/A"')
        port_id=$(echo "$row" | jq -r '.port_id // ""')

        monthly_cost=$(echo "scale=2; $bw_size * $BANDWIDTH_MONTHLY_RATE" | bc 2>/dev/null || echo "0")
        monthly_cost=$(format_cost "$monthly_cost")

        if [ -z "$port_id" ] || [ "$port_id" = "null" ]; then
            eip_type="闲置"
        else
            eip_type="使用中"
        fi

        local bound_str="否"
        [ -n "$port_id" ] && [ "$port_id" != "null" ] && bound_str="是"

        printf "%-18s %-12s %-10s %-10s %-10s %-10s\n" "$ip" "$bw_size" "$status" "$bound_str" "$monthly_cost" "$eip_type"
    done < <(echo "$eips_json" | jq -c '.[]')

    echo "================================================================"
    echo ""
}

# ── 生成 HTML 报告 ────────────────────────────────────────────────
generate_html_report() {
    local eips_json="$1"
    local count="$2"
    local idle_count="$3"
    local bound_count="$4"
    local total_bw="$5"
    local total_monthly="$6"

    local ip_retain_monthly
    ip_retain_monthly=$(echo "scale=2; $idle_count * $IP_RETAIN_HOURLY_RATE * 720" | bc 2>/dev/null || echo "0")
    ip_retain_monthly=$(format_cost "$ip_retain_monthly")

    local grand_total
    grand_total=$(echo "scale=2; $total_monthly + $ip_retain_monthly" | bc 2>/dev/null || echo "0")
    grand_total=$(format_cost "$grand_total")

    cat <<HTML
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>EIP 成本分析报告 - ${HW_REGION}</title>
<style>
body{font-family:Arial,sans-serif;margin:20px;background:#f5f5f5}
.container{max-width:900px;margin:0 auto;background:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1)}
h1{color:#333;border-bottom:2px solid #0071c5;padding-bottom:10px}
h2{color:#0071c5;margin-top:20px}
table{width:100%;border-collapse:collapse;margin:10px 0}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #ddd}
th{background:#0071c5;color:#fff}
tr:hover{background:#f0f7ff}
.idle{color:#e74c3c;font-weight:bold}
.bound{color:#27ae60}
.summary{display:flex;gap:20px;flex-wrap:wrap}
.card{flex:1;min-width:150px;background:#f8f9fa;padding:15px;border-radius:6px;text-align:center}
.card .value{font-size:24px;font-weight:bold;color:#0071c5}
.card .label{font-size:12px;color:#666;margin-top:5px}
.cost{color:#e74c3c;font-size:20px;font-weight:bold}
</style>
</head>
<body>
<div class="container">
<h1>📊 EIP 成本分析报告</h1>
<p>区域：<strong>${HW_REGION}</strong> | 报告时间：<strong>$(date '+%Y-%m-%d %H:%M:%S')</strong></p>

<div class="summary">
<div class="card"><div class="value">${count}</div><div class="label">EIP 总数</div></div>
<div class="card"><div class="value">${bound_count}</div><div class="label">已绑定</div></div>
<div class="card"><div class="value">${idle_count}</div><div class="label">未绑定（闲置）</div></div>
<div class="card"><div class="value">${total_bw} Mbps</div><div class="label">总带宽</div></div>
</div>

<h2>💰 成本估算（按带宽计费模型）</h2>
<p>带宽费：<strong>¥${total_monthly}/月</strong>（${BANDWIDTH_MONTHLY_RATE} 元/Mbps/月 × ${total_bw} Mbps）</p>
<p>IP 保有费：<strong>¥${ip_retain_monthly}/月</strong>（${idle_count} 个未绑定 × ${IP_RETAIN_HOURLY_RATE} 元/小时）</p>
<p class="cost">合计：≈ ¥${grand_total}/月</p>

<h2>📋 EIP 明细</h2>
<table>
<tr><th>IP 地址</th><th>带宽(Mbps)</th><th>状态</th><th>绑定</th><th>月费(¥)</th><th>类型</th></tr>
HTML

    while IFS= read -r row; do
        local ip bw_size status port_id monthly_cost eip_type bound_str css_class
        ip=$(echo "$row" | jq -r '.public_ip_address // "N/A"')
        bw_size=$(echo "$row" | jq -r '.bandwidth_size // 0')
        status=$(echo "$row" | jq -r '.status // "N/A"')
        port_id=$(echo "$row" | jq -r '.port_id // ""')

        monthly_cost=$(echo "scale=2; $bw_size * $BANDWIDTH_MONTHLY_RATE" | bc 2>/dev/null || echo "0")
        monthly_cost=$(format_cost "$monthly_cost")

        if [ -z "$port_id" ] || [ "$port_id" = "null" ]; then
            eip_type="闲置"; bound_str="否"; css_class="idle"
        else
            eip_type="使用中"; bound_str="是"; css_class="bound"
        fi

        echo "<tr><td>${ip}</td><td>${bw_size}</td><td>${status}</td><td>${bound_str}</td><td>${monthly_cost}</td><td class=\"${css_class}\">${eip_type}</td></tr>"
    done < <(echo "$eips_json" | jq -c '.[]')

    cat <<HTML2
</table>
<p style="color:#999;font-size:12px">* 成本估算基于按带宽计费模型（参考 cn-north-4 按需价格），实际费用以账单为准</p>
</div>
</body>
</html>
HTML2
}

# ── 生成 JSON 报告 ────────────────────────────────────────────────
generate_json_report() {
    local eips_json="$1"
    local count="$2"
    local idle_count="$3"
    local bound_count="$4"
    local total_bw="$5"
    local total_monthly="$6"

    local ip_retain_monthly
    ip_retain_monthly=$(echo "scale=2; $idle_count * $IP_RETAIN_HOURLY_RATE * 720" | bc 2>/dev/null || echo "0")
    ip_retain_monthly=$(format_cost "$ip_retain_monthly")

    local grand_total
    grand_total=$(echo "scale=2; $total_monthly + $ip_retain_monthly" | bc 2>/dev/null || echo "0")
    grand_total=$(format_cost "$grand_total")

    local details
    details=$(echo "$eips_json" | jq -c '[ .[] | {
        public_ip: .public_ip_address,
        bandwidth_mbps: .bandwidth_size,
        status: .status,
        bound: (if .port_id then true else false end),
        monthly_cost_cny: (.bandwidth_size * 3),
        type: (if .port_id then "in_use" else "idle" end)
    }]')

    jq -n -c \
        --arg region "$HW_REGION" \
        --arg timestamp "$(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(+[0-9]\{2\}\)\([0-9]\{2\}\)/\1:\2/')" \
        --argjson total "$count" \
        --argjson idle "$idle_count" \
        --argjson bound "$bound_count" \
        --argjson bw "$total_bw" \
        --argjson bw_cost "$total_monthly" \
        --argjson retain_cost "$ip_retain_monthly" \
        --argjson grand "$grand_total" \
        --argjson details "$details" \
        '{
            region: $region,
            timestamp: $timestamp,
            pricing_model: "bandwidth (≈3 CNY/Mbps/month + 0.02 CNY/hr IP retain fee)",
            summary: {
                total_eips: $total,
                idle_eips: $idle,
                bound_eips: $bound,
                total_bandwidth_mbps: $bw,
                bandwidth_cost_monthly_cny: $bw_cost,
                ip_retain_cost_monthly_cny: $retain_cost,
                total_cost_monthly_cny: $grand
            },
            details: $details
        }' | jq .
}

# ── 主逻辑 ────────────────────────────────────────────────────────
main() {
    [[ "$FORMAT" != "json" ]] && color_print "$BLUE" "📊 正在查询区域 ${HW_REGION} 的 EIP 成本数据..."

    local raw_json
    raw_json=$(fetch_eip_list)

    local eips_json
    eips_json=$(echo "$raw_json" | jq -c '.publicips // []')

    local count
    count=$(echo "$eips_json" | jq 'length')

    if [ "$count" -eq 0 ]; then
        if [ "$FORMAT" = "json" ]; then
            local ts
            ts=$(date '+%Y-%m-%dT%H:%M:%S+08:00')
            jq -n \
                --arg region "$REGION" \
                --arg ts "$ts" \
                '{
                    region: $region,
                    timestamp: $ts,
                    pricing_model: "bandwidth: 3 CNY/Mbps/month + IP retain: 0.02 CNY/hour (API charge_mode unavailable)",
                    summary: { total_eips: 0, idle_eips: 0, bound_eips: 0, total_bandwidth_mbps: 0, bandwidth_cost_monthly_cny: 0, ip_retain_cost_monthly_cny: 0, total_cost_monthly_cny: 0 },
                    details: []
                }'
        elif [ "$FORMAT" = "html" ]; then
            cat <<'HTMLEOF'
<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>EIP 成本报告</title>
<style>body{font-family:sans-serif;padding:20px}h1{color:#333}.info{color:#888;padding:20px}</style>
</head><body><h1>EIP 成本报告</h1><p class="info">当前区域无 EIP 资源</p></body></html>
HTMLEOF
        else
            color_print "$YELLOW" "ℹ️  未找到任何 EIP"
        fi
        exit 0
    fi

    # 统计
    local idle_count=0 bound_count=0 total_bw=0
    while IFS= read -r row; do
        local port_id bw_size
        port_id=$(echo "$row" | jq -r '.port_id // ""')
        bw_size=$(echo "$row" | jq -r '.bandwidth_size // 0')

        if [ -z "$port_id" ] || [ "$port_id" = "null" ]; then
            idle_count=$((idle_count + 1))
        else
            bound_count=$((bound_count + 1))
        fi
        total_bw=$((total_bw + bw_size))
    done < <(echo "$eips_json" | jq -c '.[]')

    # 成本计算
    local total_monthly total_hourly
    total_monthly=$(echo "scale=2; $total_bw * $BANDWIDTH_MONTHLY_RATE" | bc 2>/dev/null || echo "0")
    total_monthly=$(format_cost "$total_monthly")
    total_hourly=$(echo "scale=4; $total_bw * $BANDWIDTH_MONTHLY_RATE / 720" | bc 2>/dev/null || echo "0")
    total_hourly=$(format_cost "$total_hourly")

    # 按格式输出
    local report_content
    case "$FORMAT" in
        text) report_content=$(generate_text_report "$eips_json" "$count" "$idle_count" "$bound_count" "$total_bw" "$total_monthly" "$total_hourly") ;;
        html) report_content=$(generate_html_report "$eips_json" "$count" "$idle_count" "$bound_count" "$total_bw" "$total_monthly") ;;
        json) report_content=$(generate_json_report "$eips_json" "$count" "$idle_count" "$bound_count" "$total_bw" "$total_monthly") ;;
    esac

    if [ -n "$OUTPUT_FILE" ]; then
        # 确保输出目录存在
        local output_dir
        output_dir=$(dirname "$OUTPUT_FILE")
        [ -d "$output_dir" ] || mkdir -p "$output_dir"
        echo "$report_content" > "$OUTPUT_FILE"
        color_print "$GREEN" "✅ 报告已写入: ${OUTPUT_FILE}"
    else
        echo "$report_content"
    fi
}

main
