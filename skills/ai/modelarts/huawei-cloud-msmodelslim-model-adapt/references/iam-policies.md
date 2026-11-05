# IAM Permission Policies - msModelSlim Model Adapter

IAM permission policies required by this skill.

## Permission Model Overview

This skill is primarily a **local execution workflow**: it generates a slim
random-weight test model, runs full fallback quantization with `msmodelslim`,
verifies weight consistency, and validates the quantization description file.
All four steps (`step1` - `step4`) operate on the local filesystem with
`transformers` / `msmodelslim` and do **not** call any Huawei Cloud API, so no
IAM cloud-action permission is required for the core workflow.

Cloud-side access is only relevant in the optional surrounding stages:

| Stage | Operation | Required Permission | Description |
|-------|-----------|--------------------|-------------|
| Model download (optional) | ModelScope download | None (external service) | Download model via `modelscope download` |
| Deployment (optional) | Upload/run on ModelArts or Ascend NPU | `modelarts:*` read/list + instance access | Deploy the quantized model for inference |

## Minimum Required Policy (JSON)

### Core workflow (recommended, minimal)

The four-step verification needs **no IAM policy** — it runs entirely on the
local machine. No JSON policy is required.

### Optional: ModelArts deployment

If the quantized model is deployed through ModelArts, allow at least read/list
over ModelArts resources:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:service:list",
        "modelarts:service:get",
        "modelarts:model:list",
        "modelarts:model:get"
      ]
    }
  ]
}
```

## Least Privilege Principle

- The core adapter-creation and verification workflow does not require any
  Huawei Cloud IAM permission - do not grant cloud actions purely to run the
  scripts locally.
- Only add ModelArts/Ascend permissions when the user explicitly asks to deploy
  or manage the quantized model in the cloud.
- Never hardcode AK/SK in scripts or documents; use environment variables
  (`HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK`) or the standard `hcloud configure`
  flow when cloud access is actually needed.