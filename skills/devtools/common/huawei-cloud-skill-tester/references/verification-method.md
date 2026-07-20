# Verification Method — huawei-cloud-skill-tester

## Overview

This document describes how to verify the skill-tester framework is correctly installed, configured, and producing valid results.

## Prerequisites Verification

### 1. Check Directory Structure

```bash
ls $HOME/.hermes/skills/huawei-cloud-skill-tester/
# Should contain: SKILL.md, scripts/, references/
```

### 2. Verify Script Availability

```bash
ls scripts/
# Should contain: run-test-pipeline.sh, tier1/, tier2/, tier3/, lib/
```

### 3. Check Required Dependencies

```bash
python3 --version            # Python 3.8+
hcloud version               # hcloud CLI installed
jq --version                 # jq installed
env | grep -E "HUAWEI_AK|HWC_AK"  # AK/SK configured
```

## Pipeline Verification

### Unit Test (Single Skill)

```bash
bash scripts/run-test-pipeline.sh --skills "huawei-cloud-bss-voucher-manage"
```

Expected output:
- Phase 0~5 complete with `pass` verdict
- `phase-5-summary.json` generated

### Integration Test (Multi-Skill)

```bash
bash scripts/run-test-pipeline.sh --skills "skill-a, skill-b"
```

Expected output:
- Phase 6 generates orchestration scenarios
- Phase 7 executes E2E flow
- Phase 8 produces consolidated report

## Output Validation

Each phase produces a `phase-N-summary.json`. Validate using:

```bash
jq '.summary.verdict' phase-4-summary.json
```

Expected verdicts: `pass`, `fail`, `partial`, `skipped`, or `downgraded`.

## Chain Integrity Verification

Verify chain dependency between phases:

```bash
# Phase 2 requires Phase 1
test -f phase-1-summary.json && echo "Chain OK" || echo "Chain broken"
```

## Error Recovery Verification

1. Delete a phase JSON file
2. Re-run the pipeline
3. Confirm it detects the missing phase and restarts from that point
