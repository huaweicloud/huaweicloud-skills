# Hook配置与部署指南

## 概述

VoD收集Skill通过各平台的Hook机制实现自动触发。本文档说明各平台的Hook配置方法和自定义扩展方式。

## OpenClaw Hook配置

配置文件：`hooks/openclaw/hooks.yaml`

### 三个Hook定义

| Hook名称 | 触发事件 | 触发条件 | 优先级 |
|---------|---------|---------|--------|
| vod-on-tool-error | PostToolUse | exit_code≠0 或 stderr含error 或 status_code∈[4xx,5xx] | high |
| vod-on-user-rejection | UserPromptSubmit | user_input匹配拒绝关键词 | normal |
| vod-on-user-report | UserPromptSubmit | user_input匹配报告关键词 | high |

### 触发条件配置

触发条件使用`value_from_config`引用config.yaml中的配置项：

- `rejection.rejection_keywords` → config.yaml中`rejection.rejection_keywords`列表
- `report.trigger_keywords` → config.yaml中`report.trigger_keywords`列表

修改关键词只需编辑config.yaml，无需修改Hook配置。

## Hermes Hook配置

配置文件：`hooks/hermes/hooks.yaml`

### 三个Hook定义

| Hook名称 | 触发事件 | 触发条件 | 优先级 |
|---------|---------|---------|--------|
| vod-on-error | on_tool_result | result.success=false | high |
| vod-on-prompt | on_prompt | prompt.text匹配拒绝关键词 | normal |
| vod-on-user-report | on_prompt | prompt.text匹配报告关键词 | high |

## 关键词配置方法

### 拒绝关键词（rejection_keywords）

在config.yaml中配置：

```yaml
rejection:
  rejection_keywords:
    - "不对"
    - "不是"
    - "错了"
    - "不要"
    - "不行"
```

### 报告触发关键词（trigger_keywords）

在config.yaml中配置：

```yaml
report:
  trigger_keywords:
    - "我要报告一个问题"
    - "这个有bug"
    - "报告bug"
```

## 自定义Hook扩展

### 新增平台

要为新Agent平台添加Hook支持：

1. 创建`hooks/<platform>/`目录
2. 在其中创建`hooks.yaml`，定义触发事件和条件
3. 在`references/`中创建`<platform>-integration.md`说明文档
4. 在config.yaml中添加`platform.<platform>`配置段

**核心原则**：Hook配置仅定义触发条件和事件映射，不包含业务逻辑。所有业务逻辑在SKILL.md和辅助脚本中。

### 示例：添加新平台Hook

```yaml
# hooks/newplatform/hooks.yaml
hooks:
  - name: vod-on-error
    event: on_execution_end
    condition:
      - field: execution.success
        operator: eq
        value: false
    action: activate_skill
    skill: agent-vod-collector
    priority: high
```

## 部署验证

部署后可通过以下方式验证Hook是否生效：

1. **OpenClaw**：`openclaw hooks list` 查看已注册的Hook
2. **Hermes**：检查Hermes配置中是否包含agent-vod-collector的Hook引用

触发测试：
- 执行一个会失败的命令，观察是否生成反馈记录
- 输入拒绝关键词（如"不对"），观察是否触发拒绝检测
- 输入报告关键词（如"我要报告一个问题"），观察是否进入引导流程