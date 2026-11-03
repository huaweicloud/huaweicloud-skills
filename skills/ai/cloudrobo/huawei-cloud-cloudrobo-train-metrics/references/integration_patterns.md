# Integration Patterns per Framework

This file provides copy-paste-ready integration code snippets for common
training frameworks. Choose the pattern that matches your codebase.

## Table of Contents

1. [Custom PyTorch Loop](#1-custom-pytorch-loop)
2. [HuggingFace Trainer](#2-huggingface-trainer)
3. [PyTorch Lightning](#3-pytorch-lightning)
4. [Accelerate](#4-accelerate)
5. [MMEngine](#5-mmengine)
6. [Shared Base Class (multiple trainers)](#6-shared-base-class-multiple-trainers)

---

## 1. Custom PyTorch Loop

Applies to training scripts with a manual `for` loop and a
`_log_metrics` (or similar) function. This is the most common pattern in
research codebases.

**Step 1 — copy `ocms_recorder.py` into the project's
`migrate_to_cloudrobo/` directory.**

**Step 2 — initialize in setup, log in the metrics function:**

```python
from ocms_recorder import OcmsRecorder

class MyTrainer:
    def setup(self):
        # ... existing setup ...
        if rank == 0:  # rank-0 only
            self.recorder = OcmsRecorder.from_output_dir(self.output_dir)

    def log_metrics(self, step, metrics):
        if rank == 0:
            # ... existing logging (wandb, tensorboard, etc.) ...
            self.recorder.log(step=step, metrics=metrics)

    def train(self):
        self.setup()
        for step in range(max_steps):
            # ... training step ...
            if step % log_freq == 0:
                self.log_metrics(step, {"loss": loss.item(), "learning_rate": lr, ...})
```

**Key points:**
- `OcmsRecorder.from_output_dir()` uses the `METRICS` env var on the
  Octopus platform and falls back to `<output_dir>/ocms_metrics` outside
  the platform.
- Create and log on rank-0 only to avoid file conflicts.
- The recorder degrades gracefully when `ocms` is not installed.

---

## 2. HuggingFace Trainer

Applies to scripts using `transformers.Trainer`. Add a `TrainerCallback`:

```python
from transformers import TrainerCallback
from ocms_recorder import OcmsRecorder

class OcmsTrainerCallback(TrainerCallback):
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.recorder = None

    def on_train_begin(self, args, state, control, **kwargs):
        self.recorder = OcmsRecorder.from_output_dir(self.output_dir)

    def on_log(self, args, state, control, metrics=None, **kwargs):
        if self.recorder is None or metrics is None:
            return
        self.recorder.log(step=state.global_step, metrics=metrics)

    def on_train_end(self, args, state, control, **kwargs):
        if self.recorder:
            self.recorder.finish()

# Pass to the Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    callbacks=[OcmsTrainerCallback(training_args.output_dir)],
    **data_module,
)
```

**HF Trainer metrics** typically include: `loss`, `learning_rate`,
`epoch`, `grad_norm`. The default chart groups handle all of these.

---

## 3. PyTorch Lightning

Applies to scripts using `pytorch_lightning.Trainer`. Add a `Callback`:

```python
from lightning.pytorch import Callback
from ocms_recorder import OcmsRecorder

class OcmsLightningCallback(Callback):
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.recorder = None

    def on_train_start(self, trainer, pl_module):
        if trainer.is_global_zero:
            self.recorder = OcmsRecorder.from_output_dir(self.output_dir)

    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        if self.recorder and trainer.is_global_zero:
            metrics = {
                "loss": float(outputs.get("loss", 0)),
                "learning_rate": float(trainer.optimizers[0].param_groups[0]["lr"]),
            }
            self.recorder.log(step=trainer.global_step, metrics=metrics)

    def on_train_end(self, trainer, pl_module):
        if self.recorder:
            self.recorder.finish()

# Pass to the Trainer
trainer = L.Trainer(callbacks=[OcmsLightningCallback(output_dir)])
```

**Note:** Lightning's `outputs` dict in `on_train_batch_end` contains
everything returned by `training_step`. Extract the metrics you need from
it.

---

## 4. Accelerate

Applies to scripts using `accelerate.Accelerator` (common in VLA projects
like starVLA). The pattern is similar to the custom loop:

```python
from accelerate import Accelerator
from ocms_recorder import OcmsRecorder

accelerator = Accelerator()
recorder = None

if accelerator.is_main_process:
    recorder = OcmsRecorder.from_output_dir(cfg.output_dir)

# In the training loop:
while step < max_steps:
    # ... training step ...
    if step % log_freq == 0 and accelerator.is_main_process:
        metrics = {"loss": loss.item(), "learning_rate": scheduler.get_last_lr()[0]}
        # ... wandb.log, logger.info, etc. ...
        recorder.log(step=step, metrics=metrics)
```

**Tip:** if there is a shared base class (like `TrainerUtils`), add the
recorder to the base class so all trainers inherit it automatically. See
[Pattern 6](#6-shared-base-class-multiple-trainers) below.

---

## 5. MMEngine

Applies to scripts using `mmengine.runner.Runner`. Add a custom `Hook`:

```python
from mmengine.hooks import Hook
from ocms_recorder import OcmsRecorder

class OcmsHook(Hook):
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.recorder = None

    def before_run(self, runner):
        if runner.rank == 0:
            self.recorder = OcmsRecorder.from_output_dir(self.output_dir)

    def after_train_iter(self, runner, data, outputs, batch_idx):
        if self.recorder and runner.rank == 0:
            metrics = {
                "loss": float(outputs.get("loss", 0)),
                "learning_rate": float(runner.optimizer.param_groups[0]["lr"]),
            }
            self.recorder.log(step=runner.iter, metrics=metrics)

    def after_run(self, runner):
        if self.recorder:
            self.recorder.finish()

# Register with the Runner
runner = Runner(
    model=model,
    ...
    custom_hooks=[OcmsHook(output_dir)],
)
```

---

## 6. Shared Base Class

When multiple trainers inherit the same shared base class, add the recorder
to the base class so all trainers inherit it automatically. This is the
pattern used by starVLA's `TrainerUtils`.

```python
from ocms_recorder import OcmsRecorder

class TrainerBase:
    def _init_ocms(self):
        """Call from prepare_training/setup (rank-0 only)."""
        self._ocms_recorder = OcmsRecorder.from_output_dir(self.config.output_dir)

    def _ocms_log(self, metrics):
        """Call from _log_metrics (rank-0 only)."""
        if hasattr(self, "_ocms_recorder"):
            self._ocms_recorder.log(step=self.completed_steps, metrics=metrics)

class TrainerA(TrainerBase):
    def prepare_training(self):
        # ... existing setup ...
        self._init_ocms()

    def _log_metrics(self, metrics):
        # ... wandb.log, logger.info, etc. ...
        self._ocms_log(metrics)
```

**Why this pattern?** When 3-4 trainers share the same metric-logging flow,
adding it to the base class means one change applies everywhere. New
trainers get the feature automatically.

---

## Choosing the Right Pattern

| Framework | Pattern | Integration point |
|---|---|---|
| Custom PyTorch loop | direct call | `_log_metrics` or equivalent |
| HuggingFace Trainer | `TrainerCallback` | `on_log` |
| PyTorch Lightning | `Callback` | `on_train_batch_end` |
| Accelerate | direct call | in the training loop |
| MMEngine | `Hook` | `after_train_iter` |
| Shared base class | base-class method | `_init_ocms` + `_ocms_log` |

**General rule:** find where metrics are currently logged (search for
`wandb.log`, `logger.info`, `print` with metric values), then add
`recorder.log(step, metrics)` right after it.
