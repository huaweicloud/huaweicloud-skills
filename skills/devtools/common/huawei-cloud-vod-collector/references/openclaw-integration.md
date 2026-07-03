# OpenClaw平台集成说明

## 概述

VoD收集Skill通过OpenClaw的Hook机制集成，在Agent运行时自动捕获异常和用户拒绝事件。

## Hook事件格式

### PostToolUse事件

当Agent执行工具调用后触发，事件数据包含：

```json
{
  "tool_name": "Bash",
  "tool_result": {
    "exit_code": 1,
    "stdout": "...",
    "stderr": "error: command not found",
    "status_code": null
  },
  "session_id": "sess_abc123",
  "timestamp": "2026-06-09T10:00:00Z"
}
```

### UserPromptSubmit事件

当用户提交新Prompt时触发，事件数据包含：

```json
{
  "user_input": "不对，我想要的是...",
  "session_id": "sess_abc123",
  "timestamp": "2026-06-09T10:01:00Z"
}
```

## Skill部署步骤

1. 将`vod_collect/`目录复制到OpenClaw workspace的skills目录：
   ```bash
   cp -r vod_collect/ ~/.openclaw/skills/huawei-cloud-vod-collector
   ```

2. 初始化（可选，首次运行时自动创建 `.vod/` 目录和 `config.yaml`）：
   ```bash
   cd ~/.openclaw/skills/huawei-cloud-vod-collector
   pip install -r requirements.txt
   ```

3. 在OpenClaw settings中启用Hook：
   ```bash
   openclaw hooks enable huawei-cloud-vod-collector
   ```

## config.yaml中platform.openclaw配置说明

```yaml
platform:
  type: "openclaw"              # 或 "auto" 自动检测
  openclaw:
    hook_events:                # 监听的Hook事件类型
      - "UserPromptSubmit"
      - "PostToolUse"
    context_api_endpoint: ""    # 对话上下文API地址（如需远程访问）
```

## 交互会话API

OpenClaw提供以下工具用于跨会话通信（仅在用户明确授权时使用）：

- `sessions_list` — 查看活跃会话
- `sessions_history` — 读取会话历史
- `sessions_send` — 向其他会话发送消息

**注意**：VoD Skill默认不使用跨会话通信，仅处理当前会话上下文。