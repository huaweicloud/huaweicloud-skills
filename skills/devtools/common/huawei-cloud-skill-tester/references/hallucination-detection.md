# Hallucination Detection Specification

> Defines hallucination detection methods, criteria, and defense strategies for huawei-cloud-skill-tester.

## Hallucination Type Definitions

### 1. Responsibility Confusion

**Definition**: Agent invokes the wrong Skill to handle the current task.

**Detection Method**:
- Construct explicit trigger words, verify Agent loads the expected Skill
- Compare Agent's actually invoked Skill name with expected Skill name

**Criterion**: `actual_skill == expected_skill`

**Example**:
- Request "create ECS management Skill" → expected `huawei-cloud-skill-creator`, if actual invocation is `huawei-cloud-ecs-manage` then responsibility confusion

### 2. Parameter Fabrication

**Definition**: Agent fabricates non-existent parameter values to satisfy Skill invocation format.

**Detection Method**:
- Maintain known cloud service/resource whitelist
- Verify service names and resource IDs in output are in the whitelist
- Verify output parameter values conform to format specification

**Criterion**: `output_params subset of known_whitelist`

**Example**:
- Request "create XXXYYY service Skill" → if output contains `huawei-cloud-xxxyyy-manage` instead of error prompt, then parameter fabrication

### 3. Workflow Stitching Error

**Definition**: During multi-Skill collaboration, Agent skips necessary steps or reverses order.

**Detection Method**:
- Define expected step sequence
- Compare Agent's actually executed steps with expected sequence
- Verify input/output衔接of intermediate steps

**Criterion**: `actual_steps == expected_steps_sequence`

**Example**:
- Skill creation workflow should include Steps 1-8, if Step 3 (API research) is skipped then workflow stitching error

### 4. Context Pollution

**Definition**: Output residue from a previous Skill affects subsequent Skill judgment.

**Detection Method**:
- Execute different Skill tasks sequentially
- Verify subsequent task output does not contain prior task entity names/parameters

**Criterion**: `task_B_output intersect task_A_entities == empty`

**Example**:
- First execute "create CCE Skill", then execute "list OBS buckets" → if OBS query output contains "CCE" then context pollution

### 5. Format Hallucination

**Definition**: Output structure does not match specification.

**Detection Method**:
- Define output JSON Schema
- Verify output matches Schema
- Verify YAML Frontmatter format correct

**Criterion**: `validate_schema(output) == true`

**Example**:
- SKILL.md Frontmatter missing `version` field then format hallucination

## Detection Flow

```text
1. Load tested Skill and related Skills
2. Execute test case set
3. For each case output, execute 5 types of hallucination detection
4. Aggregate detection results, calculate hallucination rate
5. Generate hallucination detection report
```

## Hallucination Rate Calculation

```text
hallucination_rate = hallucination_count / total_test_cases
```

**Threshold**: `hallucination_rate < 0.05` (5%)

## Defense Strategies

| Strategy | Implementation | Applicable Hallucination Type |
|----------|---------------|-------------------------------|
| Description precision | Skill description includes explicit trigger condition boundaries | Responsibility confusion |
| Output Schema validation | Assert JSON Schema on output | Format hallucination, parameter fabrication |
| Service whitelist | Agent can only invoke known existing cloud services | Parameter fabrication |
| Context window management | Clean irrelevant context after each Skill invocation | Context pollution |
| Workflow step validation | Verify multi-step workflow step completeness | Workflow stitching error |
| Manual review | Key combination test nodes require manual confirmation | All types |
