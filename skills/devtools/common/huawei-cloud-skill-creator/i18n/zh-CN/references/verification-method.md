# 验证方法 - huawei-cloud-skill-creator-skill

> 当需要验证生成的 Skill 是否符合规范时读取此文件。

## 自动验证

使用 `scripts/validate-skill.sh` 自动检查：

```bash
bash scripts/validate-skill.sh {generated-skill-path}
```

验证覆盖：SKILL.md 结构、Frontmatter 完整性、命名规范、AK/SK 安全、references 引用、正文行数等。

## 手动验证清单

### 结构验证

1. 目录结构完整：SKILL.md + references/ + scripts/（按需）+ templates/（按需）
2. SKILL.md YAML Frontmatter 格式正确
3. references/ 中被引用的文件全部存在

### 内容验证

1. description 包含 5 点结构化描述
2. 每步操作有 CLI 指令
3. 提供 3-5 个使用示例
4. AK/SK 未硬编码
5. iam-policies.md 包含最小权限策略 JSON

### 功能验证

1. CLI 命令语法正确（通过 CLI help 输出验证）
2. 参数名称与 CLI 帮助一致
3. 区域参数使用有效值

## 验证评分

| 等级 | 条件 | 说明 |
|------|------|------|
| A | 必需项全通过，WARN ≤ 2 | 可正式发布 |
| B | 必需项全通过，WARN ≤ 5 | 可发布，需改进 |
| C | 必需项全通过，WARN > 5 | 可发布，质量待提升 |
| D | 必需项有失败 | 不可发布 |
