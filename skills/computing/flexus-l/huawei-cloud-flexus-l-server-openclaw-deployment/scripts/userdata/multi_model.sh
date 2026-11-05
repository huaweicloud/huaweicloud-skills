#!/bin/bash

# 1、若不存在默认模型，默认设置第一个为默认模型
# 2、批量添加多个模型时，只允许添加一个供应商的多个模型
# 3、api协议当前仅支持openai-completions/anthropic-messages

# 1. Silent jq check
if ! command -v jq &>/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y -qq jq 2>/dev/null ||
        sudo yum install -y -q jq 2>/dev/null
fi

log_error() {
    echo "{\"errorCode\": $1, \"messageEn\":\"$2\", \"messageCh\":\"$3\", \"details\": \"$4\"}"
}

log_info() {
    log_error 0 "$1" "$2" "$3"
}

if [ $# -ne 1 ] && [ $# -ne 4 ]; then
    echo "Usage: $0 <provider> <model_id> <model_alias> <api_key> "
    echo "Usage: $0 {\"provider\": \"huawei\", \"api\": \"openai-completions\", \"api_key\": \"sk-xxx\", \"model_ids\":[\"model_id1\", \"model_id2\", \"model_id3\"]} "
    exit 1
fi


if [ "$#" -eq 4 ]; then
    PROVIDER="$1"
    MODEL_IDS=$(echo "$2" | jq -R '[.]')
    MODEL_ALIAS="$3"
    API_KEY="$4"
    API_PROTOCOL="openai-completions"
else
    JSON_PARAM="$1"
    if ! echo "$JSON_PARAM" | jq -e '.' >/dev/null 2>&1; then
        log_error 1 "Invalid input: JSON invalid!" "传入参数json非法！" 
        exit 1
    fi

    PROVIDER=$(echo $JSON_PARAM| jq -r '.provider')
    if [ -z ${PROVIDER} ]; then
        log_error 1 "Invalid provider!" "传入参数provider非法！" 
        exit 1
    fi

    API_PROTOCOL=$(echo $JSON_PARAM| jq -r '.api')
    if [ -z "${API_PROTOCOL}" ] || [ "X${API_PROTOCOL}" == "Xnull" ]; then
        API_PROTOCOL="openai-completions"
    else
        if [ "X${API_PROTOCOL}" != "Xopenai-completions" ] && [ "X${API_PROTOCOL}" != "Xanthropic-messages" ]; then
            log_error 1 "Supports api protocols openai-completions and anthropic-messages only!" "Api协议仅支持openai-completions和anthropic-messages！"
            exit 1
        fi
    fi

    API_KEY=$(echo $JSON_PARAM| jq -r '.api_key // empty')
    MODEL_IDS=$(echo $JSON_PARAM| jq -r '.model_ids // empty')
    if [ -z "${API_KEY}" ] && [ -z "${MODEL_IDS}" ] ;then
        log_error 1 "Invalid param, api_key and model_ids are invalid!" "入参api_key和model_ids不能同时为空！" 
        exit 1
    fi
fi

# Remove Skillhub configuration
if [ -d "/home/openclaw" ]; then
    TARGET_FILE="/home/openclaw/.openclaw/openclaw.json"
    TARGET_FILE_TMP="/home/openclaw/.openclaw/openclaw.json.tmp"
    jq '.tools.profile = "full" | del(.plugins.entries.skillhub) | del(.plugins.allow[]? | select(. == "skillhub"))' "$TARGET_FILE" > "$TARGET_FILE_TMP"
    chown openclaw:openclaw $TARGET_FILE_TMP
    chmod 600 $TARGET_FILE_TMP
    cp -p $TARGET_FILE_TMP $TARGET_FILE
fi

get_url_mapping() {
    local provider=$1

    if [[ "$provider" == http://* ]] || [[ "$provider" == https://* ]]; then
        echo "$provider"
        return 0
    fi

    case "$provider" in
    "huawei")
        echo "https://api.modelarts-maas.com/v2/chat/completions"
        ;;
    "aliyun")
        echo "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ;;
    "volcano")
        echo "https://ark.cn-beijing.volces.com/api/v3"
        ;;
    "hunyuan")
        echo "https://api.hunyuan.cloud.tencent.com/v1"
        ;;
    "deepseek")
        echo "https://api.deepseek.com"
        ;;
    "zhipu")
        echo "https://open.bigmodel.cn/api/paas/v4"
        ;;
    "minimax")
        echo "https://api.minimaxi.com/v1/text/chatcompletion_v2"
        ;;
    "moonshot")
        echo "https://api.moonshot.cn/v1"
        ;;
    "xiaomi")
        echo "https://api.xiaomimimo.com/v1/chat/completions"
        ;;
    *)
        echo "" # Unknown provider
        ;;
    esac
}

# # Pass provider and model ID to get BASE_URL
BASE_URL=$(get_url_mapping "$PROVIDER")
if [ -z ${BASE_URL} ]; then
    log_error 1 "Error:Provider $PROVIDER invalid!" "provider:$PROVIDER非法！" 
    exit 1
fi

# 3. Clean Base URL
CLEANED_URL="${BASE_URL%/chat/completions}"
TARGET_FILE="/root/.openclaw/openclaw.json"
if [ -d "/home/openclaw" ]; then
    TARGET_FILE="/home/openclaw/.openclaw/openclaw.json"
fi
DOMAIN=$(echo "$BASE_URL" | awk -F/ '{print $3}')

PROVIDER_ALIAS=$(echo "$DOMAIN" | awk -F. '{print $(NF-1)}')

# 使用自定义供应商，但是填入了华为云Maas的地址
if [ "$PROVIDER_ALIAS" == "modelarts-maas" ] && [ "$PROVIDER" != "huawei" ]; then
    PROVIDER_ALIAS="modelarts-maas-custom"
fi

# 默认供应商名称，规则为openai类型接口，如果指定为anthropic-messages, 则供应商名称设置为anthropic-messages后缀
if [ "$API_PROTOCOL" == "anthropic-messages" ]; then
    PROVIDER_ALIAS="${PROVIDER_ALIAS}-${API_PROTOCOL}"
fi


# 如果apiKey或者model_id入参不存在，说明是更新的场景，则Provider必须存在，否则无法更新
if [ -z "${API_KEY}" ] || [ -z "${MODEL_IDS}" ]; then
    if ! jq -e --arg p "$PROVIDER_ALIAS" '.models.providers | has($p)' ${TARGET_FILE} > /dev/null; then
        log_error 1 "Error: Provider '$PROVIDER_ALIAS' not found!" "供应商$PROVIDER_ALIAS不存在！" 
        exit 1
    fi
fi

# Create the full model path string (e.g., openai_api_compatible/gpt-4)
if [ -n "${MODEL_IDS}" ]; then
    DEFAULT_MODEL=$(echo $MODEL_IDS | jq -r '.[0]')
    DEFAULT_MODEL_PATH="${PROVIDER_ALIAS}/${DEFAULT_MODEL}"
fi

# 4. Atomic Multi-Path Update
# We use ';' to chain multiple assignments in one jq pass
# use first model as default model when add model first time.
# if defaul model deleted, add model next time ,will not set default model
UPDATED_JSON=$(jq \
    --arg provider "$PROVIDER_ALIAS" \
    --arg url "$CLEANED_URL" \
    --arg key "$API_KEY" \
    --arg api "$API_PROTOCOL" \
    --arg model_alias "$MODEL_ALIAS" \
    --arg def_mod_path "$DEFAULT_MODEL_PATH" \
    --argjson ids "${MODEL_IDS:-[]}" \
'
# ---------- 基于原始数据判断 ----------
def is_new_model:
    try (
        # 尝试遍历所有 providers
        (.models.providers // {}) |
        to_entries |
        map(
            .value.models // [] |
            map(
                .id // "<model_name>" |
                select(. != "<model_name>")
            )
        ) |
        flatten |
        length == 0
    ) catch false;  # 如果出错，保守地返回 false

# ---------- 冻结原始数据用于判断 ----------
. as $orig |

# -----------清理脏数据------------

# 清理 models
if .models?.providers then
  .models.providers |= (
    map_values(
      if (.models | type) == "array" then
        .models |= [
          .[] | select(
            .id and 
            (.id | type == "string") and
            .id != "" and 
            .id != "<model_name>"
          )
        ]
      else .
      end
    )
  )
else .
end

# 删除空的 providers
| if .models?.providers then
    .models.providers |= (
      with_entries(select(.value.models and (.value.models | length > 0)))
    )
  else .
  end

# 清理 agents.defaults.models
| if .agents?.defaults?.models then
    .agents.defaults.models |= (
      map_values(
        select(
          .alias and 
          (.alias | type == "string") and
          .alias != "" and 
          .alias != "<model_name>"
        )
      )
    )
  else .
  end |

# ---------- 开始修改 ----------
.models //= {} |
.models.providers //= {} |

# 创建 provider
if (.models.providers[$provider] == null) then
    .models.providers[$provider] = {
        baseUrl: $url,
        apiKey: $key,
        api: $api,
        models: []
    }
else
    .
end |

# baseUrl 变化
if (.models.providers[$provider].baseUrl != $url) then
    .models.providers[$provider].models = [] |
    .agents.defaults.models |=
        with_entries(
            select(.key | startswith($provider + "/") | not)
        )
else
    .
end |

# 更新 provider
.models.providers[$provider].baseUrl = $url |
.models.providers[$provider].apiKey |= (if $key != "" then $key else . end) |

# 确保 models
.models.providers[$provider].models //= [] |

# 写入 model
.models.providers[$provider].models |=
(
    if (($ids | type == "array") and ($ids | length > 0)) then
        map(select(.id as $curr | ($ids | index($curr) | not))) + 
        ($ids | map({
            id: .,
            name: (($model_alias | select(. != "")) // .),
            reasoning: false,
            input: ["text"],
            cost: {
                input: 0,
                output: 0,
                cacheRead: 0,
                cacheWrite: 0
            },
            contextWindow: 100000,
            maxTokens: 8192
        }))
    else
        .
    end
) |

# agents 结构
.agents //= {} |
.agents.defaults //= {} |
.agents.defaults.model //= {} |
.agents.defaults.models //= {} |

# 添加到agents/设置 primary

reduce range(0; $ids | length) as $id (.;
    ($provider + "/" + $ids[$id]) as $idPath |
    .agents.defaults.models[$idPath].alias = $ids[$id]
  ) |

if ( ($orig | is_new_model) or (.agents?.defaults?.model.primary | (not or . == "")) ) then
    .agents.defaults.model.primary = $def_mod_path
else
    .
end
' "$TARGET_FILE")

# 5. Safe Save
if [ $? -eq 0 ] && [ -n "$UPDATED_JSON" ]; then
    TARGET_FILE_TMP="${TARGET_FILE}.tmp"
    echo "$UPDATED_JSON" >"$TARGET_FILE_TMP"
    if [ -d "/home/openclaw" ]; then
        chown openclaw:openclaw $TARGET_FILE_TMP
    fi
    chmod 600 $TARGET_FILE_TMP
    cp -p $TARGET_FILE_TMP $TARGET_FILE
    if [ -d "/home/openclaw" ]; then
        chown openclaw:openclaw $TARGET_FILE_TMP
    fi

    # Clean agent models.json and  auth-profiles.json as backup for model config update
    AGENTS_BASE_DIR="/root/.openclaw/agents"
    if [ -d "/home/openclaw" ]; then
        AGENTS_BASE_DIR="/home/openclaw/.openclaw/agents"
    fi
    if [ -d "$AGENTS_BASE_DIR" ]; then
        TIMESTAMP=$(date +%Y%m%d%H%M%S)
        for agent_dir in "$AGENTS_BASE_DIR"/*/agent; do
            AGENT_MODELS_FILE="${agent_dir}/models.json"
            AGENT_AUTH_PROFILE_FILE="${agent_dir}/auth-profiles.json"

            if [ -f "$AGENT_MODELS_FILE" ]; then
                mv "$AGENT_MODELS_FILE" "${AGENT_MODELS_FILE}.bak.${TIMESTAMP}"
                log_info "Agent models.json backup created" "Agent models.json备份已创建" "Backup: ${AGENT_MODELS_FILE}.bak.${TIMESTAMP}"
            fi

            if [ -f "$AGENT_AUTH_PROFILE_FILE" ]; then
                mv "$AGENT_AUTH_PROFILE_FILE" "${AGENT_AUTH_PROFILE_FILE}.bak.${TIMESTAMP}"
                log_info "Agent auth-profiles.json backup created" "Agent auth-profiles.json备份已创建" "Backup: ${AGENT_MODELS_FILE}.bak.${TIMESTAMP}"
            fi
        done
    fi

    log_info "Update Complete!" "更新成功" "Primary Model set to: $(jq -r '.agents.defaults.model.primary // empty' "$TARGET_FILE")"
else
    log_error 1 "Error: Modification failed. Please ensure $TARGET_FILE contains valid JSON." "配置失败，请确认$TARGET_FILE文件内容是否是合法json"
    exit 1
fi

