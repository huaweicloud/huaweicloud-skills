#!/bin/bash
# monitor_idle_eips.sh - 闲置 EIP 监控与告警
# 基于 hcloud CLI（KooCLI），替代 Python SDK 方式
#
# Usage:
#   bash monitor_idle_eips.sh [--region cn-north-4] [--idle-days 7] \
#     [--webhook URL] [--email ADDR] [--setup-cron] [--remove-cron]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# ── 参数解析 ──────────────────────────────────────────────────────
REGION=""
MIN_IDLE_DAYS=7
WEBHOOK_URL=""
EMAIL_ADDR=""
SETUP_CRON=false
REMOVE_CRON=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --region)         REGION="$2"; shift 2 ;;
        --idle-days)      MIN_IDLE_DAYS="$2"; shift 2 ;;
        --min-idle-days)  MIN_IDLE_DAYS="$2"; shift 2 ;;    # 向后兼容
        --webhook)        WEBHOOK_URL="$2"; shift 2 ;;
        --email)          EMAIL_ADDR="$2"; shift 2 ;;
        --setup-cron)     SETUP_CRON=true; shift ;;
        --remove-cron)    REMOVE_CRON=true; shift ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo "  --region       华为云区域 ID（默认从环境变量读取）"
            echo "  --idle-days    闲置天数阈值（默认：7）"
            echo "  --webhook URL  Webhook 告警地址"
            echo "  --email ADDR   邮件告警地址"
            echo "  --setup-cron   自动安装 crontab 定时任务"
            echo "  --remove-cron  移除 crontab 定时任务"
            exit 0 ;;
        *) echo "未知选项: $1" >&2; exit 1 ;;
    esac
done

if [ -n "$REGION" ]; then
    HW_REGION="$REGION"
fi

# ── crontab 管理 ──────────────────────────────────────────────────
CRON_MARKER="# EIP_IDLE_MONITOR"

setup_cron() {
    # 检查 crontab 是否可用
    if ! command -v crontab >/dev/null 2>&1; then
        color_print "$YELLOW" "⚠️  crontab 命令不可用，无法设置定时任务"
        color_print "$BLUE" "   替代方案："
        color_print "$BLUE" "     1. 安装 cronie/cron 包后重试"
        color_print "$BLUE" "     2. 使用 systemd timer 替代 crontab"
        color_print "$BLUE" "     3. 使用外部调度器（如 Jenkins/CodeArts）定时执行以下命令："
        local script_path="$(cd "$SCRIPT_DIR" && pwd)/monitor_idle_eips.sh"
        color_print "$BLUE" "        ${script_path} --region ${HW_REGION} --idle-days ${MIN_IDLE_DAYS}"
        return 1
    fi

    local script_path="$(cd "$SCRIPT_DIR" && pwd)/monitor_idle_eips.sh"
    # 每天早上 9 点执行
    local cron_line="0 9 * * * ${script_path} --region ${HW_REGION} --idle-days ${MIN_IDLE_DAYS} ${CRON_MARKER}"

    # 检查是否已存在
    if crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
        color_print "$YELLOW" "⚠️  crontab 中已存在 EIP 闲置监控任务，先移除旧任务..."
        remove_cron
    fi

    # 添加新任务
    (crontab -l 2>/dev/null; echo "$cron_line") | crontab -
    color_print "$GREEN" "✅ 已添加 crontab 定时任务：每天 09:00 执行监控"
    color_print "$BLUE" "   命令：${cron_line}"
}

remove_cron() {
    # 检查 crontab 是否可用
    if ! command -v crontab >/dev/null 2>&1; then
        color_print "$YELLOW" "⚠️  crontab 命令不可用，无法操作定时任务"
        color_print "$BLUE" "   请手动移除调度器中的 EIP 闲置监控任务"
        return 1
    fi

    if ! crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
        color_print "$YELLOW" "⚠️  crontab 中未找到 EIP 闲置监控任务"
        return 0
    fi

    crontab -l 2>/dev/null | grep -vF "$CRON_MARKER" | crontab -
    color_print "$GREEN" "✅ 已移除 crontab 中的 EIP 闲置监控任务"
}

# 如果仅操作 crontab
if [ "$SETUP_CRON" = true ]; then
    setup_cron && exit 0 || exit 0
fi

if [ "$REMOVE_CRON" = true ]; then
    remove_cron && exit 0 || exit 0
fi

# ── 工具函数 ──────────────────────────────────────────────────────
# 计算闲置天数（使用 date 命令，与 analyze 脚本保持一致）
calculate_idle_days() {
    local create_time="$1"
    if [ -z "$create_time" ] || [ "$create_time" = "null" ] || [ "$create_time" = "N/A" ]; then
        echo "-1"
        return
    fi

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

# ── 告警发送 ──────────────────────────────────────────────────────
send_webhook() {
    local payload="$1"
    local url="$2"

    # URL 安全验证: 仅允许 HTTPS + 已知 webhook 域名 (防 SSRF)
    case "$url" in
        https://oapi.dingtalk.com/*|https://qyapi.weixin.qq.com/*|https://hooks.slack.com/*|https://*.api.slack.com/*)
            ;; # 允许的 webhook 域名
        *)
            color_print "$RED" "❌ Webhook URL 不在允许列表中（仅支持钉钉/企微/Slack HTTPS 地址）"
            return 1 ;;
    esac

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST -H "Content-Type: application/json" \
        -d "$payload" "$url" 2>/dev/null) || {
        color_print "$RED" "❌ Webhook 发送失败：网络不可达或 URL 无效"
        return 1
    }

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        color_print "$GREEN" "✅ Webhook 告警已发送 (HTTP ${http_code})"
    elif [ "$http_code" -ge 400 ] && [ "$http_code" -lt 500 ]; then
        color_print "$RED" "❌ Webhook 发送失败：HTTP ${http_code}（URL 无效或认证失败）"
        return 1
    else
        color_print "$RED" "❌ Webhook 发送失败：HTTP ${http_code}（服务端错误）"
        return 1
    fi
}

send_email() {
    local subject="$1"
    local body="$2"
    local addr="$3"

    if command -v sendmail >/dev/null 2>&1; then
        echo -e "Subject: ${subject}\nTo: ${addr}\nContent-Type: text/plain; charset=UTF-8\n\n${body}" | sendmail "$addr"
        color_print "$GREEN" "✅ 邮件告警已发送至 ${addr}"
    elif command -v mail >/dev/null 2>&1; then
        echo "$body" | mail -s "$subject" "$addr"
        color_print "$GREEN" "✅ 邮件告警已发送至 ${addr}"
    else
        color_print "$YELLOW" "⚠️  未找到 sendmail/mail 命令，无法发送邮件告警"
        color_print "$BLUE" "   请安装 mailutils 或配置 SMTP"
        return 1
    fi
}

# ── 主逻辑 ────────────────────────────────────────────────────────
main() {
    color_print "$BLUE" "🔍 正在监控区域 ${HW_REGION} 的闲置 EIP... (阈值：≥${MIN_IDLE_DAYS}天)"

    local raw_json
    raw_json=$(fetch_eip_list)

    local eips_json
    eips_json=$(echo "$raw_json" | jq -c '.publicips // []')

    local all_count
    all_count=$(echo "$eips_json" | jq 'length')

    if [ "$all_count" -eq 0 ]; then
        color_print "$YELLOW" "ℹ️  未找到任何 EIP"
        exit 0
    fi

    # 筛选闲置 EIP（port_id 为空/null 且闲置天数 >= 阈值）
    # 使用 date 命令计算天数（与 analyze 脚本保持一致，消除 UTC 偏移）
    local idle_eips_json='[]'
    local idle_count=0

    while IFS= read -r row; do
        local port_id create_time
        port_id=$(echo "$row" | jq -r '.port_id // ""')
        create_time=$(echo "$row" | jq -r '.create_time // "N/A"')

        # 仅筛选未绑定的
        [ -z "$port_id" ] || [ "$port_id" = "null" ] || continue

        # 计算闲置天数
        local idle_days
        idle_days=$(calculate_idle_days "$create_time")

        # 过滤阈值
        if [ "$idle_days" -ge "$MIN_IDLE_DAYS" ] || [ "$idle_days" -eq -1 ]; then
            local enriched_row
            enriched_row=$(echo "$row" | jq --argjson d "$idle_days" '. + {idle_days_calculated: $d}')
            idle_eips_json=$(echo "$idle_eips_json" | jq --argjson r "$enriched_row" '. + [$r]')
            idle_count=$((idle_count + 1))
        fi
    done < <(echo "$eips_json" | jq -c '.[]')

    # 监控结果
    echo ""
    echo "================================================================"
    echo "📡 EIP 闲置监控报告"
    echo "================================================================"
    echo "区域：${HW_REGION} | 阈值：≥${MIN_IDLE_DAYS}天 | 时间：$(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    if [ "$idle_count" -eq 0 ]; then
        color_print "$GREEN" "✅ 未发现闲置超过 ${MIN_IDLE_DAYS} 天的 EIP"
        echo "================================================================"
        exit 0
    fi

    color_print "$RED" "⚠️  发现 ${idle_count} 个闲置超过 ${MIN_IDLE_DAYS} 天的 EIP！"
    echo ""

    # 列表
    printf "%-18s %-12s %-10s %-20s %s\n" "IP 地址" "带宽(Mbps)" "闲置天数" "创建时间" "EIP ID"
    echo "----------------------------------------------------------------"

    while IFS= read -r row; do
        local ip bw_size idle_days create_time eip_id
        ip=$(echo "$row" | jq -r '.public_ip_address // "N/A"')
        bw_size=$(echo "$row" | jq -r '.bandwidth_size // 0')
        idle_days=$(echo "$row" | jq -r '.idle_days_calculated // 0')
        create_time=$(echo "$row" | jq -r '.create_time // "N/A"')
        eip_id=$(echo "$row" | jq -r '.id // "N/A"')

        local create_time_short="${create_time:0:19}"
        local idle_days_str="${idle_days} 天"
        [ "$idle_days" -eq -1 ] && idle_days_str="未知"

        printf "%-18s %-12s %-10s %-20s %s\n" "$ip" "$bw_size" "$idle_days_str" "$create_time_short" "${eip_id:0:20}"
    done < <(echo "$idle_eips_json" | jq -c '.[]')

    echo "================================================================"
    echo ""

    # 发送告警
    if [ -n "$WEBHOOK_URL" ]; then
        color_print "$BLUE" "🔔 正在发送 Webhook 告警..."

        local alert_payload
        alert_payload=$(jq -n -c \
            --arg region "$HW_REGION" \
            --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            --argjson idle "$idle_count" \
            --argjson threshold "$MIN_IDLE_DAYS" \
            '{
                alert_type: "idle_eip",
                region: $region,
                timestamp: $timestamp,
                idle_count: $idle,
                threshold_days: $threshold,
                severity: (if $idle > 5 then "high" elif $idle > 0 then "medium" else "low" end),
                message: ("发现 " + ($idle | tostring) + " 个闲置超过 " + ($threshold | tostring) + " 天的 EIP")
            }')

        # 添加 EIP 详情
        local idle_details
        idle_details=$(echo "$idle_eips_json" | jq -c '[ .[] | {
            eip_id: .id,
            public_ip: .public_ip_address,
            idle_days: .idle_days_calculated
        }]')

        alert_payload=$(echo "$alert_payload" | jq --argjson details "$idle_details" '. + {idle_eips: $details}')

        send_webhook "$alert_payload" "$WEBHOOK_URL" || true
    fi

    if [ -n "$EMAIL_ADDR" ]; then
        color_print "$BLUE" "🔔 正在发送邮件告警..."

        local subject="[EIP 告警] ${HW_REGION} 发现 ${idle_count} 个闲置 EIP"
        local body="EIP 闲置监控告警

区域：${HW_REGION}
时间：$(date '+%Y-%m-%d %H:%M:%S')
闲置阈值：≥${MIN_IDLE_DAYS}天
发现闲置 EIP 数量：${idle_count}

闲置 EIP 列表："

        while IFS= read -r row; do
            local ip idle_days eip_id
            ip=$(echo "$row" | jq -r '.public_ip_address // "N/A"')
            idle_days=$(echo "$row" | jq -r '.idle_days_calculated // 0')
            eip_id=$(echo "$row" | jq -r '.id // "N/A"')
            body="${body}
  - ${ip} (ID: ${eip_id:0:20}..., 闲置 ${idle_days} 天)"
        done < <(echo "$idle_eips_json" | jq -c '.[]')

        body="${body}

建议操作：
1. 确认闲置 EIP 的业务用途
2. 对确认不用的 EIP，手动在控制台释放
3. 对可能需要的 EIP，可调整为最低带宽

此邮件由 EIP 闲置监控脚本自动发送。"

        send_email "$subject" "$body" "$EMAIL_ADDR" || true
    fi

    # 如果没有配置告警渠道，给出提示
    if [ -z "$WEBHOOK_URL" ] && [ -z "$EMAIL_ADDR" ]; then
        color_print "$YELLOW" "💡 提示：使用 --webhook URL 或 --email ADDR 配置告警通知"
        color_print "$BLUE" "   使用 --setup-cron 可自动安装定时监控任务"
    fi
}

main
