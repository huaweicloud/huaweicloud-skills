# Quality Checklist

> Quality check items for huawei-cloud-skill-tester, used by validate-skill.sh.

## Directory Structure Checks

- [ ] SKILL.md exists **[required]**
- [ ] references/ directory exists [recommended]
- [ ] scripts/ directory exists [recommended]
- [ ] templates/ directory exists [recommended]
- [ ] demo/ directory exists [recommended]

## SKILL.md Checks

- [ ] YAML Frontmatter exists and is valid
- [ ] name field non-empty, follows naming formula
- [ ] description field non-empty, contains 5-point structured description
- [ ] version field non-empty, follows SemVer
- [ ] tags field non-empty, 3-8 tags
- [ ] Body <= 500 lines

## SKILL.md Section Checks (Bilingual)

> Section names accept either Chinese or English variant. A section is considered present if **any** variant is found.

| Section | Chinese Variant | English Variant(s) | Required |
|---------|----------------|--------------------|----------|
| 概述 | `## 概述` | `## Overview` | Yes |
| 前置条件 | `## 前置条件` | `## Prerequisites` | Yes |
| 工作流 | `## 工作流` | `## Workflow`, `## Main Steps` | Yes |
| 核心命令 | `## 核心命令` | `## Core Commands` | Yes |
| 参数确认 | `## 参数确认` | `## Parameters` | Yes |
| 参考文档 | `## 参考文档` | `## References`, `## Reference Documents` | Yes |
| KooCLI命令格式标准 | `## KooCLI命令格式标准` | `## KooCLI Command Format`, `## Huawei Cloud CLI Command Format` | Yes (when CLI operations present) |

- [ ] Body contains 概述/Overview section **[required]**
- [ ] Body contains 前置条件/Prerequisites section **[required]**
- [ ] Body contains 工作流/Workflow section **[required]**
- [ ] Body contains 核心命令/Core Commands section **[required]**
- [ ] Body contains 参数确认/Parameters section **[required]**
- [ ] Body contains 参考文档/References section **[required]**
- [ ] Body contains KooCLI命令格式标准 section **[required if CLI operations present]**
- [ ] No direct cross-Skill references (Skills should be orchestrated by Agent) **[recommended]**

## Reference Document Checks

- [ ] references/iam-policies.md exists [recommended]
- [ ] references/acceptance-criteria.md exists [recommended]
- [ ] Reference files have brief header description [recommended]
- [ ] Reference files have no mixed content (each file focuses on one topic) [recommended]

## Script Checks

- [ ] scripts/validate-skill.sh exists and is executable [recommended]
- [ ] scripts/test-skill.sh exists and is executable [recommended]
- [ ] scripts/detect-hallucination.sh exists and is executable [recommended]
- [ ] Scripts have shebang line [recommended]
- [ ] Scripts contain no hardcoded AK/SK [recommended]

## Security Checks

- [ ] No plaintext AK/SK
- [ ] Sensitive information uses environment variables
- [ ] Examples use placeholders `{placeholder}`
- [ ] Destructive operations have confirmation mechanism

## Test-Specific Checks

- [ ] Four-phase test workflow completely defined
- [ ] Hallucination detection items completely defined
- [ ] Acceptance criteria clearly defined
- [ ] Test case configuration template exists
- [ ] Test report template exists

## Language Checks

- [ ] SKILL.md body is primarily in English
- [ ] Reference documents are primarily in English
- [ ] Script output messages are in English
- [ ] Template comments are in English
- [ ] Demo examples are in English
- [ ] Trigger words support Chinese-English mixed patterns (e.g., "测试skill", "验证skill质量", "创建华为云ECS Skill")
- [ ] Trigger keywords in scripts include both Chinese, English, and mixed patterns

## i18n Checks

- [ ] i18n/ directory exists [recommended]
- [ ] Locale directory names follow BCP 47 format (xx-XX, e.g., zh-CN, en-US, ja-JP) [recommended]
- [ ] Each locale directory contains at least one SKILL translation file (e.g., SKILL_CN.md) [recommended]
- [ ] i18n SKILL translation files have valid YAML Frontmatter (name, description, version, tags) [recommended]
- [ ] i18n SKILL translation files name field matches original SKILL.md [recommended]
- [ ] i18n directory structure follows: skillname/i18n/{locale}/SKILL_{suffix}.md [recommended]
