#!/bin/bash

# 1. Silent jq check
if ! command -v jq &>/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y -qq jq 2>/dev/null ||
        sudo yum install -y -q jq 2>/dev/null
fi

JSON_ARRAY="$1"

# 2. Argument Validation
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 \"[{\"channel\":\"<channel>\",\"account_id\":\"<account_id>\",\"bot_name\":\"<bot_name>\",\"id\":\"<id>\",\"secret\":\"<sectet>\"}]\""
    echo "Example: $0 \"[{\"channel\":\"ch1\",\"account_id\":\"bot1\",\"bot_name\":\"bot1\",\"id\":\"cli_a9gjduihgdf\",\"secret\":\"fafasdgrefraqferfa\"}]\""
    exit 1
fi

# 定义允许的channel值
ALLOWED_CHANNELS=("feishu" "wecom" "dingtalk" "qqbot" "xiaoyi" "whatsapp" "telegram" "discord")

# 定义必填字段
REQUIRED_FIELDS=("channel" "account_id" "bot_name" "id" "secret")
# 国际站复用wecom
REQUIRED_FIELDS_WECOM=("channel" "bot_name" "id" "secret")

# 使用jq校验JSON数组
ERRORS=""

# 校验JSON格式
if ! echo "$JSON_ARRAY" | jq -e '.' >/dev/null 2>&1; then
    echo "❌ Invalid input: JSON invalid!"
    exit 1
fi

# 校验json格式数组
if ! echo "$JSON_ARRAY" | jq -e 'type=="array"' >/dev/null 2>&1; then
    echo "❌ Invalid input: Expected a JSON array!"
    exit 1
fi

# 获取数组长度
ARRAY_LENGTH=$(echo "$JSON_ARRAY" | jq 'length')
if [ "$ARRAY_LENGTH" -eq 0 ]; then
    echo "❌ Invalid input: Empty JSON array!"
    exit 1
fi

# 3. Clean TARGET_FILE Path
TARGET_FILE="/root/.openclaw/openclaw.json"
if [ -d "/home/openclaw" ]; then
    TARGET_FILE="/home/openclaw/.openclaw/openclaw.json"
fi

# 遍历每个元素进行校验
for ((i=0; i<ARRAY_LENGTH; i++)); do
    # 提取当前元素
    ELEMENT=$(echo "$JSON_ARRAY" | jq -c ".[$i]")

    # 校验channel值是否有效
    CHANNEL=$(echo "$ELEMENT" | jq -r '.channel')
    if [[ ! " ${ALLOWED_CHANNELS[@]} " =~ " ${CHANNEL} " ]]; then
        ERRORS="${ERRORS}element $((i+1)): channel '$CHANNEL' invalid, need: ${ALLOWED_CHANNELS[*]}\n"
    fi

    #检查id是否已经存在，如果已经存在，报错
    id=$(echo "$ELEMENT" | jq -r '.id')
    case "$CHANNEL" in
        dingtalk)
            filter='.channels.dingtalk.accounts[]? | select(.clientId == $id)'
            ;;
        feishu)
            filter='.channels.feishu.accounts[]? | select(.appId == $id)'
            ;;
        qqbot)
            filter='.channels.qqbot.accounts[]? | select(.appId == $id)'
            ;;
        xiaoyi)
            filter='.channels.xiaoyi.accounts[]? | select(.ak == $id)'
            ;;
        wecom)
            filter='.channels.wecom | select(.botId == $id)'
            ;;
        discord)
            filter='.channels.discord | select(.name == $id)'
            ;;
        telegram)
            filter='.channels.telegram | select(.name == $id)'
            ;;
        *)
            echo "Error: Unknown channel $CHANNEL" >&2
            exit 1
            ;;
    esac
    # 执行检查，若 jq 找到匹配项则返回 0（存在重复）
    if jq --arg id "$id" -e "$filter" "$TARGET_FILE" > /dev/null 2>&1; then
        echo "{\"errorCode\":2, \"messageEn\":\"Error: Duplicate id '$id' found in channel $CHANNEL\", \"messageCh\":\"属于通道:'$CHANNEL'的id:'$id' 已经存在\"}"
        exit 2
    fi

    # 校验必填字段是否为空
    if [ "$CHANNEL" != "wecom" ]; then
        for FIELD in "${REQUIRED_FIELDS[@]}"; do
            VALUE=$(echo "$ELEMENT" | jq -r --arg f "$FIELD" '.[$f]')

            if [ "$VALUE" = "null" ] || [ -z "$VALUE" ]; then
                ERRORS="${ERRORS}element $((i+1)): field '$FIELD' required\n"
            fi
        done
    else
        for FIELD in "${REQUIRED_FIELDS_WECOM[@]}"; do
            VALUE=$(echo "$ELEMENT" | jq -r --arg f "$FIELD" '.[$f]')

            if [ "$VALUE" = "null" ] || [ -z "$VALUE" ]; then
                ERRORS="${ERRORS}element $((i+1)): field '$FIELD' required\n"
            fi
        done
    fi
done

# 输出校验结果
if [ -n "$ERRORS" ]; then
    echo "❌ Invalid input param:"
    echo -e "$ERRORS"
    exit 1
else
    echo "✅ Param check success"
    echo "$ARRAY_LENGTH elements"
fi

# 4. Atomic Multi-Path Update
# We use ';' to chain multiple assignments in one jq pass
BATCH_CHANNEL_HANDLER() {
    local json_array=$1

    jq --argjson input "$json_array" '
    .channels //= {} |

    .channels as $orig_channels
    | (($input // []) | reduce .[] as $item ($orig_channels;

        ($item.channel) as $channel
        | ($item.account_id // ($channel + "-pre")) as $account_id
        | ($item.bot_name // "") as $bot_name
        | ($item.id) as $id
        | ($item.secret) as $secret

        # 只保留指定 channel
        | select($channel | IN("feishu","wecom","dingtalk","qqbot","xiaoyi","whatsapp","telegram","discord"))

        # ========== wecom 特殊逻辑 ==========
        | if $channel == "wecom" then
            .[$channel] = {
                botId: $id,
                secret: $secret,
                dmPolicy: "open",
                botName: $bot_name,
                allowFrom: ["*"],
                enabled: true
            }
        # ========== 其他 channel ==========
        else
            (
                # 确保 channel
                .[$channel] //= {enabled:true}

                # 旧结构迁移（排除 wecom）
                | if $channel != "wecom"
                    and (.[$channel].accounts? == null)
                    and (
                       ($channel=="feishu" and .[$channel].appId? != null) or
                       ($channel=="dingtalk" and .[$channel].clientId? != null) or
                       ($channel=="qqbot" and .[$channel].appId? != null) or
                       ($channel=="xiaoyi" and .[$channel].ak? != null) or
                       ($channel=="discord" and .[$channel].name? != null) or
                       ($channel=="telegram" and .[$channel].name? != null)
                    )
                  then
                    (.[$channel] as $old
                     | {
                         enabled: ($old.enabled // true),
                         accounts: {
                             ($channel + "-pre"): (
                                 ($old | del(.enabled)) + { botName: ($channel + "-pre") }
                             )
                         }
                       }
                    ) as $migrated
                    | .[$channel] = $migrated
                  else
                    .
                  end

                # 确保 accounts
                | .[$channel].accounts //= {}

                # merge 账号
                | .[$channel].accounts[$account_id] =
                    (
                        (.[$channel].accounts[$account_id] // {})
                        + (
                            if $channel=="feishu" then {appId: $id, appSecret: $secret, botName: $bot_name, dmPolicy:"open", allowFrom:["*"]}
                            elif $channel=="dingtalk" then {clientId: $id, clientSecret: $secret, botName: $bot_name}
                            elif $channel=="qqbot" then {appId: $id, clientSecret: $secret, botName: $bot_name, allowFrom:["*"]}
                            elif $channel=="xiaoyi" then {ak: $id, sk: $secret, botName: $bot_name}
                            elif $channel=="discord" then {name: $bot_name,  dmPolicy: "open", allowFrom: ["*"], token: $secret}
                            elif $channel=="telegram" then {name: $bot_name,  dmPolicy: "open", allowFrom: ["*"], botToken: $secret}
                            else {}
                            end
                        )
                    )
            )
        end

    )) as $updated_channels
    | .channels = $updated_channels
    ' "$TARGET_FILE"
}

UPDATED_JSON=$(BATCH_CHANNEL_HANDLER "$JSON_ARRAY")

# 5. Safe Save
TARGET_FILE_TMP="${TARGET_FILE}.tmp"
if [ $? -eq 0 ] && [ -n "$UPDATED_JSON" ]; then
    echo "$UPDATED_JSON" >"$TARGET_FILE_TMP"
    if [ -d "/home/openclaw" ]; then
       chown openclaw:openclaw $TARGET_FILE_TMP
    fi
    chmod 600 $TARGET_FILE_TMP
    cp -p $TARGET_FILE_TMP $TARGET_FILE
    echo "-----------------------------------------------"
    echo "Add channels Complete!"
    # openclaw gateway restart
else
    echo "Error: Modification failed. Please ensure $TARGET_FILE contains valid JSON."
    exit 1
fi

# 6. Add agent
while read -r item; do
    channel=$(echo "$item" | jq -r '.channel // empty')
    account_id=$(echo "$item" | jq -r '.account_id // empty')
    bot_name=$(echo "$item" | jq -r '.bot_name // empty')
    international_type=$(echo "$item" | jq -r '.international_type // empty')

    # 跳过wecom
    if [ "$channel" = "wecom" ]; then
        echo "----------------------------------------"
        echo "Add agent,skip"
        continue
    fi

    echo "----------------------------------------"
    echo "Processing: account_id=$account_id, bot_name=$bot_name, channel=$channel, id=$id"

    # 使用与本脚本一同打包内置的 multi-agent.sh（不再运行时下载外部脚本）
    OPENCLAW_MULTI_AGENT_SH="$(cd "$(dirname "$0")" && pwd)/multi-agent.sh"
    if [ ! -f "$OPENCLAW_MULTI_AGENT_SH" ]; then
        echo "Error: bundled multi-agent.sh not found next to multi_channel.sh" >&2
        exit 1
    fi
    bash "$OPENCLAW_MULTI_AGENT_SH" add "$account_id" "$bot_name" "$channel"
    # 可选：检查执行结果
    if [ $? -ne 0 ]; then
        echo "Error: target script failed for account_id=$account_id, bot_name=$bot_name, channel=$channel"
    fi
done < <(echo "$JSON_ARRAY" | jq -c '.[]')
