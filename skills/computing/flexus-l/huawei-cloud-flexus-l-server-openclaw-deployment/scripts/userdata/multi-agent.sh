#!/bin/bash

# 脚本功能：向 OpenClaw 配置文件添加或删除 agent 和对应的 binding
# 使用方法：$0 <action> <agent_id> [agent_name] [channel] [config_file]
# 批量删除：$0 delete <agent_id1> <agent_id2> ... [config_file]
# 示例：
# 添加 agent: $0 add bot3 Bot3 feishu /path/to/openclaw.json
# 删除单个 agent: $0 delete bot3 /path/to/openclaw.json
# 批量删除多个 agent: $0 delete bot3 bot4 bot5 /path/to/openclaw.json

# 检查 jq 是否安装
if ! command -v jq &>/dev/null; then
    echo "Installing jq..."
    sudo apt-get update -qq && sudo apt-get install -y -qq jq 2>/dev/null ||
        sudo yum install -y -q jq 2>/dev/null
    if ! command -v jq &>/dev/null; then
        echo "Error: Failed to install jq! Please install jq manually."
        exit 1
    fi
fi

CMD_NAME="openclaw"
HOME_PATH="/root"
if [ -d "/home/openclaw" ]; then
    HOME_PATH="/home/openclaw"
fi

DEFAULT_CONFIG=${HOME_PATH}/.openclaw/openclaw.json
WORKSPACE_BASE=${HOME_PATH}/.openclaw

# 检查参数
if [ $# -lt 2 ]; then
    echo "Usage: $0 <action> <agent_id> [agent_name] [channel] [config_file]"
    echo "Batch delete：$0 delete <agent_id1> <agent_id2> ... [config_file]"
    echo "Default config_file: $DEFAULT_CONFIG"
    exit 1
fi

ACTION=$1

if [ "$ACTION" = "add" ]; then
    if [ $# -lt 3 ]; then
        echo "Error: Missing agent_name for add action!"
        echo "Usage: $0 add <agent_id> <agent_name> [channel] [config_file]"
        exit 1
    fi
    AGENT_ID=$2
    AGENT_NAME=$3
    # 处理 channel 参数（可选，默认为 feishu）
    CHANNEL=${4:-"feishu"}
    # 处理 config_file 参数（可选）
    if [ $# -ge 5 ]; then
        CONFIG_FILE=$5
    else
        CONFIG_FILE="$DEFAULT_CONFIG"
    fi
elif [ "$ACTION" = "delete" ]; then
    if [ $# -lt 2 ]; then
        echo "Error: Missing agent_id for delete action!"
        echo "Usage: $0 delete <agent_id> [config_file]"
        echo "批量删除：$0 delete <agent_id1> <agent_id2> ... [config_file]"
        exit 1
    fi
    # 提取所有 agent_id 参数（排除最后一个可能是 config_file 的参数）
    if [[ "${!#}" == *.json ]]; then
        CONFIG_FILE=${!#}
        AGENT_IDS=(${@:2:$(($#-2))})
    else
        CONFIG_FILE="$DEFAULT_CONFIG"
        AGENT_IDS=(${@:2})
    fi
else
    echo "Error: Invalid action! Must be 'add' or 'delete'"
    exit 1
fi

CONFIG_FILE=$(echo "$CONFIG_FILE" | sed 's/\\/\//g')

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE not found!"
    exit 1
fi

# 确保默认 agent (main) 存在且在 agents.list 的第一个位置
DEFAULT_AGENT_ID="main"
DEFAULT_AGENT_EXISTS=$(jq ".agents.list[]? | select(.id == \"$DEFAULT_AGENT_ID\")" "$CONFIG_FILE")

if [ -z "$DEFAULT_AGENT_EXISTS" ]; then
    # 如果默认 agent 不存在，添加它
    # 设置工作目录
    DEFAULT_WORKSPACE="${HOME_PATH}/.openclaw/workspace"
    DEFAULT_AGENT_DIR="${HOME_PATH}/.openclaw/agents/main/agent"

    jq ".agents.list = [{\"id\": \"$DEFAULT_AGENT_ID\", \"name\": \"main\", \"workspace\": \"$DEFAULT_WORKSPACE\", \"agentDir\": \"$DEFAULT_AGENT_DIR\"}] + .agents.list" "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
    if [ $? -eq 0 ]; then
        mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
        echo "Added default agent to agents.list"
    else
        echo "Error: Failed to add default agent"
        exit 1
    fi
else
    # 如果默认 agent 存在，确保它在第一个位置
    jq ".agents.list = [.agents.list[]? | select(.id == \"$DEFAULT_AGENT_ID\")] + [.agents.list[]? | select(.id != \"$DEFAULT_AGENT_ID\")]" "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
    if [ $? -eq 0 ]; then
        mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    fi
fi

if [ "$ACTION" = "add" ]; then
    # 检查 agent 是否已存在（先检查 agents 和 agents.list 是否存在）
    if jq 'has("agents")' "$CONFIG_FILE" | grep -q "true" && jq '.agents | has("list")' "$CONFIG_FILE" | grep -q "true"; then
        # 跳过检查默认存在的 agent (main)
        if [ "$AGENT_ID" != "main" ]; then
            AGENT_EXISTS=$(jq ".agents.list[]? | select(.id == \"$AGENT_ID\")" "$CONFIG_FILE")
            if [ -n "$AGENT_EXISTS" ]; then
                echo "Agent with id '$AGENT_ID' already exists!"
                exit 1
            fi
        fi
    else
        # 如果 agents 或 agents.list 不存在，创建它们
        jq '.agents += {"list": []}' "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
        if [ $? -eq 0 ]; then
            mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
            echo "Added agents.list to $CONFIG_FILE"
        else
            echo "Error: Failed to add agents.list"
            exit 1
        fi
    fi

    # 确保 bindings 存在
    if ! jq 'has("bindings")' "$CONFIG_FILE" | grep -q "true"; then
        jq '. += {"bindings": []}' "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
        if [ $? -eq 0 ]; then
            mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
            echo "Added bindings to $CONFIG_FILE"
        else
            echo "Error: Failed to add bindings"
            exit 1
        fi
    fi

    # 添加新 agent 到 agents.list
    jq ".agents.list += [{\"id\": \"$AGENT_ID\", \"name\": \"$AGENT_NAME\", \"workspace\": \"$WORKSPACE_BASE/workspace-$AGENT_ID\", \"agentDir\": \"$WORKSPACE_BASE/agents/$AGENT_ID/agent\"}]" "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
    if [ $? -eq 0 ]; then
        mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
        echo "Added agent '$AGENT_NAME' with id '$AGENT_ID' to agents.list"
    else
        echo "Error: Failed to add agent to agents.list"
        exit 1
    fi

    # 确保默认 agent (main) 在 agents.list 的第一个位置
    jq ".agents.list = [.agents.list[]? | select(.id == \"$DEFAULT_AGENT_ID\")] + [.agents.list[]? | select(.id != \"$DEFAULT_AGENT_ID\")]" "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
    if [ $? -eq 0 ]; then
        mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
        echo "Ensured default agent is at the first position in agents.list"
    else
        echo "Warning: Failed to reorder agents.list"
    fi

    # 添加对应的 binding
    jq ".bindings += [{\"agentId\": \"$AGENT_ID\", \"match\": {\"channel\": \"$CHANNEL\", \"accountId\": \"$AGENT_ID\"}}]" "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
    if [ $? -eq 0 ]; then
        mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
        echo "Added binding for agent '$AGENT_ID'"
    else
        echo "Error: Failed to add binding"
        exit 1
    fi

    # 创建 workspace 目录
    WORKSPACE_DIR="$WORKSPACE_BASE/workspace-$AGENT_ID"
    if [ ! -d "$WORKSPACE_DIR" ]; then
        mkdir -p "$WORKSPACE_DIR"
        if [ $? -eq 0 ]; then
            echo "Created workspace directory: $WORKSPACE_DIR"
            # 设置正确的权限
            if [ -d "/home/openclaw" ]; then
                chown -R openclaw:openclaw "$WORKSPACE_DIR"
                echo "Set permissions for workspace directory"
            fi
        else
            echo "Warning: Failed to create workspace directory"
        fi
    fi

    # 创建 agentDir 目录
    AGENT_DIR="$WORKSPACE_BASE/agents/$AGENT_ID/agent"
    if [ ! -d "$AGENT_DIR" ]; then
        mkdir -p "$AGENT_DIR"
        if [ $? -eq 0 ]; then
            echo "Created agent directory: $AGENT_DIR"
            # 设置正确的权限
            if [ -d "/home/openclaw" ]; then
                chown -R openclaw:openclaw "$WORKSPACE_BASE/agents/$AGENT_ID"
                echo "Set permissions for agent directory"
            fi
        else
            echo "Warning: Failed to create agent directory"
        fi
    fi

    echo "Done! Agent '$AGENT_NAME' has been added to $CONFIG_FILE"

elif [ "$ACTION" = "delete" ]; then
    # 遍历所有 agent_id 进行删除
    for AGENT_ID in "${AGENT_IDS[@]}"; do
        echo "Processing agent: $AGENT_ID"
        
        # 跳过删除默认 agent
        if [ "$AGENT_ID" = "$DEFAULT_AGENT_ID" ]; then
            echo "Warning: Cannot delete default agent!"
            continue
        fi
        
        # 检查 agent 是否已存在（先检查 agents 和 agents.list 是否存在）
        AGENT_EXISTS=""
        if jq 'has("agents")' "$CONFIG_FILE" | grep -q "true" && jq '.agents | has("list")' "$CONFIG_FILE" | grep -q "true"; then
            AGENT_EXISTS=$(jq ".agents.list[]? | select(.id == \"$AGENT_ID\")" "$CONFIG_FILE")
        fi
        if [ -z "$AGENT_EXISTS" ]; then
            echo "Warning: Agent with id '$AGENT_ID' does not exist!"
            continue
        fi

        # 从 agents.list 中删除对应 agent
        jq ".agents.list = [.agents.list[]? | select(.id != \"$AGENT_ID\")]" "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
        if [ $? -eq 0 ]; then
            mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
            echo "Removed agent with id '$AGENT_ID' from agents.list"
        else
            echo "Error: Failed to remove agent from agents.list"
            continue
        fi

        #  从 agents.list 中删除对应 agent中的subagents下的allowAgents中
        jq --arg id "$AGENT_ID" '
            .agents.list |= map(
                if .subagents?.allowAgents? then
                .subagents.allowAgents |= map(select(. != $id)) |
                if .subagents.allowAgents == [] then
                    del(.subagents.allowAgents) |
                    if .subagents == {} then del(.subagents) else . end
                    else . end
                else . end
            )
            ' "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
        if [ $? -eq 0 ]; then
            mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
            echo "Removed subagents with id '$AGENT_ID' from agents.list"
        else
            echo "Error: Failed to remove subagents from agents.list"
            continue
        fi

        # 从 bindings 中删除对应 binding
        jq ".bindings = [.bindings[]? | select(.agentId != \"$AGENT_ID\")]" "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
        if [ $? -eq 0 ]; then
            mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
            echo "Removed binding for agent '$AGENT_ID'"
        else
            echo "Error: Failed to remove binding"
            continue
        fi

        # 删除 workspace 目录及其所有文件
        WORKSPACE_DIR="$WORKSPACE_BASE/workspace-$AGENT_ID"
        if [ -d "$WORKSPACE_DIR" ]; then
            rm -rf "$WORKSPACE_DIR" 2>/dev/null
            if [ $? -ne 0 ]; then
                echo "Warning: Failed to remove workspace directory '$WORKSPACE_DIR' (permission denied or directory not empty)"
                echo "  You may need to manually run: sudo rm -rf '$WORKSPACE_DIR'"
            else
                echo "Removed workspace directory: $WORKSPACE_DIR"
            fi
        fi

        # 删除 agentDir 目录及其所有文件
        AGENT_DIR="$WORKSPACE_BASE/agents/$AGENT_ID"
        if [ -d "$AGENT_DIR" ]; then
            rm -rf "$AGENT_DIR" 2>/dev/null
            if [ $? -ne 0 ]; then
                echo "Warning: Failed to remove agent directory '$AGENT_DIR' (permission denied or directory not empty)"
                echo "  You may need to manually run: sudo rm -rf '$AGENT_DIR'"
            else
                echo "Removed agent directory: $AGENT_DIR"
            fi
        fi

        echo "Done! Agent '$AGENT_ID' has been deleted from $CONFIG_FILE"
        echo
    done
    
    # 确保默认 agent 仍然在 agents.list 的第一个位置
    jq ".agents.list = [.agents.list[]? | select(.id == \"$DEFAULT_AGENT_ID\")] + [.agents.list[]? | select(.id != \"$DEFAULT_AGENT_ID\")]" "$CONFIG_FILE" > "$CONFIG_FILE.tmp"
    if [ $? -eq 0 ]; then
        mv -f "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    fi
    
    echo "Batch deletion completed! Processed ${#AGENT_IDS[@]} agents."
fi
