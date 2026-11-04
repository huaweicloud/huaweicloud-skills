# IAM Policies — huawei-cloud-cloudrobo-npu-patcher

## Summary

**This skill requires no Huawei Cloud IAM permissions.** It does not call any
Huawei Cloud API and needs no AK/SK.

Everything the skill does runs locally on the user's model codebase and NPU host:

| Operation | Where it runs | Cloud permission |
|---|---|---|
| Scan the model codebase (`python scripts/scan.py`) | local filesystem | none |
| Track and mark issues (`python scripts/progress.py`) | local filesystem | none |
| Apply fixes from `references/fix-templates/` and `scripts/runtime_patches.py` | local filesystem | none |
| Verify NPU runtime / pipeline / data loading (`python scripts/verify.py`) | local NPU host (torch_npu) | none |
| Generate `migrate_to_cloudrobo/` (`env_npu.sh`, `train.sh`) from `templates/` | local filesystem | none |

## Notes

- Submitting training jobs to the CloudRobo platform is out of scope for this
  skill. The permissions for that are listed in the IAM policies of the skill
  that submits the job, such as `huawei-cloud-cloudrobo-train`.

## Least privilege

No IAM policy, system role, or AK/SK needs to be created or granted for this
skill. Do not grant extra permissions for it.
