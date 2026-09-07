# MaaS API Readiness Playbook

Use this playbook before a live Huawei Cloud MaaS API call.

## Scope

This playbook covers MaaS model calls for:

- large language models and text generation,
- image understanding,
- image generation and image editing,
- video generation.

It does not cover deploying custom ModelArts services, fine-tuning jobs, MaaS control-plane custom endpoint management, or billing/statistics APIs. For token usage, request count, error count, and ShowStatistics planning, use `references/playbooks/maas-usage-governance.md`.

## Readiness Checklist

1. Confirm the user wants Huawei Cloud MaaS specifically.
2. Identify the capability and model family from `references/maas-model-catalog.json`.
3. Confirm that the request will use MaaS API Key authentication, not hcloud profile authentication.
4. If no key exists yet, create one in the Huawei Cloud MaaS console: left navigation `管理与统计 > API Key 管理`, then `创建API Key`.
5. Check key presence without printing the key:

```bash
python3 scripts/hcloud_environment_doctor.py --need maas --pretty
```

6. Build a dry-run plan with the relevant helper.
7. Review request body size, image formats, prompt length, model parameter, region limitation, and expected billing behavior.
8. For video, explain that task creation is not completion and that a query/wait step is required.

## API Key Creation Notes

- Open the Huawei Cloud console, switch to the region where MaaS is available, then enter MaaS.
- In the MaaS console, use `管理与统计 > API Key 管理 > 创建API Key`.
- Configure a label, description, optional IP allowlist, and optional model/custom-endpoint access scope.
- Copy the key immediately from the `您的API Key` dialog. It is shown only once; if lost, create a new API Key.
- A maximum of 30 valid API Keys can exist per account.
- MaaS API Keys are region-level and do not support cross-region use.
- A newly created key may need a few minutes before it becomes effective.

## Capability Routing

| User intent | First helper | Reference |
| --- | --- | --- |
| "有哪些 MaaS 模型" | `scripts/maas_models.py` | `references/maas-model-catalog.json` |
| "调用大模型" | `scripts/maas_chat.py` | `references/maas-model-calls.md` |
| "图像理解" | `scripts/maas_chat.py --api vision-v1` | `references/maas-model-calls.md` |
| "文生图/图片编辑" | `scripts/maas_image_generation.py` | `references/maas-model-calls.md` |
| "文生视频/图生视频" | `scripts/maas_video_generation.py` | `references/maas-model-calls.md` |

## Safety Rules

- Never ask the user to paste a MaaS API Key into chat.
- Never echo the API Key in command examples.
- Do not write generated base64 image content into planning files or final answers.
- Do not use non-Huawei model endpoints as fallback for this skill.
- Do not treat `task_id` from video creation as a generated video.
- Do not claim live MaaS availability from the local catalog alone.

## Acceptance Evidence

For text or image understanding:

- request endpoint and model,
- returned status code,
- response id/model/usage,
- generated content or summarized answer.

For image generation:

- local output file path relative to the task directory,
- manifest path,
- model and endpoint host,
- image inspection result if used downstream.

For video generation:

- create response with `task_id`,
- query response status,
- `result_url` only after `succeeded`,
- failure code/message if `failed`.
