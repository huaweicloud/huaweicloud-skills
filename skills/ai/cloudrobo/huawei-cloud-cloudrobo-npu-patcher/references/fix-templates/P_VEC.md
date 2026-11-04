# P_VEC: Tensor-Indexing Loops (Vectorization)

## Problem

Python loops over tensor indices cause 100x+ slowdowns on NPU because
every iteration requires a CPU/GPU sync.

## Fix

### Fix 1: dict → lookup_table, loop → torch.where

**Before:**
```python
num_disappear_track = 0
for j in range(len(track_instances)):
    obj_id = track_instances.obj_idxes[j].item()
    if obj_id >= 0:
        if obj_id in obj_idx_to_gt_idx:
            track_instances.matched_gt_idxes[j] = obj_idx_to_gt_idx[obj_id]
        else:
            num_disappear_track += 1
            track_instances.matched_gt_idxes[j] = -1
    else:
        track_instances.matched_gt_idxes[j] = -1
```

**After:**
```python
obj_idxes = track_instances.obj_idxes
mask_valid = obj_idxes >= 0

current_max = obj_idxes.max().item() if mask_valid.any() else 0

lookup_size = max(current_max + 1, 1)
lookup_table = torch.full((lookup_size,), -1, dtype=torch.long, device=track_instances.obj_idxes.device)

if obj_idx_to_gt_idx:
    keys = torch.tensor(list(obj_idx_to_gt_idx.keys()), dtype=torch.long, device=track_instances.obj_idxes.device)
    valid_keys = keys[keys < lookup_size]
    valid_values = torch.tensor([obj_idx_to_gt_idx[k.item()] for k in valid_keys], device=track_instances.obj_idxes.device)
    lookup_table[valid_keys] = valid_values

matched_gt_idxes = torch.where(
    mask_valid,
    lookup_table[torch.clamp(obj_idxes, max=lookup_size-1)],
    torch.tensor(-1, dtype=torch.long, device=track_instances.obj_idxes.device)
)

num_disappear_track = (mask_valid & (matched_gt_idxes == -1)).sum().item()
track_instances.matched_gt_idxes = matched_gt_idxes
```

### Fix 2: cat/split — vectorize variable-length list loops

When a loop processes per-sample variable-length tensors (e.g. per-batch
ground truth), use the **cat → batch compute → split** pattern instead of
the loop.

**Before:**
```python
def encode_reg_target(self, box_target, device=None):
    outputs = []
    for i in range(len(box_target)):
        output = torch.cat([
            box_target[i][..., [X, Y, Z]],
            box_target[i][..., [W, L, H]].log(),
            torch.sin(box_target[i][..., YAW]).unsqueeze(-1),
            torch.cos(box_target[i][..., YAW]).unsqueeze(-1),
            box_target[i][..., YAW + 1:],
        ], dim=-1)
        outputs.append(output)
    return outputs
```

**After:**
```python
def encode_reg_target(self, box_target, device=None):
    sizes = [box.shape[0] for box in box_target]
    boxes = torch.cat(box_target, dim=0)
    output = torch.cat([
        boxes[..., [X, Y, Z]],
        boxes[..., [W, L, H]].log(),
        torch.sin(boxes[..., YAW]).unsqueeze(-1),
        torch.cos(boxes[..., YAW]).unsqueeze(-1),
        boxes[..., YAW + 1:],
    ], dim=-1)
    if device is not None:
        output = output.to(device=device)
    outputs = torch.split(output, sizes, dim=0)
    return outputs
```

Key steps:
1. `sizes = [box.shape[0] for box in box_target]` — record each sample's
   size
2. `torch.cat(box_target, dim=0)` — concatenate all samples into one tensor
3. Compute on the concatenated tensor (single kernel launch)
4. `torch.split(output, sizes, dim=0)` — split back into per-sample tensors

This method works even when the tensors have different lengths along the
cat dimension.

## Notes

- Fix 1: the dict→lookup_table construction still has Python loop
  overhead, but the complexity is O(dict_size) instead of
  O(track_instances).
- Fix 2: cat/split avoids per-sample kernel launches. The cat/split
  overhead is negligible compared to the per-iteration NPU sync cost.
