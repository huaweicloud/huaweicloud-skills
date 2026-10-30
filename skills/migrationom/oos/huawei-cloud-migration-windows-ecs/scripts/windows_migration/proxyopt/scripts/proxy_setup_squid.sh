#!/bin/bash
#=============================================================
# Squid 代理安装与配置脚本 (Linux)
# 在代理服务器上执行，安装 Squid 并生成缓存配置。
#
# 功能:
#   - 安装 Squid (yum / apt 自动检测)
#   - 生成 squid.conf（缓存大小、TTL、ACL、允许源端访问）
#   - 初始化缓存目录
#   - 启动/重启 Squid 服务
#   - 验证 Squid 正常运行
#
# 用法:
#   bash proxy_setup_squid.sh [--config /path/to/config.yaml]
#
# 参数也可通过环境变量覆盖:
#   SQUID_PORT, SQUID_CACHE_SIZE_MB, SQUID_CACHE_DIR,
#   SQUID_ALLOWED_CIDR, SQUID_MAX_OBJECT_SIZE, SQUID_REFRESH_HOURS
#=============================================================

set -euo pipefail

# ── 默认参数（可被环境变量或配置文件覆盖）──────────────────
SQUID_PORT="${SQUID_PORT:-3128}"
SQUID_CACHE_SIZE_MB="${SQUID_CACHE_SIZE_MB:-4096}"
SQUID_CACHE_DIR="${SQUID_CACHE_DIR:-/var/spool/squid}"
# 安全基线: 默认只放行 RFC1918 内网（else 分支还会统一追加 RFC1918）；
# 确需全网开放代理时显式设 SQUID_ALLOWED_CIDR=0.0.0.0/0 并知悉风险
SQUID_ALLOWED_CIDR="${SQUID_ALLOWED_CIDR:-10.0.0.0/8}"
SQUID_MAX_OBJECT_SIZE="${SQUID_MAX_OBJECT_SIZE:-512 MB}"
SQUID_REFRESH_HOURS="${SQUID_REFRESH_HOURS:-24}"
SQUID_CACHE_MEM="${SQUID_CACHE_MEM:-256 MB}"
SQUID_COLLAPSED_FORWARDING="${SQUID_COLLAPSED_FORWARDING:-true}"
SQUID_CONNECT_PORTS="${SQUID_CONNECT_PORTS:-443}"
SQUID_CONFIG_FILE="${SQUID_CONFIG_FILE:-/etc/squid/squid.conf}"
LOG_DIR="${LOG_DIR:-/var/log/proxyopt}"

# ── 日志函数 ──────────────────────────────────────────────
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/squid_setup.log"

log() {
    local level="$1"; shift
    local msg="$*"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$ts [$level] $msg" | tee -a "$LOG_FILE"
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
        --port)
            SQUID_PORT="$2"
            shift 2
            ;;
        --cache-size)
            SQUID_CACHE_SIZE_MB="$2"
            shift 2
            ;;
        --help)
            echo "Usage: bash proxy_setup_squid.sh [--config config.yaml] [--port 3128] [--cache-size 4096]"
            exit 0
            ;;
        *)
            log_warn "未知参数: $1"
            shift
            ;;
    esac
done

# ── 从 YAML 配置读取参数（安全方式，不使用 eval）─────────
if [[ -n "$CONFIG_PATH" && -f "$CONFIG_PATH" ]]; then
    log_info "从配置文件读取参数: $CONFIG_PATH"
    if command -v python3 &>/dev/null; then
        # 使用 python3 安全提取配置值，逐行赋值
        while IFS='=' read -r key value; do
            [[ -z "$key" || -z "$value" ]] && continue
            case "$key" in
                SQUID_PORT)                  SQUID_PORT="$value" ;;
                SQUID_CACHE_SIZE_MB)         SQUID_CACHE_SIZE_MB="$value" ;;
                SQUID_CACHE_DIR)             SQUID_CACHE_DIR="$value" ;;
                SQUID_MAX_OBJECT_SIZE)       SQUID_MAX_OBJECT_SIZE="$value" ;;
                SQUID_REFRESH_HOURS)         SQUID_REFRESH_HOURS="$value" ;;
                ALLOWED_SRC_CIDR)            SQUID_ALLOWED_CIDR="$value" ;;
                SQUID_ALLOWED_CIDR)          SQUID_ALLOWED_CIDR="$value" ;;
                SQUID_COLLAPSED_FORWARDING)  SQUID_COLLAPSED_FORWARDING="$value" ;;
                CONNECT_PORTS)             SQUID_CONNECT_PORTS="$value" ;;
            esac
        done < <(python3 -c "
import yaml
try:
    with open('$CONFIG_PATH') as f:
        c = yaml.safe_load(f) or {}
    sq = c.get('squid', {})
    for k, v in sq.items():
        if isinstance(v, list):
            v = ' '.join(str(x) for x in v)
        print(f'{k.upper()}={v}')
except Exception:
    pass
" 2>/dev/null)
    fi
fi

log_info "Squid 配置参数:"
log_info "  端口: $SQUID_PORT"
log_info "  缓存大小: ${SQUID_CACHE_SIZE_MB} MB"
log_info "  缓存目录: $SQUID_CACHE_DIR"
log_info "  内存缓存: $SQUID_CACHE_MEM"
log_info "  允许源端 CIDR: $SQUID_ALLOWED_CIDR"
log_info "  最大对象大小: $SQUID_MAX_OBJECT_SIZE"
log_info "  刷新周期: ${SQUID_REFRESH_HOURS}h"
log_info "  collapsed_forwarding: $SQUID_COLLAPSED_FORWARDING"
log_info "  CONNECT 放行端口: $SQUID_CONNECT_PORTS"

# ── 检测包管理器并安装 Squid ───────────────────────────────
install_squid() {
    if command -v squid &>/dev/null; then
        log_info "Squid 已安装: $(squid -v 2>&1 | head -1)"
        return 0
    fi

    log_info "安装 Squid..."
    if command -v yum &>/dev/null; then
        yum install -y squid
    elif command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y squid
    elif command -v dnf &>/dev/null; then
        dnf install -y squid
    else
        log_error "未找到 yum/apt-get/dnf，请手动安装 Squid"
        exit 1
    fi

    if ! command -v squid &>/dev/null; then
        log_error "Squid 安装失败"
        exit 1
    fi
    log_success "Squid 安装成功"
}

# ── 生成 squid.conf ───────────────────────────────────────
generate_config() {
    log_info "生成 Squid 配置: $SQUID_CONFIG_FILE"

    # 备份原配置
    if [[ -f "$SQUID_CONFIG_FILE" ]]; then
        cp "$SQUID_CONFIG_FILE" "${SQUID_CONFIG_FILE}.bak.$(date +%s)"
    fi

    # 计算刷新周期(分钟)
    local SQUID_REFRESH_MIN=$(( SQUID_REFRESH_HOURS * 60 ))

    # 生成 ACL 行: 如果允许所有来源则只写 src all，避免与 RFC1918 子网混用导致 Squid 警告
    local ACL_SECTION=""
    if [[ "$SQUID_ALLOWED_CIDR" == "0.0.0.0/0" || "$SQUID_ALLOWED_CIDR" == "all" ]]; then
        ACL_SECTION="acl localnet src all"
    else
        # 默认仅放行 RFC1918 内网 + 127.0.0.1；显式 CIDR 为空则不再追加（防非法行）
        ACL_SECTION="acl localnet src 10.0.0.0/8
acl localnet src 172.16.0.0/12
acl localnet src 192.168.0.0/16
acl localnet src 127.0.0.1/32"
        if [[ -n "$SQUID_ALLOWED_CIDR" ]]; then
            ACL_SECTION="${ACL_SECTION}
acl localnet src ${SQUID_ALLOWED_CIDR}"
        fi
    fi

    # collapsed_forwarding 指令
    local CF_LINE=""
    if [[ "$SQUID_COLLAPSED_FORWARDING" == "true" ]]; then
        CF_LINE="collapsed_forwarding on"
    fi

    log_info "  刷新周期(分钟): ${SQUID_REFRESH_MIN}"

    cat > "$SQUID_CONFIG_FILE" << EOF
#=============================================================
# Squid 配置 — 由 proxy_setup_squid.sh 自动生成
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
#=============================================================

# ── 监听端口 ──────────────────────────────────────────────
http_port ${SQUID_PORT}

# ── 缓存目录 ──────────────────────────────────────────────
cache_dir ufs ${SQUID_CACHE_DIR} ${SQUID_CACHE_SIZE_MB} 16 256

# ── 最大缓存对象大小 ──────────────────────────────────────
maximum_object_size ${SQUID_MAX_OBJECT_SIZE}
maximum_object_size_in_memory 64 MB

# ── 内存缓存 ──────────────────────────────────────────────
cache_mem ${SQUID_CACHE_MEM}

# ── 日志 ──────────────────────────────────────────────────
access_log /var/log/squid/access.log
cache_log /var/log/squid/cache.log
pid_filename /var/run/squid.pid

# ── ACL 定义 ──────────────────────────────────────────────
${ACL_SECTION}
acl SSL_ports port ${SQUID_CONNECT_PORTS}
acl Safe_ports port 80 8080 3128    # HTTP
acl Safe_ports port ${SQUID_CONNECT_PORTS}   # 迁移控制/数据通道 (22/8899/8900/443)
acl CONNECT method CONNECT

# ── 访问控制 ──────────────────────────────────────────────
http_access allow localnet
http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access deny all

# ── 刷新策略 — 长时间缓存文件 ────────────────────────────
# refresh_pattern: regex min max percent
# 对所有文件缓存 ${SQUID_REFRESH_HOURS} 小时
refresh_pattern .                       ${SQUID_REFRESH_MIN}    100%  ${SQUID_REFRESH_MIN}
refresh_pattern -i \.(exe|msi|zip|tar|gz|tgz|bz2|7z|iso|img|vhd|vhdx)$  43200  100%  43200 override-expire ignore-reload
refresh_pattern -i \.(ps1|bat|cmd|sh)$  43200  100%  43200 override-expire ignore-reload

# ── 透明代理选项 ──────────────────────────────────────────
via off
forwarded_for off

# ── DNS ──────────────────────────────────────────────────
dns_timeout 10 seconds
positive_dns_ttl 1 hours
negative_dns_ttl 10 seconds

# ── 超时 ──────────────────────────────────────────────────
connect_timeout 30 seconds
read_timeout 60 seconds
request_timeout 60 seconds

# ── 并发支持 ──────────────────────────────────────────────
max_filedescriptors 65536
${CF_LINE}

# ── 并发安全: 防缓存雪崩 ──────────────────────────────
# 多个客户端同时请求同一未缓存文件时，只转发一个到源，其余等缓存
EOF

    log_success "Squid 配置已生成"
}

# ── 初始化缓存目录 ────────────────────────────────────────
init_cache() {
    log_info "初始化缓存目录: $SQUID_CACHE_DIR"
    mkdir -p "$SQUID_CACHE_DIR"
    chown -R squid:squid "$SQUID_CACHE_DIR" 2>/dev/null || true

    # squid -z 初始化缓存
    squid -z 2>&1 | tee -a "$LOG_FILE" || log_warn "缓存初始化可能有警告（首次运行正常）"
    log_success "缓存目录初始化完成"
}

# ── 启动/重载 Squid ───────────────────────────────────────
# 修复: CentOS7 squid systemd ExecStop (-k shutdown) 在写清理日志时阻塞,
# systemctl restart 的 stop 阶段挂起导致旧实例退出后新实例未启动。
# 因此: 已在运行时用 -k reconfigure 热加载(不重启); 未运行时才启动, 并加手动兜底。
restart_squid() {
    log_info "配置 Squid 服务"

    if pgrep -x squid >/dev/null 2>&1; then
        log_info "Squid 已在运行，热加载配置 (-k reconfigure)"
        squid -k reconfigure -f "$SQUID_CONFIG_FILE" 2>&1 | tee -a "$LOG_FILE" || log_warn "reconfigure 有输出（通常无害）"
        sleep 2
        log_success "Squid 配置已热加载"
        return 0
    fi

    log_info "Squid 未运行，尝试启动"
    # 1) systemd 启动（首次或已 enabled）
    if systemctl list-unit-files 2>/dev/null | grep -q squid; then
        systemctl enable squid 2>/dev/null || true
        systemctl start squid
        sleep 3
        if pgrep -x squid >/dev/null 2>&1; then
            log_success "Squid 服务已启动 (systemd)"
            return 0
        fi
        log_warn "systemd 启动未确认，尝试手动启动兜底"
        systemctl reset-failed squid 2>/dev/null || true
    fi

    # 2) 手动启动兜底（避免 systemctl restart 的 stop 阻塞问题）
    squid -z 2>&1 | tee -a "$LOG_FILE" || true
    if pgrep -x squid >/dev/null 2>&1; then
        log_info "存在残留 squid 实例，先优雅关闭"
        squid -k shutdown -f "$SQUID_CONFIG_FILE" 2>/dev/null || true
        for i in $(seq 1 15); do
            pgrep -x squid >/dev/null 2>&1 || break
            sleep 2
        done
    fi
    setsid nohup /usr/sbin/squid -f "$SQUID_CONFIG_FILE" > /var/log/squid/manual_start.log 2>&1 < /dev/null &
    sleep 3

    if pgrep -x squid >/dev/null 2>&1; then
        log_success "Squid 进程已启动 (手动)"
    else
        log_error "Squid 启动失败"
        journalctl -u squid --no-pager 2>/dev/null | tail -20 | tee -a "$LOG_FILE" || true
        exit 1
    fi
}

# ── 验证 Squid ────────────────────────────────────────────
verify_squid() {
    log_info "验证 Squid 运行状态"

    # 检查端口监听
    if ss -tlnp 2>/dev/null | grep -q ":${SQUID_PORT} " || \
       netstat -tlnp 2>/dev/null | grep -q ":${SQUID_PORT} "; then
        log_success "Squid 端口 ${SQUID_PORT} 正在监听"
    else
        log_warn "无法确认端口 ${SQUID_PORT} 监听状态，请手动检查"
    fi

    # 检查进程
    if pgrep -x squid &>/dev/null; then
        local pid
        pid=$(pgrep -x squid | head -1)
        log_success "Squid 进程运行中 (PID: $pid)"
    else
        log_error "Squid 进程未运行"
        exit 1
    fi

    log_info "Squid 配置验证:"
    squid -k parse 2>&1 | tail -5 | tee -a "$LOG_FILE"
}

# ── 主流程 ────────────────────────────────────────────────
main() {
    log_info "========== Squid 代理安装配置开始 =========="

    install_squid
    generate_config
    init_cache
    restart_squid
    verify_squid

    log_info "========== Squid 代理安装配置完成 =========="
    log_info "代理地址: http://<proxy_server_ip>:${SQUID_PORT}"
    log_info "日志文件: /var/log/squid/access.log"
    log_info "缓存目录: $SQUID_CACHE_DIR (${SQUID_CACHE_SIZE_MB} MB)"
}

main
