# DWS SQL 检查报告模板

## 报告结构

```markdown
# DWS SQL 检查报告

**检查时间**: {check_time}
**语句类型**: {statement_type}
**检查模式**: {check_mode}

## 检查概要

| 指标 | 值 |
|------|------|
| 检查规则数 | {total_rules} |
| 通过 | {passed} |
| 违规 | {failed} |
| 错误 (ERROR) | {errors} |
| 警告 (WARNING) | {warnings} |
| 提示 (INFO) | {infos} |

## 语法检查

{syntax_section}

## 规范检查

{spec_section}

## 执行计划分析

{plan_section}

## 性能建议

{perf_section}

## 原始 SQL

```sql
{sql_text}
```
```

## 违规条目格式

```markdown
### [{level_icon}] {rule_id}: {rule_name}

- **级别**: {level}
- **位置**: 行 {line}, 列 {column}
- **描述**: {message}
- **代码片段**: `{sql_snippet}`
- **修复建议**: {fix_suggestion}
```

## 级别图标

| 级别 | 图标 |
|------|------|
| ERROR | X |
| WARNING | ! |
| INFO | i |
