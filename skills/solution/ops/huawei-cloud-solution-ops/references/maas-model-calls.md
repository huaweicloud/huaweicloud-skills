# Huawei Cloud MaaS Model Calls

Use this reference when a task explicitly needs Huawei Cloud MaaS API calls for text generation, image understanding, image generation/editing, or video generation. MaaS is API-first in this skill; it is not registered as a KooCLI service.

## Boundaries

- MaaS model calls use `https://api.modelarts-maas.com` and `Authorization: Bearer <MaaS API Key>`.
- Read the key only from `MAAS_API_KEY` or `MODELARTS_MAAS_API_KEY`.
- Do not write API keys into source files, prompt files, manifests, run journals, docs, shell history examples, or final answers.
- Run dry-run first when constructing a new request shape.
- Image, video, and other potentially billable MaaS generation calls are external side effects. Before an online call, present the model, count or scope, intended use, and cost/risk boundary, then wait for the user's explicit confirmation. An initial request to create content is not itself execution authorization.
- Token Plan endpoints are for supported AI tools and must not be treated as generic API-call quota.
- Local model information comes from `references/maas-model-catalog.json`; for live availability use MaaS console or `scripts/maas_models.py --online --execute` after the user confirms a live API call.

## Official Online Docs

Use these Huawei Cloud support links when local docs are insufficient or the agent needs to verify latest MaaS behavior:

| Topic | URL |
| --- | --- |
| MaaS documentation index | `https://support.huaweicloud.com/maas/index.html` |
| Model list | `https://support.huaweicloud.com/model-call-maas/usermanual_maas_0008.html` |
| Text generation overview | `https://support.huaweicloud.com/model-call-maas/model-call-004.html` |
| Text generation API details | `https://support.huaweicloud.com/model-call-maas/model-call-005.html` |
| Text generation examples | `https://support.huaweicloud.com/model-call-maas/model-call-006.html` |
| Text generation notes | `https://support.huaweicloud.com/model-call-maas/model-call-008.html` |
| Image understanding | `https://support.huaweicloud.com/model-call-maas/model-call-011.html` |
| Image generation overview | `https://support.huaweicloud.com/model-call-maas/model-call-012.html` |
| Video generation overview | `https://support.huaweicloud.com/model-call-maas/model-call-063.html` |
| Text-to-video | `https://support.huaweicloud.com/model-call-maas/model-call-064.html` |
| Image-to-video | `https://support.huaweicloud.com/model-call-maas/model-call-065.html` |
| Reference-to-video | `https://support.huaweicloud.com/model-call-maas/model-call-066.html` |
| First/last-frame video | `https://support.huaweicloud.com/model-call-maas/model-call-067.html` |
| MaaS standard API V2 | `https://support.huaweicloud.com/model-call-maas/model-call-019.html` |
| OpenAI-compatible API | `https://support.huaweicloud.com/model-call-maas/model-call-021.html` |
| Image generation API | `https://support.huaweicloud.com/model-call-maas/model-call-023.html` |
| Model API call specification | `https://support.huaweicloud.com/model-call-maas/model-call-017.html` |
| API overview | `https://support.huaweicloud.com/api-maas/api-maas-0002.html` |

## Endpoint Map

| Capability | Endpoint | Helper |
| --- | --- | --- |
| Model list | `GET /v2/models` | `scripts/maas_models.py` |
| Text generation | `POST /v2/chat/completions` | `scripts/maas_chat.py --api standard-v2` |
| OpenAI-compatible chat | `POST /openai/v1/chat/completions` | `scripts/maas_chat.py --api openai-compatible` |
| Image understanding | `POST /v1/chat/completions` | `scripts/maas_chat.py --api vision-v1` |
| Image generation/edit | `POST /v1/images/generations` | `scripts/maas_image_generation.py` |
| Video generation create | `POST /v1/video/generations` | `scripts/maas_video_generation.py --action create` |
| Video generation query | `GET /v1/video/generations/{task_id}` | `scripts/maas_video_generation.py --action query` |

## Default Workflow

1. Identify capability: text, image understanding, image generation/editing, text-to-video, image-to-video, reference-to-video, or keyframe-to-video.
2. Check local model candidates:

```bash
python3 scripts/maas_models.py --capability text --pretty
python3 scripts/maas_models.py --capability video_generation --pretty
```

3. Build a dry-run request and inspect endpoint, payload, model, image/video parameters, and key presence.
4. If the user confirms a live MaaS API call, run the helper without `--dry-run`.
5. For video, persist the returned `task_id` in the user-facing report and query or wait until `succeeded` or `failed`; do not claim completion from task creation alone.
6. For generated images, inspect local files before deployment or downstream use.

## Text Generation

Use `maas_chat.py` for standard V2 chat or OpenAI-compatible chat:

```bash
python3 scripts/maas_chat.py \
  --api standard-v2 \
  --model deepseek-v3.2 \
  --prompt "用三句话解释华为云 MaaS 的适用场景" \
  --dry-run --pretty
```

Useful optional fields:

- `--system`
- `--temperature`
- `--top-p`
- `--max-tokens`
- `--max-completion-tokens`
- `--reasoning-effort high|max`
- `--extra-body-json` for model-specific fields such as `thinking`

`maas_chat.py` can plan `stream=true` payloads but does not execute streaming responses directly.

## Image Understanding

Use the V1 chat endpoint with `qwen2.5-vl-72b`. Local images are converted to data URIs in the request; dry-run output summarizes the base64 instead of printing it.

```bash
python3 scripts/maas_chat.py \
  --api vision-v1 \
  --model qwen2.5-vl-72b \
  --prompt "描述这张图片里的主体和风险点" \
  --image ./input.png \
  --dry-run --pretty
```

Supported input image formats in the local catalog: png, jpeg, jpg, webp, bmp, and tiff.

## Image Generation And Editing

Use `maas_image_generation.py` for new image generation and image editing. For batch site-asset generation from a prompt manifest, use `maas_text_to_image.py`.

Text-to-image dry-run:

```bash
python3 scripts/maas_image_generation.py \
  --prompt "A clean product hero image for a cloud AI service dashboard" \
  --file hero.webp \
  --out-dir ./assets \
  --model qwen-image \
  --size 1024x1024 \
  --dry-run --pretty
```

Image edit dry-run:

```bash
python3 scripts/maas_image_generation.py \
  --prompt "将背景改成浅色办公环境，保持主体不变" \
  --file edited.webp \
  --image ./source.png \
  --out-dir ./assets \
  --model qwen-image-edit-2509 \
  --dry-run --pretty
```

Prompt files can contain an `items` list with `file`, `prompt`, `size`, `seed`, `image` or `images`, and `watermark`.

## Video Generation

Video generation is asynchronous.

Text-to-video dry-run:

```bash
python3 scripts/maas_video_generation.py \
  --action create \
  --model Wan2.2-T2V-A14B \
  --prompt "小猫在城市公园慢慢散步，镜头平稳推进" \
  --size 720x1280 \
  --fps 16 \
  --duration 5 \
  --dry-run --pretty
```

Image-to-video dry-run:

```bash
python3 scripts/maas_video_generation.py \
  --action create \
  --model Wan2.2-I2V-A14B \
  --prompt "让图片中的主体自然转身，背景保持稳定" \
  --image ./frame.jpg \
  --size 720x1280 \
  --duration 5 \
  --dry-run --pretty
```

PixVerse reference or keyframe models can use `--media type=image_url,url=https://...`, `--first-frame`, and `--last-frame`. For complex provider-specific shapes, pass `--body-json-file` or `--body-json-text` with the exact documented request body.

Query or wait:

```bash
python3 scripts/maas_video_generation.py --action query --task-id <task_id> --pretty
python3 scripts/maas_video_generation.py --action wait --task-id <task_id> --max-attempts 20 --interval 15 --pretty
```

Do not download generated videos by default. Report `status`, `task_id`, `result_url`, and usage metadata.

## Error Handling

- `401` or `403`: API key invalid, not active yet, wrong region, or missing permission.
- `429`: Rate-limited; stop or retry later with bounded attempts.
- `5xx`: Model service or platform issue; retry only if low risk and bounded.
- Video `queued` or `running`: not complete.
- Video `failed`: surface `error.code` and `error.message`.
