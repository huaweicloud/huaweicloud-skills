# Acceptance Criteria 验收标准

A model adaptation task on the CloudRobo platform is considered complete when **all** of
the following hold.

## Gates

| Gate | Criterion | Check |
|------|-----------|-------|
| G1 | Model code runs on NPU | `progress.py issues.json --check-complete` passes; `verify.py --runtime --pipeline --data` green; `migrate_to_cloudrobo/` contains `env_npu.sh / train.sh / runtime_patches.py` |
| G2 | Standard weight layout | `{output_root}/` root holds final-step checkpoint; `{output_root}/_ckpt/checkpoint_{step}/` holds periodic checkpoints; loader resolves `{output_root}` from the weight file |
| G3 | Metric reporting integrated | ocms recorder copied; rank-0 only reporting; `{output_root}/ocms_metrics/` produced and visible on Octopus |
| G4 | Training output produced | `train.sh` started training; final weights + `dataset_statistics.json` at `{output_root}` root; `_ckpt/` populated |
| G5 | Inference interface works | `verify_adapter.py` unit tests PASS; running server + `test_client.py` smoke test PASS (actions shape `(T,D)`, `server_timing.prev_total_ms` correct) |

## Final Deliverables

1. `migrate_to_cloudrobo/ADAPTATION_SUMMARY.md` covering the full flow (file inventory,
   training command, metric status, wire-format contract, known issues).
2. Final weights and statistics at `{output_root}/` (Stage 4 output).
3. Deployment directory (`migrate_to_cloudrobo/deployment/`) with adapter, transport
   server, entry point, and passing `test_client.py`.

## Not In Scope

- Cross-skill delegation: this workflow orchestrates sub-skills via the Skill tool and
  never re-implements their internals.
- Guaranteeing cluster-level readiness (HCCL config) — that belongs to the user's Ascend
  environment.