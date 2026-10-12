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

# ============================================================================
# 安装渠道 (官方)
#   GitCode: https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh
#   注意: GitCode 官方仓库名拼写就是 "devbrige"（少一个 d），非笔误，请勿"修正"。
#   GitHub:  https://github.com/huaweicloud/devspace-devbridge/releases/latest/download/install.sh
#   OBS:     https://tools-artifact.developer.huaweicloud.com/sharedata/devbridge/install.sh
# 无终端环境请使用 -s (silent) 模式，避免 /dev/tty 交互提示失败。
# ============================================================================
DEVBRIDGE_INSTALL_URL="https://gitcode.com/CloudDeveloperDepartment/devbrige/releases/download/latest/install.sh"

# 日志和认证
_DB_LOG_DIR="/tmp"
_DB_APIKEY_URL="https://devstation.connect.huaweicloud.com/space/devbridge/apikey"
# OBS 渠道提供最新 v0.2.x；旧渠道 res-hd.hc-cdn.cn 只有 v0.1.x（域名已迁移，不可用）
_DB_INSTALL_URL_OBS="https://tools-artifact.developer.huaweicloud.com/sharedata/devbridge/install.sh"

# ============================================================================
# 内部工具函数 — flag 检测
# ============================================================================

_db_has_flag() {
    local subcmd="$1"
    local flag="$2"
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

# ============================================================================
# 内部工具函数 — 错误解析与自动恢复
# ============================================================================

# 从 help 输出中提取 flag 的默认值
_db_flag_default() {
    echo "$1" | grep -- "$2" | grep -oP '\(default "\K[^"]+' | head -1
}

# 从 help 输出中提取 flag 的第一个可选值
_db_flag_options() {
    echo "$1" | grep -- "$2" | grep -oP '\(options: \K[^)]+' | head -1 | cut -d/ -f1
}

# 从 help 输出中提取 flag 的类型
_db_flag_type() {
    local line
    line=$(echo "$1" | grep -- "$2" | head -1)
    if echo "$line" | grep -q ' int '; then echo "int"
    elif echo "$line" | grep -q ' string '; then echo "string"
    elif echo "$line" | grep -q ' bool '; then echo "bool"
    elif echo "$line" | grep -q ' uints '; then echo "uints"
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

    for f in $(echo "$help_output" | grep -oP '\-\-\K[a-zA-Z0-9-]+' | sort -u); do
        # 去掉 "port-" 前缀差异后比较
        local cf="${f#port-}" cn="${flag_name#port-}"
        if [ "$cf" = "$cn" ]; then echo "--$f"; return 0; fi
    done

    # 子串匹配
    for f in $(echo "$help_output" | grep -oP '\-\-\K[a-zA-Z0-9-]+' | sort -u); do
        if echo "$f" | grep -q "$flag_name" || echo "$flag_name" | grep -q "$f"; then
            echo "--$f"; return 0
        fi
    done
}

# 核心: 带自动恢复的命令执行器
_db_exec_retry() {
    local subcmd="$1"
    local cmd="$2"

    # 第一次执行
    local output rc
    output=$(eval "$cmd" 2>&1)
    rc=$?

    if [ $rc -eq 0 ]; then
        echo "$output"
        return 0
    fi

    # ---- 失败，开始错误解析与恢复 ----

    # 错误类型 1: required flag(s) "xxx" not set
    if echo "$output" | grep -q 'required flag(s)'; then
        local missing
        missing=$(echo "$output" | grep -oP '"\K[^"]+' | head -1)
        if [ -n "$missing" ]; then
            local guessed
            guessed=$(_db_guess_flag_value "$output" "$missing")
            if [ -n "$guessed" ]; then
                local retry_output retry_rc
                retry_output=$(eval "$cmd --$missing $guessed" 2>&1)
                retry_rc=$?
                if [ $retry_rc -eq 0 ]; then echo "$retry_output"; return 0; fi
                echo "$retry_output" >&2; return $retry_rc
            else
                echo "ERROR: 新必填参数 '--$missing' 无法自动适配，请运行 'devbridge $subcmd --help' 查看选项。" >&2
                echo "$output" >&2; return $rc
            fi
        fi
    fi

    # 错误类型 2: unknown flag: --xxx
    if echo "$output" | grep -q 'unknown flag'; then
        local bad_flag
        bad_flag=$(echo "$output" | grep -oP 'unknown flag: \K\S+' | head -1)
        if [ -n "$bad_flag" ]; then
            # 先找相似 flag
            local similar
            similar=$(_db_find_similar_flag "$output" "${bad_flag#--}")
            if [ -n "$similar" ] && [ "$similar" != "$bad_flag" ]; then
                local retry_output retry_rc
                retry_output=$(eval "${cmd//$bad_flag/$similar}" 2>&1)
                retry_rc=$?
                if [ $retry_rc -eq 0 ]; then echo "$retry_output"; return 0; fi
            fi
            # 找不到相似 flag，去掉该 flag 重试
            local retry_output retry_rc
            retry_output=$(eval "${cmd//$bad_flag /}" 2>&1)
            retry_rc=$?
            if [ $retry_rc -eq 0 ]; then echo "$retry_output"; return 0; fi
            echo "$retry_output" >&2; return $retry_rc
        fi
    fi

    # 错误类型 3: unknown command "xxx"
    if echo "$output" | grep -q 'unknown command'; then
        local bad_cmd
        bad_cmd=$(echo "$output" | grep -oP 'unknown command "\K[^"]+' | head -1)
        if [ -n "$bad_cmd" ]; then
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
                # 子串匹配或同义词匹配
                if [ "$c" = "$synonym" ] || \
                   echo "$c" | grep -q "$bad_cmd" || \
                   echo "$bad_cmd" | grep -q "$c"; then
                    local retry_output retry_rc
                    retry_output=$(eval "${cmd//$bad_cmd/$c}" 2>&1)
                    retry_rc=$?
                    if [ $retry_rc -eq 0 ]; then echo "$retry_output"; return 0; fi
                fi
            done
        fi
    fi

    # 无法自动恢复
    echo "$output" >&2
    return $rc
}

# ============================================================================
# 内部工具函数 — CLI 安装与认证
# ============================================================================

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
        echo "ERROR: Downloaded file is not a valid shell script" >&2
        rm -f "$tmpfile"
        return 1
    fi
    bash "$tmpfile" -s 2>&1
    local rc=$?
    rm -f "$tmpfile"
    return $rc
}

_db_install_cli() {
    echo "Installing DevBridge CLI..." >&2
    _db_download_and_run "$_DB_INSTALL_URL_OBS" \
        || _db_download_and_run "$DEVBRIDGE_INSTALL_URL"
    export PATH="$HOME/.huawei/bin:$PATH"
    if ! command -v devbridge &>/dev/null; then
        echo "ERROR: devbridge CLI installation failed" >&2
        return 1
    fi
}

_db_ensure_cli_version() {
    local ver raw_output
    raw_output=$(devbridge version 2>&1)
    # 透传 CLI 的新版本提示（第一行是版本号，其余输出透传到 stderr）
    echo "$raw_output" | tail -n +2 | grep -v '^$' >&2
    ver=$(echo "$raw_output" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [ -z "$ver" ]; then ver="0.0.0"; fi
    local major minor
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "$major" -lt 1 ] && [ "$minor" -lt 2 ]; then
        echo "Detected v$ver (old domain, cannot connect). Upgrading..." >&2
        _db_download_and_run "$_DB_INSTALL_URL_OBS"
        raw_output=$(devbridge version 2>&1)
        echo "$raw_output" | tail -n +2 | grep -v '^$' >&2
        ver=$(echo "$raw_output" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        echo "Upgraded to v$ver" >&2
    fi
}

_db_ensure_auth() {
    local auth
    auth=$(devbridge auth status 2>&1)
    if echo "$auth" | grep -qiE "^(Logged|logged) in"; then
        # "Logged in" 状态可能来自过期凭证的残留，用轻量 API 调用验证
        if devbridge list >/dev/null 2>&1; then
            return 0
        fi
        # list 失败说明凭证过期，继续往下走重新登录
    fi
    local api_key="${DEVBRIDGE_API_KEY:-${HW_API_KEY:-${JOB_ENV_HW_DEVBRIDGE_API_KEY:-}}}"
    if [ -n "$api_key" ]; then
        devbridge auth login --api-key "$api_key" >/dev/null 2>&1
        # 登录后同样验证凭证有效性
        if devbridge list >/dev/null 2>&1; then
            return 0
        fi
    fi
    echo "ERROR: Not logged in. Set DEVBRIDGE_API_KEY or HW_API_KEY env var, or run:" >&2
    echo "  devbridge auth login --api-key YOUR_API_KEY" >&2
    echo "  Get API key: $_DB_APIKEY_URL" >&2
    return 1
}

# ============================================================================
# 对外封装函数
# ============================================================================

db_init() {
    # 自动发现并 source job 环境的 hw-env 文件（获取 JOB_ENV_HW_DEVBRIDGE_API_KEY 等）
    if [ -d /root/job-envs/sandboxes ]; then
        for _db_envf in /root/job-envs/sandboxes/*-hw-env; do
            [ -f "$_db_envf" ] && . "$_db_envf" 2>/dev/null
        done
        unset _db_envf
    fi
    if ! command -v devbridge &>/dev/null; then
        _db_install_cli || return 1
    fi
    _db_ensure_cli_version || return 1
    _db_ensure_auth || return 1
    return 0
}

db_create() {
    local name="$1"; shift
    local desc="" expiration=""
    while [ $# -gt 0 ]; do
        case "$1" in
            -d) desc="$2"; shift 2;;
            -e) expiration="$2"; shift 2;;
            *)  shift;;
        esac
    done
    local cmd="devbridge create \"$name\""
    if [ -n "$desc" ] && _db_has_flag "create" "-d"; then
        cmd+=" -d \"$desc\""
    fi
    if [ -n "$expiration" ] && _db_has_flag "create" "-e"; then
        cmd+=" -e $expiration"
    fi
    local output rc
    output=$(_db_exec_retry "create" "$cmd" 2>&1)
    rc=$?
    if [ $rc -ne 0 ]; then
        echo "$output" >&2
        return $rc
    fi
    # Extract and return just the tunnel ID
    echo "$output" | grep -oP 'Tunnel ID:\s+\K\S+' | head -1
}

db_port_create() {
    local tunnel_id="$1"; shift
    local port="" protocol="" anon=""
    while [ $# -gt 0 ]; do
        case "$1" in
            -p)         port="$2"; shift 2;;
            --protocol) protocol="$2"; shift 2;;
            --anon)     anon="$2"; shift 2;;
            -a|--allow-anonymous) anon="allow"; shift;;
            --deny-anonymous)     anon="deny"; shift;;
            *)          shift;;
        esac
    done
    local port_flag=$(_db_port_flag "port create")
    local anon_flag=""
    if [ -n "$anon" ]; then
        if [ "$anon" = "allow" ]; then
            anon_flag=$(_db_anon_allow_flag "port create")
        else
            anon_flag=$(_db_anon_deny_flag "port create")
        fi
    fi
    # 默认不传匿名 flag: v0.2.x 端口默认为禁止匿名访问 (deny)
    local cmd="devbridge port create $tunnel_id"
    if [ -n "$port_flag" ] && [ -n "$port" ]; then cmd+=" $port_flag $port"; fi
    if [ -n "$protocol" ] && _db_has_flag "port create" "--protocol"; then cmd+=" --protocol $protocol"; fi
    if [ -n "$anon_flag" ]; then cmd+=" $anon_flag"; fi
    _db_exec_retry "port create" "$cmd"
}

db_host() {
    local tunnel_id="$1"
    local log_file="${_DB_LOG_DIR}/devbridge_host_${tunnel_id}.log"
    nohup devbridge host "$tunnel_id" > "$log_file" 2>&1 &
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
            echo "ERROR: host connection failed" >&2
            tail -5 "$log_file" >&2
            return 1
        fi
        sleep 1
    done
    echo "ERROR: timeout waiting for tunnel URL (15s)" >&2
    echo "PID: $pid"
    return 1
}

db_connect() {
    local tunnel_id="$1"
    local log_file="${_DB_LOG_DIR}/devbridge_connect_${tunnel_id}.log"
    nohup devbridge connect "$tunnel_id" > "$log_file" 2>&1 &
    local pid=$!
    echo "$pid"
}

db_tunnel_url() {
    local tunnel_id="$1"
    local log_file="${_DB_LOG_DIR}/devbridge_host_${tunnel_id}.log"
    if [ -f "$log_file" ]; then
        local url
        url=$(grep -oP 'Tunnel URL:\s+\K\S+' "$log_file" | head -1)
        if [ -n "$url" ]; then
            echo "$url"
            return 0
        fi
    fi
    echo "ERROR: Tunnel URL not found. Start hosting first with db_host." >&2
    return 1
}

db_processes() {
    ps aux | grep -E "devbridge (host|connect)" | grep -v grep
}

db_process_stop() {
    local pid="$1"
    if kill "$pid" 2>/dev/null; then
        echo "Process $pid stopped"
        return 0
    else
        echo "ERROR: Failed to stop process $pid" >&2
        return 1
    fi
}

db_process_logs() {
    local pid="$1"
    local tunnel_id
    tunnel_id=$(ps -p "$pid" -o args= 2>/dev/null | grep -oP 'devbridge (host|connect) \K\S+')
    if [ -n "$tunnel_id" ]; then
        local log_file="${_DB_LOG_DIR}/devbridge_host_${tunnel_id}.log"
        [ -f "$log_file" ] && cat "$log_file" && return 0
        log_file="${_DB_LOG_DIR}/devbridge_connect_${tunnel_id}.log"
        [ -f "$log_file" ] && cat "$log_file" && return 0
    fi
    echo "ERROR: No logs found for PID $pid" >&2
    return 1
}

# db_host_bg <tunnelId> [logfile] — 后台运行 db_host。
# 不能写成 `nohup db_host ...`：db_host 是 shell 函数，nohup 是外部命令，
# exec 时找不到函数（No such file or directory）。这里用 nohup bash -c
# 在子 shell 里重新 source 本脚本再调用 db_host，既保留函数上下文又可抗 HUP。
db_host_bg() {
    local tunnel_id="$1"
    local log="${2:-/tmp/devbridge-host.log}"
    if [ -z "$tunnel_id" ]; then
        echo "ERROR: db_host_bg 需要 tunnel-id 参数" >&2
        return 1
    fi
    local self
    self="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/devbridge_cmd.sh"
    local db_dir
    db_dir="$(dirname "$(command -v devbridge 2>/dev/null || echo "${HOME:-$(eval echo ~)}/.huawei/bin/devbridge")")"
    nohup bash -c "export PATH=\"$db_dir:\$PATH\"; source '$self'; db_host $tunnel_id" >"$log" 2>&1 &
    local pid=$!
    echo "db_host backgrounded: pid=$pid, log=$log"
}

db_list() {
    # v0.2.x 已移除 --json; 若用户请求 --json 则提示
    if [ "$1" = "--json" ]; then
        local jf=$(_db_json_flag "list")
        if [ -n "$jf" ]; then
            _db_exec_retry "list" "devbridge list $jf"
        else
            echo "WARN: 当前 CLI 版本 (v0.2.x) 已移除 list --json，返回文本表格。" >&2
            _db_exec_retry "list" "devbridge list"
        fi
    else
        _db_exec_retry "list" "devbridge list"
    fi
}

db_show()        { _db_exec_retry "show" "devbridge show $1"; }
db_delete()      { _db_exec_retry "delete" "devbridge delete $1"; }
db_delete_all()  { _db_exec_retry "delete-all" "devbridge delete-all"; }
db_port_list()   { _db_exec_retry "port list" "devbridge port list $1"; }
db_limits()      { _db_exec_retry "limits" "devbridge limits"; }
db_echo()        { _db_exec_retry "echo" "devbridge echo $*"; }
db_ping() {
    if [ $# -eq 0 ]; then
        echo "ERROR: db_ping 需要 URI 参数，例如: db_ping https://<tunnelId>.<clusterId>.myhuaweicloud.com" >&2
        return 1
    fi
    local uri="$1"; shift
    # devbridge ping 是持续循环命令（默认 interval 1s），直接调用会在脚本中永久挂起。
    # 默认限制 3 秒做一次性探测；DB_PING_SECONDS=0 时直通（持续观测用）。
    local secs="${DB_PING_SECONDS:-3}"
    if command -v timeout >/dev/null 2>&1 && [ "$secs" != "0" ]; then
        timeout "$secs" devbridge ping "$uri" "$@" 2>&1
        local rc=$?
        if [ "$rc" -eq 124 ]; then
            echo "[db_ping] 已完成 ${secs}s 探测（timeout 正常结束）" >&2
            return 0
        fi
        return "$rc"
    fi
    _db_exec_retry "ping" "devbridge ping \"$uri\" $*"
}
db_version()     { devbridge version; }
db_auth_status() { devbridge auth status; }
db_auth_login()  { devbridge auth login "$@"; }

db_update() {
    local tunnel_id="$1"; shift
    local cmd="devbridge update $tunnel_id"
    while [ $# -gt 0 ]; do
        case "$1" in
            -n) cmd+=" -n \"$2\""; shift 2;;
            -d) cmd+=" -d \"$2\""; shift 2;;
            -e) cmd+=" -e $2"; shift 2;;
            *)  shift;;
        esac
    done
    _db_exec_retry "update" "$cmd"
}

db_port_delete() {
    local tunnel_id="$1"; shift
    local port=""
    while [ $# -gt 0 ]; do
        case "$1" in
            -p) port="$2"; shift 2;;
            *)  shift;;
        esac
    done
    local pf=$(_db_port_flag "port delete")
    if [ -n "$pf" ] && [ -n "$port" ]; then
        _db_exec_retry "port delete" "devbridge port delete $tunnel_id $pf $port"
    else
        _db_exec_retry "port delete" "devbridge port delete $tunnel_id -p $port"
    fi
}