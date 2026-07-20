---
name: huawei-cloud-skill-tester
description: |
  End-to-end functional testing framework for Huawei Cloud skills — three-tier pipeline covering
  single-skill unit testing, multi-skill orchestration, and end-to-end full flow testing.
  Each phase produces structured JSON output with chain verification.
  Supports skill installation validation, functional analysis, CLI→SDK→API feasibility research,
  test case generation, real-environment execution with resource lifecycle, resource cleanup,
  multi-skill scenario orchestration, trigger-conflict detection, and consolidated reporting.
  Triggers include: 测试技能, 执行技能测试, 跑测试流程, 技能回归测试,
  skill test, run skill tests, test huawei cloud skill, verify skill,
  测试华为云skill, 全流程测试, 编排测试, 技能完整性检查,
  skill-tester, 跑测试, 回归测试, 组合测试, 多skill编排, verification, e2e.
tags: [huawei-cloud, testing, e2e, orchestration, qa]
---

# Huawei Cloud Skill Tester — Three-Track Eight-Phase E2E Testing Pipeline

> Independent, repeatable Huawei Cloud Skill testing framework. Does not depend on skill-creator; can test any existing Huawei Cloud Skill.
> Focuses on **real-environment functional testing** and **multi-skill orchestration scenarios**.

---

## Overview

This Skill provides a **three-track, eight-phase** standardized testing pipeline:

| Tier | Phases | Goal |
|------|--------|------|
| **Tier 1: Single-Skill Unit Testing** | Phase 0~5 | Verify each skill item by item: installation, feature extraction, technical research, test case generation, execution, cleanup |
| **Tier 2: Integration Testing** | Phase 6~7 | Multi-skill orchestration scenario derivation + end-to-end real-environment flow verification |
| **Tier 3: Final Report** | Phase 8 | Consolidated report merging all phase outputs |

### Core Design Principles

1. **Chain Verification** — Before each Phase, check that the previous phase's JSON exists; if missing, refuse to execute
2. **Agent-proof** — Write operations require user confirmation for each item; automatic gate bypassing is not allowed
3. **Three-Track Layering** — Clear gates between Tiers; Tier 1 must be completed before entering Tier 2
4. **Batch Repeatable** — Supports `--skills "skill-a,skill-b"` or `--all-installed`
5. **Fallback Strategy** — When only 1 skill, Phase 6/7 automatically downgrade to single-skill lifecycle testing
6. **Standardized JSON Output** — All phases output in a unified schema; Phase 8 merges into a single report
7. **Real-Environment First** — All Tier 2 orchestrations execute against real Huawei Cloud; no mocks or simulations

### Data Flow Diagram

```
User Input (--skills or --all-installed)
    │
    ├── Tier 1 ──── Iterate over each skill ────
    │   Phase 0 → 1 → 2 → 3 → 4 → 5
    │   (phase-N-summary.json chain validation)
    │
    ├── Tier 2 ──── Integration ────
    │   Phase 6 (orchestration scenario derivation + real-environment execution)
    │   Phase 7 (e2e full-flow: create→query→update→delete lifecycle)
    │   Only 1 skill → Downgrade single-skill closed loop
    │
    └── Tier 3 ──── Final ────
        Phase 8 (merge phase-0~7 JSON into consolidated report)
```

---

## Prerequisites

1. **hcloud CLI** installed and authenticated (for Tier 2 CLI mode testing) — Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
2. **Python 3.8+** + `huaweicloudsdk` packages (for SDK mode testing) — SDK Reference: https://console.huaweicloud.com/apiexplorer/#/sdkcenter
3. **Huawei Cloud AK/SK** environment variables (`HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` or `HWC_AK` / `HWC_SK`) — **If missing, must prompt the user to provide them; if the user does not provide, terminate the process. Strictly prohibited from skipping**
4. **Target Skill** must be under $HOME/.hermes/skills/ or a user-specified path
5. **jq** command (all JSON processing depends on it)
6. **API Reference**: https://console.huaweicloud.com/apiexplorer/#/openapi

---

## Workflow — Three-Track Eight-Phase

```
Tier 1: Single-Skill Unit Testing
   Phase 0: Installation Verification (install/uninstall/reinstall)
   Phase 1: Feature Extraction (metadata + commands + resource types)
   Phase 2: Technical Research (CLI→SDK→API three-level availability)
   Phase 3: Test Case Generation (functional cases TC-F + API cases TC-A)
   Phase 4: Real-Environment Execution (read-only automatic + write operations require confirmation)
   Phase 5: Cleanup (automatic cleanup + legacy report)

Tier 2: Integration Testing — Real-Environment Orchestration
   Phase 6: Multi-Skill Orchestration (scenario derivation → step execution → state verification)
   Phase 7: End-to-End Flow (resource lifecycle: create→query→update→delete)

Tier 3: Final Report
   Phase 8: Consolidated Report (merge phase-0~7 JSON into single report)
```

---

### Phase 0: Installation Verification

**Goal:** Verify whether the skill can be installed/uninstalled/reinstalled normally.

**Steps:**

1. Check skill directory structure (SKILL.md exists, references/ exists)
2. Confirm whether Hermes has the skill installed (check if a directory with the same name exists under $HOME/.hermes/skills/)
3. Perform installation verification (simulated or actual installation)
4. Perform uninstallation verification (simulated or actual uninstallation)
5. Perform reinstallation verification (install → uninstall → install)
6. Record installation duration, directory integrity, and installation status

```bash
# Simulated verification (directory structure check)
[ -f "${skill_path}/SKILL.md" ] && echo "SKILL.md exists"
[ -d "${skill_path}/scripts" ] && echo "scripts/ exists"
[ -d "${skill_path}/references" ] && echo "references/ exists"

# Installation status
hermes skills list | grep "${skill_name}"
echo $?  # 0=installed, 1=not installed
```

**Output:** `phase-0-summary.json`

```json
{
  "install": {"status": "pass", "existing": true, "duration_s": 1.2},
  "uninstall": {"status": "skipped", "reason": "not installed"},
  "reinstall": {"status": "skipped", "reason": "not installed"},
  "directory_integrity": {"pass": true, "checks": {...}}
}
```

---

### Phase 1: Feature Extraction

**Goal:** Extract structured feature information from SKILL.md as input for all subsequent phases.

**Steps:**

1. Read YAML frontmatter from SKILL.md → name, description, tags, triggers
2. Extract core commands table (Core Commands section)
3. Extract parameter confirmation table
4. Identify feature types (query/create/modify/delete)
5. Extract resource types involved (ECS instance, VPC, voucher, etc.)
6. Note whether there are write operations (Create/Update/Delete)
7. Read the list of test scripts under scripts/
8. Read the list of reference files under references/

**Output:** `phase-1-summary.json`

```json
{
  "metadata": {
    "name": "huawei-cloud-bss-voucher-manage",
    "triggers": ["查代金券", "删除代金券", "list vouchers", ...],
    "tags": ["huawei-cloud", "bss", "voucher"]
  },
  "capabilities": {
    "list": ["查询代金券", "统计代金券"],
    "create": [],
    "update": [],
    "delete": ["删除代金券"]
  },
  "has_write_operations": true,
  "resource_types": ["bss_voucher"],
  "commands": [
    {"id": "CMD-01", "source": "SKILL.md", "description": "查询代金券列表", "executor": "sdk"},
    {"id": "CMD-02", "source": "SKILL.md", "description": "统计代金券", "executor": "sdk"},
    {"id": "CMD-03", "source": "SKILL.md", "description": "删除代金券", "executor": "sdk"}
  ],
  "scripts": ["scripts/test-cli-commands.sh"],
  "references": ["references/iam-policies.md", "references/api-paths.md"]
}
```

---

### Phase 2: Technical Research

**Goal:** Perform CLI→SDK→API three-level fallback verification for each command extracted in Phase 1, determining the actual executable method.

**Dependency:** Phase 1 completed (phase-1-summary.json exists)

**Research order (per command):**

| Priority | Method | Verification |
|----------|--------|-------------|
| 1st | **CLI** | `hcloud <Service> <Operation> --cli-region=cn-north-4 --help` |
| 2nd | **SDK** | `python3 -c "from huaweicloudsdk{service}.v2 import ..."` |
| 3rd | **API** | Only from SDK source `_http_info` or Huawei Cloud API Explorer |

**Rule:** API endpoints are **strictly prohibited from being inferred**; only allowed from SDK `_http_info.resource_path` or user confirmation from API Explorer.

**Output:** `phase-2-summary.json`

```json
{
  "research": [
    {
      "cmd_id": "CMD-01",
      "description": "查询代金券列表",
      "cli": {"available": false, "reason": "BSS not in hcloud service list"},
      "sdk": {
        "available": true,
        "package": "huaweicloudsdkbss.v2",
        "method": "list_sub_customer_coupons",
        "api_path": "/v2/promotions/benefits/coupons"
      },
      "api": {"available": true, "endpoint": "/v2/promotions/benefits/coupons"},
      "recommended_executor": "sdk",
      "risk_level": "low"
    }
  ]
}
```

---

### Phase 3: Test Case Generation

**Goal:** Generate two types of test cases based on Phase 1+2, present them to the user for confirmation.

**Dependency:** Phase 1+2 completed (phase-1-summary.json + phase-2-summary.json exist)

**Functional case division rules:**

| Operation Type | Case Requirements | Risk Level |
|---------------|-------------------|------------|
| Query (List/Show/Get) | 1 positive + 1 boundary (limit=0 or empty filter) | low |
| Create | 1 standard + 1 parameter variant | high |
| Update | 1 verification that modification took effect | medium |
| Delete | 1 pre-deletion confirmation + 1 post-deletion verification | high |
| Statistics (count/aggregate) | 1 positive + 1 time range boundary | low |

**Case IDs:** `TC-F-01` ~ `TC-F-NN` (functional), `TC-A-01` ~ `TC-A-NN` (API/SDK)

**Output:** `phase-3-summary.json`

```json
{
  "functional_cases": [
    {
      "id": "TC-F-01",
      "name": "List vouchers - positive",
      "command": "list_sub_customer_coupons(limit=10)",
      "expected": "Return voucher list, no more than 10 items",
      "is_write": false,
      "risk_level": "low",
      "executor": "sdk",
      "prerequisites": [],
      "verification": "resp.count >= 0"
    },
    {
      "id": "TC-F-03",
      "name": "Delete voucher - positive",
      "command": "reclaim_partner_coupons(coupon_id=...)",
      "expected": "Voucher status changed to reclaimed",
      "is_write": true,
      "risk_level": "high",
      "executor": "sdk",
      "prerequisites": ["TC-F-01 (provide valid coupon_id)"],
      "verification": "Query after delete to confirm status change"
    }
  ],
  "api_cases": [...]
}
```

---

### Phase 4: Execution

**Goal:** Execute test cases from Phase 3 one by one; read-only runs automatically, write operations require per-case confirmation.

**Dependency:** Phase 3 completed (phase-3-summary.json exists)

**Execution rules:**

```
Pre-check: Is AK/SK set?
  if AK/SK not set:
    Prompt user to provide AK/SK
    if user does not provide:
      Terminate process, output "⛔ AK/SK missing, cannot execute tests"
    else:
      Set as environment variables, continue execution

Iterate over each test case:
  if is_write == false:
    Auto-execute → Record pass/fail
  if is_write == true:
    Show command and expected → Wait for user y/N confirmation
    if confirmed:
      Execute → Record pass/fail + resource changes
    else:
      Skip → Record skipped (user_cancelled)
```

**Resource change record (key fields):**

```json
"resource_changes": [
  {
    "tc_id": "TC-F-03",
    "resource_type": "bss_voucher",
    "resource_id": "VCH-abc123",
    "change_type": "deleted",
    "cleanup_method": {"type": "sdk", "command": "already deleted, no cleanup needed"},
    "cleanup_required": false
  }
]
```

**Output:** `phase-4-summary.json`

```json
{
  "execution_results": [
    {"tc_id": "TC-F-01", "status": "pass", "duration_s": 2.1, "output_snippet": "..."},
    {"tc_id": "TC-F-03", "status": "pass", "duration_s": 1.5, "output_snippet": "...",
     "resource_changes": [{"resource_type": "bss_voucher", "change_type": "deleted", ...}]}
  ],
  "statistics": {"total": 10, "pass": 9, "fail": 0, "skip": 1},
  "all_resources_changed": [...]
}
```

---

### Phase 5: Cleanup

**Goal:** Automatically clean up resource changes produced in Phase 4. For failures, output manual cleanup instructions.

**Dependency:** Phase 4 completed (phase-4-summary.json exists)

**Execution rules:**

```
if phase-4.all_resources_changed == []:
  Output skipped_no_resources → Phase 5 complete

Iterate over phase-4.all_resources_changed:
  if cleanup_required == false:
    Skip (resource already deleted or no cleanup needed)
  if cleanup_required == true:
    Attempt automatic cleanup (retry 3 times)
    if all 3 retries failed:
      Mark failed → Add to manual_cleanup list
      Generate manual operation instructions
```

**Output:** `phase-5-summary.json`

```json
{
  "resources_to_clean": [{"resource_type": "ecs_instance", "change_type": "created", ...}],
  "auto_cleaned": [{"resource_id": "VCH-abc123", "status": "success"}],
  "failed_cleanup": [],
  "manual_cleanup": [
    {
      "resource_type": "disk_volume",
      "resource_id": "vol-xyz789",
      "reason": "Dependent resource not released",
      "manual_steps": ["# User confirmation required before executing the Delete command", "hcloud EVS DeleteVolume --volume_id=vol-xyz789"],
      "reference": "Huawei Cloud Console → Elastic Volume → Delete"
    }
  ],
  "verdict": "partial"
}
```

---

### Phase 6: Multi-Skill Orchestration — Real-Environment Scenario Testing

**Goal:** Derive multi-skill business scenarios and execute them against the real Huawei Cloud environment to verify cross-skill integration.

**Dependency:** Phase 5 completed for all tested skills

**Branch logic:**

```
if skills_count == 1:
  Downgrade to single-skill orchestration:
    Extract all feature points from Phase 1
    Sort by CRUD lifecycle (query → create → update → delete)
    Execute sequentially against real environment
    Verify each step's output feeds correctly into the next

if skills_count >= 2:
  6a: Scenario derivation
      - Group feature points by resource type from each skill's Phase 1 output
      - Sort by dependency order (e.g., VPC must exist before ECS)
      - Auto-generate scenario chains with resource passing between skills
      - Present scenarios to user for confirmation
  6b: Real-environment execution
      - Execute each step in the confirmed scenario chain
      - Pass resource IDs/outputs between steps as runtime context
      - Record actual CLI/SDK output for each step
  6c: Cross-skill data flow verification
      - Verify output of skill A's operation can be consumed by skill B
      - Check data format compatibility (JSON field mapping)
  6d: Rollback on failure
      - If any step fails, execute rollback steps for already-created resources
```

**Auto-derivation example (ECS + VPC + EIP):**

```
Input skills: [ECS-manage, VPC-manage, EIP-manage]
Derived scenario:
  Step 1: VPC-manage.CreateVPC → outputs vpc_id
  Step 2: ECS-manage.CreateECS (in vpc_id) → outputs instance_id
  Step 3: EIP-manage.CreateEIP → outputs eip_id
  Step 4: EIP-manage.BindEIP (bind to instance_id) → outputs binding_status
  Step 5: ECS-manage.ListInstances (verify instance is running)
  Step 6: EIP-manage.UnbindEIP (unbind from instance_id)
  Step 7: ECS-manage.DeleteECS (instance_id)
  Step 8: EIP-manage.ReleaseEIP (eip_id)
  Step 9: VPC-manage.DeleteVPC (vpc_id)
```

**Resource passing mechanism:**

```json
{
  "runtime_context": {
    "vpc_id": {"from_step": 1, "skill": "VPC-manage", "output_field": "vpc.id"},
    "instance_id": {"from_step": 2, "skill": "ECS-manage", "output_field": "server.id"}
  }
}
```

**Execution mode:** All steps run against real Huawei Cloud. Read-only steps (List/Show/Describe) run automatically. Write steps (Create/Delete/Update) require user confirmation for each step.

**Output:** `phase-6-summary.json`

```json
{
  "mode": "full" | "downgraded_single",
  "scenario": {
    "name": "VPC-ECS-EIP lifecycle",
    "skills_involved": ["vpc-manage", "ecs-manage", "eip-manage"],
    "steps": [
      {"seq": 1, "skill": "vpc-manage", "action": "CreateVPC", "status": "pass", "output": {"vpc_id": "vpc-abc"}},
      {"seq": 2, "skill": "ecs-manage", "action": "CreateECS", "status": "pass", "output": {"instance_id": "srv-xyz"}},
      {"seq": 3, "skill": "eip-manage", "action": "CreateEIP", "status": "pass", "output": {"eip_id": "eip-123"}},
      {"seq": 4, "skill": "eip-manage", "action": "BindEIP", "status": "pass", "output": {}},
      {"seq": 5, "skill": "ecs-manage", "action": "ListInstances", "status": "pass", "output": {}},
      {"seq": 6, "skill": "eip-manage", "action": "UnbindEIP", "status": "pass", "output": {}},
      {"seq": 7, "skill": "ecs-manage", "action": "DeleteECS", "status": "pass", "output": {}},
      {"seq": 8, "skill": "eip-manage", "action": "ReleaseEIP", "status": "pass", "output": {}},
      {"seq": 9, "skill": "vpc-manage", "action": "DeleteVPC", "status": "pass", "output": {}}
    ]
  },
  "data_flow_verification": {"pass": true, "mismatches": []},
  "rollback_required": false
}
```

---

### Phase 7: End-to-End Flow Testing — Real-Environment Lifecycle

**Goal:** End-to-end verification of complete resource lifecycles against real Huawei Cloud, automatically deriving scenario chains from Phase 1 feature lists and executing them with real API calls.

**Dependency:** Phase 6 completed (phase-6-summary.json exists)

**Branch logic:**

```
if skills_count == 1:
  Single-skill closed loop:
    Sort all feature points by create→list→show→update→delete
    Chain into a single-skill resource lifecycle
    Execute each step via real CLI/SDK against production
    Verify resource state after each mutation

if skills_count >= 2:
  7a: Scenario derivation (from Phase 6 output)
      - Use the confirmed scenario chain from Phase 6
      - Extend with additional verification steps
  7b: Lifecycle execution
      - Execute each step against real Huawei Cloud environment
      - Read-only steps auto-execute; write steps prompt user
  7c: State consistency verification
      - After each write operation, verify via read operation
      - Confirm resource state matches expected
  7d: Cross-step data validation
      - Verify output schema compatibility between steps
      - Detect field name mismatches, type mismatches
  7e: Cleanup verification
      - Verify all created resources are properly deleted
      - Check for orphaned resources
```

**Single-skill closed loop example (RDS query skill):**

```
Steps:
  Step 1: ListInstances (read-only, auto) → get instance count
  Step 2: ShowInstanceDetail (if instance exists) → get instance config
  Step 3: ListConfigurations (auto) → get parameter templates
  Step 4: ShowBackupPolicy (if instance exists) → get backup config
  Step 5: Analyze slow SQL (read-only, auto) → ListSlowLogs + ListTopSqls
  Step 6: Parameter tuning recommendation (analysis, no API call)
  Step 7: Backup strategy assessment (analysis, no API call)
```

**Multi-skill E2E example (EC2 + EVS):**

```
Steps:
  Step 1: Create EVS volume → verify volume exists
  Step 2: Attach volume to ECS instance → verify attachment
  Step 3: Query volume metrics → verify I/O
  Step 4: Detach volume → verify detached
  Step 5: Delete volume → verify deleted
```

**Output:** `phase-7-summary.json`

```json
{
  "mode": "full" | "downgraded_single_skill_flow",
  "scenario": {
    "name": "RDS Intelligent Service Inspection",
    "skills_involved": ["huawei-cloud-rds-intelligent-service"],
    "steps": [
      {"seq": 1, "action": "ListInstances", "status": "pass", "output_summary": "3 instances found"},
      {"seq": 2, "action": "ShowInstanceDetail", "status": "pass", "output_summary": "instance config retrieved"},
      {"seq": 3, "action": "ListConfigurations", "status": "pass", "output_summary": "5 templates found"},
      {"seq": 4, "action": "ListDatastores", "status": "pass", "output_summary": "MySQL 8.0 available"},
      {"seq": 5, "action": "ShowBackupUsage", "status": "pass", "output_summary": "2.3GB used"},
      {"seq": 6, "action": "ListInstanceDiagnosis", "status": "pass", "output_summary": "No issues found"}
    ]
  },
  "state_consistency": {"pass": true},
  "cleanup_verification": {"pass": true, "orphaned": []}
}
```
---

### Phase 8: Consolidated Report

**Goal:** Merge Phase 0~7 JSON outputs into a single, comprehensive test report.

**Dependency:** Phase 0~7 all exist

**Output:** `phase-8-summary.json`

```json
{
  "test_id": "test-20260716-100300",
  "phases_summary": [
    {"phase": 0, "name": "install-check", "verdict": "pass", "duration_s": 3.5},
    {"phase": 1, "name": "skill-analysis", "verdict": "pass", "duration_s": 12.0},
    {"phase": 2, "name": "tech-research", "verdict": "pass", "duration_s": 45.0},
    {"phase": 3, "name": "test-generation", "verdict": "pass", "duration_s": 8.0},
    {"phase": 4, "name": "execution", "verdict": "pass", "duration_s": 120.0},
    {"phase": 5, "name": "cleanup", "verdict": "pass", "duration_s": 15.0},
    {"phase": 6, "name": "orchestration", "verdict": "pass", "duration_s": 200.0},
    {"phase": 7, "name": "e2e-flow", "verdict": "pass", "duration_s": 180.0}
  ],
  "overall_statistics": {
    "total_phases": 8,
    "pass": 8,
    "fail": 0,
    "skipped": 0,
    "total_duration_s": 583.5,
    "test_cases_total": 24,
    "test_cases_pass": 22,
    "test_cases_fail": 1,
    "test_cases_skip": 1,
    "orchestration_scenarios": 2,
    "e2e_flows_executed": 1
  },
  "resources_created": 3,
  "resources_cleaned": 2,
  "resources_manual": 1,
  "manual_interventions": [
    {
      "phase": 5,
      "resource_type": "disk_volume",
      "resource_id": "vol-xyz789",
      "steps": ["# User confirmation required before executing the Delete command", "hcloud EVS DeleteVolume --volume_id=vol-xyz789"]
    }
  ],
  "html_report": "reports/test-20260716-100300.html"
}
```

---

## Core Commands

### Full Pipeline Run

```bash
# Specify skills
bash scripts/run-test-pipeline.sh --skills "huawei-cloud-bss-voucher-manage"

# Specify multiple skills (comma-separated)
bash scripts/run-test-pipeline.sh --skills "huawei-cloud-bss-voucher-manage, huawei-cloud-ecs-manage"

# Scan all installed
bash scripts/run-test-pipeline.sh --all-installed

# Start from a specific phase (recovery scenarios only)
bash scripts/run-test-pipeline.sh --skills "bss-voucher" --phase 4

# Fresh mode
bash scripts/run-test-pipeline.sh --skills "bss-voucher" --fresh
```

### Single Phase Run (Debug)

```bash
bash scripts/tier1/phase-0-install-check.sh --skill "huawei-cloud-bss-voucher-manage"
bash scripts/tier1/phase-1-skill-analysis.sh --skill "huawei-cloud-bss-voucher-manage"
bash scripts/tier2/phase-6-orchestration.sh --skills "skill-a, skill-b"
bash scripts/tier3/phase-8-report.sh --skills "skill-a, skill-b"
```

### Run Multi-Skill Orchestration

```bash
# Derive and execute orchestration scenarios for 3 skills
bash scripts/tier2/phase-6-orchestration.sh --skills "ecs-manage, vpc-manage, eip-manage"

# Run E2E lifecycle test for a single skill
bash scripts/tier2/phase-7-e2e-flow.sh --skill "huawei-cloud-rds-intelligent-service"
```

---

## Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--skills` | Mutually exclusive | Comma-separated skill names or directory names | `"bss-voucher-manage, ecs-manage"` |
| `--all-installed` | Mutually exclusive | Scan all `huawei-cloud-*` under $HOME/.hermes/skills/ | — |
| `--phase` | No | Start from a specific Phase (defaults to resume from missing phase) | `--phase 0` |
| `--fresh` | No | Delete all existing phase-*.json and start from scratch | — |
| `--output` | No | Report output directory (default: reports/) | `--output ./test-reports` |
| `--skill-path` | No | Skill directory path (default: $HOME/.hermes/skills/huawei-cloud/) | `--skill-path ./skills` |

---

## References

- `references/architecture.md` — Three-track eight-phase architecture diagram (Mermaid)
- `references/output-schema-spec.md` — Complete JSON field specification for each phase
- `references/phase-transition-rules.md` — Phase transition/fallback/skip rules

---

## Output Format

All phases output `phase-N-summary.json`; Phase 8 merges them into a single report. See `references/output-schema-spec.md` for the JSON schema.

Phase 6 and 7 additionally output scenario execution logs with real CLI/SDK responses for auditability.

## Best Practices

- Complete Tier 1 before entering Tier 2 to ensure skills are individually functional before orchestration
- Confirm write operations one by one in Phase 4 and Phase 6/7; do not batch-confirm to avoid misoperations
- With only 1 skill, Phase 6/7 automatically downgrade to single-skill closed loop; no need to manually skip
- When using `--fresh` to reset and rerun, confirm there are no uncleaned test resources
- Review orchestration scenarios before execution to ensure resource dependency order is correct
- After E2E flow, verify cleanup phase to avoid orphaned cloud resources

## Notes

- Three-track eight-phase strictly follows sequential order; chain verification prevents skipping
- API endpoints are strictly prohibited from being inferred; only obtain from SDK `_http_info` or API Explorer
- Credentials are read from environment variables; hardcoding is prohibited
- **If AK/SK is missing, must prompt the user to provide them; if the user does not provide, terminate the process. Strictly prohibited from skipping any step that requires credentials**
- Resource cleanup failures must never be silently ignored; output manual operation instructions
- Orchestration scenarios are auto-derived; user should review and confirm before execution
- Write operations in orchestration scenarios require per-step user confirmation

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Skill directory does not exist | Report error and terminate, output available skill list |
| AK/SK environment variables not set | Prompt user to provide AK/SK; if user does not provide, terminate process, strictly prohibited from skipping |
| User specifies skill name but not installed in Hermes | --fresh performs directory-level detection; if not found, report error with guidance |
| Some Phase JSON files deleted | Chain detection → Restart from the deleted Phase |
| Network interruption during Phase 4 execution | Already executed case results are not lost; on rerun, skip passed cases (via `--phase` flag) |
| User hits Ctrl+C mid-execution | Already output phase JSON is valid; next time `--resume` will recover from the current phase |
| Only 1 skill under test | Phase 6 → single-skill orchestration, Phase 7 → single-skill closed loop |
| No resource changes in Phase 4 | Phase 5 automatically skips (`skipped_no_resources`) |
| Resource cleanup retry fails 3 times | Output manual operation instructions to `manual_cleanup`, mark failed |
| User unsatisfied with derived orchestration scenarios | User can manually edit the scenario or choose to skip it |
| Multi-skill scenario step fails midway | Execute rollback steps for already-created resources, report partial failure |
| Cross-skill data flow mismatch | Log field mapping details, suggest adapter/fix |
| Orphaned resources detected after E2E flow | List in report with manual cleanup instructions |

## Design Principles

- **Chain Verification** — Each Phase checks the previous phase's JSON to prevent skipping
- **Agent-proof** — Write operations must be confirmed by the user; fake confirmations are not allowed
- **Data-Driven** — All phases output in JSON format; Phase 8 merges
- **Batch Repeatable** — The same set of skills can be tested repeatedly; --fresh resets
- **Real-Environment First** — All orchestrations and E2E flows execute against real Huawei Cloud; no mocks
- **Degrade Without Losing Value** — Single skill does not run empty orchestration phases; degrades to meaningful single-skill lifecycle tests
- **Resource Safety** — Resource cleanup failures must never be silently ignored; output clear manual operation instructions
- **Credentials Mandatory** — If AK/SK is missing, must prompt the user to provide; if not provided, terminate process. Strictly prohibited from skipping
