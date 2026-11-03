---
name: huawei-cloud-cloudrobo-weight-layout
description: |
  Standard directory layout and naming conventions for saving model weights
  (checkpoints). Use this skill when the user needs to implement checkpoint
  saving in a training script, restructure an existing checkpoint/output
  directory layout, decide where to store checkpoint weights and final
  weights, name weight files, or write a loader/deployment path resolver that
  consumes checkpoints. Applies to any deep learning training pipeline (VLA /
  robot foundation models, LLM fine-tuning, diffusion models, etc.) — not
  tied to a single codebase. Also triggers when the user simply says "save
  weights", "checkpoint directory", "output layout", or asks where model
  weights should go after training.
---

# Weight Save Layout

## Overview

Standardized rules for training-side output directories. The top level is
`{output_root}`: **all contents of the final-step weight folder** go directly
under `{output_root}`; **all contents of each periodic weight folder** go into
`{output_root}/_ckpt/checkpoint_{step}/`.

Checkpoint internals produced by different models/frameworks (weight file
names, configs, statistics, etc.) differ from one another — this layout only
**defines the outer storage location; it does not presuppose the internal
structure and does not rename any files**. Any loader, deployment service, or
evaluation tool built on this layout can locate weights across models.

## Prerequisites

1. **A training script** that saves checkpoints (the code to modify).
2. **`{output_root}`** — the training-side output root directory for the
   standard layout (its parent must be writable).
3. **A loader or path resolver** (optional) — if the project consumes
   checkpoints, copy `references/loader.py` into the project's
   `migrate_to_cloudrobo/loader.py` for locating `{output_root}` and
   selecting the latest checkpoint. Loading `.pt` weights with
   `load_state_dict()` needs torch>=1.13, because it uses
   `torch.load(..., weights_only=True)` so that a checkpoint cannot execute
   code when loaded.

## Workflow

### 1. Define the layout

```
{output_root}/
├── <all contents of the final-step weight folder>    # files/subfolders directly under root
└── _ckpt/                            # periodic checkpoints
    ├── checkpoint_1000/
    │   └── <all contents of that step's weight folder>
    └── checkpoint_2000/
        └── <all contents of that step's weight folder>
```

### 2. Apply the rules in the training script

1. **Final step**: place **all files/subfolders** under the final-step weight
   folder directly at the root of `{output_root}/` (do not create a
   `final_model/` subdirectory).
2. **Periodic checkpoints**: place **all files/subfolders** under each
   periodic weight folder into `{output_root}/_ckpt/checkpoint_{step}/`
   (`step` is the saved step of that checkpoint).
3. **Move/copy contents only**: do not rename or modify checkpoint-internal
   files — every model has a different checkpoint structure, and this layout
   does not presuppose one.
4. **`_ckpt/` is created at training start**, so the layout exists before the
   first checkpoint.

### 3. Loader / path resolution

Walk **upward** from the weight file and find the ancestor that contains the
`_ckpt/` directory — that ancestor is `{output_root}`. Do not hardcode a
fixed parent depth (e.g. `path.parents[1]`).

```
{output_root}/<final weight>                        # final-step content (any file name)
{output_root}/_ckpt/checkpoint_1000/<weight file>   # periodic checkpoint
```

See `references/loader.py` for a reference implementation.

### 4. Resuming training

Scan checkpoints under `_ckpt/` whose directory names match `checkpoint_<N>`
(also compatible with legacy plain `<N>` or `steps_<N>_*.pt` flat files) and
resume from the one with the largest N.

## Core Commands

`references/loader.py` provides the following functions (copy to
`migrate_to_cloudrobo/loader.py` and extend the model rebuild logic):

| Function | Purpose |
|---|---|
| `locate_output_root(weight_path)` | walk upward from a weight file to find the ancestor containing `_ckpt/` — returns `{output_root}` |
| `find_latest_checkpoint(ckpt_root)` | return `(step, checkpoint_dir)` of the latest checkpoint under `_ckpt/`, or `(None, 0)` |
| `load_state_dict(weight_path)` | load a raw state dict from a `.pt` or `.safetensors` file (CPU) |

## Parameter Confirmation

| Parameter | Description |
|---|---|
| `{output_root}` | Top-level output directory of the standard layout; final-step weight content lives at its root |
| `_ckpt/` | Periodic-checkpoint directory under `{output_root}` |
| `checkpoint_{step}` | Per-step periodic checkpoint directory; `step` is the saved step |
| `<N>` | Step number matched for resume (`checkpoint_<N>` / plain `<N>` / `steps_<N>_*.pt`) |

## Reference Documents

- `references/loader.py` — locates `{output_root}` + selects the latest
  checkpoint (copy it to the project's `migrate_to_cloudrobo/loader.py`)
- `references/verification-method.md` — verify the loader against a sample
  layout and check a real training output
- `references/iam-policies.md` — IAM permissions (none required)
