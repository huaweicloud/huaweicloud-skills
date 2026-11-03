---
name: huawei-cloud-cloudrobo-train-metrics
description: |
  Integrate the ocms (Octopus Metrics Summary) library into any PyTorch
  training script to report training metrics (loss, learning rate, timing,
  eval scores, grad norm, etc.) to the Huawei Octopus platform for
  visualization. Use this skill when the user mentions ocms, Octopus
  metrics, training metric reporting/upload/visualization, or wants to add
  metric logging to a training script. Supports custom training loops,
  HuggingFace Trainer, PyTorch Lightning, Accelerate, MMEngine, and shared
  base classes. Also triggers when the user asks to report/upload/log
  training metrics and the ocms package is installed in the conda env.
---

# ocms Training Metric Integration

## Overview

This skill integrates the `ocms` library into PyTorch training scripts so
training metrics can be reported to the Huawei Octopus platform. It provides
a framework-agnostic recorder module plus integration patterns for common
training frameworks.

Workflow at a glance:

0. **Check** whether the ocms package is available (optional install, see
   "Step 0" — the integration works without it)
1. **Discover** where the training script logs metrics
2. **Copy** `scripts/ocms_recorder.py` into the project
3. **Integrate** per the training framework (see below)
4. **Verify** with `python3 scripts/verify_ocms.py`

## Prerequisites

1. **A PyTorch training script** to integrate with (custom loop, HF
   Trainer, Lightning, Accelerate, MMEngine, or a shared base class).
2. **Python 3.8+**: run all commands with the training environment
   activated (e.g. `conda activate <env>`), so `python3` is that
   environment's interpreter. The `ocms` package is **optional**: when it is
   missing, `OcmsRecorder` degrades gracefully without affecting training.
3. **Training output directory**: metrics fall back to
   `<output_dir>/ocms_metrics` outside the Octopus platform (on the
   platform, the `METRICS` env var is preferred).

All commands below run from this skill's directory. Project-specific paths
are passed through shell variables that the agent sets from the user's
answers (see "Parameter Confirmation"); no command contains a placeholder
that must be edited by hand.

## Workflow

### Step 0: Check ocms (install only where available)

```bash
python3 scripts/verify_ocms.py
```

The script reports whether ocms is installed and runs a self-test of the
recorder in a temporary directory. Both outcomes are valid:

| Result | Meaning | Next step |
|---|---|---|
| `ocms: installed` + `OK: metrics.json and ... chart CSVs produced` | metric reporting is enabled | continue with Step 1 |
| `ocms: not installed` + `OK: graceful degradation verified` | the recorder disables itself; training is unaffected | continue with Step 1; install ocms only where it is available |

ocms is a **proprietary Octopus platform package**: it is not on PyPI and is
distributed only through a time-limited signed link in the Octopus course
README. Environments that cannot obtain it (for example evaluation
environments without that link) stay
on the graceful-degradation path, which is the expected result there, not a
failure. To install it where it is available, get the currently valid signed
link from the official
[octopus-courses README](https://gitee.com/huawei-octopus/octopus-courses/blob/master/ch2-Training/2.5-whls/1-octopus-metrics-summary/README.md)
(time-limited; re-fetch if expired), download the wheel to the current
directory, then run:

```bash
python3 -m pip install ./ocms-*.whl
```

After installing on the Octopus platform, re-run the check as
`python3 scripts/verify_ocms.py --require-ocms`, which reports a missing
package as an error instead of a degradation. Use that flag only where ocms
is expected to be installed.

### Step 1: Discover Metric-Logging Points

Search the training script for where metrics are built and logged. Common
code patterns include:

```python
# Code patterns to SEARCH FOR in the training script (not commands to run):
wandb.log(metrics, step=...)
logger.info(f"Step ..., Loss: {metrics}")
tensorboard_writer.add_scalar(...)
print(f"loss={loss.item()}")
metrics = {"loss": loss.item(), ...}
```

The function or method containing these calls is the integration point.
Typical function names: `_log_metrics`, `log_metrics`, `on_log`,
`after_train_iter`.

Also identify the available metric items — inspect the metrics dict keys:
- Loss: `loss`, `train_loss`, `action_dit_loss`, `vlm_loss`, etc.
- Learning rate: `learning_rate`, `learning_rate/<group_name>`, etc.
- Epoch: `epoch`
- Timing: `timing/data`, `timing/model`
- Eval: `mse_score`, `accuracy`, `mIoU`, etc.
- Gradient: `grad_norm`

### Step 2: Copy the Recorder Module

Copy this skill's `scripts/ocms_recorder.py` into the target project's
`migrate_to_cloudrobo/` directory.
It is a standalone, framework-agnostic module with no dependencies beyond
`ocms` and the Python standard library.

```bash
# Run from the skill directory. PROJECT_DIR is the training project root,
# set by the agent from the user's answer (see "Parameter Confirmation").
mkdir -p "$PROJECT_DIR/migrate_to_cloudrobo"
cp scripts/ocms_recorder.py "$PROJECT_DIR/migrate_to_cloudrobo/ocms_recorder.py"
```

The module exposes the following **Python API**. These are names used inside
the training code, not shell commands:

```python
from ocms_recorder import OcmsRecorder

recorder = OcmsRecorder.from_output_dir(output_dir)  # prefers $METRICS, else <output_dir>/ocms_metrics
# or: OcmsRecorder(log_dir=..., chart_groups=..., enabled=True)
recorder.log(step=global_step, metrics=metrics)       # log one metric snapshot (rank-0 only)
recorder.finish()                                     # cleanup (currently a no-op)
```

### Step 3: Integrate Per Framework

The integration approach depends on the training framework. Read the
corresponding section of `references/integration_patterns.md` for
copy-paste-ready code snippets.

**Quick reference** — the integration points below are Python
classes/methods to edit in the training code, not commands to execute:

| Framework | Integration point (Python) | Pattern |
|---|---|---|
| Custom PyTorch loop | `_log_metrics` or equivalent | direct `recorder.log()` |
| HuggingFace Trainer | `TrainerCallback.on_log` | callback class |
| PyTorch Lightning | `Callback.on_train_batch_end` | callback class |
| Accelerate | training loop (rank-0 guard) | direct `recorder.log()` |
| MMEngine | `Hook.after_train_iter` | Hook class |
| Shared base class | base `_init_ocms` + `_ocms_log` | inherited methods |

**General rule:** find where metrics are currently logged (wandb,
tensorboard, logger), then add
`recorder.log(step=step, metrics=metrics)` right after it. Run on rank-0
only to avoid file conflicts.

### Step 4: Verify

After integration, run a short training, then check the metric files of that
run (`OUTPUT_DIR` is the training output directory, set by the agent from the
user's answer):

```bash
python3 scripts/verify_ocms.py --output-dir "$OUTPUT_DIR"
```

- ocms installed: checks `metrics.json` and the chart CSVs (for example
  `loss.csv`, `learning_rate.csv`, `epoch.csv`, `timing.csv`) in `$METRICS`
  or `$OUTPUT_DIR/ocms_metrics`, and fails if they are missing.
- ocms not installed: no metric files are expected, so the check passes on
  the graceful-degradation path.
- An empty `OUTPUT_DIR` falls back to the self-test from Step 0.

Each CSV file's row format is `[step, val1, val2, ...]` with no header row.
The `metrics.json` file describes the chart structure for the Octopus UI.

## How the Recorder Works

### Chart Groups

Metrics are grouped by predicate functions into at most 6 charts (ocms hard
limit). Each group is a `(chart_name, predicate)` tuple; the predicate
receives a metric key name and returns True when that metric belongs to
this chart:

```python
DEFAULT_CHART_GROUPS = [
    ("loss",         lambda k: k == "loss" or k.endswith("_loss")),
    ("learning_rate", lambda k: k == "learning_rate" or k.startswith("learning_rate/")),
    ("epoch",        lambda k: k == "epoch"),
    ("timing",       lambda k: k.startswith("timing/")),
    ("eval_score",   lambda k: k == "mse_score" or k == "accuracy" or k == "mIoU"),
    ("grad_norm",    lambda k: k == "grad_norm"),
]
```

### Custom Chart Groups

If the default groups do not cover your metrics, pass custom groups:

```python
recorder = OcmsRecorder(
    log_dir="...",
    chart_groups=[
        ("loss", lambda k: "loss" in k),
        ("lr", lambda k: "lr" in k or "learning_rate" in k),
        ("reward", lambda k: "reward" in k),
        # ... up to 6 groups
    ],
)
```

### Key Name Sanitization

ocms only allows `[a-zA-Z0-9_\-]` for y-axis names. Metric keys like
`learning_rate/vision_tower` or `timing/data` are automatically sanitized
to `lr_vision_tower` and `data`.

### Log Directory

Prefers the `METRICS` env var (set by the Octopus platform), falling back
to `<output_dir>/ocms_metrics` for non-platform runs. This means the same
code works both on the Octopus platform and locally.

## Core Commands

Real, placeholder-free commands, run from this skill's directory with the
training environment activated:

```bash
# Check ocms and self-test the recorder (passes with or without ocms)
python3 scripts/verify_ocms.py

# Check the metric files of a training run (empty OUTPUT_DIR = self-test)
python3 scripts/verify_ocms.py --output-dir "$OUTPUT_DIR"
```

On the Octopus platform only, add `--require-ocms` to the first command to
treat a missing ocms package as an error.

Integration itself is a code edit (Steps 2–3). `OcmsRecorder`,
`recorder.log()`, and the framework callbacks are Python APIs, not commands.

## Parameter Confirmation

Confirm these with the user before Step 2. The agent exports the paths as
shell variables used by the commands above:

| Parameter | Description |
|---|---|
| Training environment | The Python/conda environment with the training stack; activate it before running the commands so `python3` is its interpreter |
| `PROJECT_DIR` | Training project root; the recorder is copied to `$PROJECT_DIR/migrate_to_cloudrobo/` |
| `OUTPUT_DIR` | Training output directory; metrics fall back to `$OUTPUT_DIR/ocms_metrics` |
| `METRICS` env var | Set by the Octopus platform; preferred metric directory when present |
| `chart_groups` | `(chart_name, predicate)` tuples, up to 6 charts (ocms hard limit) |
| `step` / `metrics` | Args to `recorder.log()`: training step (X axis) and flat metric dict |
| rank-0 only | Report from rank-0 only to avoid file conflicts |

## Reference Documents

- `scripts/ocms_recorder.py` — standalone recorder module (copy into the
  project to use)
- `scripts/verify_ocms.py` — ocms check + recorder self-test, and metric-file
  check for a training run (works with or without ocms)
- `references/iam-policies.md` — IAM permissions (none required)
- `references/ocms_api.md` — detailed ocms library API reference
- `references/integration_patterns.md` — integration code snippets per
  framework
