# <Model Name> NPU Adaptation Summary

## 1. Adaptation Goal and User Prompt

### Adaptation Goal

Migrate the <Model Name> VLA model from GPU to Huawei Ascend NPU, using the
`huawei-cloud-cloudrobo-npu-patcher` skill for adaptation.

- **Environment**: <conda env name>
- **NPU cards**: <card number list> (N × 910B/910A total)
- **Pretrained weights**: <weights path>
- **Dataset**: <dataset path>

### User Prompt (original requirement)

> <Record the user's original adaptation requirement verbatim, e.g. "adapt
> this model to run training on NPU", plus any follow-up requirements>

---

## 2. Adaptation Workflow

<Record each step in the actual execution order, referencing the skill's
execution workflow, and note which steps were taken/skipped>

1. **Prep**: create the `migrate_to_cloudrobo/` directory and copy the
   template files (env_npu.sh / train.sh / runtime_patches.py)
2. **Scan**: `scan.py <model path> --output .` → generates issues.json
   (<N> issues)
3. **Fix**: process issues one by one per the "Issue Fix Workflow"
   (P_ENT entry points, P_FLA Flash Attention, etc.), marked with
   `progress.py --fixed/--skip`
4. **Re-check**: `progress.py --check-complete` confirms everything is
   handled
5. **Verify**: `verify.py --runtime --pipeline --data --config <config>`
   (iterate until passing)
6. **Train**: start training (train.sh passes through the original
   project's launch command)
7. **Summarize**: write this file

---

## 3. Per-Step Timing

| Step | Duration | Notes |
|------|------|------|
| Scan | <X min> | scanned <N> files, <M> lines total |
| Fix | <X hours> | handled <N> issues (<A> fixed / <B> skipped as false positives) |
| Verify | <X hours> | iterated <N> rounds until passing |
| Train | <X hours> | <N> steps / <time> to complete |
| **Total** | **<X hours>** | |

---

## 4. Code Modification Inventory (add/remove/modify)

| File | Add/Remove/Modify | Line | Change | Pattern/Basis |
|------|---------|------|----------|-------------|
| <file path> | modify | <line> | <change description> | <P_ENT/P_FLA or runtime error> |
| <file path> | add | <line> | <new content description> | |

**New files:**

| File | Purpose |
|------|------|
| `runtime_patches.py` | runtime patches (float64→32, numpy safety, nan_to_num, and the other 8 core patches) |
| `env_npu.sh` | NPU performance-optimization environment variables |
| `train.sh` | training launch script (passes through the original project's launch command) |
| `patch.py` | <e.g. a new special-purpose patch> |

---

## 5. Problems Encountered and Solutions

### Problem 1: <problem title>

- **Symptom**: <error message or manifestation>
- **Root cause**: <cause analysis>
- **Solution**: <fix approach, referencing the Pattern ID such as
  P_FLA/P_ENT, etc.>

### Problem 2: <problem title>

- **Symptom**:
- **Root cause**:
- **Solution**:

---

## 6. Verification Results and Known Issues

### Verification Results

| Verification item | Result |
|--------|------|
| runtime verification | <pass/fail> |
| pipeline verification | <pass/fail> |
| data verification | <pass/fail> |
| training start | <pass/fail> |
| training steps | <N> steps / <loss trend> |

### Known Issues

<Unresolved problems, known limitations, future optimization directions.
For example:>
- <known issue 1: description + impact + possible direction>
- <known issue 2>
