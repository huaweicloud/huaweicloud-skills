# GitCode Issue 模板

## 标题格式

【xx产品】问题描述摘要

## 正文模板

### 描述问题 (Description)

<!-- 从 FeedbackRecord.problem_description（error_stack 中【问题描述】）或 error_message 或 user_intent 提取 -->

### 复现步骤 (To Reproduce)

<!-- 从 FeedbackRecord.occurrence_scenario（error_stack 中【复现场景】）或 Context.dialog_context 提取 -->

### 预期行为 (Expected behavior)

<!-- 从 FeedbackRecord.expected_behavior（error_stack 中【预期行为】）提取，无则为 "(待补充)" -->

### 错误堆栈 (Stack Trace)

<!--
从 error_stack 中提取原始堆栈部分（去除【问题描述】【预期行为】等标记后）。
仅当存在真正的问题堆栈时包含，纯【】标记则不展示。
```
从 error_stack 中【错误堆栈】之后的部分提取
```
-->

### 环境信息 (Environment)

<!-- 从 Context.environment 提取 key: value 列表 -->
