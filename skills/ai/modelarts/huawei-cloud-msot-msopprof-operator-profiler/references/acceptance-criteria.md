# Acceptance Criteria

## Functional Acceptance Criteria

### 1. Mode Selection

- AC-1.1: Should correctly identify device vs simulator mode
  - Verification: Check mode determination logic
- AC-1.2: Should recommend appropriate mode based on requirements
  - Verification: Verify recommendation reasoning
- AC-1.3: Should explain mode differences clearly
  - Verification: Check output explanation

### 2. Command Generation

- AC-2.1: Should generate correct msprof op command
  - Verification: Compare with reference commands
- AC-2.2: Should include required parameters
  - Verification: Check parameter completeness
- AC-2.3: Should set correct output directory
  - Verification: Verify path in command

### 3. Result Interpretation

- AC-3.1: Should interpret CSV files correctly
  - Verification: Compare with actual data
- AC-3.2: Should explain visualize_data.bin usage
  - Verification: Verify visualization guidance
- AC-3.3: Should identify bottleneck operators
  - Verification: Check TOP analysis

### 4. Report Generation

- AC-4.1: Should follow fixed 4-section report template
  - Verification: Verify report structure
- AC-4.2: Should include TOP5 items
  - Verification: Check report completeness
- AC-4.3: Should provide actionable suggestions
  - Verification: Verify recommendation quality

## Correct/Error Pattern Comparison

### Mode Selection

**Correct:** Choose device when real NPU available

```bash
# User has real NPU and wants real hardware bottleneck analysis
# -> Recommend device mode
msprof op --output=./output ./execute_op
```

**Error:** Use simulator when device mode needed

```bash
# User asks for real hardware analysis but uses simulator
msprof op simulator ...  # Wrong mode
```

### Parameter Usage

**Correct:** Use --kernel-name only for application mode

```bash
msprof op --kernel-name="Add|Sub" --output=./output ./execute_op
# Correct for application
```

**Error:** Apply device parameters to simulator

```bash
msprof op simulator --kernel-name="Add" ...
# Wrong: --kernel-name not valid for simulator
```

### Report Format

**Correct:** Follow fixed template

```markdown
## 1. Operator Basic Information

| Field | Content |
|-------|---------|
| Mode | device |

## 2. Key Data TOP5

| Name | Metric | Value |

## 3. Core Bottleneck TOP5

| Name | Conclusion | Evidence |

## 4. Optimization Suggestions TOP5

| Name | Suggestion | Related Bottleneck |
```

**Error:** Use custom report format

```markdown
# Profiling Results

Top operators:
1. Add
2. Mul
...
```

## Non-Functional Acceptance Criteria

- NAC-1.1: Command generation time < 5 seconds
- NAC-1.2: Report generation time < 10 seconds
- NAC-1.3: Mode selection accuracy > 95%

## Test Cases Summary

### Positive Test Cases

1. TC-001: Device mode with application input
2. TC-002: Device mode with config input
3. TC-003: Simulator mode with application input
4. TC-004: Simulator mode with export input
5. TC-005: Fixed report generation
6. TC-006: visualize_data.bin interpretation

### Negative Test Cases

1. TC-N01: Use device parameters for simulator
2. TC-N02: Use simulator parameters for device
3. TC-N03: Missing required parameters
4. TC-N04: Report missing required sections
5. TC-N05: Invalid mode selection for input type
