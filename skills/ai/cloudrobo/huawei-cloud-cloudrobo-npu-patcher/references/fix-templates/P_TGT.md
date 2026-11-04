# P_TGT: Target Computation Optimization

## Problem

Target computation repeatedly executes expensive operations (sigmoid, log,
pow) inside loops, or creates constant tensors for every batch element.

## Fix

### Fix 1: Compute in batch once, index per sample

**Before:**
```python
def _cls_cost(self, cls_pred, cls_target):
    bs = cls_pred.shape[0]
    cls_pred = cls_pred.sigmoid()
    costs = []
    for i in range(bs):
        neg_cost = -(1 - cls_pred[i] + self.eps).log() * (1 - self.alpha) * cls_pred[i].pow(self.gamma)
        pos_cost = -(cls_pred[i] + self.eps).log() * self.alpha * (1 - cls_pred[i]).pow(self.gamma)
        cost = (pos_cost - neg_cost) * self.cls_weight
        costs.append(cost[:, cls_target[i]] if len(cls_target[i]) > 0 else None)
    return costs
```

**After:**
```python
def _cls_cost(self, cls_pred, cls_target):
    bs = cls_pred.shape[0]
    cls_pred = cls_pred.sigmoid()
    neg_cost = -(1 - cls_pred + self.eps).log() * (1 - self.alpha) * cls_pred.pow(self.gamma)
    pos_cost = -(cls_pred + self.eps).log() * self.alpha * (1 - cls_pred).pow(self.gamma)
    cost = (pos_cost - neg_cost) * self.cls_weight
    costs = []
    for i in range(bs):
        costs.append(cost[i, :, cls_target[i]] if len(cls_target[i]) > 0 else None)
    return costs
```

### Fix 2: Extract loop-invariant computations

When full vectorization is infeasible (e.g. per-sample variable-length data
prevents batch computation), extract all loop-invariant computations and
tensor creations outside the loop.

**Before:**
```python
def _box_cost(self, box_pred, box_target, instance_reg_weights):
    bs = box_pred.shape[0]
    cost = []
    for i in range(bs):
        if len(box_target[i]) > 0:
            weights = box_pred.new_tensor(self.reg_weights)  # ← created every iteration!
            cost.append(
                torch.sum(
                    torch.abs(box_pred[i, :, None] - box_target[i][None])
                    * instance_reg_weights[i][None]
                    * weights,
                    dim=-1,
                )
                * self.box_weight
            )
        else:
            cost.append(None)
    return cost
```

**After:**
```python
def _box_cost(self, box_pred, box_target, instance_reg_weights):
    bs = box_pred.shape[0]
    weights = box_pred.new_tensor(self.reg_weights)  # ← extracted outside the loop
    cost = []
    for i in range(bs):
        if len(box_target[i]) > 0:
            cost.append(
                torch.sum(
                    torch.abs(box_pred[i, :, None] - box_target[i][None])
                    * instance_reg_weights[i][None]
                    * weights,
                    dim=-1,
                )
                * self.box_weight
            )
        else:
            cost.append(None)
    return cost
```

## Notes

- Common loop-invariant candidates: `tensor.new_tensor(constant)`
  (creating a tensor from a constant), `self.some_weight * ...` (scalar
  multiplication with a class attribute), and any computation depending
  only on loop-invariant variables (`self.*`, function args not indexed
  by `i`).
