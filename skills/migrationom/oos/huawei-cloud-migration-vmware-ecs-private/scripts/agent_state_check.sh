#!/bin/bash
# ================================================================
# agent_state_check.sh — SMS Agent 状态检测/清理/配置/启动
#
# 用法:
#   bash agent_state_check.sh check                     # 检测状态
#   bash agent_state_check.sh clean [target_dir]         # 清理agent
#   bash agent_state_check.sh config <dir> <region> [proxy_ip]  # 写配置
#   bash agent_state_check.sh start <dir> <ak> <sk> <region> [password]  # 启动
#
# check 输出格式 (KEY=VALUE):
#   STATE=NO_PACKAGE|RUNNING|INSTALLED_NOT_CONFIGURED|INSTALLED_CONFIGURED
#   AGENT_DIR=/opt/SMS-Agent  (或空)
#   ALL_DIRS=/opt/SMS-Agent,/tmp/SMS-Agent  (所有找到的目录)
#   VERSION=26.6.0  (或空)
#   PROC_COUNT=1  (linuxmain进程数)
#   PROC_PID=12345
#   CONFIG_COMPLETE=yes|no
#   DOMAIN=sms.cn-north-1.myhuaweicloud.com
#   CONF_EXISTS=yes|no  (agent_conf.json)
#   AUTH_ENABLE=yes|no  (auth.cfg enable=true)
#   BINARY_OK=yes|no    (linuxmain可执行)
# ================================================================

# Agent 可能存在的目录
AGENT_DIRS=("/opt/SMS-Agent" "/tmp/SMS-Agent" "/usr/local/sms-agent" "/SMSAgent")

# ─── check 模式 ───
do_check() {
    local found_dir=""
    local all_dirs=""
    local version=""
    local proc_count=0
    local proc_pid=""
    local config_complete="no"
    local domain=""
    local conf_exists="no"
    local auth_enable="no"
    local binary_ok="no"

    # 1. 检查进程 (linuxmain 是核心进程)
    proc_count=$(pgrep -x linuxmain 2>/dev/null | wc -l)
    proc_count=$(echo "$proc_count" | tr -d '[:space:]')
    if [ "$proc_count" -gt 0 ] 2>/dev/null; then
        proc_pid=$(pgrep -x linuxmain 2>/dev/null | head -1)
    fi

    # 2. 查找 agent 目录
    for dir in "${AGENT_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            if [ -n "$all_dirs" ]; then
                all_dirs="$all_dirs,$dir"
            else
                all_dirs="$dir"
            fi
            if [ -z "$found_dir" ]; then
                found_dir="$dir"
            fi
        fi
    done

    # 3. 读取版本 (优先使用找到的第一个目录)
    if [ -n "$found_dir" ]; then
        if [ -f "$found_dir/version" ]; then
            version=$(cat "$found_dir/version" 2>/dev/null | tail -1 | tr -d '[:space:]')
        fi
        # 也检查 agent/version 子目录
        if [ -z "$version" ] && [ -f "$found_dir/agent/version" ]; then
            version=$(cat "$found_dir/agent/version" 2>/dev/null | tail -1 | tr -d '[:space:]')
        fi
    fi

    # 4. 检查配置完整性
    if [ -n "$found_dir" ]; then
        # sms_domain
        if [ -f "$found_dir/config/sms_domain.txt" ]; then
            domain=$(cat "$found_dir/config/sms_domain.txt" 2>/dev/null | tr -d '[:space:]')
        fi

        # agent_conf.json
        if [ -f "$found_dir/agent_conf.json" ]; then
            conf_exists="yes"
        fi

        # auth.cfg
        local auth_cfg="$found_dir/agent/config/auth.cfg"
        if [ -f "$auth_cfg" ]; then
            if grep -q "enable.*=.*true" "$auth_cfg" 2>/dev/null; then
                auth_enable="yes"
            fi
        fi

        # linuxmain 二进制
        local linuxmain_path=""
        if [ -x "$found_dir/agent/linuxmain" ]; then
            linuxmain_path="$found_dir/agent/linuxmain"
            binary_ok="yes"
        elif [ -x "$found_dir/linuxmain" ]; then
            linuxmain_path="$found_dir/linuxmain"
            binary_ok="yes"
        fi
    fi

    # 5. 判定状态
    local state="NO_PACKAGE"
    if [ -z "$found_dir" ] && [ "$proc_count" -eq 0 ] 2>/dev/null; then
        state="NO_PACKAGE"
    elif [ "$proc_count" -gt 0 ] 2>/dev/null; then
        state="RUNNING"
    elif [ -n "$found_dir" ]; then
        # 有目录但进程没跑
        # config_complete 判定: sms_domain + auth.cfg + binary (agent_conf.json是运行时产物, 不要求)
        if [ -n "$domain" ] && [ "$auth_enable" = "yes" ] && [ "$binary_ok" = "yes" ]; then
            state="INSTALLED_CONFIGURED"
            config_complete="yes"
        else
            state="INSTALLED_NOT_CONFIGURED"
            config_complete="no"
        fi
    fi

    # 6. 输出 KEY=VALUE
    echo "STATE=$state"
    echo "AGENT_DIR=$found_dir"
    echo "ALL_DIRS=$all_dirs"
    echo "VERSION=$version"
    echo "PROC_COUNT=$proc_count"
    echo "PROC_PID=$proc_pid"
    echo "CONFIG_COMPLETE=$config_complete"
    echo "DOMAIN=$domain"
    echo "CONF_EXISTS=$conf_exists"
    echo "AUTH_ENABLE=$auth_enable"
    echo "BINARY_OK=$binary_ok"
}

# ─── clean 模式 ───
do_clean() {
    local target_dir="$1"

    # 杀进程
    pkill -x linuxmain 2>/dev/null
    sleep 1
    # 确认杀掉
    local remain=$(pgrep -x linuxmain 2>/dev/null | wc -l)
    remain=$(echo "$remain" | tr -d '[:space:]')
    if [ "$remain" -gt 0 ] 2>/dev/null; then
        pkill -9 -x linuxmain 2>/dev/null
        sleep 1
    fi

    # 删除目录
    if [ -n "$target_dir" ]; then
        rm -rf "$target_dir" 2>/dev/null
    else
        for dir in "${AGENT_DIRS[@]}"; do
            rm -rf "$dir" 2>/dev/null
        done
    fi

    # 清理临时包
    rm -f /opt/sms-agent-linux.tar.gz /tmp/sms-agent-linux.tar.gz 2>/dev/null

    echo "CLEAN_DONE=yes"
}

# ─── config 模式 ───
do_config() {
    local agent_dir="$1"
    local region="$2"
    local proxy_ip="$3"

    if [ -z "$agent_dir" ] || [ -z "$region" ]; then
        echo "CONFIG_DONE=no"
        echo "ERROR=missing agent_dir or region"
        return 1
    fi

    local sms_domain="sms.${region}.myhuaweicloud.com"

    # sms_domain 配置
    mkdir -p "$agent_dir/config"
    echo "$sms_domain" > "$agent_dir/config/sms_domain.txt"
    chmod 640 "$agent_dir/config/sms_domain.txt"

    # auth.cfg (私网代理)
    if [ -n "$proxy_ip" ]; then
        mkdir -p "$agent_dir/agent/config"
        echo "enable = true" > "$agent_dir/agent/config/auth.cfg"
        echo "proxy_addr = http://${proxy_ip}" >> "$agent_dir/agent/config/auth.cfg"
        chmod 640 "$agent_dir/agent/config/auth.cfg"
    fi

    # 确保二进制就位
    if [ -d "$agent_dir/agent" ]; then
        cd "$agent_dir/agent/"
        if [ ! -e linuxmain ]; then
            if [ -x aarch64/linuxmain ]; then
                cp -f aarch64/linuxmain .
            elif [ -x x64/linuxmain ]; then
                cp -f x64/linuxmain .
            fi
        fi
        if [ ! -e libsrcAgent.so ]; then
            if [ -f ioblock/x64/libsrcAgent.so ]; then
                cp -f ioblock/x64/libsrcAgent.so .
            elif [ -f ioblock/aarch64/libsrcAgent.so ]; then
                cp -f ioblock/aarch64/libsrcAgent.so .
            fi
        fi
        chmod +x linuxmain 2>/dev/null
    fi

    echo "CONFIG_DONE=yes"
}

# ─── start 模式 ───
do_start() {
    local agent_dir="$1"
    local ak="$2"
    local sk="$3"
    local region="$4"
    local password="$5"

    if [ -z "$agent_dir" ] || [ -z "$ak" ] || [ -z "$sk" ] || [ -z "$region" ]; then
        echo "START_RESULT=failed"
        echo "ERROR=missing required args"
        return 1
    fi

    local sms_domain="sms.${region}.myhuaweicloud.com"
    local linuxmain_input="${ak} ${sk} ${sms_domain} ${password}"

    # 杀掉已有进程
    pkill -x linuxmain 2>/dev/null
    sleep 1

    # 设置 LD_LIBRARY_PATH 并启动
    cd "$agent_dir/agent/" 2>/dev/null || {
        echo "START_RESULT=failed"
        echo "ERROR=cannot cd to $agent_dir/agent/"
        return 1
    }

    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${agent_dir}/agent/lib"
    nohup ./linuxmain 0 <<< "$linuxmain_input" > /dev/null 2>&1 &

    # 等待并验证
    sleep 3
    local count=$(pgrep -x linuxmain 2>/dev/null | wc -l)
    count=$(echo "$count" | tr -d '[:space:]')

    if [ "$count" -gt 0 ] 2>/dev/null; then
        echo "START_RESULT=success"
        echo "PROC_PID=$(pgrep -x linuxmain 2>/dev/null | head -1)"
    else
        # 再等一下
        sleep 5
        count=$(pgrep -x linuxmain 2>/dev/null | wc -l)
        count=$(echo "$count" | tr -d '[:space:]')
        if [ "$count" -gt 0 ] 2>/dev/null; then
            echo "START_RESULT=success"
            echo "PROC_PID=$(pgrep -x linuxmain 2>/dev/null | head -1)"
        else
            echo "START_RESULT=failed"
            echo "ERROR=linuxmain not running after start"
        fi
    fi
}

# ─── 主入口 ───
main() {
    local mode="$1"
    shift

    case "$mode" in
        check)
            do_check
            ;;
        clean)
            do_clean "$@"
            ;;
        config)
            do_config "$@"
            ;;
        start)
            do_start "$@"
            ;;
        *)
            echo "Usage: $0 {check|clean|config|start} [args...]"
            echo "  check                              - detect agent state"
            echo "  clean [target_dir]                 - kill + delete agent"
            echo "  config <dir> <region> [proxy_ip]   - write config files"
            echo "  start <dir> <ak> <sk> <region> [password] - start agent"
            exit 1
            ;;
    esac
}

main "$@"
