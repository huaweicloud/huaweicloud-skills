#!/bin/bash

# OpenClaw Gateway 管理日志目录配置
LOG_DIR="/var/log/openclaw"
LOG_FILE="$LOG_DIR/manage_operate.log"

# 校验日志目录/文件参数：仅允许固定路径，拒绝任何外部可控值
case "$LOG_FILE" in
	/var/log/openclaw/manage_operate.log) ;;
	*) echo "非法 LOG_FILE 路径: $LOG_FILE" >&2; exit 1 ;;
esac

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"
chmod 644 "$LOG_FILE"
# OpenClaw Gateway 管理脚本
# 集成停止、开启、状态查询、重启四个子能力
CMD_NAME=""
command_name() {
	if [ -d "/home/openclaw" ]; then
		export PNPM_HOME="/home/openclaw/.local/share/pnpm"
		export NVM_DIR="/home/openclaw/.nvm"
		ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/node /usr/local/bin/node
		ln -sf /home/openclaw/.nvm/versions/node/v22.22.1/bin/npm /usr/local/bin/npm
		CMD_NAME="/home/openclaw/.local/share/pnpm/openclaw"
	else
		ln -sf /root/.nvm/versions/node/v22.22.0/bin/node /usr/local/bin/node
		ln -sf /root/.nvm/versions/node/v22.22.0/bin/npm /usr/local/bin/npm
		CMD_NAME="/root/.local/share/pnpm/openclaw"
	fi
}

# 默认状态查询（与原脚本兼容）
default_status() {
	local operation_message="$1" # 接收操作消息参数
	local command_result="$2"   # 接收命令执行结果参数
	local result="success"
	if [ -z "$operation_message" ]; then
		operation_message=""
	fi
	if [ "$command_result" -ne 0 ]; then
		result="failed"
	fi
	command_name
        if [ -d "/home/openclaw" ]; then
            GATEWAY_STATUS_OUTPUT=$(sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus $CMD_NAME gateway status 2>&1)
        else
            GATEWAY_STATUS_OUTPUT=$($CMD_NAME gateway status 2>&1)
        fi
	QUERY_EXIT_CODE=$?
	NORMAL_KEYWORDS="Runtime: running|RPC probe: ok"
	IS_NORMAL=0
	if [ $QUERY_EXIT_CODE -ne 0 ]; then
		IS_NORMAL=1
	else
		KEYWORD_LIST=$NORMAL_KEYWORDS
		while [ -n "$KEYWORD_LIST" ]; do
			KEYWORD=${KEYWORD_LIST%%|*}
			if [ "$KEYWORD_LIST" = "$KEYWORD" ]; then
				KEYWORD_LIST=""
			else
				KEYWORD_LIST=${KEYWORD_LIST#*|}
			fi

			if echo "$GATEWAY_STATUS_OUTPUT" | grep -qi "$KEYWORD"; then
				IS_NORMAL=0
				break
			else
				IS_NORMAL=1
			fi
		done
	fi

	if [ $IS_NORMAL -eq 0 ]; then
		# 如果状态正常，优先显示操作结果的详细信息
		echo "{\"status\":\"normal\", \"message\":\"$operation_message\",\"result\":\"$result\"}"
		exit 0
	else
		echo "{\"status\":\"abnormal\", \"message\":\"$operation_message\",\"result\":\"$result\"}"
		exit 1
	fi
}

# 网关重启功能（与原脚本相同的逻辑）
gateway_restart() {
	local operation_message=""
	local command_result=""
	command_name
	if [ -d "/home/openclaw" ]; then
		operation_message=$(sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus $CMD_NAME gateway restart 2>&1)
		command_result=$?
	else
		operation_message=$($CMD_NAME gateway restart 2>&1)
		command_result=$?
	fi

	# 记录操作结果到日志
	if [ -n "$operation_message" ]; then
		echo "网关重启操作结果: $operation_message, 返回码: $command_result" >> "$LOG_FILE"
	fi

	# 启动后查询状态
	#sleep 2  # 等待启动完成
	default_status "$operation_message" "$command_result"
}

# 网关启动功能
gateway_start() {
	local operation_message=""
	local command_result=""
	command_name
	if [ -d "/home/openclaw" ]; then
		operation_message=$(sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus $CMD_NAME gateway start 2>&1)
		command_result=$?
	else
		operation_message=$($CMD_NAME gateway start 2>&1)
		command_result=$?
	fi

	# 记录操作结果到日志
	if [ -n "$operation_message" ]; then
		echo "网关启动操作结果: $operation_message, 返回码: $command_result" >> "$LOG_FILE"
	fi

	# 启动后查询状态
	#sleep 2  # 等待启动完成
	default_status "$operation_message" "$command_result"
}

# 网关停止功能
gateway_stop() {
	local operation_message=""
	local command_result=""
	command_name
	if [ -d "/home/openclaw" ]; then
		operation_message=$(sudo -i -u openclaw env DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus $CMD_NAME gateway stop 2>&1)
		command_result=$?
	else
		operation_message=$($CMD_NAME gateway stop 2>&1)
		command_result=$?
	fi

	# 记录操作结果到日志
	if [ -n "$operation_message" ]; then
		echo "网关停止操作结果: $operation_message, 返回码: $command_result" >> "$LOG_FILE"
	fi

	# 停止后查询状态
	#sleep 2  # 等待停止完成
	default_status "$operation_message" "$command_result"
}

# 显示帮助信息
show_help() {
	cat << EOF
OpenClaw Gateway 管理脚本

使用方法:
    $0 <command>

命令:
    stop     停止 OpenClaw Gateway 并查询状态
    start    启动 OpenClaw Gateway 并查询状态
    status   查询 OpenClaw Gateway 状态 (默认)
    restart  重启 OpenClaw Gateway 并查询状态
    help     显示帮助信息

示例:
    $0 stop          # 停止服务并检查状态
    $0 start         # 启动服务并检查状态
    $0 status        # 查询状态
    $0 restart       # 重启服务并检查状态
    $0 help          # 显示帮助

注意:
    - 脚本会自动检测环境并配置相应的命令路径
    - 停止、启动、重启操作完成后会自动查询状态
    - 状态检查使用与原脚本相同的逻辑和关键词匹配
    - 所有操作日志记录到 $LOG_FILE

EOF
}

# 主入口
case "${1:-status}" in
restart)
	echo "执行 OpenClaw Gateway 重启操作..." >> "$LOG_FILE" 2>&1
	gateway_restart
	;;
start)
	echo "执行 OpenClaw Gateway 启动操作..." >> "$LOG_FILE" 2>&1
	gateway_start
	;;
stop)
	echo "执行 OpenClaw Gateway 停止操作..." >> "$LOG_FILE" 2>&1
	gateway_stop
	;;
status)
	default_status
	;;
help |   --help | -h)
	show_help
	;;
*)
	echo "命令错误: $1"
	echo ""
	show_help
	exit 1
	;;
esac
