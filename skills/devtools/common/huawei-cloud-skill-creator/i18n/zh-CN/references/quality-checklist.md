# 质量检查清单

> 创建 Skill 后逐项检查，确保符合规范。运行 `bash scripts/validate-skill.sh {skill-path}` 可自动检查部分项。

## 必需项（不通过则不可发布）

### SKILL.md 结构

- [ ] SKILL.md 文件存在
- [ ] YAML Frontmatter 以 `---` 正确包裹
- [ ] `name` 字段存在且非空
- [ ] `name` 符合 `{platform}-{product}-{function}` 命名公式
- [ ] `description` 字段存在且非空
- [ ] `description` 包含功能定位（第 1 点）
- [ ] `description` 包含触发条件（第 2 点）
- [ ] `description` 包含价值描述（第 3 点）
- [ ] `description` 包含使用方式（第 4 点）
- [ ] `description` 包含前置条件（第 5 点）
- [ ] `tags` 字段存在且有 3-8 个标签
- [ ] `version` 字段存在且符合 SemVer（MAJOR.MINOR.PATCH）

### 正文结构

- [ ] 包含"概述"章节
- [ ] 包含"主要步骤"章节
- [ ] 每步操作有清晰的 CLI 指令
- [ ] 关键参数有配置说明
- [ ] 每个操作标注所需权限
- [ ] 提供 3-5 个典型使用示例
- [ ] 正文行数 ≤ 500

### 安全

- [ ] SKILL.md 中无硬编码 AK/SK
- [ ] 脚本中无硬编码 AK/SK
- [ ] 敏感信息通过环境变量获取
- [ ] 写入/删除操作有用户确认提示
- [ ] 高危操作有 dry-run 选项说明
- [ ] 包含安全操作规范章节（必须遵守 + 必须避免）
- [ ] 包含 User-Agent 标识说明

### 权限

- [ ] `references/iam-policies.md` 存在
- [ ] 查询类操作已列出
- [ ] 操作类操作已列出
- [ ] 包含最小权限策略 JSON
- [ ] 高危操作标注是否需要 MFA

### 认证

- [ ] 认证方式已明确说明（AK/SK / CLI 配置 / 临时令牌 / IAM 角色）
- [ ] CLI 配置流程有安全提醒

## 推荐项（不通过可发布但应改进）

### 参考文档

- [ ] `references/cli-installation-guide.md` 存在
- [ ] `references/verification-method.md` 存在
- [ ] `references/acceptance-criteria.md` 存在
- [ ] `references/related-commands.md` 存在
- [ ] SKILL.md 中引用的 references/ 文件全部存在
- [ ] 每个 ref 文件专注解决一个问题
- [ ] ref 文件头部有简短说明
- [ ] 大文件（>300 行）顶部有目录

### 目录结构

- [ ] Skill 位于正确的领域目录下
- [ ] scripts/ 中的脚本有 shebang（#!/bin/bash 或 #!/usr/bin/env python3）
- [ ] scripts/ 中的脚本有参数校验和错误处理
- [ ] Python 脚本目录有 `__init__.py`
- [ ] Node.js 脚本使用 `.mjs` 后缀
- [ ] templates/ 中的模板占位符使用花括号 `{placeholder}`

### 内容质量

- [ ] 代码块标注了语言类型
- [ ] CLI 命令语法正确（可运行）
- [ ] 常见错误有处理方案（边界情况章节）
- [ ] 操作成功验证方法已说明
- [ ] 包含脚本使用说明（如有 scripts/）

### 版本管理

- [ ] 版本号遵循 SemVer
- [ ] 分支策略已说明（main / preview）
- [ ] 废弃策略已说明

## 评分标准

| 等级 | 必需项 | 推荐项 | 说明 |
|------|--------|--------|------|
| A | 全部通过 | ≥ 80% | 可正式发布 |
| B | 全部通过 | ≥ 50% | 可发布，需后续改进 |
| C | 全部通过 | < 50% | 可发布，质量待提升 |
| D | 有未通过 | — | 不可发布，需修复 |
