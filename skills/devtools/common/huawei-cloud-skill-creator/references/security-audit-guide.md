# Security Audit Guide — Phase 6 安全审视

> Phase 6 使用 skill-targeted-audit 对生成的 Skill 执行五项安全与质量检查。

## 五项检查概览

| # | 工具 | 检查内容 | 安装 |
|---|------|----------|------|
| 1 | skillcheck | SKILL.md agentskills.io 规范（frontmatter、description 质量、引用安全） | `pip install skillcheck` |
| 2 | markdownlint-cli2 | Markdown 风格一致性（行长度、标题、代码块） | `npm install -g markdownlint-cli2` |
| 3 | cisco-ai-skill-scanner | AI 安全：命令注入、反向 Shell、凭证泄露、危险函数、提示注入 | `pip install cisco-ai-skill-scanner`（CLI: `skill-scanner`） |
| 4 | hwcloud-spec | 华为云规范：frontmatter 字段、章节结构、文件大小 | 内置 |
| 5 | gitleaks | 凭证泄露：800+ 种 API 密钥、密码、私钥、token 格式 | [GitHub Releases](https://github.com/gitleaks/gitleaks/releases) |

## 执行命令

```bash
python3 scripts/skill_audit.py --target {skill-path}
```

报告输出到 `{skill-path}/../skill-gate-report-<timestamp>.txt`。

## 修复策略

### skillcheck

| 规则 | 修复 |
|------|------|
| description.quality-score | 以动词开头（Generates/Analyzes/Validates），添加触发上下文 |
| disclosure.metadata-budget | 将非必要 frontmatter 字段移至正文 |
| disclosure.body-bloat | 将大表格（>20行）移至 references/ 文件 |
| frontmatter.field.unknown | 在 skillcheck.toml 的 extension_fields 中添加，或移除 |
| references.escape | 将 `../other-skill/SKILL.md` 替换为纯文本 `[text (other-skill-name)]` |

### markdownlint-cli2

```bash
# 自动修复（处理 MD022/MD031/MD032/MD047/MD012 等）
markdownlint-cli2 "{skill-path}/**/*.md" --config "{skill-path}/.markdownlint.json" --fix

# 手动修复不可自动修复项
# MD036: 将 **伪标题** 替换为 ### 真标题
# MD040: 将裸 ``` 替换为 ```bash 或 ```text
```

### cisco-ai-skill-scanner

| 类别 | 修复 |
|------|------|
| command_injection | 将危险命令移至 scripts/ 独立脚本，SKILL.md 中引用脚本路径 |
| reverse_shell | 移除或使用 `<!-- skill-scanner:ignore -->` 注释 |
| credential_leak | 替换硬编码密钥为 `${VAR}` 或 `os.environ.get("VAR")` |
| dangerous_function | 用 ast.literal_eval() 替代 eval()/exec()，添加输入验证 |
| prompt_injection | 审查并清理用户可控输入，使用结构化输入模板 |

### hwcloud-spec

| 规则 | 修复 |
|------|------|
| frontmatter.missing.{field} | 补充必需字段：name/description/tags；推荐字段：version |
| frontmatter.tags-too-many | 精简标签至 ≤5 个 |
| section.missing-required | 补充必需章节：概述/前置条件/核心命令/参数确认/参考文档 |
| section.missing-recommended | 补充推荐章节：最佳实践/注意事项/验证方法 |
| size.skill-md-lines | SKILL.md 超 500 行时拆分至 references/ |
| size.dir-too-large | 目录超 5MB 时拆分大文件 |

### gitleaks

| 规则 | 修复 |
|------|------|
| generic-api-key | 替换为 `os.environ.get("VAR")`，误报加入 `.gitleaksignore` |
| private-key | 移除硬编码私钥，运行时从文件或密钥管理器加载 |

## skill-scanner 的凭证检测盲区

skill-scanner 的 YARA 规则仅匹配已知云 API 密钥格式（AWS AKIA/GitHub ghp_/OpenAI sk-），**不检测**：
- 通用密码（`password = "xxx"`）
- SMTP 认证码
- 华为云 AK/SK
- 中文关键词凭证（授权码/密码/密钥）

**对于完整凭证检测，需额外运行 gitleaks。**

## 审视结果处理

| 结果 | 处理 |
|------|------|
| PASS（0 issues） | 安全审视通过 |
| PASS（仅 WARNING） | 提示用户确认是否接受 |
| FAIL（ERROR/CRITICAL） | **必须修复后重新审视，不可跳过** |
