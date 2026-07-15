# Functional Test Specification

> Defines the six-step functional testing framework for Huawei Cloud AI Shell Skills, executed by `scripts/functional-test.sh`.
> Includes **Lifecycle Mode** (`--lifecycle`) for end-to-end resource Create→Verify→Delete workflows.

## Overview

Functional testing verifies that a Skill actually works — its hcloud CLI commands execute correctly, output contains expected content, edge cases are handled, and the overall quality meets release thresholds.

Unlike Phase 1 (structural validation) and Phase 2 (basic functionality), functional testing actually **runs the Skill's commands** against real cloud resources and evaluates the results.

## Lifecycle Mode (--lifecycle)

Lifecycle mode chains resource creation, state verification, and deletion into a single end-to-end workflow, with automatic variable passing, polling, and cleanup.

**Workflow pattern**: `Create → Show/List (poll until ACTIVE) → Delete (confirm DELETED)`

### When to Use

| Mode | When | What it does |
|------|------|-------------|
| Standard (default) | Non-CLI skills, read-only operations | Independent test cases, no side effects |
| `--lifecycle` | Skills with Create/Delete operations | Chained workflow, real resource lifecycle |

### Workflow Detection

The script automatically detects lifecycle workflow from SKILL.md's Core Commands section:

- Looks for `Create`/`Add`/`Allocate` commands → identifies as step 1
- Looks for `Show`/`Get`/`List`/`Query` commands → identifies as step 2 (poll target)
- Looks for `Delete`/`Remove`/`Release`/`Terminate` commands → identifies as step 3
- All three must exist for the same service (e.g., ECS)

### Variable Capture

When a resource is created, the script extracts the resource ID from the output by trying these patterns:

1. `"id": "<value>"` (JSON)
2. `"server_id": "<value>"` (JSON)
3. `"instance_id": "<value>"` (JSON)
4. UUID pattern: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

The captured ID is substituted into subsequent commands via `{server_id}`, `{instance_id}`, or `{id}` placeholders.

### Resource Polling

After creation, the script polls the Show/List command every 10 seconds until:
- Target status (default: `ACTIVE`) appears in output → success
- Timeout (default: 120s) → failure
- Status updates printed every 30s

### Deferred Cleanup

A `trap` is registered on `EXIT` to ensure resources are cleaned up even on failure:
- Resources deleted in reverse creation order (LIFO)
- Up to 3 retries with 5s delay between attempts
- Can be disabled via `--skip-cleanup` (dangerous)

### AK/SK Authentication

When `--lifecycle` is used, the script checks hcloud authentication:
1. If already authenticated, proceed
2. If `HCLOUD_AK` / `HCLOUD_SK` env vars set, use them
3. Otherwise, prompt user interactively for AK/SK

### Cost Confirmation

Before any destructive operation (Create or Delete), the script shows:
- Operation type and target
- Resource details
- Warning about potential charges (for Create)

User must confirm with `y`/`Y` unless `--yes` flag is set.

## Six-Step Framework

### Execution Backend (--executor)

The script supports three execution backends, tried in priority order in `auto` mode:

| Backend | Tool | Requires | Auto-install? |
|---------|------|----------|---------------|
| **CLI** (priority 1) | `hcloud` CLI | hcloud binary + AK/SK configured | No |
| **SDK** (priority 2) | Python SDK | `huaweicloudsdkcore` + service SDK, `HCLOUD_AK`/`HCLOUD_SK` env | Yes (`pip install`) |
| **API** (priority 3) | `curl` + Python signing | `curl`, `python3`, `HCLOUD_AK`/`HCLOUD_SK` env | No (stdlib only) |

**Priority Resolution** (`--executor auto`):
1. If `hcloud` CLI is installed → use CLI
2. Else if `huaweicloudsdkcore` is importable → use SDK
3. Else if `curl` + Python stdlib available → use API
4. If none available → error with install instructions

**SDK Mode**: Generates a temporary Python script that:
- Imports `huaweicloudsdk{service}.v1` dynamically
- Creates a client with `HCLOUD_AK`/`HCLOUD_SK` credentials
- Translates `hcloud Service Operation --key=val` into SDK calls
- Outputs JSON response

**API Mode**: Generates a Python signer that:
- Constructs the REST API endpoint from the service+operation mapping
- Signs the request using SDK-HMAC-SHA256 (Huawei Cloud AK/SK v2)
- Executes via `curl` with signed headers
- Returns the API JSON response

### Step 1: 准备与配置 (Preparation & Configuration)

**Goal**: Parse SKILL.md metadata and extract test parameters.

**Activities**:
| Activity | Description | Verification |
|----------|-------------|-------------|
| Parse SKILL.md | Read and validate SKILL.md exists | PASS: file found, FAIL: not found |
| Extract metadata | Read name, version, tags from YAML frontmatter | PASS: all required fields present |
| Parse service operations | Extract all `hcloud <Service> <Operation>` lines from Core Commands section | PASS: ≥1 command found |
| Detect cloud service | Infer target service from tags, path, or commands | PASS: detected, WARN: unknown |
| Define evaluation thresholds | Set scoring criteria for execution, accuracy, completeness, format | PASS: thresholds configured |

**Input**: SKILL.md file path
**Output**: SERVICE, PARSED_COMMANDS[], thresholds

---

### Step 2: 设计测试用例 (Test Case Design)

**Goal**: Auto-generate structured test cases from the Skill's command definitions.

**Test Case Types**:

| Type | Source | Count | Purpose |
|------|--------|-------|---------|
| CLI Command | Parsed `hcloud` commands from SKILL.md | N (one per command) | Execute each command and verify output |
| Trigger | Declaration in description (Triggers include:) | ≤5 | Verify trigger keywords activate the skill |
| Boundary | Generated from service context | 1 | Test error handling with invalid input |
| Workflow | ≥2 commands from same service | 1 | Verify multi-step coherence |

**Test Case Schema**:
```
{
  "id": "TC-FUNC-001",
  "name": "ECS ListServers",
  "type": "cli_command|trigger|boundary|workflow",
  "command": "hcloud ECS ListServers --cli-region=cn-north-4",
  "expect": {
    "exit_code": 0,
    "contains": ["expected", "patterns"],
    "not_contains": ["Error", "Traceback"]
  },
  "weight": {
    "execution": 30,
    "accuracy": 35,
    "completeness": 20,
    "format": 15
  }
}
```

**Output**: TEST_CASES[] array of generated test case objects

---

### Step 3: 评分与评估标准 (Scoring & Evaluation Criteria)

**Goal**: Define quantitative scoring dimensions and severity levels.

**Scoring Dimensions**:

| Dimension | Weight | Description | Threshold |
|-----------|--------|-------------|-----------|
| Execution | 30 pts | Did the command execute without error? | ≥90% success |
| Accuracy | 35 pts | Does output contain all expected content? | ≥85% match |
| Completeness | 20 pts | Are all required fields present? | ≥80% coverage |
| Format | 15 pts | Is output structure well-formed? | ≥90% compliance |

**Total score**: Weighted average of all four dimensions.

**Severity Levels**:

| Severity | Score Impact | Description | Action |
|----------|-------------|-------------|--------|
| CRITICAL | 0.0 | Command fails, wrong API, security issue | Blocks release |
| MAJOR | 0.5 | Missing required fields, incorrect output | Must fix before release |
| MINOR | 0.8 | Format deviation, non-critical missing info | Should fix if time |
| SUGGESTION | 1.0 | Performance optimization, best practice | Nice to have |

**Pass Thresholds**:

| Level | Threshold | Meaning |
|-------|-----------|---------|
| Overall | ≥0.85 (85%) | Release-ready |
| Per-dimension | See above | Each dimension must meet its threshold |
| Bug severity | 0 critical + 0 major | No blocking bugs |

---

### Step 4: 自动化执行与验证 (Automated Execution & Verification)

**Goal**: Execute hcloud CLI commands and verify output against expectations.

**Execution Flow**:

```
For each test case:
  1. If CLI command: run via `bash -c "<command>"` with 30s timeout
  2. Capture exit code and stdout/stderr
  3. Verify:
     a. Exit code == 0 (or any if expect_any_exit)
     b. Output CONTAINS all expected patterns
     c. Output NOT_CONTAINS any forbidden patterns
  4. Record PASS/FAIL per check
  5. On FAIL: classify_bug() with severity + root cause
```

**Verification Rules**:

| Rule | Check | Expected |
|------|-------|----------|
| Exit code | `$? == 0` | Command succeeded |
| Contains | `grep -qi` (case-insensitive) | All expected patterns present |
| Not contains | `grep -qi` (case-insensitive) | No forbidden patterns found |
| Timeout | `timeout 30` | Command completes in ≤30s |

**Output**: PASS_COUNT, FAIL_COUNT, WARN_COUNT, BUGS[]

---

### Step 5: 结果分析与分类 (Analysis & Bug Classification)

**Goal**: Classify test failures by severity, perform root cause analysis.

**Bug Classification**:

| Bug Type | Common Patterns | Severity | Example |
|----------|----------------|----------|---------|
| Command execution failure | Exit code != 0, timeout | CRITICAL | `hcloud ECS ListServers` returns 1 |
| Output accuracy issue | Missing expected content | MAJOR | Output missing expected field |
| Unexpected content | Forbidden pattern found | MAJOR | Error message in output |
| Format deviation | Non-standard output format | MINOR | JSON not properly indented |
| Performance concern | Slow execution | SUGGESTION | Command takes >10s |

**Root Cause Analysis Buckets**:

| Bucket | Criteria | Fix Strategy |
|--------|----------|-------------|
| command_execution | Exit code, timeout, crash | Fix command syntax, check API availability |
| output_accuracy | Missing/extra content | Update skill templates, check API response |
| format_error | Structure/schema mismatch | Standardize output format |
| other | Uncategorized | Manual investigation |

**Output**: Bug severity distribution, root cause breakdown, detailed bug list

---

### Step 6: 迭代优化 (Regression & Optimization)

**Goal**: Compare current run with previous baseline, detect regressions.

**Regression Comparison**:

| Metric | Comparison | Actionable |
|--------|-----------|------------|
| Pass count delta | Current - Previous | New passes = improvements |
| Fail count delta | Current - Previous | New failures = regressions |
| Warn count delta | Current - Previous | More warnings = quality drift |

**Optimization Suggestions**:

| Condition | Suggestion |
|-----------|-----------|
| WARN_COUNT > 0 | Address warnings to improve test quality |
| TEST_CASES < 3 | Expand test coverage |
| Any regression | Investigate and fix regressions |

**Output**: Regression deltas, optimization suggestions

## Phase Dependencies

```
Step 1 (Preparation) → Step 2 (Test Design) → Step 3 (Scoring)
  → Step 4 (Execution) → Step 5 (Analysis) → Step 6 (Regression)
```

- Each step depends on the output of the previous step
- Use `--phase` to start from a specific step (if prior steps completed)
- The `all` phase runs all six steps sequentially and generates a report

## Usage Examples

```bash
# Full six-step functional testing
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --region cn-north-4 \
  --verbose

# Lifecycle mode: Create → Poll → Delete (with AK/SK prompt + cost confirm)
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --lifecycle \
  --region cn-north-4

# Lifecycle mode with auto-confirm (non-interactive)
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --lifecycle \
  --region cn-north-4 \
  --yes

# Lifecycle dry run (parse workflow, check auth, no API calls)
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --lifecycle \
  --dry-run

# Lifecycle with custom poll timeout and skip cleanup
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --lifecycle \
  --poll-timeout 180 \
  --skip-cleanup

# Dry run: parse and generate test cases only, no execution
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --dry-run

# Single step execution (e.g., just run tests, skip preparation)
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --phase step4

# Regression testing with previous report
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --regression-base ./functional-report.yaml \
  --output ./regression-report.yaml

# Use Python SDK instead of CLI
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --executor sdk \
  --region cn-north-4

# Use REST API directly (requires HCLOUD_AK/HCLOUD_SK env vars)
bash scripts/functional-test.sh huawei-cloud-ecs-manage \
  --skill-path ./skills/compute/huawei-cloud-ecs-manage \
  --executor api \
  --region cn-north-4

# Override detected service
bash scripts/functional-test.sh huawei-cloud-vpc-manage \
  --skill-path ./skills/network/huawei-cloud-vpc-manage \
  --service VPC
```

## Pass Criteria

| Step | Required | Recommended |
|------|----------|-------------|
| Step 1 | SKILL.md parseable, metadata extracted | Service detection |
| Step 2 | ≥1 test case generated | Mixed test case types |
| Step 3 | Scoring criteria defined | All thresholds set |
| Step 4 | All CLI commands execute | Execution rate ≥90% |
| Step 5 | Bug classification complete | 0 critical + 0 major bugs |
| Step 6 | Baseline recorded | No regressions |
| All | Overall score ≥85% | All dimensions meet thresholds |
