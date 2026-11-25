#!/bin/bash
# devbridge_cmd.sh — DevBridge CLI 动态命令适配层
#
# 通过解析 devbridge <command> --help 输出，自动发现当前 CLI 版本
# 实际支持哪些 flag，从而适配不同版本之间的参数差异。
# 执行后如果报错，自动解析 cobra 错误信息，尝试恢复并重试。
#
# 目标版本: DevBridge CLI v0.2.x (API Key auth, new tunnel domain)
#
# 用法: source devbridge_cmd.sh，然后调用 db_* 系列函数

# --- 安装渠道（官方） ---
#   GitCode: https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh
#   注意: GitCode 官方仓库名拼写就是 "devbrige"（少一个 d），非笔误，请勿"修正"。
#   GitHub:  https://github.com/huaweicloud/devspace-devbridge/releases/latest/download/install.sh
#   OBS:     https://tools-artifact.developer.huaweicloud.com/sharedata/devbridge/install.sh
# 无终端环境请使用 -s (silent) 模式，避免 /dev/tty 交互提示失败。
DEVBRIDGE_INSTALL_URL="https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh"

# 日志和认证
_DB_LOG_DIR="/tmp"
_DB_APIKEY_URL="https://devstation.connect.huaweicloud.com/space/devbridge/apikey"
# OBS 渠道提供最新 v0.2.x；旧渠道 res-hd.hc-cdn.cn 只有 v0.1.x（域名已迁移，不可用）
_DB_INSTALL_URL_OBS="https://tools-artifact.developer.huaweicloud.com/sharedata/devbridge/install.sh"

# --- 参数白名单 ---

_db_err() { printf '%s\n' "$*" >&2; }

_db_valid_tunnel_id() {
    case "$1" in
        ''|*[!a-z0-9]*) return 1 ;;
    esac
    [ "${#1}" -le 128 ]
}

_db_valid_name() {
    case "$1" in
        ''|*[!A-Za-z0-9_-]*) return 1 ;;
    esac
    [ "${#1}" -le 128 ]
}

_db_valid_port() {
    case "$1" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "${#1}" -le 5 ] || return 1
    [ "$1" -ge 1 ] && [ "$1" -le 65535 ]
}

_db_valid_flag_name() {
    case "$1" in
        ''|*[!a-z0-9-]*) return 1 ;;
    esac
    return 0
}

# 拒绝换行与 shell 元字符，避免任何值被解释为命令
_db_safe_value() {
    case "$1" in
        *';'*|*'|'*|*'&'*|*'$'*|*'`'*|*'<'*|*'>'*|*'('*|*')'*|*'{'*|*'}'*|*'['*|*']'*|*'!'*|*'\'*|*"'"*|*'"'*|*$'\n'*|*$'\r'*)
            return 1 ;;
    esac
    return 0
}

_db_valid_subcmd() {
    local s="$1" w
    [ -n "$s" ] || return 1
    for w in $s; do
        _db_valid_flag_name "$w" || return 1
    done
    return 0
}

# --- 显式确认 ---
# 默认必须确认；受控自动化可在显式设置 DEVBRIDGE_YES=1 后跳过。
_db_confirm() {
    local action="$1" assume_yes="${2:-0}"
    if [ "$assume_yes" = "1" ] || [ "${DEVBRIDGE_YES:-0}" = "1" ]; then
        return 0
    fi
    _db_err "Confirmation required: ${action}."
    printf '%s' 'Type "yes" to continue: ' >&2
    local reply=""
    if ! IFS= read -r reply; then
        _db_err ""
        return 1
    fi
    [ "$reply" = "yes" ]
}

_db_confirm_phrase() {
    local phrase="$1" assume_yes="${2:-0}"
    if [ "$assume_yes" = "1" ] || [ "${DEVBRIDGE_YES:-0}" = "1" ]; then
        return 0
    fi
    _db_err "This deletes ALL tunnels in the current workspace."
    printf '%s' "Type \"$phrase\" to confirm: " >&2
    local reply=""
    if ! IFS= read -r reply; then
        _db_err ""
        return 1
    fi
    [ "$reply" = "$phrase" ]
}

# 安装/升级需要用户同意；自动化需显式设置 DEVBRIDGE_AUTO_SETUP=1。
_db_confirm_setup() {
    local action="$1"
    if [ "${DEVBRIDGE_AUTO_SETUP:-0}" = "1" ] || [ "${DEVBRIDGE_YES:-0}" = "1" ]; then
        return 0
    fi
    _db_err "Permission is required to ${action}."
    printf '%s' 'Type "yes" to continue: ' >&2
    local reply=""
    if ! IFS= read -r reply; then
        _db_err ""
        return 1
    fi
    [ "$reply" = "yes" ]
}

# --- flag 检测 ---

_db_has_flag() {
    local subcmd="$1"
    local flag="$2"
    _db_valid_subcmd "$subcmd" || return 1
    _db_valid_flag_name "${flag#--}" || return 1
    devbridge $subcmd --help 2>&1 | grep -q -- "$flag"
}

_db_anon_allow_flag() {
    local subcmd="$1"
    if _db_has_flag "$subcmd" "--allow-anonymous"; then
        echo "--allow-anonymous"
    elif _db_has_flag "$subcmd" "-a"; then
        echo "-a"
    elif _db_has_flag "$subcmd" "--anonymous"; then
        echo "--anonymous"
    fi
}

_db_anon_deny_flag() {
    local subcmd="$1"
    if _db_has_flag "$subcmd" "--deny-anonymous"; then
        echo "--deny-anonymous"
    elif _db_has_flag "$subcmd" "--no-anonymous"; then
        echo "--no-anonymous"
    fi
}

_db_port_flag() {
    local subcmd="$1"
    if _db_has_flag "$subcmd" "--port-number"; then
        echo "--port-number"
    elif _db_has_flag "$subcmd" "--port"; then
        echo "--port"
    elif _db_has_flag "$subcmd" "--ports"; then
        echo "--ports"
    fi
}

# v0.2.x 已移除 list/port list 的 --json 输出；保留探测用于兼容旧版
_db_json_flag() {
    local subcmd="$1"
    if _db_has_flag "$subcmd" "--json"; then
        echo "--json"
    elif _db_has_flag "$subcmd" "-j"; then
        echo "-j"
    fi
}

# --- 错误解析与自动恢复 ---

# 从 help 输出中提取 flag 的默认值
_db_flag_default() {
    printf '%s\n' "$1" | grep -- "$2" | grep -oP '\(default "\K[^"]+' | head -1
}

# 从 help 输出中提取 flag 的第一个可选值
_db_flag_options() {
    printf '%s\n' "$1" | grep -- "$2" | grep -oP '\(options: \K[^)]+' | head -1 | cut -d/ -f1
}

# 从 help 输出中提取 flag 的类型
_db_flag_type() {
    local line
    line=$(printf '%s\n' "$1" | grep -- "$2" | head -1)
    if printf '%s\n' "$line" | grep -q ' int '; then echo "int"
    elif printf '%s\n' "$line" | grep -q ' string '; then echo "string"
    elif printf '%s\n' "$line" | grep -q ' bool '; then echo "bool"
    elif printf '%s\n' "$line" | grep -q ' uints '; then echo "uints"
    fi
}

# 为缺失的必填 flag 猜测一个合理的默认值
_db_guess_flag_value() {
    local help_output="$1"
    local flag_name="$2"
    local flag_with_dashes="--$flag_name"

    # 1. 先看 help 里有没有 (default "...")
    local v
    v=$(_db_flag_default "$help_output" "$flag_with_dashes")
    [ -n "$v" ] && { echo "$v"; return 0; }

    # 2. 看 help 里有没有 (options: a/b/c)，取第一个
    v=$(_db_flag_options "$help_output" "$flag_with_dashes")
    [ -n "$v" ] && { echo "$v"; return 0; }

    # 3. 根据 flag 名做常见猜测
    case "$flag_name" in
        region)         echo "cn-north-4"; return 0 ;;
        protocol)       echo "auto"; return 0 ;;
        name|tunnel-name) echo "dev-tunnel"; return 0 ;;
        description|desc) echo "dev-tunnel"; return 0 ;;
        expiration|expiry|ttl) echo "72"; return 0 ;;
        port|port-number|ports) echo "8080"; return 0 ;;
        api-key)        echo "${HW_API_KEY:-}"; return 0 ;;
    esac

    # 4. 根据类型猜测
    local t
    t=$(_db_flag_type "$help_output" "$flag_with_dashes")
    case "$t" in
        int)    echo "0"; return 0 ;;
        bool)   echo "true"; return 0 ;;
        string) echo ""; return 0 ;;
    esac

    return 1  # 无法猜测
}

# 在 help 输出中查找与给定 flag 名相似的 flag
_db_find_similar_flag() {
    local help_output="$1"
    local flag_name="$2"
    local f

    for f in $(printf '%s\n' "$help_output" | grep -oP '\-\-\K[a-zA-Z0-9-]+' | sort -u); do
        # 去掉 "port-" 前缀差异后比较
        local cf="${f#port-}" cn="${flag_name#port-}"
        if [ "$cf" = "$cn" ]; then echo "--$f"; return 0; fi
    done

    # 子串匹配
    for f in $(printf '%s\n' "$help_output" | grep -oP '\-\-\K[a-zA-Z0-9-]+' | sort -u); do
        if printf '%s\n' "$f" | grep -q -- "$flag_name" || printf '%s\n' "$flag_name" | grep -q -- "$f"; then
            echo "--$f"; return 0
        fi
    done
}

# 核心: 带自动恢复的命令执行器（Bash 数组传参，不做字符串拼接）
_db_exec_retry() {
    local subcmd="$1"
    shift
    local -a cmd=("$@")

    # 第一次执行
    local output rc
    output=$("${cmd[@]}" 2>&1)
    rc=$?

    if [ "$rc" -eq 0 ]; then
        printf '%s\n' "$output"
        return 0
    fi

    # ---- 失败，开始错误解析与恢复 ----

    # 错误类型 1: required flag(s) "xxx" not set
    if printf '%s\n' "$output" | grep -q 'required flag(s)'; then
        local missing
        missing=$(printf '%s\n' "$output" | grep -oP '"\K[^"]+' | head -1)
        if [ -n "$missing" ] && _db_valid_flag_name "$missing"; then
            local guessed
            guessed=$(_db_guess_flag_value "$output" "$missing")
            if [ -n "$guessed" ] && _db_safe_value "$guessed"; then
                local -a retry=("${cmd[@]}" "--$missing" "$guessed")
                local retry_output retry_rc
                retry_output=$("${retry[@]}" 2>&1)
                retry_rc=$?
                if [ "$retry_rc" -eq 0 ]; then printf '%s\n' "$retry_output"; return 0; fi
                printf '%s\n' "$retry_output" >&2; return "$retry_rc"
            fi
            _db_err "ERROR: 新必填参数 '--$missing' 无法自动适配，请运行 'devbridge $subcmd --help' 查看选项。"
            printf '%s\n' "$output" >&2; return "$rc"
        fi
    fi

    # 错误类型 2: unknown flag: --xxx
    if printf '%s\n' "$output" | grep -q 'unknown flag'; then
        local bad_flag
        bad_flag=$(printf '%s\n' "$output" | grep -oP 'unknown flag: \K\S+' | head -1)
        if [ -n "$bad_flag" ] && _db_valid_flag_name "${bad_flag#--}"; then
            # 先找相似 flag
            local similar
            similar=$(_db_find_similar_flag "$output" "${bad_flag#--}")
            local idx=-1 i
            for i in "${!cmd[@]}"; do
                if [ "${cmd[$i]}" = "$bad_flag" ]; then idx=$i; break; fi
            done
            if [ "$idx" -ge 0 ]; then
                local -a retry=("${cmd[@]}")
                if [ -n "$similar" ] && [ "$similar" != "$bad_flag" ] && _db_valid_flag_name "${similar#--}"; then
                    retry[$idx]="$similar"
                else
                    unset "retry[$idx]"
                fi
                local retry_output retry_rc
                retry_output=$("${retry[@]}" 2>&1)
                retry_rc=$?
                if [ "$retry_rc" -eq 0 ]; then printf '%s\n' "$retry_output"; return 0; fi
            fi
        fi
    fi

    # 错误类型 3: unknown command "xxx"
    if printf '%s\n' "$output" | grep -q 'unknown command'; then
        local bad_cmd
        bad_cmd=$(printf '%s\n' "$output" | grep -oP 'unknown command "\K[^"]+' | head -1)
        if [ -n "$bad_cmd" ] && _db_valid_flag_name "$bad_cmd"; then
            # 常见命令同义词映射
            local synonym=""
            case "$bad_cmd" in
                list|ls)         synonym="tunnels" ;;
                tunnels)         synonym="list" ;;
                rm|remove)       synonym="delete" ;;
                delete)          synonym="rm" ;;
                add|new)         synonym="create" ;;
                create)          synonym="add" ;;
                show|info|detail) synonym="get" ;;
                get)             synonym="show" ;;
            esac

            # 候选列表: 同义词 + 所有可用命令
            local candidates="$synonym"
            candidates+=" $(devbridge --help 2>&1 | grep -oP '^\s+\K\S+' | sort -u)"

            local c
            for c in $candidates; do
                [ -z "$c" ] && continue
                [ "$c" = "$bad_cmd" ] && continue
                _db_valid_flag_name "$c" || continue
                # 子串匹配或同义词匹配
                if [ "$c" = "$synonym" ] || \
                   printf '%s\n' "$c" | grep -q -- "$bad_cmd" || \
                   printf '%s\n' "$bad_cmd" | grep -q -- "$c"; then
                    local -a retry=("${cmd[@]}")
                    local idx=-1 i
                    for i in "${!retry[@]}"; do
                        if [ "${retry[$i]}" = "$bad_cmd" ]; then idx=$i; break; fi
                    done
                    [ "$idx" -ge 0 ] || continue
                    retry[$idx]="$c"
                    local retry_output retry_rc
                    retry_output=$("${retry[@]}" 2>&1)
                    retry_rc=$?
                    if [ "$retry_rc" -eq 0 ]; then printf '%s\n' "$retry_output"; return 0; fi
                fi
            done
        fi
    fi

    # 无法自动恢复
    printf '%s\n' "$output" >&2
    return "$rc"
}

# --- CLI 安装与认证 ---

# 安全下载并执行安装脚本（先下载到临时文件，校验为 shell 脚本后再执行）
_db_download_and_run() {
    local url="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/devbridge_install.XXXXXX.sh)
    if ! curl -fsSL "$url" -o "$tmpfile" 2>&1; then
        rm -f "$tmpfile"
        return 1
    fi
    # 基本校验：确保下载的是 shell 脚本
    if ! head -1 "$tmpfile" | grep -qE '^#!'; then
        _db_err "ERROR: Downloaded file is not a valid shell script"
        rm -f "$tmpfile"
        return 1
    fi
    bash "$tmpfile" -s 2>&1
    local rc=$?
    rm -f "$tmpfile"
    return $rc
}

_db_install_cli() {
    if ! _db_confirm_setup "download and install the DevBridge CLI"; then
        _db_err "ERROR: installation not approved. Install it manually, or set DEVBRIDGE_AUTO_SETUP=1 for approved automation."
        return 1
    fi
    _db_err "Installing DevBridge CLI..."
    _db_download_and_run "$_DB_INSTALL_URL_OBS" \
        || _db_download_and_run "$DEVBRIDGE_INSTALL_URL"
    export PATH="$HOME/.huawei/bin:$PATH"
    if ! command -v devbridge >/dev/null 2>&1; then
        _db_err "ERROR: devbridge CLI installation failed"
        return 1
    fi
}

_db_ensure_cli_version() {
    local ver raw_output
    raw_output=$(devbridge version 2>&1)
    # 透传 CLI 的新版本提示（第一行是版本号，其余输出透传到 stderr）
    printf '%s\n' "$raw_output" | tail -n +2 | grep -v '^$' >&2
    ver=$(printf '%s\n' "$raw_output" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [ -z "$ver" ]; then ver="0.0.0"; fi
    local major minor
    major=$(printf '%s\n' "$ver" | cut -d. -f1)
    minor=$(printf '%s\n' "$ver" | cut -d. -f2)
    if [ "$major" -lt 1 ] && [ "$minor" -lt 2 ]; then
        if ! _db_confirm_setup "upgrade the DevBridge CLI from v$ver to v0.2.x"; then
            _db_err "ERROR: upgrade not approved. Upgrade it manually, or set DEVBRIDGE_AUTO_SETUP=1 for approved automation."
            return 1
        fi
        _db_err "Detected v$ver (old domain, cannot connect). Upgrading..."
        _db_download_and_run "$_DB_INSTALL_URL_OBS"
        raw_output=$(devbridge version 2>&1)
        printf '%s\n' "$raw_output" | tail -n +2 | grep -v '^$' >&2
        ver=$(printf '%s\n' "$raw_output" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        _db_err "Upgraded to v$ver"
    fi
}

_db_ensure_auth() {
    local auth
    auth=$(devbridge auth status 2>&1)
    if printf '%s\n' "$auth" | grep -qiE "^(Logged|logged) in"; then
        # "Logged in" 状态可能来自过期凭证的残留，用轻量 API 调用验证
        if devbridge list >/dev/null 2>&1; then
            return 0
        fi
        # list 失败说明凭证过期，继续往下走重新登录
    fi
    local api_key="${DEVBRIDGE_API_KEY:-${HW_API_KEY:-${JOB_ENV_HW_DEVBRIDGE_API_KEY:-}}}"
    if [ -n "$api_key" ]; then
        # 调用方显式提供 API Key 环境变量 = 已完成登录授权
        devbridge auth login --api-key "$api_key" >/dev/null 2>&1
        # 登录后同样验证凭证有效性
        if devbridge list >/dev/null 2>&1; then
            return 0
        fi
    fi
    _db_err "ERROR: Not logged in. Set DEVBRIDGE_API_KEY or HW_API_KEY env var, then run:"
    _db_err "  devbridge auth login"
    _db_err "  Get API key: $_DB_APIKEY_URL"
    return 1
}

# --- 对外封装函数 ---

db_init() {
    # 自动发现并 source job 环境的 hw-env 文件（获取 JOB_ENV_HW_DEVBRIDGE_API_KEY 等）
    if [ -d /root/job-envs/sandboxes ]; then
        for _db_envf in /root/job-envs/sandboxes/*-hw-env; do
            [ -f "$_db_envf" ] && . "$_db_envf" 2>/dev/null
        done
        unset _db_envf
    fi
    if ! command -v devbridge >/dev/null 2>&1; then
        _db_install_cli || return 1
    fi
    _db_ensure_cli_version || return 1
    _db_ensure_auth || return 1
    return 0
}

db_create() {
    local name="$1"; shift || true
    local desc="" expiration=""
    while [ $# -gt 0 ]; do
        case "$1" in
            -d) desc="${2:-}"; if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
            -e) expiration="${2:-}"; if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
            *)  shift ;;
        esac
    done
    _db_valid_name "$name" || { _db_err "ERROR: invalid tunnel name (allowed: letters, digits, _ and -)"; return 2; }
    if [ -n "$desc" ] && ! _db_safe_value "$desc"; then
        _db_err "ERROR: description contains unsupported characters"; return 2
    fi
    if [ -n "$expiration" ]; then
        case "$expiration" in
            ''|*[!0-9]*) _db_err "ERROR: expiration must be an integer between 1 and 720"; return 2 ;;
        esac
        if [ "$expiration" -lt 1 ] || [ "$expiration" -gt 720 ]; then
            _db_err "ERROR: expiration must be between 1 and 720 hours"; return 2
        fi
    fi
    local -a cmd=(devbridge create "$name")
    if [ -n "$desc" ] && _db_has_flag "create" "-d"; then
        cmd+=(-d "$desc")
    fi
    if [ -n "$expiration" ] && _db_has_flag "create" "-e"; then
        cmd+=(-e "$expiration")
    fi
    local output rc
    output=$(_db_exec_retry "create" "${cmd[@]}" 2>&1)
    rc=$?
    if [ "$rc" -ne 0 ]; then
        printf '%s\n' "$output" >&2
        return "$rc"
    fi
    # Extract and return just the tunnel ID
    printf '%s\n' "$output" | grep -oP 'Tunnel ID:\s+\K\S+' | head -1
}

db_port_create() {
    local tunnel_id="$1"; shift || true
    local port="" protocol="" anon=""
    while [ $# -gt 0 ]; do
        case "$1" in
            -p)         port="${2:-}"; if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
            --protocol) protocol="${2:-}"; if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
            --anon)     anon="${2:-}"; if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
            -a|--allow-anonymous) anon="allow"; shift ;;
            --deny-anonymous)     anon="deny"; shift ;;
            *)          shift ;;
        esac
    done
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    if [ -n "$port" ] && ! _db_valid_port "$port"; then
        _db_err "ERROR: port must be an integer between 1 and 65535"; return 2
    fi
    if [ -n "$protocol" ]; then
        case "$protocol" in
            http|https|auto) ;;
            *) _db_err "ERROR: protocol must be http, https or auto"; return 2 ;;
        esac
    fi
    # 允许匿名访问会形成公网暴露入口，必须先获得显式确认
    if [ "$anon" = "allow" ]; then
        if ! _db_confirm "allow anonymous (public) access on tunnel ${tunnel_id} port ${port:-default}"; then
            _db_err "ERROR: anonymous access not approved; keeping deny-by-default."
            return 3
        fi
    fi
    local port_flag
    port_flag=$(_db_port_flag "port create")
    local anon_flag=""
    if [ -n "$anon" ]; then
        if [ "$anon" = "allow" ]; then
            anon_flag=$(_db_anon_allow_flag "port create")
        else
            anon_flag=$(_db_anon_deny_flag "port create")
        fi
    fi
    # 默认不传匿名 flag: v0.2.x 端口默认为禁止匿名访问 (deny)
    local -a cmd=(devbridge port create "$tunnel_id")
    if [ -n "$port_flag" ] && [ -n "$port" ]; then cmd+=("$port_flag" "$port"); fi
    if [ -n "$protocol" ] && _db_has_flag "port create" "--protocol"; then cmd+=(--protocol "$protocol"); fi
    if [ -n "$anon_flag" ]; then cmd+=("$anon_flag"); fi
    _db_exec_retry "port create" "${cmd[@]}"
}

db_host() {
    local tunnel_id="$1"
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    local log_file="${_DB_LOG_DIR}/devbridge_host_${tunnel_id}.log"
    devbridge host "$tunnel_id" </dev/null > "$log_file" 2>&1 &
    local pid=$!
    local i url
    for i in $(seq 1 15); do
        if grep -q "Tunnel URL:" "$log_file" 2>/dev/null; then
            url=$(grep -oP 'Tunnel URL:\s+\K\S+' "$log_file" | head -1)
            # 统一输出到 stdout，带标签格式，避免 stdout/stderr 混流
            echo "PID: $pid"
            echo "Tunnel URL: $url"
            return 0
        fi
        if grep -q "Connection lost" "$log_file" 2>/dev/null; then
            _db_err "ERROR: host connection failed"
            tail -5 "$log_file" >&2
            return 1
        fi
        sleep 1
    done
    _db_err "ERROR: timeout waiting for tunnel URL (15s)"
    echo "PID: $pid"
    return 1
}

db_connect() {
    local tunnel_id="$1"
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    local log_file="${_DB_LOG_DIR}/devbridge_connect_${tunnel_id}.log"
    devbridge connect "$tunnel_id" </dev/null > "$log_file" 2>&1 &
    local pid=$!
    echo "$pid"
}

db_tunnel_url() {
    local tunnel_id="$1"
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    local log_file="${_DB_LOG_DIR}/devbridge_host_${tunnel_id}.log"
    if [ -f "$log_file" ]; then
        local url
        url=$(grep -oP 'Tunnel URL:\s+\K\S+' "$log_file" | head -1)
        if [ -n "$url" ]; then
            echo "$url"
            return 0
        fi
    fi
    _db_err "ERROR: Tunnel URL not found. Start hosting first with db_host."
    return 1
}

db_processes() {
    ps aux | grep -E "devbridge (host|connect)" | grep -v grep
}

db_process_stop() {
    local pid="$1"
    case "$pid" in
        ''|*[!0-9]*) _db_err "ERROR: invalid PID"; return 2 ;;
    esac
    if kill "$pid" 2>/dev/null; then
        echo "Process $pid stopped"
        return 0
    else
        _db_err "ERROR: Failed to stop process $pid"
        return 1
    fi
}

db_process_logs() {
    local pid="$1"
    case "$pid" in
        ''|*[!0-9]*) _db_err "ERROR: invalid PID"; return 2 ;;
    esac
    local tunnel_id
    tunnel_id=$(ps -p "$pid" -o args= 2>/dev/null | grep -oP 'devbridge (host|connect) \K\S+')
    if [ -n "$tunnel_id" ] && _db_valid_tunnel_id "$tunnel_id"; then
        local log_file="${_DB_LOG_DIR}/devbridge_host_${tunnel_id}.log"
        [ -f "$log_file" ] && cat "$log_file" && return 0
        log_file="${_DB_LOG_DIR}/devbridge_connect_${tunnel_id}.log"
        [ -f "$log_file" ] && cat "$log_file" && return 0
    fi
    _db_err "ERROR: No logs found for PID $pid"
    return 1
}

# db_host_bg <tunnelId> [logfile] — 后台运行 host 并立即返回 PID。
# 直接使用 devbridge 命令 + shell 后台作业；stdin 接 /dev/null，避免占用终端。
db_host_bg() {
    local tunnel_id="$1"
    local log="${2:-/tmp/devbridge-host.log}"
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    _db_safe_value "$log" || { _db_err "ERROR: invalid log path"; return 2; }
    devbridge host "$tunnel_id" </dev/null >>"$log" 2>&1 &
    echo "db_host backgrounded: pid=$!, log=$log"
}

db_list() {
    # v0.2.x 已移除 --json; 若用户请求 --json 则提示
    if [ "${1:-}" = "--json" ]; then
        local jf
        jf=$(_db_json_flag "list")
        if [ -n "$jf" ]; then
            _db_exec_retry "list" devbridge list "$jf"
        else
            _db_err "WARN: 当前 CLI 版本 (v0.2.x) 已移除 list --json，返回文本表格。"
            _db_exec_retry "list" devbridge list
        fi
    else
        _db_exec_retry "list" devbridge list
    fi
}

db_show() {
    local tunnel_id="$1"
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    _db_exec_retry "show" devbridge show "$tunnel_id"
}

db_delete() {
    local tunnel_id="$1"; shift || true
    local assume_yes=0
    while [ $# -gt 0 ]; do
        case "$1" in
            -y|--yes) assume_yes=1; shift ;;
            *) shift ;;
        esac
    done
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    if ! _db_confirm "delete tunnel ${tunnel_id} and all of its ports" "$assume_yes"; then
        _db_err "ERROR: deletion not confirmed."
        return 3
    fi
    _db_exec_retry "delete" devbridge delete "$tunnel_id"
}

db_delete_all() {
    local assume_yes=0
    while [ $# -gt 0 ]; do
        case "$1" in
            -y|--yes) assume_yes=1; shift ;;
            *) shift ;;
        esac
    done
    # 二次确认：必须输入固定短语，或显式 --yes
    if ! _db_confirm_phrase "delete-all" "$assume_yes"; then
        _db_err "ERROR: delete-all not confirmed."
        return 3
    fi
    _db_exec_retry "delete-all" devbridge delete-all
}

db_port_list() {
    local tunnel_id="$1"
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    _db_exec_retry "port list" devbridge port list "$tunnel_id"
}

db_limits() { _db_exec_retry "limits" devbridge limits; }

db_echo() { _db_exec_retry "echo" devbridge echo "$@"; }

db_ping() {
    if [ $# -eq 0 ]; then
        _db_err "ERROR: db_ping 需要 URI 参数，例如: db_ping https://<tunnelId>.<clusterId>.myhuaweicloud.com"
        return 1
    fi
    local uri="$1"; shift
    _db_safe_value "$uri" || { _db_err "ERROR: invalid URI"; return 2; }
    # devbridge ping 是持续循环命令（默认 interval 1s），直接调用会在脚本中永久挂起。
    # 默认限制 3 秒做一次性探测；DB_PING_SECONDS=0 时直通（持续观测用）。
    local secs="${DB_PING_SECONDS:-3}"
    if command -v timeout >/dev/null 2>&1 && [ "$secs" != "0" ]; then
        timeout "$secs" devbridge ping "$uri" "$@" 2>&1
        local rc=$?
        if [ "$rc" -eq 124 ]; then
            _db_err "[db_ping] 已完成 ${secs}s 探测（timeout 正常结束）"
            return 0
        fi
        return "$rc"
    fi
    _db_exec_retry "ping" devbridge ping "$uri" "$@"
}
db_version()     { devbridge version; }
db_auth_status() { devbridge auth status; }
db_auth_login()  { devbridge auth login "$@"; }

db_update() {
    local tunnel_id="$1"; shift || true
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    local -a cmd=(devbridge update "$tunnel_id")
    while [ $# -gt 0 ]; do
        case "$1" in
            -n)
                if ! _db_valid_name "${2:-}"; then _db_err "ERROR: invalid new name"; return 2; fi
                cmd+=(-n "$2"); if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
            -d)
                if ! _db_safe_value "${2:-}"; then _db_err "ERROR: invalid description"; return 2; fi
                cmd+=(-d "$2"); if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
            -e)
                case "${2:-}" in ''|*[!0-9]*) _db_err "ERROR: invalid expiration"; return 2 ;; esac
                if [ "$2" -lt 1 ] || [ "$2" -gt 720 ]; then
                    _db_err "ERROR: expiration must be between 1 and 720 hours"; return 2
                fi
                cmd+=(-e "$2"); if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
            *) shift ;;
        esac
    done
    _db_exec_retry "update" "${cmd[@]}"
}

db_port_delete() {
    local tunnel_id="$1"; shift || true
    local port="" assume_yes=0
    while [ $# -gt 0 ]; do
        case "$1" in
            -p) port="${2:-}"; if [ $# -ge 2 ]; then shift 2; else shift; fi ;;
            -y|--yes) assume_yes=1; shift ;;
            *)  shift ;;
        esac
    done
    _db_valid_tunnel_id "$tunnel_id" || { _db_err "ERROR: invalid tunnel id"; return 2; }
    _db_valid_port "$port" || { _db_err "ERROR: port must be an integer between 1 and 65535"; return 2; }
    if ! _db_confirm "delete port ${port} from tunnel ${tunnel_id}" "$assume_yes"; then
        _db_err "ERROR: deletion not confirmed."
        return 3
    fi
    local pf
    pf=$(_db_port_flag "port delete")
    if [ -n "$pf" ]; then
        _db_exec_retry "port delete" devbridge port delete "$tunnel_id" "$pf" "$port"
    else
        _db_exec_retry "port delete" devbridge port delete "$tunnel_id" -p "$port"
    fi
}
