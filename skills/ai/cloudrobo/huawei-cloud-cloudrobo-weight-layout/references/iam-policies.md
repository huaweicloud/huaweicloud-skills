# IAM Policies — huawei-cloud-cloudrobo-weight-layout

## Summary

**This skill requires no Huawei Cloud IAM permissions.** It defines a local
directory layout convention and ships a local reference loader
(`references/loader.py`). It calls no Huawei Cloud or CloudRobo API and
needs no AK/SK.

| Operation | Where it runs | Cloud permission |
|---|---|---|
| Change the training script to save checkpoints in the standard layout | local filesystem | none |
| Copy `references/loader.py` into the project | local filesystem | none |
| Locate `{output_root}` / pick the latest checkpoint / load a state dict | local Python process | none |

## Notes

- **Where the output lives**: if `{output_root}` sits on storage that is
  mounted from the cloud (for example an OBS path mounted into a training
  job), access to it is granted by the training job's own configuration.
  This skill does not request or need any permission for it.
- **Training and deployment jobs**: submitting training jobs or deploying
  models is out of scope here. The skills that do it (for example
  `huawei-cloud-cloudrobo-train` and `huawei-cloud-cloudrobo-infer`) document
  the credentials they need in their own `references/iam-policies.md`.

## Least privilege

No IAM policy, system role, or AK/SK needs to be created or granted for this
skill. Do not grant extra permissions for it.
