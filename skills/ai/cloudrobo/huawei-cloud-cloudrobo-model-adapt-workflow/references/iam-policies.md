# IAM Policies & Access Control

## Auth Model Overview

The CloudRobo model adaptation workflow runs **entirely on the user's own Ascend NPU
training/inference environment** (model project root). It does not call any Huawei Cloud
APIG/REST API directly, so it needs **no Huawei Cloud IAM policy or AK/SK** for its own
execution.

What the workflow *does* consume from Huawei Cloud services is delivered through its
sub-skills (e.g. `huawei-cloud-cloudrobo-npu-patcher`,
`huawei-cloud-cloudrobo-weight-layout`, `huawei-cloud-cloudrobo-train-metrics`,
`huawei-cloud-cloudrobo-inference-adapter`). Therefore the IAM permission model below is
limited to what a collaborating agent must hold when those sub-skills call CloudRobo /
Octopus platform APIs.

## Least-Privilege Principle

| Scope | Required Permission | Reason |
|-------|--------------------|--------|
| Local NPU project | Full control over the model project directory | `migrate_to_cloudrobo/`, `{output_root}`, `ocms_metrics/` are read/written here |
| CloudRobo training tasks | `cloudrobo train create-task / show-task / get-stages / get-events` | Stage 4 starts training; metric reporting and progress checks read staging/event data |
| Octopus platform (metrics) | Create/read `ocms_metrics/` artifacts | Stage 3 posts training metrics for visualization |
| Object storage (optional) | Read/write only the bucket that holds checkpoints/outputs | Only when weight output is synced to OBS |

> **Never grant a broad `*:*` on the Huawei Cloud account.** Grant only the service
> actions listed above; restrict object-storage access to the exact bucket the model
> project writes to.

## Credential Best Practices

- Read AK/SK from environment variables or a local credentials file — never hardcode them
  in `SKILL.md`, scripts, or `migrate_to_cloudrobo/` templates.
- Prefer temporary credentials (STS) with a short expiry for CI/agent runs.
- Keep the ocms access token / signed download link out of version control.
- Rotate AK/SK when a training container or notebook is destroyed or shared.

## What This Workflow Never Needs

- No Huawei Cloud IAM **token** acquisition — this skill performs no IAM `GetUserToken`
  call.
- No `iam:CreatePolicy` / `iam:AttachRole` — permission to run model adaptation on the
  NPU machine is the matter of the local OS account and the CloudRobo workspace the user
  already has.

## Security Notes for Files This Skill Ships

- `templates/migrate_to_cloudrobo/env_npu.sh` sets performance/offline env vars only; it
  contains **no credentials**.
- `templates/migrate_to_cloudrobo/train.sh` is a pass-through launcher; keep the
  `${VAR:-default}` pattern so external env overrides (e.g. `GR00T_VLM_BACKBONE_PATH`)
  propagate into the training command without being hardcoded.
- `scripts/` are local analysis/verification utilities; they never send code to the cloud.