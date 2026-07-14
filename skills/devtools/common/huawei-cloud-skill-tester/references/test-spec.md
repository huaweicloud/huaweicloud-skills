# Four-Phase Test Specification

> Defines the complete four-phase test specification for huawei-cloud-skill-tester.

## Phase Definitions

### Phase 1: Installation Verification

**Goal**: Verify Skill installs correctly, structure is complete, and specification is compliant.

**Prerequisites**:
- hcloud CLI installed
- AK/SK configured
- npx skills command available

**Test Items**:

| ID | Test Item | Required | Verification Method |
|----|-----------|----------|---------------------|
| I-01 | npx skills add install success | Yes | Command return code = 0 |
| I-02 | SKILL.md exists | Yes | File exists and is readable |
| I-03 | YAML Frontmatter compliant | Yes | name, description (5-point), version, tags exist |
| I-04 | references/ directory exists | No | Directory exists (recommended) |
| I-05 | scripts/ directory exists | No | Directory exists (recommended) |
| I-06 | templates/ directory exists | No | Directory exists (recommended) |
| I-07 | demo/ directory exists | No | Directory exists (recommended) |
| I-08 | validate-skill.sh passes | No | Script execution return code = 0 (recommended) |
| I-09 | CLI dependency ready | No | hcloud --version has output (recommended) |
| I-10 | Reference docs complete | No | Key files exist under references/ (recommended) |
| I-11 | Scripts executable | No | Scripts under scripts/ have execute permission (recommended) |
| I-12 | i18n/ directory exists | No | Directory exists (recommended) |
| I-13 | i18n locale format valid | No | Locale dirs follow BCP 47 (xx-XX) format (recommended) |
| I-14 | i18n SKILL files present | No | Each locale has SKILL translation file (recommended) |
| I-15 | i18n frontmatter valid | No | Translation files have valid frontmatter (recommended) |
| I-16 | i18n name matches original | No | Translation name field matches SKILL.md (recommended) |
| I-17 | SKILL.md required sections present | Yes | Bilingual section check: 概述/Overview, 前置条件/Prerequisites, 工作流/Workflow, 核心命令/Core Commands, 参数确认/Parameters, 参考文档/References |
| I-18 | KooCLI section when CLI present | Yes | KooCLI命令格式标准/KooCLI Command Format required if SKILL.md contains CLI operations |
| I-19 | No direct Skill cross-references | No | SKILL.md should not directly invoke other Skills (recommended) |

**Pass Criteria**: I-01 through I-03, I-17, I-18 all PASS. I-04 through I-16, I-19 generate WARN if missing but do not block.

### Phase 2: Basic Functionality Testing

**Goal**: Verify Skill is correctly triggered in AIShell and core functionality outputs correctly.

**Test Items**:

| ID | Test Item | Required | Verification Method |
|----|-----------|----------|---------------------|
| B-01 | Trigger identification | Yes | Input trigger words, Skill is correctly loaded |
| B-02 | Core functionality output | Yes | Output contains expected structure and content |
| B-03 | Trigger accuracy | Yes | Correct rate >= 90% across 10 trigger words |
| B-04 | Boundary/exception handling | Yes | Invalid input returns error prompt, no fabrication |
| B-05 | No false trigger | Yes | Unrelated requests do not trigger this Skill |
| B-06 | With/Without comparison | Recommended | Output quality with Skill significantly higher than without |

**Pass Criteria**: B-01 through B-05 all PASS, B-06 delta > 0.

### Phase 3: Combination Compatibility Testing

**Goal**: Verify multiple Skills under the same cloud service work together without conflicts or hallucination.

**Prerequisites**:
- Phase 1 and 2 passed
- Related Skills installed

**Test Items**:

| ID | Test Item | Required | Verification Method |
|----|-----------|----------|---------------------|
| C-01 | Cross-Skill scenario workflow | Yes | Multi-Skill sequential collaboration, workflow衔接correct |
| C-02 | Multi-Skill competition routing | Yes | When request matches multiple Skills, routes to correct Skill |
| C-03 | Context isolation | Yes | Preceding and following tasks do not interfere |
| C-04 | Responsibility confusion detection | Yes | Agent did not invoke wrong Skill |
| C-05 | Parameter fabrication detection | Yes | Output parameter values within valid range |
| C-06 | Workflow stitching detection | Yes | Multi-step workflow steps complete, order correct |
| C-07 | Format hallucination detection | Yes | Output structure matches specification |

**Pass Criteria**: C-01 through C-07 all PASS, hallucination rate < 5%.

### Phase 4: Solution-Level Testing

**Goal**: Verify Skill performance in real business solution end-to-end scenarios.

**Prerequisites**:
- Phase 1, 2, and 3 passed

**Test Items**:

| ID | Test Item | Required | Verification Method |
|----|-----------|----------|---------------------|
| S-01 | End-to-end business flow | Yes | Complete user journey full pipeline passes |
| S-02 | Multi-Skill collaboration solution | Recommended | Multi-Skill collaboration completes solution |
| S-03 | Performance metrics met | Yes | Time/Tokens/Accuracy within thresholds |
| S-04 | Test report generated | Yes | Report contains complete four-phase results |

**Pass Criteria**: S-01 through S-04 all PASS.

## Phase Dependencies

## SKILL.md Section Matching Rules

Section detection supports **bilingual matching**: a section is considered present if **any** variant (Chinese or English) is found as a `##`-level heading.

| Section | Chinese Variant | English Variant(s) | Required |
|---------|----------------|--------------------|----------|
| 概述 | `## 概述` | `## Overview` | Yes |
| 前置条件 | `## 前置条件` | `## Prerequisites` | Yes |
| 工作流 | `## 工作流` | `## Workflow`, `## Main Steps` | Yes |
| 核心命令 | `## 核心命令` | `## Core Commands` | Yes |
| 参数确认 | `## 参数确认` | `## Parameters` | Yes |
| 参考文档 | `## 参考文档` | `## References`, `## Reference Documents` | Yes |
| KooCLI命令格式标准 | `## KooCLI命令格式标准` | `## KooCLI Command Format`, `## Huawei Cloud CLI Command Format` | Yes (when CLI ops present) |

**Matching logic**: `grep -qP "^##\s+<variant>" SKILL.md` — if any variant matches, the section is considered present.

**CLI detection**: If SKILL.md body contains `hcloud <Service>` or `npx skills` patterns, the KooCLI section is required; otherwise it is skipped.

**Cross-Skill reference detection**: If SKILL.md references other `huawei-cloud-*` Skill names (excluding its own name), a WARN is emitted recommending Agent orchestration instead of direct invocation.

## Phase Dependencies (original)

```text
Phase 1 (Installation) -> Phase 2 (Basic) -> Phase 3 (Combination) -> Phase 4 (Solution)
```

- If a preceding phase fails, subsequent phases are not entered
- Use `--phase` parameter to start from a specific phase (provided prior phases passed)
- Use `--skip-phase` to skip specific phases (requires explicit confirmation)

## Test Ratio Recommendations

| Phase | Case Ratio | Automation Level |
|-------|------------|------------------|
| Phase 1 | 40% | Fully automated |
| Phase 2 | 30% | Semi-automated |
| Phase 3 | 20% | Semi-automated |
| Phase 4 | 10% | Primarily manual |
