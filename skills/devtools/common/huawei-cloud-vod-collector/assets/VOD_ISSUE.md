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

### 实际行为 (Actual behavior)

<!-- 从 FeedbackRecord.actual_behavior（error_stack 中【实际行为】）提取 -->

### 错误堆栈 (Stack Trace)

<!--
```
从 error_stack 中【错误堆栈】部分提取
```
-->

### 环境信息 (Environment)

<!-- 从 Context.environment 提取 key: value 列表 -->

### 更多详情 (More Details)

<!-- 从 More Details 提取，包含总结性内容等补充信息 -->
