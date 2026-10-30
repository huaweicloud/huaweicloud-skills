#!/bin/bash
#=============================================================
# 沙箱侧安装包下载脚本 — 从 OBS 下载迁移工具包到本地中转目录。
#
# ⚠️ 架构说明（2026-09 调整）：
#   私网场景的文件服务器已「部署到代理主机」而非沙箱——
#   源端经 Squid 代理/同网段直连代理主机 8080 下载安装包，
#   不再依赖沙箱入站。Squid/gost/HTTP/文件同步/preCache 统一由:
#       proxyopt/scripts/deploy_jumpbox.py --config config/migrate.yaml
#   完成（同时也是 private_scenario Phase1 的自动部署引擎）。
#
#   本脚本保留为「沙箱侧 OBS 下载」工具（--step obs），
#   http/precache 步骤仅用于沙箱可在内网被源端访问的旧式 LAN 场景。
#
# 用法:
#   bash run_pipeline.sh --config config.yaml        # 等价 --step obs
#   bash run_pipeline.sh --step obs                  # 只执行 OBS 下载
#   bash run_pipeline.sh --step http                 # 沙箱 HTTP（LAN 场景）
#   bash run_pipeline.sh --step precache             # 经 Squid 预缓存
#=============================================================

set -euo pipefail

# ── 路径与变量 ────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_DIR/config"
LOG_DIR="$PROJECT_DIR/logs"
DEFAULT_CONFIG="$CONFIG_DIR/config.yaml"

# ── 日志函数 ──────────────────────────────────────────────
mkdir -p "$LOG_DIR"
PIPELINE_LOG="$LOG_DIR/pipeline.log"

log() {
    local level="$1"; shift
    local msg="$*"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$ts [$level] [PIPELINE] $msg" | tee -a "$PIPELINE_LOG"
}

log_info()    { log "INFO"    "$@"; }
log_warn()    { log "WARN"    "$@"; }
log_error()   { log "ERROR"   "$@"; }
log_success() { log "SUCCESS" "$@"; }
log_step()    { log "STEP"    "$@"; }

# ── 解析参数 ──────────────────────────────────────────────
CONFIG_PATH="$DEFAULT_CONFIG"
STEP="all"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --config|-c)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --step|-s)
            STEP="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: bash run_pipeline.sh [--config config.yaml] [--step <obs|http|precache|all>]"
            echo ""
            echo "Steps:"
            echo "  obs       - 从 OBS 下载文件到沙箱本地"
            echo "  http      - 启动 HTTP 文件服务"
            echo "  precache  - 通过 Squid 代理预缓存所有文件"
            echo "  all       - 顺序执行 obs -> http -> precache (默认)"
            echo ""
            echo "注意: Squid/gost 安装需在代理服务器上单独执行:"
            echo "  bash proxy_setup_squid.sh --config config.yaml"
            echo "  bash proxy_setup_gost.sh --config config.yaml"
            exit 0
            ;;
        *)
            log_warn "未知参数: $1"
            shift
            ;;
    esac
done

if [[ ! -f "$CONFIG_PATH" ]]; then
    log_error "配置文件不存在: $CONFIG_PATH"
    exit 1
fi

log_info "========== 迁移文件分发流水线 =========="
log_info "配置文件: $CONFIG_PATH"
log_info "执行步骤: $STEP"
log_info "项目目录: $PROJECT_DIR"

# ── 状态文件（原子写入）──────────────────────────────────
STATE_FILE="$LOG_DIR/.pipeline_state"
write_state() {
    # 原子追加：先写临时文件再 mv，避免并发写损坏
    local tmp
    tmp=$(mktemp)
    echo "$1=$2" > "$tmp"
    cat "$STATE_FILE" 2>/dev/null >> "$tmp" || true
    mv "$tmp" "$STATE_FILE"
}
read_state() {
    grep "^$1=" "$STATE_FILE" 2>/dev/null | tail -1 | cut -d= -f2
}
init_state() {
    : > "$STATE_FILE"
}

# ── 步骤 1: OBS 下载 ──────────────────────────────────────
step_obs() {
    log_step "1/4 OBS 下载 -> START"

    local script="$SCRIPT_DIR/sandbox_download_obs.py"
    if [[ ! -f "$script" ]]; then
        log_error "脚本不存在: $script"
        return 1
    fi

    if python3 "$script" --config "$CONFIG_PATH"; then
        log_success "OBS 下载完成"
        write_state "obs" "done"
        log_step "1/4 OBS 下载 -> DONE"
        return 0
    else
        log_error "OBS 下载失败"
        write_state "obs" "failed"
        log_step "1/4 OBS 下载 -> FAILED"
        return 1
    fi
}

# ── 步骤 2: HTTP 文件服务 ─────────────────────────────────
step_http() {
    log_step "2/4 HTTP 文件服务 -> START"

    local script="$SCRIPT_DIR/sandbox_http_server.py"
    if [[ ! -f "$script" ]]; then
        log_error "脚本不存在: $script"
        return 1
    fi

    # 检查是否已有 HTTP 服务在运行
    local http_port
    http_port=$(python3 -c "
import yaml
with open('$CONFIG_PATH') as f:
    c = yaml.safe_load(f) or {}
print(c.get('sandbox', {}).get('http_port', 8080))
" 2>/dev/null || echo "8080")

    if ss -tlnp 2>/dev/null | grep -q ":${http_port} " || \
       netstat -tlnp 2>/dev/null | grep -q ":${http_port} "; then
        log_warn "端口 $http_port 已被占用，假设 HTTP 服务已在运行"
        write_state "http" "running"
        log_step "2/4 HTTP 文件服务 -> ALREADY_RUNNING"
        return 0
    fi

    # 后台启动 HTTP 服务
    log_info "后台启动 HTTP 服务 (端口 $http_port)"
    nohup python3 "$script" --config "$CONFIG_PATH" >> "$LOG_DIR/http_server_stdout.log" 2>&1 &
    local http_pid=$!
    echo "$http_pid" > "$LOG_DIR/.http_server.pid"

    # 等待服务启动
    local retries=10
    while [[ $retries -gt 0 ]]; do
        sleep 1
        if ss -tlnp 2>/dev/null | grep -q ":${http_port} " || \
           netstat -tlnp 2>/dev/null | grep -q ":${http_port} "; then
            log_success "HTTP 服务已启动 (PID: $http_pid, 端口: $http_port)"
            write_state "http" "running"
            write_state "http_pid" "$http_pid"
            log_step "2/4 HTTP 文件服务 -> DONE"
            return 0
        fi
        retries=$((retries - 1))
    done

    log_error "HTTP 服务启动超时"
    write_state "http" "failed"
    log_step "2/4 HTTP 文件服务 -> FAILED"
    return 1
}

# ── 步骤 3: 提示代理配置 ──────────────────────────────────
step_proxy_hint() {
    log_step "3/4 代理服务器配置 -> 提示"
    log_info "请在代理服务器上执行以下命令:"
    log_info "  bash proxy_setup_squid.sh --config config.yaml"
    log_info "  bash proxy_setup_gost.sh  --config config.yaml"
    log_info ""
    log_info "确认代理服务就绪后，继续执行预缓存步骤。"

    # 仅在交互式终端时等待用户确认
    if [[ -t 0 ]]; then
        log_info "按 Enter 继续 (30秒超时自动继续)..."
        read -r -t 30 || true
    else
        log_info "非交互模式，自动继续 (假设代理已就绪)"
    fi
    write_state "proxy" "assumed_ready"
}

# ── 步骤 4: 预缓存 ────────────────────────────────────────
step_precache() {
    log_step "4/4 预缓存 -> START"

    # 前置检查：HTTP 服务必须运行
    local http_state
    http_state=$(read_state "http")
    if [[ "$http_state" != "running" ]]; then
        log_warn "HTTP 服务状态不确定，尝试继续..."
    fi

    local script="$SCRIPT_DIR/sandbox_precache.py"
    if [[ ! -f "$script" ]]; then
        log_error "脚本不存在: $script"
        return 1
    fi

    if python3 "$script" --config "$CONFIG_PATH"; then
        log_success "预缓存完成"
        write_state "precache" "done"
        log_step "4/4 预缓存 -> DONE"
        return 0
    else
        log_error "预缓存失败"
        write_state "precache" "failed"
        log_step "4/4 预缓存 -> FAILED"
        return 1
    fi
}

# ── 最终汇总 ──────────────────────────────────────────────
print_summary() {
    log_info "========== 流水线汇总 =========="
    log_info "状态文件: $STATE_FILE"
    if [[ -f "$STATE_FILE" ]]; then
        while IFS='=' read -r key value; do
            log_info "  $key: $value"
        done < "$STATE_FILE"
    fi
    log_info ""
    log_info "下一步操作:"
    log_info "  1. 确认代理服务器 Squid + gost 已就绪"
    log_info "  2. 在源端 Windows 主机上执行 Download-Agent.ps1:"
    log_info "     .\Download-Agent.ps1 -ProxyHost <squid_ip> -SandboxHost <sandbox_ip>"
    log_info ""
    log_info "  源端下载命令示例 (100台并发):"
    log_info "    .\Download-Agent.ps1 -ProxyHost 10.0.1.50 -SandboxHost 10.0.1.10 -Concurrent 10"
}

# ── 清理函数 ──────────────────────────────────────────────
cleanup() {
    log_info "收到中断信号"
    local http_pid_file="$LOG_DIR/.http_server.pid"
    if [[ -f "$http_pid_file" ]]; then
        local pid
        pid=$(cat "$http_pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "停止 HTTP 服务 (PID: $pid)"
            kill "$pid" 2>/dev/null || true
        fi
    fi
    print_summary
}
trap cleanup INT TERM

# ── 主流程 ────────────────────────────────────────────────
main() {
    init_state

    case "$STEP" in
        obs)
            step_obs
            ;;
        http)
            step_http
            ;;
        precache)
            step_precache
            ;;
        all)
            # 默认流程: 仅 OBS 下载（文件服务器已移至代理主机，
            # Squid/gost/HTTP/同步/preCache 由 deploy_jumpbox.py 负责）
            if ! step_obs; then
                log_error "流水线在 OBS 下载步骤失败，终止"
                print_summary
                exit 1
            fi

            log_success "OBS 下载完成。文件服务器/Squid/gost/preCache 请使用:"
            log_success "  python3 proxyopt/scripts/deploy_jumpbox.py --config config/migrate.yaml"
            ;;
        *)
            log_error "未知步骤: $STEP (可选: obs, http, precache, all)"
            exit 1
            ;;
    esac

    print_summary
}

main
