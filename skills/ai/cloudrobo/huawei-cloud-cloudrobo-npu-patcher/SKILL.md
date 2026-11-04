---
name: huawei-cloud-cloudrobo-npu-patcher
description: |
  Applies to adapting PyTorch-framework VLA models to Ascend NPU, fixing
  CUDA issues, or optimizing NPU performance. Includes scanning, patching,
  verification, and training script templates.
---

# Skill: huawei-cloud-cloudrobo-npu-patcher

## Overview

Adapts PyTorch VLA models to Ascend NPU. Runtime patches via
`build_npu_patcher()` automatically handle float64→float32, numpy safety,
nan_to_num, and other issues; scanners detect semantic issues that require
agent judgment.

### Runtime Patches (zero-config, always active)

`runtime_patches.py` (copy it to the `migrate_to_cloudrobo/` directory)
provides the following patches, activated by the entry point's
`build_vla_patcher()`:

| Patch | Function |
|------|------|
| Float64To32 | module-level torch.float64→float32 replacement + copyreg.pickle fix + from_numpy/as_tensor/Tensor.to hooks |
| TensorNumpySafe | auto-inserts `.cpu()` before NPU tensors call `.numpy()` |
| NanToNumSafe | auto-converts half precision to float32 before torch.nan_to_num() |
| TensorIndexDevice | auto-aligns index tensors to the indexed tensor's device |
| TorchTensorSafe | intercepts torch.tensor() to handle 0-dim NPU tensor elements |
| BuiltinMinMaxNPU | Python min/max with NPU tensors → torch.minimum/maximum |
| PowFloatSafe | torch.pow fractional exponent → result auto `.float()` |
| SdpaMaskBroadcast | fixes NPU SDPA mask broadcast error (aclnnFlashAttentionScore error 561103): explicitly expands the (B,N,1,Skv) broadcast mask to (B,N,Sq,Skv) |

| Patch | Function | How to enable |
|------|------|---------|
| AdamWFused | redirects AdamW → NpuFusedAdamW to improve NPU throughput; requires contiguous large memory blocks, may OOM with large models / tight memory | `build_vla_patcher(fused_adamw=True)` |

### Semantic-Level Issues (Agent-Assisted Fixing)

Scanners classify issues into the following categories; each pattern maps to
a fix template under `references/fix-templates/`:

| Category | Description | Pattern |
|------|------|---------|
| DEVICE | NPU tensor device mismatch | P_RND |
| OPERATOR | CUDA extensions → NPU API | P_FLA |
| STRUCTURE | loops, initialization, entry points | P_ENT, P_VEC |
| FRAMEWORK | pytorch_lightning | P_LTM |
| SEMANTIC | optimization | P_TGT |

## Prerequisites

Before starting, the following must be in place:

1. **Python ≥ 3.10** — all scripts under `scripts/` require Python 3.10 or
   later. Run them with the conda environment's interpreter when the system
   Python is older.
2. **Model project** — the PyTorch VLA codebase to adapt (the scan/verify
   target path).
3. **conda environment with torch_npu** — the runtime patches
   (`runtime_patches.py`) and the NPU runtime verification require
   `import torch_npu` to succeed.
4. **At least one Ascend NPU card** — select cards via
   `ASCEND_RT_VISIBLE_DEVICES` (used by training and runtime checks).

## Workflow

**Create the following TODO list before starting:**

[ ] 1. Create the `migrate_to_cloudrobo/` directory and copy the template files
[ ] 2. Run `<skill dir>/scripts/scan.py /path/to/model --output .`
[ ] 3. Fix all issues (must follow the "Issue Fix Workflow")
[ ] 4. Run `<skill dir>/scripts/progress.py --check-complete` (must pass before verifying)
[ ] 5. Verify (iterate until fully passing): `<skill dir>/scripts/verify.py /path/to/model --runtime --pipeline --config <config>`
[ ] 6. Verify (iterate until fully passing): `<skill dir>/scripts/verify.py /path/to/model --data --config <config>`
[ ] 7. Start training
[ ] 8. Write the NPU adaptation summary (`migrate_to_cloudrobo/ADAPTATION_SUMMARY.md`)

### Issue Fix Workflow

1. Get the next pending issue:
   ```bash
   python <skill dir>/scripts/progress.py issues.json --next
   ```
2. Read the fix template: `<skill dir>/references/fix-templates/<pattern_id>.md`
   (use the pattern ID from step 1)
3. Fix the issue per the template (or mark it as a false positive;
   performance issues cannot be skipped)
4. Update progress:
   - **Fixed**: `python <skill dir>/scripts/progress.py issues.json --fixed <issue_id>`
   - **False positive**: `python <skill dir>/scripts/progress.py issues.json --skip <issue_id> --reason "..."`
5. Repeat steps 1-4 until no pending issues remain
6. Check whether everything is complete:
   ```bash
   python <skill dir>/scripts/progress.py issues.json --check-complete
   ```

**Code quality requirements:**
- Each statement does one thing — no chained implicit conversions
- Variable origins should be single and clear
- Keep code symmetry and readability
- Only replace the specific lines that need changing. **Never rewrite the
  whole file.**

**Do not delegate to a sub-agent (task/background tasks).** The fix
workflow needs careful context-aware judgment and must be done in the main
session.
**Do not read issues.json contents directly. Use the `progress.py` commands
to track and manage issues.

## Core Commands

| Command | Purpose |
|---|---|
| `python <skill dir>/scripts/scan.py /path/to/model --output .` | scan the model codebase → generates issues.json |
| `python <skill dir>/scripts/progress.py issues.json --next` | get the next pending issue |
| `python <skill dir>/scripts/progress.py issues.json --fixed <issue_id>` | mark an issue as fixed |
| `python <skill dir>/scripts/progress.py issues.json --skip <issue_id> --reason "..."` | mark an issue as a false positive |
| `python <skill dir>/scripts/progress.py issues.json --check-complete` | confirm all issues are handled |
| `python <skill dir>/scripts/verify.py /path/to/model --runtime --pipeline --config <config>` | verify NPU runtime + pipeline |
| `python <skill dir>/scripts/verify.py /path/to/model --data --config <config>` | verify real data loading |
| `bash migrate_to_cloudrobo/train.sh <launch command...>` | start training (pass-through wrapper) |

## Parameter Confirmation

| Parameter | Description |
|---|---|
| `<skill dir>` | This skill's directory (contains `scripts/`, `references/fix-templates/`, `templates/`) |
| `/path/to/model` | Model project root — the scan/verify target |
| `--output .` | Where `issues.json` is written (default: current directory) |
| `<config>` | Model config file for `verify.py` (auto-detected when omitted) |
| `ASCEND_RT_VISIBLE_DEVICES` | NPU card list for training (e.g. `0,1`) |
| `<launch command...>` | The model project's own launch command passed through `train.sh` |

## Training Template

**Read and follow the instructions in the template.**

```bash
# At the model project root, create the migrate_to_cloudrobo/ directory and copy the template files
mkdir -p <project root>/migrate_to_cloudrobo
cp <skill dir>/templates/env_npu.sh <project root>/migrate_to_cloudrobo/
cp <skill dir>/templates/train.sh <project root>/migrate_to_cloudrobo/
cp <skill dir>/scripts/runtime_patches.py <project root>/migrate_to_cloudrobo/

# Start training (train.sh passes through the original project's launch command, auto-sources env_npu.sh + sets PYTHONPATH)
cd <project root>
ASCEND_RT_VISIBLE_DEVICES=0,1 bash migrate_to_cloudrobo/train.sh \
    bash <launch command...>
```

**Note**: train.sh is a pass-through wrapper — it forwards `$@` unchanged to
the model project's own launch command (e.g. `examples/finetune.sh`,
`launch_finetune.py`), and only sources env_npu.sh, sets PYTHONPATH, and
redirects logs.

## Writing the NPU Adaptation Summary

After the adaptation is complete, write a summary at
`migrate_to_cloudrobo/ADAPTATION_SUMMARY.md`, referencing the template
`<skill dir>/templates/ADAPTATION_SUMMARY.md`.
The summary should cover: the user's prompt, the adaptation workflow and
per-step timing, the code add/remove/modify inventory, problems encountered
and their solutions, and known issues.

## Reference Documents

- `references/fix-templates/P_ENT.md` — entry point NPU setup fix template
- `references/fix-templates/P_FLA.md` — Flash Attention → NPU fix template
- `references/fix-templates/P_LTM.md` — pytorch_lightning.metrics →
  torchmetrics fix template
- `references/fix-templates/P_RND.md` — random tensor device mismatch fix
  template
- `references/fix-templates/P_TGT.md` — target computation optimization fix
  template
- `references/fix-templates/P_VEC.md` — tensor-indexing loop vectorization
  fix template
- `templates/ADAPTATION_SUMMARY.md` — NPU adaptation summary template
- `templates/env_npu.sh` — NPU performance environment variables template
- `templates/train.sh` — training launch script template (pass-through)
