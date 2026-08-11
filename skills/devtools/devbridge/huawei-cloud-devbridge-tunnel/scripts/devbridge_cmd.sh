#!/bin/bash
# devbridge_cmd.sh — DevBridge CLI 动态命令适配层
#
# 通过解析 devbridge <command> --help 输出，自动发现当前 CLI 版本
# 实际支持哪些 flag，从而适配不同版本之间的参数差异。
# 执行后如果报错，自动解析 cobra 错误信息，尝试恢复并重试。
#
# 用法: source devbridge_cmd.sh，然后调用 db_* 系列函数

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
        protocol)       echo "http"; return 0 ;;
        name|tunnel-name) echo "dev-tunnel"; return 0 ;;
        description|desc) echo "dev-tunnel"; return 0 ;;
        expiration|expiry|ttl) echo "8"; return 0 ;;
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
# 对外封装函数
# ============================================================================

db_init() {
    if ! command -v devbridge &>/dev/null; then
        echo "ERROR: devbridge CLI not found. Please install it first."
        echo "Run: curl -fsSL https://res-hd.hc-cdn.cn/sharedata/hdspace/devbridge/install.sh | bash"
        return 1
    fi
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
    _db_exec_retry "create" "$cmd"
}

db_port_create() {
    local tunnel_id="$1"; shift
    local port="" protocol="" anon="allow"
    while [ $# -gt 0 ]; do
        case "$1" in
            -p)         port="$2"; shift 2;;
            --protocol) protocol="$2"; shift 2;;
            --anon)     anon="$2"; shift 2;;
            *)          shift;;
        esac
    done
    local port_flag=$(_db_port_flag "port create")
    local anon_flag=""
    if [ "$anon" = "allow" ]; then
        anon_flag=$(_db_anon_allow_flag "port create")
    else
        anon_flag=$(_db_anon_deny_flag "port create")
    fi
    local cmd="devbridge port create $tunnel_id"
    if [ -n "$port_flag" ] && [ -n "$port" ]; then cmd+=" $port_flag $port"; fi
    if [ -n "$protocol" ] && _db_has_flag "port create" "--protocol"; then cmd+=" --protocol $protocol"; fi
    if [ -n "$anon_flag" ]; then cmd+=" $anon_flag"; fi
    _db_exec_retry "port create" "$cmd"
}

db_host() {
    _db_exec_retry "host" "devbridge host $1"
}

db_connect() {
    _db_exec_retry "connect" "devbridge connect $1"
}

db_list() {
    if [ "$1" = "--json" ]; then
        local jf=$(_db_json_flag "list")
        if [ -n "$jf" ]; then
            _db_exec_retry "list" "devbridge list $jf"
        else
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
