#!/bin/bash
#=============================================================
# gost 端口转发安装与配置脚本 (Linux)
# 在代理服务器上执行，安装 gost 并配置端口转发规则。
# 主要用途: 将源端 Windows 主机的 WinRM 端口 (5985) 通过代理映射。
#
# 增强能力:
#   - 端口冲突检测: 启动前扫描所有 listen_port 是否被占用
#   - keepalive 保活: TCP keepalive 参数化配置
#   - 宕机自动恢复: systemd Restart=always + 独立健康检查脚本
#   - 高并发支持: LimitNOFILE=65535, TasksMax=infinity
#
# gost 项目: https://github.com/go-gost/gost
#
# 用法:
#   bash proxy_setup_gost.sh [--config /path/to/config.yaml]
#=============================================================

set -euo pipefail

# ── 默认参数 ──────────────────────────────────────────────
GOST_VERSION="${GOST_VERSION:-3.2.6}"
GOST_ARCH="${GOST_ARCH:-$(uname -m)}"
GOST_INSTALL_DIR="${GOST_INSTALL_DIR:-/usr/local/bin}"
GOST_CONFIG_DIR="${GOST_CONFIG_DIR:-/etc/gost}"
GOST_CONFIG_FILE="${GOST_CONFIG_FILE:-/etc/gost/gost.yaml}"
GOST_LOG_FILE="${GOST_LOG_FILE:-/var/log/proxyopt/gost_setup.log}"
GOST_SERVICE_FILE="/etc/systemd/system/gost.service"
GOST_HEALTHCHECK_SCRIPT="${GOST_HEALTHCHECK_SCRIPT:-/usr/local/bin/gost_healthcheck.sh}"
LOG_DIR="${LOG_DIR:-/var/log/proxyopt}"

# keepalive 默认值
KA_ENABLED="${KA_ENABLED:-true}"
KA_IDLE="${KA_IDLE:-15s}"
KA_INTERVAL="${KA_INTERVAL:-5s}"
KA_COUNT="${KA_COUNT:-3}"

# autolink 默认值
AL_ENABLED="${AL_ENABLED:-true}"
AL_DELAY="${AL_DELAY:-5s}"

# 宕机恢复默认值
RESTART_POLICY="${RESTART_POLICY:-always}"
RESTART_SEC="${RESTART_SEC:-5}"
LIMIT_NOFILE="${LIMIT_NOFILE:-65535}"
TASKS_MAX="${TASKS_MAX:-infinity}"
HC_ENABLED="${HC_ENABLED:-true}"
HC_INTERVAL="${HC_INTERVAL:-30}"
HC_MAX_FAILURES="${HC_MAX_FAILURES:-3}"
HC_TIMEOUT="${HC_TIMEOUT:-5}"

# ── 日志函数 ──────────────────────────────────────────────
mkdir -p "$LOG_DIR" "$GOST_CONFIG_DIR"

log() {
    local level="$1"; shift
    local msg="$*"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$ts [$level] $msg" | tee -a "$GOST_LOG_FILE"
}

log_info()    { log "INFO"    "$@"; }
log_warn()    { log "WARN"    "$@"; }
log_error()   { log "ERROR"   "$@"; }
log_success() { log "SUCCESS" "$@"; }

# ── 解析参数 ──────────────────────────────────────────────
CONFIG_PATH=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --help)
            echo "Usage: bash proxy_setup_gost.sh [--config config.yaml]"
            exit 0
            ;;
        *)
            log_warn "未知参数: $1"
            shift
            ;;
    esac
done

# ── 架构映射 ──────────────────────────────────────────────
case "$GOST_ARCH" in
    x86_64|amd64) GOST_ARCH="amd64" ;;
    aarch64|arm64) GOST_ARCH="arm64" ;;
    *) log_warn "未知架构: $GOST_ARCH，默认使用 amd64"; GOST_ARCH="amd64" ;;
esac

# ── 从 YAML 读取 gost 相关参数 ────────────────────────────
load_config_params() {
    if [[ -z "$CONFIG_PATH" || ! -f "$CONFIG_PATH" ]]; then
        log_error "配置文件未指定或不存在: $CONFIG_PATH"
        exit 1
    fi

    if ! command -v python3 &>/dev/null; then
        log_error "需要 python3 来解析配置文件"
        exit 1
    fi

    # 安全：禁止 eval 执行 YAML 派生内容（防注入）；改为 while read 逐行解析
    while IFS='=' read -r _k _v; do
        [ -n "$_k" ] && export "$_k=$_v"
    done < <(python3 -c "
import yaml
with open('$CONFIG_PATH') as f:
    c = yaml.safe_load(f) or {}
g = c.get('gost', {})
ka = g.get('keepalive', {})
al = g.get('autolink', {})
rc = g.get('recovery', {})
hc = rc.get('healthcheck', {})
print(f'GOST_VERSION={g.get("version", "$GOST_VERSION")}')
print(f'KA_ENABLED={ka.get("enabled", True)}')
print(f'KA_IDLE={ka.get("idle", "$KA_IDLE")}')
print(f'KA_INTERVAL={ka.get("interval", "$KA_INTERVAL")}')
print(f'KA_COUNT={ka.get("count", $KA_COUNT)}')
print(f'AL_ENABLED={al.get("enabled", True)}')
print(f'AL_DELAY={al.get("delay", "$AL_DELAY")}')
print(f'RESTART_POLICY={rc.get("restart_policy", "$RESTART_POLICY")}')
print(f'RESTART_SEC={rc.get("restart_sec", $RESTART_SEC)}')
print(f'LIMIT_NOFILE={rc.get("limit_nofile", $LIMIT_NOFILE)}')
print(f'TASKS_MAX={rc.get("tasks_max", "$TASKS_MAX")}')
print(f'HC_ENABLED={hc.get("enabled", True)}')
print(f'HC_INTERVAL={hc.get("interval_sec", $HC_INTERVAL)}')
print(f'HC_MAX_FAILURES={hc.get("max_failures", $HC_MAX_FAILURES)}')
print(f'HC_TIMEOUT={hc.get("timeout_sec", $HC_TIMEOUT)}')
" 2>/dev/null)

    log_info "gost 参数加载完成:"
    log_info "  keepalive: enabled=$KA_ENABLED, idle=$KA_IDLE, interval=$KA_INTERVAL, count=$KA_COUNT"
    log_info "  autolink:  enabled=$AL_ENABLED, delay=$AL_DELAY"
    log_info "  recovery:  restart=$RESTART_POLICY, restart_sec=${RESTART_SEC}s, nofile=$LIMIT_NOFILE, tasks=$TASKS_MAX"
    log_info "  healthcheck: enabled=$HC_ENABLED, interval=${HC_INTERVAL}s, max_failures=$HC_MAX_FAILURES"
}

# ── 端口冲突检测 ──────────────────────────────────────────
check_port_conflicts() {
    log_info "开始端口冲突检测..."

    local ports_json
    ports_json=$(python3 -c "
import yaml, json
with open('$CONFIG_PATH') as f:
    c = yaml.safe_load(f) or {}
rules = c.get('gost', {}).get('forward_rules', [])
ports = [r.get('listen_port') for r in rules if r.get('listen_port')]
print(json.dumps(ports))
")

    local has_conflict=0
    local checked=0

    for port in $(echo "$ports_json" | python3 -c "import sys,json; print(' '.join(str(p) for p in json.load(sys.stdin)))"); do
        checked=$((checked + 1))

        # 检查端口是否被系统占用
        local port_in_use=0
        if command -v ss &>/dev/null; then
            if ss -tlnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${port}$"; then
                port_in_use=1
            fi
        elif command -v netstat &>/dev/null; then
            if netstat -tln 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${port}$"; then
                port_in_use=1
            fi
        fi

        if [[ $port_in_use -eq 1 ]]; then
            # 检查是否是 gost 自己在用（重启场景允许）
            local gost_pid
            gost_pid=$(pgrep -x gost 2>/dev/null || echo "")
            if [[ -n "$gost_pid" ]]; then
                local owner
                owner=$(ss -tlnp 2>/dev/null | grep ":${port} " | grep "pid=${gost_pid}" || echo "")
                if [[ -n "$owner" ]]; then
                    log_info "  端口 $port 被 gost 自身占用 (重启场景，允许)"
                    continue
                fi
            fi
            log_error "  端口 $port 已被其他进程占用!"
            if command -v ss &>/dev/null; then
                ss -tlnp 2>/dev/null | grep ":${port} " | head -1 | tee -a "$GOST_LOG_FILE"
            fi
            has_conflict=1
        else
            log_info "  端口 $port 空闲"
        fi
    done

    # 检查规则内部端口重复
    local dup_check
    dup_check=$(echo "$ports_json" | python3 -c "
import sys, json
from collections import Counter
ports = json.load(sys.stdin)
dups = [p for p, c in Counter(ports).items() if c > 1]
if dups:
    print('DUPLICATE:' + ','.join(str(d) for d in dups))
else:
    print('OK')
")
    if [[ "$dup_check" != "OK" ]]; then
        log_error "  转发规则内部端口重复: ${dup_check#DUPLICATE:}"
        has_conflict=1
    fi

    if [[ $has_conflict -eq 1 ]]; then
        log_error "端口冲突检测失败，请解决冲突后重试"
        exit 1
    fi

    log_success "端口冲突检测通过 ($checked 个端口)"
}

# ── 安装 gost ─────────────────────────────────────────────
install_gost() {
    if command -v gost &>/dev/null; then
        log_info "gost 已安装: $(gost -V 2>&1 || echo 'version unknown')"
        return 0
    fi

    log_info "安装 gost (版本: $GOST_VERSION, 架构: $GOST_ARCH)"

    local download_url="https://github.com/go-gost/gost/releases/download/${GOST_VERSION}/gost_${GOST_VERSION}_linux_${GOST_ARCH}.tar.gz"

    log_info "下载: $download_url"
    local tmp_dir
    tmp_dir=$(mktemp -d)

    if curl -sL -o "$tmp_dir/gost.tar.gz" "$download_url" && \
       tar -xzf "$tmp_dir/gost.tar.gz" -C "$tmp_dir"; then
        mkdir -p "$GOST_INSTALL_DIR"
        cp "$tmp_dir/gost" "$GOST_INSTALL_DIR/gost"
        chmod +x "$GOST_INSTALL_DIR/gost"
        log_success "gost 安装成功: $(which gost)"
    else
        log_warn "从 GitHub 下载失败，尝试使用 Go 安装..."
        if command -v go &>/dev/null; then
            go install "github.com/go-gost/gost/cmd/gost@latest" 2>&1 | tee -a "$GOST_LOG_FILE"
            export PATH="$PATH:$(go env GOPATH)/bin"
        else
            log_error "无法安装 gost，请手动安装: https://github.com/go-gost/gost"
            rm -rf "$tmp_dir"
            exit 1
        fi
    fi

    rm -rf "$tmp_dir"

    if ! command -v gost &>/dev/null; then
        log_error "gost 安装后仍不可用"
        exit 1
    fi
    log_success "gost 安装验证通过"
}

# ── 生成 gost 配置 (含 keepalive + autolink) ─────────────
generate_config() {
    log_info "生成 gost 配置: $GOST_CONFIG_FILE"

    python3 << 'PYEOF' | tee -a "$GOST_LOG_FILE"
import yaml, sys, os

config_path = os.environ.get("CONFIG_PATH", "")
with open(config_path) as f:
    cfg = yaml.safe_load(f) or {}

gost_cfg = cfg.get('gost', {})
rules = gost_cfg.get('forward_rules', [])

if not rules:
    print('ERROR: 没有配置转发规则 (gost.forward_rules)', file=sys.stderr)
    sys.exit(1)

ka = gost_cfg.get('keepalive', {})
al = gost_cfg.get('autolink', {})

ka_enabled = ka.get('enabled', True)
ka_idle = ka.get('idle', '15s')
ka_interval = ka.get('interval', '5s')
ka_count = ka.get('count', 3)

al_enabled = al.get('enabled', True)
al_delay = al.get('delay', '5s')

services = []
for rule in rules:
    name = rule.get('name', f'forward-{rule.get("listen_port", "?")}')
    listen_port = rule.get('listen_port')
    target_host = rule.get('target_host')
    target_port = rule.get('target_port', 5985)

    if not listen_port or not target_host:
        print(f'ERROR: 规则 {name} 缺少 listen_port 或 target_host', file=sys.stderr)
        sys.exit(1)

    # listener metadata: keepalive
    listener_meta = {}
    if ka_enabled:
        listener_meta['keepalive'] = True
        listener_meta['keepalive.idle'] = ka_idle
        listener_meta['keepalive.interval'] = ka_interval
        listener_meta['keepalive.count'] = ka_count

    # handler metadata: autolink (自动重连)
    handler_meta = {}
    if al_enabled:
        handler_meta['autolink.delay'] = al_delay

    service = {
        'name': name,
        'addr': f':{listen_port}',
        'handler': {
            'type': 'tcp',
            'chain': 'chain-0',
        },
        'listener': {
            'type': 'tcp',
        },
        'forwarder': {
            'nodes': [{'name': f'{target_host}:{target_port}', 'addr': f'{target_host}:{target_port}'}],
        },
    }

    if listener_meta:
        service['listener']['metadata'] = listener_meta
    if handler_meta:
        service['handler']['metadata'] = handler_meta

    services.append(service)

config = {
    'services': services,
    'chains': [{'name': 'chain-0'}],
}

gost_config_file = os.environ.get("GOST_CONFIG_FILE", "/etc/gost/gost.yaml")
with open(gost_config_file, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print(f'生成 {len(services)} 条转发规则 (keepalive={ka_enabled}, autolink={al_enabled})')
for s in services:
    lm = s.get('listener', {}).get('metadata', {})
    ka_str = f"keepalive(idle={lm.get('keepalive.idle','?')},interval={lm.get('keepalive.interval','?')},count={lm.get('keepalive.count','?')})" if lm else "keepalive=off"
    hm = s.get('handler', {}).get('metadata', {})
    al_str = f"autolink(delay={hm.get('autolink.delay','?')})" if hm else "autolink=off"
    print(f'  {s["name"]}: :{s["addr"][1:]} -> {s["forwarder"]["nodes"][0]["addr"]}  [{ka_str}, {al_str}]')
PYEOF

    if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
        log_error "gost 配置生成失败"
        exit 1
    fi

    log_success "gost 配置已生成: $GOST_CONFIG_FILE"
}

# ── 生成健康检查脚本 ─────────────────────────────────────
generate_healthcheck_script() {
    if [[ "$HC_ENABLED" != "true" ]]; then
        log_info "健康检查未启用，跳过"
        return 0
    fi

    log_info "生成健康检查脚本: $GOST_HEALTHCHECK_SCRIPT"

    cat > "$GOST_HEALTHCHECK_SCRIPT" << 'HCEOF'
#!/bin/bash
#=============================================================
# gost 健康检查脚本 — 定期检测 gost 进程和端口状态，
# 连续失败超过阈值则强制重启 systemd 服务。
# 由 systemd timer 或 cron 调用，也可手动执行。
#
# 用法:
#   gost_healthcheck.sh                    # 执行一次检查
#   gost_healthcheck.sh --pre-check        # 启动前预检 (systemd ExecStartPre)
#   gost_healthcheck.sh --daemon           # 守护模式 (持续运行)
#=============================================================

set -euo pipefail

GOST_CONFIG_FILE="${GOST_CONFIG_FILE:-/etc/gost/gost.yaml}"
GOST_SERVICE_NAME="${GOST_SERVICE_NAME:-gost}"
LOG_FILE="${LOG_FILE:-/var/log/proxyopt/gost_healthcheck.log}"
HC_INTERVAL="${HC_INTERVAL:-30}"
HC_MAX_FAILURES="${HC_MAX_FAILURES:-3}"
HC_TIMEOUT="${HC_TIMEOUT:-5}"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    local level="$1"; shift
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$ts [$level] $*" | tee -a "$LOG_FILE"
}

# 从配置文件读取所有期望监听的端口
get_expected_ports() {
    if [[ ! -f "$GOST_CONFIG_FILE" ]]; then
        echo ""
        return
    fi
    python3 -c "
import yaml
with open('$GOST_CONFIG_FILE') as f:
    c = yaml.safe_load(f) or {}
for s in c.get('services', []):
    addr = s.get('addr', '')
    if addr.startswith(':'):
        print(addr[1:])
" 2>/dev/null || echo ""
}

# 检查 gost 进程是否存活
check_process() {
    if pgrep -x gost &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# 检查端口是否在监听
check_port() {
    local port="$1"
    if command -v ss &>/dev/null; then
        ss -tlnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${port}$"
    elif command -v netstat &>/dev/null; then
        netstat -tln 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${port}$"
    else
        return 0  # 无法检测，假定正常
    fi
}

# 执行一次完整健康检查
run_check() {
    local failures=0

    # 1. 进程检查
    if ! check_process; then
        log "ERROR" "gost 进程不存在!"
        return 1
    fi

    # 2. 端口检查
    local ports
    ports=$(get_expected_ports)
    if [[ -z "$ports" ]]; then
        log "WARN" "无法从配置文件读取期望端口列表，仅检查进程"
        return 0
    fi

    local total=0
    local ok=0
    local fail=0
    while IFS= read -r port; do
        [[ -z "$port" ]] && continue
        total=$((total + 1))
        if check_port "$port"; then
            ok=$((ok + 1))
        else
            fail=$((fail + 1))
            log "WARN" "端口 $port 未监听"
        fi
    done <<< "$ports"

    if [[ $fail -gt 0 ]]; then
        log "ERROR" "健康检查失败: $fail/$total 个端口未监听"
        return 1
    fi

    log "INFO" "健康检查通过: 进程存活, $ok/$total 端口正常"
    return 0
}

# 强制重启 gost
force_restart() {
    log "ERROR" "连续 $HC_MAX_FAILURES 次健康检查失败，强制重启 gost"
    if command -v systemctl &>/dev/null; then
        systemctl restart "$GOST_SERVICE_NAME" 2>&1 | tee -a "$LOG_FILE" || true
        sleep 3
        if systemctl is-active --quiet "$GOST_SERVICE_NAME"; then
            log "INFO" "gost 重启成功"
        else
            log "ERROR" "gost 重启后仍不正常，请人工介入"
        fi
    else
        pkill -x gost 2>/dev/null || true
        sleep 1
        nohup gost -C "$GOST_CONFIG_FILE" >> "$LOG_FILE" 2>&1 &
        sleep 3
        if pgrep -x gost &>/dev/null; then
            log "INFO" "gost 手动重启成功"
        else
            log "ERROR" "gost 手动重启失败，请人工介入"
        fi
    fi
}

# 守护模式: 持续运行健康检查
run_daemon() {
    log "INFO" "健康检查守护进程启动 (间隔=${HC_INTERVAL}s, 最大失败=${HC_MAX_FAILURES})"
    local consecutive_failures=0

    while true; do
        if run_check; then
            consecutive_failures=0
        else
            consecutive_failures=$((consecutive_failures + 1))
            if [[ $consecutive_failures -ge $HC_MAX_FAILURES ]]; then
                force_restart
                consecutive_failures=0
                sleep 5  # 重启后等待稳定
            fi
        fi
        sleep "$HC_INTERVAL"
    done
}

# 主入口
main() {
    local mode="once"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --pre-check)
                mode="precheck"
                shift
                ;;
            --daemon)
                mode="daemon"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    case "$mode" in
        precheck)
            # systemd ExecStartPre: 仅检查端口冲突，不检查进程
            log "INFO" "启动前预检..."
            ports=$(get_expected_ports)
            has_conflict=0
            while IFS= read -r port; do
                [[ -z "$port" ]] && continue
                if check_port "$port"; then
                    # 端口被占用，但可能是旧 gost 实例
                    if ! pgrep -x gost &>/dev/null; then
                        log "ERROR" "端口 $port 被占用且 gost 未运行，可能冲突"
                        has_conflict=1
                    fi
                fi
            done <<< "$ports"
            if [[ $has_conflict -eq 1 ]]; then
                exit 1
            fi
            log "INFO" "预检通过"
            ;;
        daemon)
            run_daemon
            ;;
        once)
            run_check
            ;;
    esac
}

main "$@"
HCEOF

    chmod +x "$GOST_HEALTHCHECK_SCRIPT"
    log_success "健康检查脚本已生成: $GOST_HEALTHCHECK_SCRIPT"
}

# ── 创建 systemd 服务 (增强: always重启 + 高并发 + 健康检查) ──
create_systemd_service() {
    log_info "创建 systemd 服务: gost (增强配置)"

    local hc_pre_line=""
    if [[ "$HC_ENABLED" == "true" ]]; then
        hc_pre_line="ExecStartPre=-$GOST_HEALTHCHECK_SCRIPT --pre-check"
    fi

    cat > "$GOST_SERVICE_FILE" << EOF
[Unit]
Description=gost tunnel service (proxyopt)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$(command -v gost) -C $GOST_CONFIG_FILE
$hc_pre_line

# ── 崩溃后自动重启 ────────────────────────────────────────
Restart=$RESTART_POLICY
# 重启前等待时间
RestartSec=${RESTART_SEC}s
# 限制文件描述符，在高并发转发时防止掉线
LimitNOFILE=$LIMIT_NOFILE
# 限制任务数
TasksMax=$TASKS_MAX

# ── 日志 ──────────────────────────────────────────────────
StandardOutput=journal
StandardError=journal
SyslogIdentifier=gost

# ── 安全加固 ──────────────────────────────────────────────
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$GOST_CONFIG_DIR /var/log/proxyopt
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    # 清理空行
    sed -i '/^$/N;/^\n$/d' "$GOST_SERVICE_FILE"

    systemctl daemon-reload
    systemctl enable gost
    log_success "systemd 服务已创建 (Restart=$RESTART_POLICY, LimitNOFILE=$LIMIT_NOFILE, TasksMax=$TASKS_MAX)"
}

# ── 创建健康检查 systemd timer ────────────────────────────
create_healthcheck_timer() {
    if [[ "$HC_ENABLED" != "true" ]]; then
        return 0
    fi

    log_info "创建健康检查 systemd timer"

    local timer_file="/etc/systemd/system/gost-healthcheck.timer"
    local service_file="/etc/systemd/system/gost-healthcheck.service"

    cat > "$service_file" << EOF
[Unit]
Description=gost healthcheck (proxyopt)

[Service]
Type=oneshot
ExecStart=$GOST_HEALTHCHECK_SCRIPT
EOF

    cat > "$timer_file" << EOF
[Unit]
Description=gost healthcheck timer (proxyopt)

[Timer]
OnBootSec=60s
OnUnitActiveSec=${HC_INTERVAL}s
Unit=gost-healthcheck.service

[Install]
WantedBy=timers.target
EOF

    systemctl daemon-reload
    systemctl enable gost-healthcheck.timer
    systemctl start gost-healthcheck.timer
    log_success "健康检查 timer 已启动 (间隔=${HC_INTERVAL}s)"
}

# ── 启动/重启 gost ────────────────────────────────────────
restart_gost() {
    log_info "启动 gost 服务"

    if [[ -f "$GOST_SERVICE_FILE" ]]; then
        systemctl restart gost
        sleep 2
        if systemctl is-active --quiet gost; then
            log_success "gost 服务已启动 (systemd)"
        else
            log_error "gost 启动失败"
            systemctl status gost 2>&1 | tail -20 | tee -a "$GOST_LOG_FILE"
            exit 1
        fi
    else
        pkill -x gost 2>/dev/null || true
        sleep 1
        nohup gost -C "$GOST_CONFIG_FILE" >> "$GOST_LOG_FILE" 2>&1 &
        sleep 2
        if pgrep -x gost &>/dev/null; then
            log_success "gost 进程已启动"
        else
            log_error "gost 启动失败"
            exit 1
        fi
    fi
}

# ── 验证 gost ─────────────────────────────────────────────
verify_gost() {
    log_info "验证 gost 运行状态"

    if pgrep -x gost &>/dev/null; then
        local pid
        pid=$(pgrep -x gost | head -1)
        log_success "gost 进程运行中 (PID: $pid)"
    else
        log_error "gost 进程未运行"
        exit 1
    fi

    # 列出监听端口
    log_info "gost 转发端口监听状态:"
    if command -v ss &>/dev/null; then
        ss -tlnp 2>/dev/null | grep gost | tee -a "$GOST_LOG_FILE"
    elif command -v netstat &>/dev/null; then
        netstat -tlnp 2>/dev/null | grep gost | tee -a "$GOST_LOG_FILE"
    fi

    # 验证 keepalive 配置
    log_info "gost 配置摘要:"
    grep -E "keepalive|autolink|name:|addr:" "$GOST_CONFIG_FILE" | head -30 | tee -a "$GOST_LOG_FILE"

    # 执行一次健康检查
    if [[ "$HC_ENABLED" == "true" && -x "$GOST_HEALTHCHECK_SCRIPT" ]]; then
        log_info "执行首次健康检查..."
        "$GOST_HEALTHCHECK_SCRIPT" 2>&1 | tee -a "$GOST_LOG_FILE" || log_warn "首次健康检查未通过（刚启动可能需要等待端口绑定）"
    fi
}

# ── 主流程 ────────────────────────────────────────────────
main() {
    log_info "========== gost 端口转发安装配置开始 =========="

    load_config_params
    check_port_conflicts
    install_gost
    generate_config
    generate_healthcheck_script
    create_systemd_service
    create_healthcheck_timer
    restart_gost
    verify_gost

    log_info "========== gost 端口转发安装配置完成 =========="
    log_info "配置文件: $GOST_CONFIG_FILE"
    log_info "日志文件: $GOST_LOG_FILE"
    log_info "健康检查: $GOST_HEALTHCHECK_SCRIPT (间隔 ${HC_INTERVAL}s)"
    log_info "管理命令:"
    log_info "  systemctl {start|stop|restart|status} gost"
    log_info "  systemctl {start|stop} gost-healthcheck.timer"
    log_info "  $GOST_HEALTHCHECK_SCRIPT --daemon  # 守护模式"
}

# 导出环境变量供 Python 子进程使用
export CONFIG_PATH GOST_CONFIG_FILE

main
