# Acceptance Criteria

> Acceptance criteria for huawei-cloud-skill-tester, defining pass conditions for each phase.

## Phase 1: Installation Verification

| Acceptance Item | Pass Condition | Blocking Level |
|-----------------|----------------|----------------|
| npx install success | Return code = 0 | Blocking |
| SKILL.md exists | File exists and is readable | Blocking |
| Frontmatter compliant | name, description, version, tags non-empty | Blocking |
| references/ directory | Directory exists | Non-blocking (WARN) |
| scripts/ directory | Directory exists | Non-blocking (WARN) |
| validate script passes | Return code = 0 | Non-blocking (WARN) |
| CLI dependency ready | hcloud available and authenticated | Non-blocking (WARN) |
| i18n/ directory | Directory exists | Non-blocking (WARN) |
| i18n locale format | Locale dirs follow BCP 47 (xx-XX) | Non-blocking (WARN) |
| i18n SKILL files | Each locale has SKILL translation file | Non-blocking (WARN) |
| i18n frontmatter | Translation files have valid frontmatter | Non-blocking (WARN) |
| i18n name match | Translation name matches original SKILL.md | Non-blocking (WARN) |
| Required sections present | Bilingual match: 概述/Overview, 前置条件/Prerequisites, 工作流/Workflow, 核心命令/Core Commands, 参数确认/Parameters, 参考文档/References | Blocking |
| KooCLI section when CLI present | KooCLI命令格式标准 / KooCLI Command Format present if CLI operations detected | Blocking |
| No direct Skill cross-references | SKILL.md does not directly invoke other Skills | Non-blocking (WARN) |

## Phase 2: Basic Functionality Testing

| Acceptance Item | Pass Condition | Blocking Level |
|-----------------|----------------|----------------|
| Trigger identification | Skill correctly loaded | Blocking |
| Core functionality output | Output contains expected content | Blocking |
| Trigger accuracy | >= 90% | Blocking |
| Boundary handling | No fabrication, returns reasonable error | Blocking |
| No false trigger | Unrelated requests not triggered | Blocking |
| With/Without delta | > 0 | Non-blocking |

## Phase 3: Combination Compatibility Testing

| Acceptance Item | Pass Condition | Blocking Level |
|-----------------|----------------|----------------|
| Cross-Skill workflow | Workflow衔接correct | Blocking |
| Competition routing | Routes to correct Skill | Blocking |
| Context isolation | No residual pollution | Blocking |
| Hallucination rate | < 5% | Blocking |
| Responsibility confusion | Did not invoke wrong Skill | Blocking |
| Parameter fabrication | Parameter values within valid range | Blocking |

## Phase 4: Solution-Level Testing

| Acceptance Item | Pass Condition | Blocking Level |
|-----------------|----------------|----------------|
| End-to-end workflow | Full pipeline passes | Blocking |
| Performance met | Time < 300s, Tokens < 50000 | Non-blocking |
| Accuracy rate | > 90% | Blocking |
| Report generated | Four-phase results complete | Blocking |

## Overall Acceptance

**Release Conditions**:
1. All blocking (required) items across four phases PASS
2. Hallucination rate < 5%
3. Test report completely generated
4. No unresolved blocking-level defects

**Recommended Items**:
- Missing recommended items generate WARN but do not block release
- Recommended items include: references/, scripts/, templates/, demo/ directories, IAM policies, executable scripts
- i18n/ directory with locale subdirectories (e.g., i18n/zh-CN/SKILL_CN.md) is recommended for multi-language support
- i18n locale names should follow BCP 47 format (xx-XX like zh-CN, en-US, ja-JP)
- i18n SKILL translation files should have valid frontmatter and name matching original SKILL.md
- WARN count is reported in test report for visibility
