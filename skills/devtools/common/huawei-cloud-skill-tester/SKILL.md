---
name: huawei-cloud-skill-tester
version: 1.0.0
description: |
  1. Execute four-phase testing on Huawei Cloud AI Shell Skills: installation verification, basic functionality, combination compatibility, and solution-level testing (purpose)
  2. Triggered when users need to test Skill quality, verify multi-Skill combination compatibility, detect Agent hallucination, or generate test reports (trigger condition)
  3. Provides structured test framework, hallucination detection mechanism, With/Without comparison evaluation, and automated test scripts to ensure Skill quality before release (value proposition)
  4. Orchestrates test flow via npx skills commands, combined with validate-skill.sh, test-skill.sh, and detect-hallucination.sh scripts (usage)
  5. Requires only SKILL.md as mandatory structure; references/, scripts/, templates/, demo/ are recommended but not required. Test reports distinguish required (PASS/FAIL) from recommended (WARN) checks (prerequisites)
  Triggers include: "测试Skill","Skill测试","华为云Skill测试","测试华为云Skill","Skill质量测试","Skill质量验证","Skill兼容性测试","检测Skill幻觉","Skill幻觉检测","test skill","skill test","test skill quality","verify skill compatibility","detect skill hallucination","skill tester","华为云Skill测试器","帮我测试Skill","帮我验证Skill质量","运行Skill四阶段测试","测试skill质量","验证skill兼容性","检测skill幻觉","skill测试","skill质量验证","华为云skill测试","帮我test skill","运行skill四阶段测试","test华为云Skill","verify skill质量","detect skill幻觉","skill tester测试","测试Skill quality","验证Skill compatibility"
tags: [huawei-cloud, skill-testing, quality-assurance, hallucination-detection, compatibility, devops]
---

# Huawei Cloud Skill Tester

Execute four-phase quality testing on Huawei Cloud AI Shell Skills, covering the full pipeline from installation verification to end-to-end solutions, with built-in hallucination detection and multi-Skill combination compatibility verification.

> **Test Spec:** [`references/test-spec.md`](references/test-spec.md) — Complete four-phase test specification.
> **Test Guide:** [`references/skill-test-guide.md`](references/skill-test-guide.md) — Industry best practices and optimization directions.

## 概述

Current AIShell Skill testing only covers "install → run → uninstall", lacking structured validation, multi-Skill combination testing, hallucination detection, and regression mechanisms. This Skill provides a complete four-phase test framework to ensure Skills meet quality standards at every level — single functionality, multi-Skill collaboration, and end-to-end solutions.

## Design Principles

**Principle 1**: Test Pyramid — Installation verification (many) → Basic functionality (moderate) → Combination compatibility (some) → Solution-level (few). Fast feedback at the bottom, real-world coverage at the top.

**Principle 2**: Hallucination Defense — Apply structured assertions to Agent output, verify Skill routing correctness, detect responsibility confusion and parameter fabrication.

**Principle 3**: Combination First — Multiple Skills under the same cloud service must undergo unified combination testing to verify no conflicts or gaps.

## 前置条件

1. **hcloud CLI** installed with AK/SK authentication configured
   ```bash
   hcloud --version
   hcloud configure list
   ```

2. **Target Skill** installable via npx
   ```bash
   npx skills add <repo> --skill <target-skill-name>
   ```

3. **AIShell** running, Agent can load Skills

4. **Test case configuration** prepared (or generated from template)
   ```bash
   # Generate test cases from template
   cp templates/test-cases.yaml.template ./test-cases.yaml
   ```

## 核心命令

| Command | Description |
|---------|-------------|
| `bash scripts/validate-skill.sh <skill-path> --phase all-install` | Phase 1: Full installation verification |
| `bash scripts/validate-skill.sh <skill-path> --phase i18n` | i18n directory validation |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase all-basic` | Phase 2: All basic functionality tests |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase all-combination --related <s2,s3>` | Phase 3: All combination compatibility tests |
| `bash scripts/detect-hallucination.sh <name> --skill-path <path> --related <s2,s3>` | Hallucination detection |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase solution --scenario <name>` | Phase 4: Solution-level testing |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase full --related <s2,s3> --output ./report.yaml` | Full four-phase pipeline |

## 参数确认

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `<skill-name>` | Yes | Target Skill name | `your-skill-name` |
| `<skill-path>` | Yes | Target Skill directory path | `./skills/<domain>/<your-skill-name>` |
| `--phase` | Yes | Test phase to execute | `all-install`, `all-basic`, `all-combination`, `solution`, `full` |
| `--related` | No | Related Skill names for combination testing | `skill2,skill3` |
| `--scenario` | No | Solution scenario name for Phase 4 | `build-network-env` |
| `--output` | No | Test report output path | `./test-report.yaml` |

## KooCLI命令格式标准

```bash
# General format
hcloud <Service> <Operation> --cli-region=<region> --param1=value1 --param2=value2

# Concrete example
hcloud ECS ListServers --cli-region=cn-north-4

# Idempotent operations (safe to repeat)
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id={instance_id}
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Uppercase PascalCase | `ECS`, `VPC`, `IAM` |
| Operation name | PascalCase | `ListServers`, `ShowServer` |
| Region param | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple param | `--key=value` | `--server_id=xxx` |
| Index param | `--key.1=value1` | `--servers.1.id=xxx` |
| Nested param | `--key.sub_key=value` | `--config.protocol=vnc` |

## 工作流

### Phase 1: Installation Verification

Verify Skill installs correctly, structure is complete, and specification is compliant.

```bash
# Step 1.1: Install target Skill
npx skills add <skill-repo> --skill <target-skill-name>

# Step 1.2: Verify directory structure completeness
bash scripts/validate-skill.sh <skill-path> --phase install

# Step 1.3: Verify YAML Frontmatter specification
bash scripts/validate-skill.sh <skill-path> --phase frontmatter

# Step 1.4: Verify prerequisite dependencies
bash scripts/validate-skill.sh <skill-path> --phase dependency

# Step 1.5: Verify required sections (bilingual matching)
bash scripts/validate-skill.sh <skill-path> --phase sections

# Step 1.6: Run all installation verification at once
bash scripts/validate-skill.sh <skill-path> --phase all-install
```

**Verification Items:**

| Item | Description | Level |
|------|-------------|-------|
| SKILL.md | SKILL.md exists and is readable | Required |
| Frontmatter | name, description (5-point), version, tags compliant | Required |
| references/ | Directory with reference documents | Recommended |
| scripts/ | Directory with test/validate scripts | Recommended |
| templates/ | Directory with templates | Recommended |
| demo/ | Directory with demo examples | Recommended |
| i18n/ | Directory with internationalization translations | Recommended |
| i18n locale format | Locale dirs follow BCP 47 (xx-XX) format | Recommended |
| i18n SKILL files | Each locale has SKILL translation file (e.g., SKILL_CN.md) | Recommended |
| i18n frontmatter | Translation files have valid frontmatter | Recommended |
| i18n name match | Translation name field matches original SKILL.md | Recommended |
| validate script | `validate-skill.sh` executable and passes | Recommended |
| CLI dependency | hcloud available and authenticated | Recommended |
| Reference docs | Key files exist under references/ | Recommended |
| Required sections | Bilingual match: 概述/Overview, 前置条件/Prerequisites, 工作流/Workflow, 核心命令/Core Commands, 参数确认/Parameters, 参考文档/References | Required |
| KooCLI section | KooCLI命令格式标准 / KooCLI Command Format (required if CLI operations present) | Required |
| Cross-Skill refs | No direct Skill cross-references (Agent orchestrates) | Recommended |

#### Section Bilingual Matching Rules

Section detection supports **bilingual matching**: a section is considered present if **any** variant (Chinese or English) is found as a `##`-level heading.

| Section | Chinese Variant | English Variant(s) | Required |
|---------|----------------|--------------------|----------|
| 概述 | `## 概述` | `## Overview` | Yes |
| 前置条件 | `## 前置条件` | `## Prerequisites` | Yes |
| 工作流 | `## 工作流` | `## Workflow`, `## Main Steps` | Yes |
| 核心命令 | `## 核心命令` | `## Core Commands` | Yes |
| 参数确认 | `## 参数确认` | `## Parameters` | Yes |
| 参考文档 | `## 参考文档` | `## References`, `## Reference Documents` | Yes |
| KooCLI命令格式标准 | `## KooCLI命令格式标准` | `## KooCLI Command Format`, `## Huawei Cloud CLI Command Format` | Yes (CLI ops) |

### i18n Directory Testing

Verify internationalization directory structure and translation file compliance.

**Expected structure**: `skillname/i18n/{locale}/SKILL_{suffix}.md`

Example:
```text
skillname/
├── SKILL.md
└── i18n/
    ├── zh-CN/
    │   └── SKILL_CN.md
    ├── ja-JP/
    │   └── SKILL_JP.md
    └── en-US/
        └── SKILL_US.md
```

```bash
# Step i18n.1: Validate i18n directory structure
bash scripts/validate-skill.sh <skill-path> --phase i18n

# Step i18n.2: Run i18n test as part of basic testing
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase i18n
```

**i18n Verification Items:**

| Item | Description | Level |
|------|-------------|-------|
| i18n/ directory | Directory exists | Recommended |
| Locale format | Locale dir names follow BCP 47 (xx-XX) | Recommended |
| SKILL files | Each locale has SKILL translation file | Recommended |
| Frontmatter | Translation files have valid frontmatter | Recommended |
| Name match | Translation name matches original SKILL.md | Recommended |

### Phase 2: Basic Functionality Testing

Verify Skill is correctly triggered in AICLI and core functionality outputs correctly.

```bash
# Step 2.1: Load target Skill and run basic use cases
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase basic

# Step 2.2: Run trigger accuracy test
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase trigger

# Step 2.3: Run boundary/exception use cases
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase boundary

# Step 2.4: Run With/Without comparison test
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase compare

# Step 2.5: Run all basic functionality tests at once
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-basic
```

**Test Types:**

| Type | Method | Target |
|------|--------|--------|
| Trigger identification | Input trigger words, verify Skill is correctly loaded | Trigger accuracy >= 90% |
| Core functionality | Execute typical use cases, verify output contains expected content | Output structure complete |
| Boundary/exception | Input invalid/boundary parameters | Error handling reasonable, no fabrication |
| No false trigger | Input unrelated requests | Skill not incorrectly activated |
| With/Without | Compare same task with/without Skill | Quantified value delta > 0 |

### Phase 3: Combination Compatibility Testing

Verify multiple Skills under the same cloud service work together without conflicts or hallucination.

```bash
# Step 3.1: Identify related Skills in the same service
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase identify-related

# Step 3.2: Run cross-Skill scenario use cases
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase combination --related <skill2,skill3>

# Step 3.3: Run multi-Skill competition test
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase competition --related <skill2,skill3>

# Step 3.4: Run context isolation test
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase isolation --related <skill2,skill3>

# Step 3.5: Run hallucination detection
bash scripts/detect-hallucination.sh <skill-name> --skill-path <skill-path> --related <skill2,skill3>

# Step 3.6: Run all combination tests at once
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-combination --related <skill2,skill3>
```

**Hallucination Detection Items:**

| Hallucination Type | Detection Method | Criterion |
|--------------------|------------------|-----------|
| Responsibility confusion | Verify Agent invokes the Skill matching the request | invoked Skill == expected Skill |
| Parameter fabrication | Verify output parameter values within valid range | parameter value in known service/resource whitelist |
| Workflow stitching error | Verify multi-step workflow step completeness | actual steps == expected step sequence |
| Context pollution | Verify subsequent tasks contain no prior residue | Task B output intersect Task A entities = empty |
| Format hallucination | Verify output structure matches specification | output matches JSON Schema |

### Phase 4: Solution-Level Testing

Verify Skill performance in real business solution end-to-end scenarios.

```bash
# Step 4.1: Run end-to-end solution scenario
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase solution --scenario <scenario-name>

# Step 4.2: Collect performance metrics
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase performance

# Step 4.3: Generate four-phase test report
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase report --output <report-path>
```

**Performance Metrics:**

| Metric | Description | Suggested Threshold |
|--------|-------------|---------------------|
| total_time_seconds | End-to-end total time | < 300s |
| total_tokens | Total token consumption | < 50000 |
| accuracy_rate | Output accuracy rate | > 0.9 |
| hallucination_rate | Hallucination occurrence rate | < 0.05 |
| trigger_accuracy | Trigger accuracy rate | > 0.9 |

## One-Command Full Pipeline

```bash
# Execute all four phases and generate report
bash scripts/test-skill.sh <skill-name> \
  --skill-path <skill-path> \
  --phase full \
  --related <skill2,skill3> \
  --scenario <scenario-name> \
  --output ./test-report.yaml
```

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Target Skill installation fails | Log error, abort subsequent phases, report marks INSTALL_FAIL |
| hcloud CLI not installed | Prompt install command, abort test |
| AK/SK not configured | Prompt configuration steps, abort test |
| Test case config missing | Use default template from templates/ |
| Related Skill not installed | Skip combination test, report marks COMBINATION_SKIP |
| Hallucination detected | Mark HALLUCINATION_DETECTED, log details, continue subsequent tests |
| Agent timeout no response | Mark TIMEOUT, log timeout phase, continue subsequent tests |
| Network unreachable | Mark NETWORK_ERROR, abort tests requiring cloud API |

## Verification Method

### Phase 1 Verification

```bash
# Installation verification pass condition
bash scripts/validate-skill.sh <skill-path> --phase all-install
# Expected output: [PASS] All installation checks passed
```

### Phase 2 Verification

```bash
# Basic functionality test pass condition
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-basic
# Expected: pass_rate >= 0.9, trigger_accuracy >= 0.9
```

### Phase 3 Verification

```bash
# Combination compatibility test pass condition
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-combination --related <skill2>
# Expected: hallucination_rate < 0.05, no conflict errors
```

### Phase 4 Verification

```bash
# Solution-level test pass condition
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase solution --scenario <name>
# Expected: full pipeline passes, performance within thresholds
```

### Test Report

After testing completes, a YAML format report is generated at the specified path. Structure details in [`templates/test-report.yaml.template`](templates/test-report.yaml.template).

Report contains:
- PASS/FAIL status for all test cases across four phases
- Hallucination detection results and details
- Performance metric data
- With/Without comparison delta values
- Overall assessment and recommendations

## 参考文档

- [`references/test-spec.md`](references/test-spec.md) — Complete four-phase test specification
- [`references/skill-test-guide.md`](references/skill-test-guide.md) — Industry best practices and optimization directions
- [`references/iam-policies.md`](references/iam-policies.md) — Required permission policies
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md) — Acceptance criteria
- [`references/hallucination-detection.md`](references/hallucination-detection.md) — Hallucination detection specification
- [`references/quality-checklist.md`](references/quality-checklist.md) — Quality checklist
- [`references/cli-installation-guide.md`](references/cli-installation-guide.md) — CLI installation guide
- [`references/related-commands.md`](references/related-commands.md) — Command quick reference
- [`references/verification-method.md`](references/verification-method.md) — Verification methods

## Script Usage

| Script | Purpose | Example |
|--------|---------|---------|
| `scripts/validate-skill.sh` | Phase 1 installation verification | `bash scripts/validate-skill.sh ./path --phase all-install` |
| `scripts/validate-skill.sh` | i18n directory validation | `bash scripts/validate-skill.sh ./path --phase i18n` |
| `scripts/test-skill.sh` | Phase 2/3/4 test execution | `bash scripts/test-skill.sh <name> --skill-path <path> --phase full` |
| `scripts/test-skill.sh` | i18n test execution | `bash scripts/test-skill.sh <name> --skill-path <path> --phase i18n` |
| `scripts/detect-hallucination.sh` | Hallucination detection | `bash scripts/detect-hallucination.sh <name> --skill-path <path> --related <s2>` |
| `scripts/generate-report.sh` | Test report generation | `bash scripts/generate-report.sh <result-dir> --output report.yaml` |

## Typical Use Cases

### Scenario 1: Test Single Skill Basic Functionality

```text
User: Help me test the <target-skill-name> Skill
Agent:
  1. Phase 1: npx install + structure validation -> PASS
  2. Phase 2: AICLI trigger + core use cases + boundary cases -> PASS
  3. Generate Phase 1+2 test report
```

### Scenario 2: Test Multi-Skill Combination Compatibility

```text
User: Test compatibility between ECS manage and ECS diagnosis Skills
Agent:
  1. Phase 1+2: Test each Skill's basic functionality -> PASS
  2. Phase 3: Combination loading + cross-scenario cases + competition test + hallucination detection -> PASS
  3. Generate combination compatibility test report
```

### Scenario 3: End-to-End Solution Testing

```text
User: Run end-to-end test on VPC networking solution Skills
Agent:
  1. Phase 1+2+3: Basic and combination tests -> PASS
  2. Phase 4: Execute "build complete network environment" solution scenario
  3. Collect performance metrics, generate complete test report
```

### Scenario 4: Detect Skill Hallucination Issues

```text
User: Detect hallucination in your-skill-name under multi-Skill environment
Agent:
  1. Identify related Skill set
  2. Run hallucination detection: responsibility confusion, parameter fabrication, context pollution
  3. Output hallucination detection report, mark HALLUCINATION_DETECTED or PASS
```

## User-Agent Identification

Add User-Agent identification when calling hcloud CLI during testing, for platform Skill usage tracking:

```bash
export HCLOUD_USER_AGENT=HuaweiCloud-Agent-Skills
```

## Key Principles

- **Test Pyramid** — Installation verification (many) → Basic functionality (moderate) → Combination compatibility (some) → Solution-level (few)
- **Hallucination Defense** — Structured assertions + routing verification + whitelist validation, reject format-abnormal output
- **Combination First** — Same-service multi-Skill must undergo unified combination testing
- **Idempotent First** — Prefer read-only/idempotent operations in testing, avoid side effects
- **Isolation** — Each test case independent, no dependency on other case results
- **Repeatability** — Same input produces same output, eliminate randomness
- **Incremental Regression** — Auto-run affected test subset after each change
- **Security First** — No hardcoded AK/SK in tests, destructive operations require confirmation
- **User-Agent** — Add User-Agent identification in CLI calls for tracking
