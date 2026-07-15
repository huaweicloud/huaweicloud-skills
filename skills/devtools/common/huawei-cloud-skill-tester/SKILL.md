---
name: huawei-cloud-skill-tester
version: 1.5.0
description: |
  1. Six-phase: Install (Phase 1), Basic (Phase 2), Combination (Phase 3), Solution (Phase 4), Functional (Phase 5) — with Phase 0 Feature Verification upfront (CLI→SDK→API→prompt user)
  2. Lifecycle mode (--lifecycle): Create→Poll→Delete with AK/SK prompt, cost confirm, auto cleanup
  3. SDK/API fallback: non-CLI skills auto-parse Core Commands table, generate SDK/API test cases
  4. Bash script commands: parse bash scripts/ from Core Commands, substitute {path}, execute
  5. Interactive questioning test: auto-detect Socratic 4-dimension flow, validate questioning patterns, one-at-a-time, summary table, user confirmation
  6. Capability detection: read workflow section, detect scaffold/create, test with temp skill from templates
  7. Phase 0 Feature Verification: read target skill features, list for user confirmation before testing
  Triggers include: "测试Skill","Skill测试","华为云Skill测试","功能测试","functional test","生命周期测试","lifecycle test","六步测试","回归测试","帮我测试Skill","test skill quality","检测交互式Skill","interactive test","Socratic测试","socratic test","测试交互式Skill"
tags: [huawei-cloud, skill-testing, functional-testing, lifecycle-testing, hallucination-detection, interactive-testing, devops]
---

# Huawei Cloud Skill Tester

Execute six-phase quality testing on Huawei Cloud AI Shell Skills, covering the full pipeline from feature verification through functional execution, with built-in hallucination detection and multi-Skill combination compatibility verification.

> **Test Spec:** [`references/test-spec.md`](references/test-spec.md) — Complete six-phase test specification.
> **Test Guide:** [`references/skill-test-guide.md`](references/skill-test-guide.md) — Industry best practices and optimization directions.

## 概述

Current AIShell Skill testing only covers "install → run → uninstall", lacking structured validation, multi-Skill combination testing, hallucination detection, regression, and functional execution mechanisms. This Skill provides a complete six-phase test framework (Phase 0–5) to ensure Skills meet quality standards at every level — feature verification, installation, single functionality, multi-Skill collaboration, end-to-end solutions, and real API execution.

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
| `bash scripts/verify-skill-features.sh <skill-path>` | Phase 0: Feature verification (user confirms before testing) |
| `bash scripts/validate-skill.sh <skill-path> --phase all-install` | Phase 1: Full installation verification (includes install, frontmatter, dependency, sections, i18n, security, lifecycle) |
| `bash scripts/validate-skill.sh <skill-path> --phase uninstall --install-mode local` | Phase 1: Install/uninstall lifecycle (5-step) |
| `bash scripts/validate-skill.sh <skill-path> --phase i18n` | Phase 1: i18n directory validation |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase all-basic` | Phase 2: All basic functionality tests |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase security` | Phase 2: Security pattern scan (hardcoded credentials) |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase all-combination --related <s2,s3>` | Phase 3: All combination tests + hallucination detection |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase identify-related` | Phase 3: Identify related skills |
| `bash scripts/detect-hallucination.sh <name> --skill-path <path> --related <s2,s3>` | Hallucination detection |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase solution --scenario <name>` | Phase 4: Solution-level testing |
| `bash scripts/functional-test.sh <name> --skill-path <path> --region cn-north-4` | Phase 5: Full six-step functional test |
| `bash scripts/functional-test.sh <name> --skill-path <path> --dry-run` | Phase 5: Dry run (parse only, no execution) |
| `bash scripts/functional-test.sh <name> --skill-path <path> --regression-base <prev> --output <report>` | Phase 5: Regression comparison |
| `bash scripts/test-skill.sh <name> --skill-path <path> --phase full --related <s2,s3> --output ./report.yaml` | Full six-phase pipeline (Phase 0–5) |

## 参数确认

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `<skill-name>` | Yes | Target Skill name | `your-skill-name` |
| `<skill-path>` | Yes | Target Skill directory path | `./skills/<domain>/<your-skill-name>` |
| `--phase` | Yes | Test phase to execute | `all-install`, `uninstall`, `i18n`, `all-basic`, `security`, `all-combination`, `identify-related`, `solution`, `functional`, `all-functional`, `full` |
| `--related` | No | Related Skill names for combination testing | `skill2,skill3` |
| `--scenario` | No | Solution scenario name for Phase 4 | `build-network-env` |
| `--output` | No | Test report output path | `./test-report.yaml` |
| `--install-mode` | No | Installation mode for lifecycle test: `local` (default) or `online` | `local` |
| `--region` | No | Huawei Cloud region for functional tests | `cn-north-4` |

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

### Phase 0: Feature Verification (NEW)

Verify target Skill's main features are correctly understood before starting any tests. The user reviews and confirms the parsed feature list.

```bash
# Step 0.1: Read and display target skill features
bash scripts/verify-skill-features.sh <skill-path>

# Step 0.2: User confirms (y) or rejects (n) — loops until confirmed
# Step 0.3: On confirmation, proceed to Phase 1
```

**Verification Items:**

| Item | Description | Level |
|------|-------------|-------|
| Description points | 5-point description correctly parsed | Required |
| Core Operations | CLI/SDK/API commands correctly extracted | Required |
| Triggers | Trigger keywords correctly identified | Required |
| Workflow scenarios | Business scenarios correctly detected | Recommended |

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

# Step 1.6: Verify i18n directory structure and translation files
bash scripts/validate-skill.sh <skill-path> --phase i18n

# Step 1.7: Run security pattern scan (sec.secret.leak -- hardcoded credentials)
bash scripts/validate-skill.sh <skill-path> --phase security

# Step 1.8: Run install/uninstall lifecycle (5-step: Install -> Verify -> Uninstall -> Verify -> Reinstall)
bash scripts/validate-skill.sh <skill-path> --phase uninstall --install-mode local

# Step 1.9: Run all installation verification at once (includes install, frontmatter, dependency, sections, i18n, security, and lifecycle)
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
| Install lifecycle | Install → Verify installed → Uninstall → Verify uninstalled → Reinstall | Required |
| Install mode local | `npx skills add <path> --skill <name>` local install succeeds | Required |
| Install mode online | `npx skills add <repo> --skill <name>` online install succeeds | Required |
| Verify installation | Skill appears in `npx skills list` after install | Required |
| Uninstall | `npx skills remove <name>` succeeds | Required |
| Verify uninstallation | Skill no longer in `npx skills list` after remove | Required |
| Reinstall | Skill reinstalled after lifecycle for subsequent tests | Required |

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

#### i18n Directory Testing

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

Verify Skill is correctly triggered in AICLI and core functionality outputs correctly. Note: when running as part of `--phase full`, i18n and uninstall checks are already covered by Phase 1 and skipped here to avoid duplication.

```bash
# Step 2.1: Verify description has 5-point structure (Phase 1 covers structural validation)
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase basic

# Step 2.2: Run trigger accuracy test
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase trigger

# Step 2.3: Run boundary/exception use cases
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase boundary

# Step 2.4: Run With/Without comparison test
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase compare

# Step 2.5: Run i18n directory validation
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase i18n

# Step 2.6: Run security pattern scan (sec.secret.leak — hardcoded credentials)
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase security

# Step 2.7: Run install/uninstall lifecycle test (Install → Verify → Uninstall → Verify → Reinstall)
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase uninstall

# Step 2.8: Run all basic functionality tests at once (basic + trigger + boundary + compare + i18n + security + uninstall)
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

# Step 4.3: Generate six-phase test report
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

### Phase 5: Functional Testing (NEW)

Verify Skill functionality through a six-step lifecycle: parse SKILL.md commands, auto-generate test cases, define scoring criteria, execute hcloud CLI commands against real APIs, classify bugs by severity, and support regression testing.

**Lifecycle Mode** (`--lifecycle`): For Skills with resource Create/Delete operations, chains end-to-end workflow with AK/SK prompt, cost confirmation, variable passing, resource polling, and automatic cleanup.

**Executor Backend** (`--executor`): Three-tier execution backend that auto-detects the best available tool — CLI → SDK → API.

**Interactive Questioning Test**: For meta-skills with Socratic questioning flow (e.g., skill-creator), auto-detects 4 questioning dimensions (Target service, Function scope, CLI operations, Trigger scenarios) and validates questioning patterns: one-at-a-time, summary table after 5 questions, user confirmation before proceeding, and mandatory interactive phase declaration.

**Interactive E2E Creation Test** (NEW): For skills with both Socratic questioning AND template scaffolding, runs a complete end-to-end creation pipeline — takes preset 4-dimension answers, scaffolds a complete skill from templates (SKILL.md, references, scripts, i18n), validates the created skill structure, tests its CLI commands, and verifies the output matches the input answers.

```bash
# Step 5.1: Run full six-step functional test
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --region cn-north-4

# Step 5.2: Specify execution backend
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --executor auto   # auto-detect (default)
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --executor cli    # force hcloud CLI
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --executor sdk    # force Python SDK
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --executor api    # force REST API

# Step 5.3: Lifecycle mode — Create → Poll → Delete (with AK/SK + cost confirm)
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --lifecycle --region cn-north-4

# Step 5.4: Lifecycle mode dry run (parse workflow, no API calls)
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --lifecycle --dry-run

# Step 5.5: Run with regression comparison against previous report
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> \
  --regression-base <previous-report.yaml> --output <report.yaml>

# Step 5.6: Run as part of all-functional test pipeline
bash scripts/test-skill.sh <skill-name> --skill-path <skill-path> --phase all-functional

# Step 5.7: Lifecycle mode with real resource values (required for Create/Delete skills)
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> \
  --lifecycle --region cn-north-4 --yes --test-vars references/test-vars.json

# Step 5.8: Interactive E2E creation test (for skills with Socratic + scaffold, e.g., skill-creator)
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --region cn-north-4
# Auto-detects interactive_e2e capability and runs the full creation pipeline
```

**Six-Step Functional Test Flow:**

| Step | Description | Verification |
|------|-------------|-------------|
| Step 1: 准备与配置 | Parse SKILL.md metadata and extract service commands | Service detected, commands parsed |
| Step 2: 设计测试用例 | Auto-generate CLI, trigger, boundary, workflow, interactive, and lifecycle test cases | ≥1 test case generated |
| Step 3: 评分与评估标准 | Define weights (execution 30%, accuracy 35%, completeness 20%, format 15%) | Scoring criteria defined |
| Step 4: 自动化执行与验证 | Execute hcloud commands, verify exit code and output content | Execution rate ≥90% |
| Step 5: 结果分析与分类 | Classify bugs by severity (critical/major/minor/suggestion), RCA | Zero critical bugs |
| Step 6: 迭代优化 | Compare with previous baseline, detect regressions | No regression spikes |

**Lifecycle Mode** (`--lifecycle`): Replaces Step 4 with a chained workflow:

| Lifecycle Step | Description | Security Checks |
|----------------|-------------|-----------------|
| 0. Authentication | Check hcloud auth, prompt AK/SK if missing | Credentials never stored in scripts |
| 1. Create resource | Execute Create command, capture resource ID | Cost confirmation required |
| 2. Poll until ACTIVE | Poll Show/List every 10s until ready (timeout: 120s) | Read-only, no side effects |
|| 3. Delete resource | Delete created resource, poll until DELETED | Cost confirmation required, auto-cleanup on failure |

**⚠ 强制性约束：生命周期测试必须执行实际功能操作**

生命周期模式直接从 SKILL.md 提取命令文本并逐字执行。如果命令中包含 `{vpc_id}`、`{image_id}`、`{subnet_id}` 等占位符，会被作为字面字符串传给 hcloud CLI 导致参数验证错误。

**解决方案：** 被测试的 Skill **必须**提供 `references/test-vars.json`，包含真实资源 ID。格式示例：

```json
{
  "vpc_id": "0b4171c1-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "subnet_id": "fa5fb1a9-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "image_id": "74d6130f-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "flavor": "kc1.small.1",
  "region": "cn-north-4"
}
```

运行生命周期测试时加 `--test-vars` 参数：

```bash
bash scripts/functional-test.sh <skill-name> --skill-path <path> \
  --lifecycle --region cn-north-4 --yes --test-vars references/test-vars.json
```

脚本会自动将命令中的 `{key}` 和 `<key>` 占位符替换为 JSON 中的值。只读命令（ListFlavors、ShowServer 等）不受影响。

**Scoring Dimensions:**

| Dimension | Weight | Threshold | Description |
|-----------|--------|-----------|-------------|
| Execution | 30 pts | ≥90% | Did the command execute without error? |
| Accuracy | 35 pts | ≥85% | Does output contain all expected content? |
| Completeness | 20 pts | ≥80% | Are all required fields present? |
| Format | 15 pts | ≥90% | Is output structure well-formed? |

**Bug Severity Levels:**

| Severity | Score | Description | Action |
|----------|-------|-------------|--------|
| CRITICAL | 0.0 | Command fails, wrong API, security issue | Blocks release |
| MAJOR | 0.5 | Missing required fields, incorrect output | Must fix before release |
| MINOR | 0.8 | Format deviation, non-critical missing info | Should fix if time |
| SUGGESTION | 1.0 | Performance optimization, best practice | Nice to have |

## One-Command Full Pipeline (Phase 0–5)

```bash
# Execute all six phases (Phase 0–5) and generate report
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
| hcloud command fails (functional test) | Classify as CRITICAL bug, log command + output, continue remaining tests |
| No hcloud commands in SKILL.md | Mark FUNCTIONAL_SKIP (non-CLI skill), skip functional execution |
| Regression: new failures detected | Mark REGRESSION_DETECTED, list delta, flag for investigation |
| Functional test dry run | Parse and generate test cases only, no API calls |
| Interactive questioning skill detected | Auto-generate Socratic pattern tests: 4 dimensions, one-at-a-time, summary table, user confirm |
| Interactive skill missing dimension | Mark DIMENSION_MISSING for each of 4 questioning dimensions not found in SKILL.md |
| Interactive + scaffold skill detected | Auto-run interactive_e2e test: scaffold skill from templates, validate, test CLI, verify answers |

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

### Phase 5 Verification

```bash
# Functional test pass condition
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --region cn-north-4
# Expected: overall >= 85%, execution >= 90%, accuracy >= 85%, 0 critical bugs

# Dry run (parse only, no API calls)
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --dry-run
# Expected: test cases generated, no execution errors

# Regression test
bash scripts/functional-test.sh <skill-name> --skill-path <skill-path> --regression-base <prev-report>
# Expected: no new failures compared to baseline
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

- [`references/test-spec.md`](references/test-spec.md) — Complete six-phase test specification
- [`references/functional-test-spec.md`](references/functional-test-spec.md) — Six-step functional testing specification (NEW)
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
| `scripts/test-skill.sh` | Functional test execution | `bash scripts/test-skill.sh <name> --skill-path <path> --phase functional` |
| `scripts/functional-test.sh` | Phase 5 six-step functional test | `bash scripts/functional-test.sh <name> --skill-path <path> --region cn-north-4` |
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

### Scenario 5: Run Six-Step Functional Test (NEW)

```text
User: Do a functional test on the huawei-cloud-ecs-manage Skill
Agent:
  1. Step 1: Parse SKILL.md, extract ECS service commands (ListServers, ShowServer, etc.)
  2. Step 2: Auto-generate test cases (CLI commands + trigger + boundary + workflow)
  3. Step 3: Apply scoring criteria (execution 30%, accuracy 35%, completeness 20%, format 15%)
  4. Step 4: Execute hcloud CLI commands against cn-north-4, verify exit codes and output
  5. Step 5: Classify any failures by severity (critical/major/minor/suggestion)
  6. Step 6: Compare with previous run (if --regression-base provided)
  7. Generate functional test report
```

### Scenario 6: Functional Dry Run (NEW)

```text
User: Run a functional test dry run on the vpc-manage Skill (don't execute commands)
Agent:
  1. Step 1: Parse SKILL.md, extract VPC commands
  2. Step 2: Generate test cases: TC-FUNC-001 (VPC ListVpcs), TC-FUNC-002 (VPC ShowVpc), etc.
  3. Step 3: Display scoring criteria and thresholds
  4. Report: "Dry run completed — 5 test cases ready. Run without --dry-run to execute."
```

### Scenario 7: Lifecycle E2E: Create ECS → Verify → Delete (NEW)

```text
User: Run lifecycle test on the huawei-cloud-ecs-manage Skill
Agent:
  1. Check hcloud authentication → prompt for AK/SK if needed
  2. Parse SKILL.md → detect CreateServer, ShowServer, DeleteServer
  3. Display cost warning for ECS CreateServer (s6.small.1, cn-north-4)
  4. After user confirmation: execute CreateServer → capture server_id
  5. Poll ShowServer every 10s until status == "ACTIVE" (timeout: 120s)
  6. Display cost warning for ECS DeleteServer
  7. After user confirmation: execute DeleteServer
  8. Poll ShowServer until 404/not found (confirm deletion)
  9. Generate lifecycle test report
  10. IF ANY STEP FAILS: cleanup_resources() trap ensures server is deleted
```

### Scenario 8: Test Interactive Socratic Skill (NEW)

```text
User: Run an interactive test on the huawei-cloud-skill-creator Skill
Agent:
  1. Step 1: Parse SKILL.md — detect Socratic questioning flow, 4 dimensions
  2. Step 2: Auto-generate interactive test cases:
     - socratic_pattern: Socratic questioning pattern detected?
     - one_at_a_time: One question at a time?
     - summary_table: Summary table requirement?
     - user_confirm: User confirmation requirement?
     - dimension_1~4: Each of 4 questioning dimensions covered?
     - mandatory_phase: Mandatory interactive phase declared?
     - overall: Overall interactive quality score
  3. Step 3-4: Validate each interactive pattern against SKILL.md content
  4. Step 5: Report which dimensions are covered/missing
  5. Generate interactive test report with PASS/FAIL for each pattern
```

### Scenario 9: Interactive E2E — Create Then Test a Skill (NEW)

```text
User: Test the full creation pipeline of huawei-cloud-skill-creator
Agent:
  1. Step 1: Detect Socratic questioning + template scaffolding → interactive_e2e capability
  2. Step 2: Generate interactive_e2e test case: full creation pipeline
  3. Step 4: Run interactive-e2e-test.sh with preset 4-dimension answers:
     - Dimension 1 (Target service): ECS
     - Dimension 2 (Function scope): Inspect and diagnose ECS instances
     - Dimension 3 (CLI operations): ListServers, ShowServer
     - Dimension 4 (Trigger scenarios): 检查ECS, inspect ecs
  4. Scaffold: Create skill from templates → render SKILL.md + references/ + scripts/ + i18n/
  5. Validate: Run validate-skill.sh on created skill → verify structure, frontmatter, sections
  6. Test: Run test-cli-commands.sh on created skill → verify CLI commands work
  7. Verify: Confirm created SKILL.md references correct service, triggers, and operations
  8. Report: Pass/fail summary of the full interactive creation pipeline
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

<!-- SLOW_UPDATE_START -->
## Critical Answer Reference — Must Surface When Asked

When asked about any of the following topics, always provide the explicit answer below. Do not defer to referenced documents or give vague summaries.

### AK/SK Security Rule (qa_004)
Never hardcode AK/SK credentials in any Skill code, test script, or configuration file. Always authenticate via `hcloud configure` (interactive) or environment variables (`HCLOUD_AK` / `HCLOUD_SK`). Any test or script that requires authentication must obtain credentials exclusively through these runtime mechanisms.

### Huawei Cloud CLI Command Format (qa_011)
Format: `hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]`
- Service: PascalCase, uppercase (e.g., `ECS`, `VPC`, `IAM`, `RDS`, `CCE`)
- Operation: PascalCase (e.g., `ListServers`, `ShowServer`, `CreateServer`)
- Region: always `--cli-region=<value>` (e.g., `--cli-region=cn-north-4`)
- Simple params: `--key=value`
- Indexed params: `--key.1=value1 --key.2=value2`
- Nested params: `--key.sub_key=value`

### Test Result Categorization (qa_020)
Test results are categorized into two levels:
- **Required checks**: result is PASS or FAIL. Failure means the Skill does not meet mandatory quality standards.
- **Recommended checks**: result is WARN if not met. Warning means the Skill lacks an optional but strongly recommended element (e.g., references/, scripts/, templates/, demo/, i18n/).

### Cost Confirmation for Resource-Mutating Operations (qa_007)
Any operation that creates, modifies, or deletes cloud resources (e.g., ECS CreateServer, VPC DeleteVpc) must: (1) display the estimated cost or resource impact to the user, and (2) obtain explicit user confirmation before execution. Read-only operations (List*, Show*) are exempt. In test environments, prefer idempotent read-only operations; if a mutating test is necessary, use `--dry-run` where available or wrap in a confirmation prompt.

### Skill Versioning Scheme (qa_009)
Skills MUST follow Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH` (e.g., `1.0.0`).
- MAJOR: breaking changes to Skill interface or workflow
- MINOR: new functionality added backward-compatibly
- PATCH: bug fixes or documentation corrections
The version field in SKILL.md frontmatter must be updated on every release.

### iam-policies.md Required Contents (qa_014)
The `references/iam-policies.md` file must include:
1. Minimum IAM permissions (policy actions) required for each operation the Skill performs
2. Grouped by cloud service (e.g., ECS, VPC, IAM)
3. Recommended policy name or custom policy JSON template
4. Distinction between read-only permissions (needed for basic testing) and write permissions (needed for resource-mutating operations)

### SKILL.md Body Line Limit (qa_015)
The recommended body line limit for SKILL.md is 500 lines (excluding frontmatter). Skills exceeding this limit should split detailed content into reference documents under `references/` and keep SKILL.md as a concise entry point with links.

### Workflow Steps for Creating a Skill (qa_013)
The 10 standard workflow steps for creating a Huawei Cloud AI Shell Skill are:
1. Define Skill scope and target cloud service operations
2. Create SKILL.md with frontmatter (name, description, version, tags)
3. Write required sections: 概述/Overview, 前置条件/Prerequisites, 工作流/Workflow, 核心命令/Core Commands, 参数确认/Parameters, 参考文档/References
4. Add KooCLI命令格式标准 section if the Skill uses CLI operations
5. Create reference documents under references/ (test-spec, iam-policies, quality-checklist)
6. Create test/validate scripts under scripts/ (validate-skill.sh, test-skill.sh)
7. Create templates under templates/ for test cases and reports
8. Add i18n translations under i18n/{locale}/SKILL_{suffix}.md
9. Run Phase 1 installation verification: `bash scripts/validate-skill.sh <path> --phase all-install`
10. Run full six-phase test pipeline: `bash scripts/test-skill.sh <name> --skill-path <path> --phase full` and fix any failures
<!-- SLOW_UPDATE_END -->
