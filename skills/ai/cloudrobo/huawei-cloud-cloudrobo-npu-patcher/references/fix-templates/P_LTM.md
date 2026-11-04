# P_LTM: pytorch_lightning.metrics → torchmetrics

## Problem

`pytorch_lightning.metrics` is deprecated and has moved to `torchmetrics`.

## Fix

### Fix 1: Import path update

**Before:**
```python
from pytorch_lightning.metrics.metric import Metric
from pytorch_lightning.metrics.functional.classification import stat_scores_multiple_classes
from pytorch_lightning.metrics.functional.reduction import reduce
```

**After:**
```python
from torchmetrics import Metric
from torchmetrics.functional import stat_scores
from torchmetrics.utilities import reduce
```

### Fix 2: Remove the deprecated compute_on_step

`compute_on_step` is deprecated in torchmetrics. Remove it from the
`__init__` parameters and the `super().__init__()` call.

**Before:**
```python
def __init__(self, n_classes, compute_on_step=False):
    super().__init__(compute_on_step=compute_on_step)
```

**After:**
```python
def __init__(self, n_classes):
    super().__init__()
```

### Fix 3: stat_scores_multiple_classes → stat_scores

`stat_scores` returns shape `(n_classes, 5)` with `average=None`, columns
`[tp, fp, tn, fn, support]`.

**Before:**
```python
tps, fps, _, fns, sups = stat_scores_multiple_classes(prediction, target, n_classes)
```

**After:**
```python
result = stat_scores(prediction, target, task='multiclass', num_classes=n_classes, average=None)
tps, fps, _, fns, sups = result[:, 0], result[:, 1], result[:, 2], result[:, 3], result[:, 4]
```

### Fix 4: reduce parameter value mapping

torchmetrics' `reduce()` uses different reduction string values:

| pytorch_lightning | torchmetrics |
|---|---|
| `'mean'` | `'elementwise_mean'` |
| `'sum'` | `'sum'` |
| `'none'` | `'none'` |

**Before:**
```python
return reduce(scores, reduction=self.reduction)  # self.reduction may be 'mean'
```

**After:**
```python
_reduction = 'elementwise_mean' if self.reduction == 'mean' else self.reduction
return reduce(scores, reduction=_reduction)
```

## Notes

- Not `torchmetrics.functional.reduction` — that path does not exist in
  torchmetrics >= 1.0. The correct location is
  `torchmetrics.utilities.reduce`.
