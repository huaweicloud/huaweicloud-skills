# Verification Method 验证方法

This section defines how to verify the CloudRobo model adaptation workflow end to end.
Each stage has a concrete gate (G1–G5) with runnable checks; both the helper scripts
shipped in `scripts/` and manual inspection are used.

## Stage 1 — NPU Adaptation (npu-patcher)

```bash
# scan the model codebase -> issues.json
python <skill dir>/scripts/scan.py /path/to/model --output /path/to/model

# iterate issues
python <skill dir>/scripts/progress.py /path/to/model/issues.json --next
python <skill dir>/scripts/progress.py /path/to/model/issues.json --fixed <issue_id>
python <skill dir>/scripts/progress.py /path/to/model/issues.json --skip <issue_id> --reason "..."
python <skill dir>/scripts/progress.py /path/to/model/issues.json --check-complete

# verify NPU runtime + pipeline (config auto-detected)
python <skill dir>/scripts/verify.py /path/to/model --runtime --pipeline

# verify real data loading
python <skill dir>/scripts/verify.py /path/to/model --data
```

**Gate G1** passes when `--check-complete` returns success and `verify.py` (runtime +
pipeline + data) reports all checks green.

## Stage 2 — Weight Save Layout

Manual verification:

1. Start the modified training script for a couple of steps.
2. Confirm `{output_root}/_ckpt/checkpoint_{step}/` collects periodic checkpoints and the
   final-step checkpoint lands at `{output_root}/` root.
3. Confirm the loader resolves `{output_root}` by walking upward from the weight file to
   `_ckpt/`.

## Stage 3 — Training Metrics (ocms)

```bash
<conda_env>/bin/pip show ocms
```

If missing, install ocms (official Octopus whl) and import-check:

```bash
<conda_env>/bin/pip install ocms
<conda_env>/bin/python -c "import ocms; from ocms import Summary; print('ocms OK')"
```

**Gate G3** passes when only rank-0 reports metrics and `ocms_metrics/` is produced at
`{output_root}`.

## Stage 4 — Training Boundary

```bash
ASCEND_RT_VISIBLE_DEVICES=<cards> bash migrate_to_cloudrobo/train.sh <launch command...>
```

Check the output layout matches Gate G4 (final weights/statistics at `{output_root}` root,
`_ckpt/checkpoint_{step}/` present, `ocms_metrics/` present).

## Stage 5 — Inference Adapter

```bash
# server-less adapter unit tests
python <skill dir>/scripts/verify_adapter.py --adapter /path/to/adapter.py --class-name MyAdapter

# start the server, then end-to-end smoke test
python <skill dir>/scripts/test_client.py --host 127.0.0.1 --port 8000
```

**Gate G5** passes when `verify_adapter.py` reports all PASS and `test_client.py` asserts
an `actions` shape of `(T, D)` with correct `server_timing.prev_total_ms` semantics.

## Prerequisite Install Checks

| Dependency | Check | Install |
|------------|-------|---------|
| `torch_npu` (CANN) | `python -c "import torch_npu"` | official Ascend PyTorch install guide (see Prerequisites) |
| `ocms` (Stage 3) | `<conda_env>/bin/pip show ocms` | `<conda_env>/bin/pip install ocms` (proprietary Octopus package; degrade gracefully when absent) |
| `migrate_to_cloudrobo/` templates | `ls migrate_to_cloudrobo/{env_npu.sh,train.sh,runtime_patches.py}` | copy from `<skill dir>/templates/migrate_to_cloudrobo/` |