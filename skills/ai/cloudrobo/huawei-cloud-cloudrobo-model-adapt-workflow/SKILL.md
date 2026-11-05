---
name: huawei-cloud-cloudrobo-model-adapt-workflow
description: |
  One-stop workflow for adapting models on the CloudRobo platform. Chains 4
  sub-skills: huawei-cloud-cloudrobo-npu-patcher (PyTorch VLA → Ascend NPU adaptation),
  huawei-cloud-cloudrobo-weight-layout (standard checkpoint layout), huawei-cloud-cloudrobo-train-metrics (Octopus
  training metric reporting), and huawei-cloud-cloudrobo-inference-adapter (target-protocol
  inference interface adaptation), covering the full pipeline of
  "model code → trainable on NPU → weights produced in standard layout →
  platform metric visualization → protocol-based inference service". Use this
  skill when the user asks to adapt a VLA or robot foundation model
  end-to-end on the CloudRobo/Ascend platform, and the task involves two or
  more of: NPU migration, checkpoint conventions, training metric reporting,
  and inference protocol adaptation.
  Triggers include: "platform model adaptation", "end-to-end adaptation",
  "adapt to CloudRobo and deploy", "run training + report metrics + wire up inference",
  "模型适配", "端到端适配", "模型迁移到NPU", "在云机器人平台部署模型", "训练并上报指标".
tags:
  - huawei-cloud-cloudrobo
  - model-adaptation
  - npu
  - training
  - inference
trigger:
  keywords:
    - "platform model adaptation"
    - "end-to-end adaptation"
    - "adapt to CloudRobo and deploy"
    - "run training + report metrics + wire up inference"
    - "模型适配"
    - "端到端适配"
    - "模型迁移到NPU"
    - "在云机器人平台部署模型"
    - "训练并上报指标"
---

# CloudRobo Platform Model Adaptation Workflow

## Overview

This skill chains 4 sub-skills into a single pipeline. Each stage calls its
corresponding sub-skill (via the Skill tool) and feeds the previous stage's
output into the next stage's input.

```
┌───────────────────────────────────────────────────────────────┐
│  Stage 0  Input confirmation                                  │
│  Model code / dataset / conda env / NPU cards / target        │
│  protocol / output_root                                       │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 1  huawei-cloud-cloudrobo-npu-patcher         ← first get code running    │
│                                    on NPU                     │
│  scan → fix → verify (no training start) → migrate_to_cloudrobo/│
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 2  huawei-cloud-cloudrobo-weight-layout      ← standardize training-side │
│                                    output                     │
│  change training-script checkpoint saving to the standard     │
│  layout (output_root + _ckpt/)                                │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 3  huawei-cloud-cloudrobo-train-metrics     ← training-side metric       │
│                                    reporting                  │
│  integrate the ocms recorder, write to output_root → Octopus  │
│  visualization                                                │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 4  Start training (boundary)                           │
│  train.sh start → produce final weights +                     │
│  dataset_statistics.json                                      │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 5  huawei-cloud-cloudrobo-inference-adapter ← deployment side       │
│            (consumes training outputs)                        │
│  protocol adapter + transport server + entry point + test     │
│  client                                                       │
└──────────────────────────────┬────────────────────────────────┘
                               ▼
┌───────────────────────────────────────────────────────────────┐
│  Stage 6  Summary (extend ADAPTATION_SUMMARY.md to cover the  │
│            full flow)                                         │
└───────────────────────────────────────────────────────────────┘
```

## Prerequisites

Before running this workflow, the user must provide the following
environment:

1. **Agent tooling and LLM service** — the agent runtime and the
   large-model service that drive this workflow are installed by the user
   (they are not provisioned by this skill).
2. **At least one Ascend NPU card** — required for Stage 1 verification,
   Stage 4 training, and the Stage 5 inference deployment; select cards
   via `ASCEND_RT_VISIBLE_DEVICES`.
3. **A ready Ascend PyTorch training environment** — including CANN and
   torch_npu with a working `import torch_npu`; follow the official Ascend
   PyTorch installation guide:
   https://www.hiascend.com/document/detail/zh/Pytorch/latest/installguide/swinstall/docs/zh/installation_guide/installation_description.md

## Workflow

### Stage 0: Input Confirmation

Before calling sub-skills, collect and confirm the following inputs
(clarify with the user if anything is missing). See
[Parameter Confirmation](#parameter-confirmation) for the full input table.

### Stage 1: NPU Adaptation (huawei-cloud-cloudrobo-npu-patcher)

Call `huawei-cloud-cloudrobo-npu-patcher` via the Skill tool and run the first 6 steps of its
"Execution Workflow":

1. Create `migrate_to_cloudrobo/` and copy the templates (env_npu.sh /
   train.sh / runtime_patches.py) — the templates are also bundled in this
   skill at `<skill dir>/templates/migrate_to_cloudrobo/` for a self-contained
   restart
2. `scan.py` scans → generates issues.json
3. Fix issues one by one following the "Issue Fix Workflow" (must NOT be
   delegated to a sub-agent; must be done in the main session)
4. `progress.py --check-complete` to re-check
5. `verify.py --runtime --pipeline --config <config>` iterate until passing
6. `verify.py --data --config <config>` iterate until passing

**Gate G1**: only enter Stage 2 after all 6 steps above pass.
**Note**: this stage does **not** start training (step 7 of the sub-skill's
own workflow is deferred to Stage 4); writing ADAPTATION_SUMMARY.md is
deferred to Stage 6 for a unified summary.

### Stage 2: Weight Save Layout (huawei-cloud-cloudrobo-weight-layout)

Call `huawei-cloud-cloudrobo-weight-layout` via the Skill tool to modify the training script's
checkpoint saving logic:

- Create `_ckpt/` at training start (rank 0 only)
- All contents of periodic checkpoints → `_ckpt/checkpoint_{step}/`
- All contents of the final-step checkpoint → directly at the root of
  `{output_root}/`
- If the project uses HF Trainer, use a custom callback to map
  save/load to the standard layout

**Gate G2**: the training script's save path follows the standard layout (no
longer writes legacy flat `checkpoints/steps_*_*.pt`); the loader resolves
`{output_root}` by "walking upward from the weight file to find `_ckpt/`".

### Stage 3: Training Metric Reporting (huawei-cloud-cloudrobo-train-metrics)

Call `huawei-cloud-cloudrobo-train-metrics` via the Skill tool to integrate the ocms recorder
into the training script:

1. Find the metric-logging points in the training script
   (`_log_metrics` / `on_log`, etc.)
2. Copy `ocms_recorder.py` into the project
3. Choose the integration mode for the training framework (custom loop / HF
   Trainer / Lightning / Accelerate / MMEngine / shared base class);
   `output_dir` uses Stage 2's `{output_root}`
4. Report on rank-0 only, to avoid file conflicts

**Gate G3**: integration point confirmed, no rank>0 reporting path; the ocms
package is installed in the conda env (`pip show ocms`; install if missing —
`<conda_env>/bin/pip install ocms`, a proprietary Octopus package; when
missing, the recorder degrades gracefully). See
[references/verification-method.md](#verification-method-验证方法) for the
install and import check.

### Stage 4: Start Training (Boundary)

1. Back to huawei-cloud-cloudrobo-npu-patcher's "Training Template": at the model project root
   `ASCEND_RT_VISIBLE_DEVICES=<cards> bash migrate_to_cloudrobo/train.sh <launch command...>`
2. Wait for training to produce the final-step content at the root of
   `{output_root}/`

**Gate G4** (training output check; only enter Stage 5 after it passes):

```
{output_root}/                          ✓ all contents of the final-step checkpoint at root
└── _ckpt/checkpoint_{step}/            ✓ periodic checkpoints collected here
```

G4 key checks (consumer dependencies):
- `{output_root}/` root contains the final weights + loadable
  config/statistics (file names vary by model; the statistics file needed
  for inference denormalization must be here)
- `_ckpt/` exists and contains `checkpoint_{step}/` periodic checkpoints
- `ocms_metrics/` (if ocms is installed) → Stage 3 output (already
  visualized on the Octopus platform)

### Stage 5: Inference Interface Adaptation (huawei-cloud-cloudrobo-inference-adapter)

Call `huawei-cloud-cloudrobo-inference-adapter` via the Skill tool and follow its
"Step-by-Step Workflow":

1. Analyze the target protocol's transport layer, serialization,
   request/response format, handshake, and error contract
2. Identify the model's inference interface (predict / metadata /
   normalization access)
3. Create the protocol adapter (observation/action conversion; image keys
   derived from the model's DataConfig, not hardcoded)
4. Create the transport server (matching the protocol error contract
   exactly)
5. Create a thin entry point (loads Stage 4's final weights +
   `dataset_statistics.json` for denormalization)
6. Verify with `verify_adapter.py` (server-less unit tests) +
   `test_client.py` (end-to-end)

**Gate G5**: `verify_adapter.py` passes; after starting the server,
`test_client.py` smoke test passes (actions shape `(T,D)`,
`server_timing.prev_total_ms` semantics correct).

### Stage 6: Summary

In `migrate_to_cloudrobo/ADAPTATION_SUMMARY.md` (refer to huawei-cloud-cloudrobo-npu-patcher's
template), summarize the full flow. In addition to what the sub-skills
require, cover:

- File inventory and paths produced by each stage (migrate_to_cloudrobo/,
  `{output_root}`, ocms_metrics/, deployment directory)
- Training command and metric reporting verification status
- Inference protocol choice and the wire format contract (metadata content)
- Known issues (e.g. AdamWFused not enabled, protocol error contract
  scenarios not covered, etc.)

### Breakpoint Resume (.workflow_state)

The workflow may fail mid-pipeline due to NPU system issues, resource
conflicts, etc. A state file records the **gates that have passed**, so a
resume continues from the last completed stage instead of rerunning
everything:

- **State file**: `{project root}/migrate_to_cloudrobo/.workflow_state`
  (JSON list)
- **Write time**: after each gate (G1-G5) passes, mark that stage as
  complete
- **Read time**: read the state file at every workflow start and skip
  completed stages

```
# migrate_to_cloudrobo/.workflow_state example
{"completed_gates": ["G1", "G2", "G3"]}
```

**Usage**:
1. At stage start, check `.workflow_state`; if the current gate is already
   in it, skip that stage directly
2. After a gate passes, append-write it
   (`echo '{"completed_gates": [...]}' > .workflow_state`)
3. On failure the state file keeps the last successful value, and the next
   run continues from the failure point

## Core Commands

> All scripts below are bundled with this skill under `<skill dir>/scripts/` and the
> train template under `<skill dir>/templates/migrate_to_cloudrobo/` — no external
> download is required. Replace `<skill dir>` with this skill's directory path.

| Stage | Command | Purpose |
|---|---|---|
| Stage 1 | `python <skill dir>/scripts/scan.py /path/to/model --output /path/to/model` | scan the model codebase → generates issues.json |
| Stage 1 | `python <skill dir>/scripts/progress.py issues.json --next` | get the next pending issue |
| Stage 1 | `python <skill dir>/scripts/progress.py issues.json --fixed <issue_id>` / `--skip <issue_id> --reason "..."` | mark an issue fixed / false positive |
| Stage 1 | `python <skill dir>/scripts/progress.py issues.json --check-complete` | confirm all issues handled |
| Stage 1 | `python <skill dir>/scripts/verify.py /path/to/model --runtime --pipeline --config <config>` | verify NPU runtime + pipeline |
| Stage 1 | `python <skill dir>/scripts/verify.py /path/to/model --data --config <config>` | verify real data loading |
| Stage 3 | `<conda_env>/bin/pip show ocms` | check the ocms package (install if missing) |
| Stage 4 | `ASCEND_RT_VISIBLE_DEVICES=<cards> bash migrate_to_cloudrobo/train.sh <launch command...>` | start training (pass-through; template in `<skill dir>/templates/migrate_to_cloudrobo/train.sh`) |
| Stage 5 | `python <skill dir>/scripts/verify_adapter.py --adapter /path/to/adapter.py --class-name MyAdapter` | server-less adapter unit tests |
| Stage 5 | `python <skill dir>/scripts/test_client.py --host 127.0.0.1 --port 8000` | end-to-end smoke test against the running server |

## Parameter Confirmation

Before calling any sub-skill, confirm the following inputs with the user
(Stage 0); clarify anything that is missing:

| Input | Description |
|---|---|
| Model code root | The PyTorch VLA project to adapt |
| Dataset path | Training dataset (writes `dataset_statistics.json` when the dataloader is built) |
| conda env | Project-specific env, must contain torch_npu; ocms package installed in it |
| NPU cards | `ASCEND_RT_VISIBLE_DEVICES` card-number list |
| Pretrained weights (optional) | If present, used by Stage 1 verification |
| Target inference protocol | OpenPI / GR00T / ROS, etc.; used by Stage 5 |
| `output_root` | Output root for the standard layout (used from Stage 2 on; final-step content lives at its root) |

## Cross-Stage Artifact Dependencies

| Artifact | Producer | Consumer |
|---|---|---|
| `migrate_to_cloudrobo/` (env_npu.sh / train.sh / runtime_patches.py) | Stage 1 | Stage 4 training start |
| Output dir `{output_root}/` (final-step content at root) | Stage 2 | Stage 3 (ocms output_dir), Stage 4 (output), Stage 5 (loading) |
| Final weights (one of the final-step checkpoint contents) | Stage 2 layout + Stage 4 training | Stage 5 (model loading) |
| `ocms_metrics/` | Stage 3 | Octopus platform visualization |
| `migrate_to_cloudrobo/deployment/` (adapter/server/entry) | Stage 5 | Deploying the inference service |

## Scope and Boundaries

- **Applies to**: end-to-end adaptation of PyTorch VLA / robot foundation
  models on the CloudRobo (Ascend NPU) platform, where both the training
  side (NPU + layout + metrics) and the deployment side (protocol
  inference) must be covered.

## Reference Documents

- `references/verification-method.md` — stage-by-stage verification and dependency install checks
- `references/acceptance-criteria.md` — gate-based acceptance criteria (G1–G5)
- `references/iam-policies.md` — permission/credential model (near-zero IAM; local NPU project + CloudRobo/Octopus scope)
- `scripts/` — bundled helpers: `scan.py`, `progress.py`, `verify.py`, `verify_adapter.py`, `test_client.py`
- `templates/migrate_to_cloudrobo/` — bundled templates: `env_npu.sh`, `train.sh`, `runtime_patches.py`

Details on each sub-skill:
- huawei-cloud-cloudrobo-npu-patcher — NPU adaptation (Stage 1)
- huawei-cloud-cloudrobo-weight-layout — standard checkpoint layout (Stage 2)
- huawei-cloud-cloudrobo-train-metrics — ocms metric reporting (Stage 3)
- huawei-cloud-cloudrobo-inference-adapter — protocol inference interface (Stage 5)
