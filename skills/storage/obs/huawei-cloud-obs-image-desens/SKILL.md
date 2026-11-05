---
name: huawei-cloud-obs-image-desens
description: |
  One-click OBS image desensitization skill for Huawei Cloud. Lists images in an OBS bucket/prefix, applies desensitization rules (full-image mosaic, Gaussian blur, region mosaic/blur/occlusion) locally via Pillow, and writes results back to a target bucket/prefix; optionally creates a FunctionGraph function + OBS event trigger for automatic on-upload desensitization.
  Use this skill when the user wants to: (1) desensitize/blur/mosaic images stored in OBS, (2) batch mosaic or blur all images under a bucket prefix, (3) occlude sensitive regions (faces, license plates, IDs) in OBS images, (4) set up automatic image desensitization when files are uploaded to an OBS bucket.
  Triggers include: "OBS图片脱敏", "图片打码", "图片马赛克", "图片模糊", "人脸打码", "敏感区域遮挡", "OBS图片一键脱敏", "批量打码", "自动脱敏", "image desensitization", "mosaic image in OBS", "blur OBS images", "auto desensitize uploads", "打码", "脱敏"
tags: [huawei-cloud, obs, image, desensitization, mosaic]
---

# Huawei Cloud OBS Image Desensitization Skill

## Overview

This skill provides a one-click flow to desensitize images stored in Huawei Cloud OBS:
**list → download → desensitize → write back**. The user only needs to specify a bucket
name (and optionally a prefix) plus a desensitization rule; the skill discovers matching
images, applies the rule locally with Pillow, and uploads the processed results to a
target bucket/prefix.

**Architecture**:

- **obsutil (via `hcloud obs`)** — OBS object listing, download and upload (KooCLI maps `obs`
  sub-commands to obsutil)
- **Pillow (PIL)** — local image desensitization processing (mosaic, Gaussian blur, region occlude)
- **huaweicloudsdkfunctiongraph** — optional automation: create a FunctionGraph function with
  an OBS event trigger so newly uploaded images are desensitized automatically

**Applicable Scenarios**:

- Batch mosaic / blur all images under a bucket or prefix (e.g. `input/`)
- Occlude sensitive regions (ID numbers, license plates, faces) in images
- Full-image desensitization of exported screenshots or photo collections
- Build an automatic "upload → desensitize → store" pipeline on an OBS bucket

**Typical Use Cases**:

1. "打码 my-bucket input/ 下的所有图片" → list `input/`, mosaic each image, write to `desensitized/`
2. "把 xxx图片的人脸区域打码" → `region` rule with face-region coordinates
3. "上传到桶里的图片自动脱敏" → `setup-trigger` creates a FunctionGraph function + OBS trigger

**Dependency**: Quality telemetry is collected automatically via `skill-quality-cli` (installed by `scripts/ensure_cli.sh` if absent).

## Prerequisites

### 1. KooCLI / obsutil

- **KooCLI >= 3.2.0** required for OBS list/download/upload (obsutil mode).
  Verify: `hcloud version`
- obsutil credentials must be configured (same AK/SK as the console). OBS operations go through
  `hcloud obs ...`; if credentials are missing the first `hcloud obs ls` returns a configuration hint.

### 2. Python + Pillow

```bash
> **⚠️ Mandatory: every `hcloud` command in this skill MUST be wrapped with `skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- ` — bare `hcloud` calls are strictly forbidden.**

skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- pip install Pillow
```

### 3. Optional: FunctionGraph SDK (only for `setup-trigger`)

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- pip install huaweicloudsdkfunctiongraph
```

### 4. Authentication (Environment)

For the `setup-trigger` sub-command, provide Huawei Cloud credentials:

```bash
export HUAWEI_AK="your-access-key"
export HUAWEI_SK="your-secret-key"
export HUAWEI_REGION="cn-north-4"
export HUAWEI_PROJECT_ID="your-project-id"
```

**Security rules**: never echo AK/SK; never ask the user to paste AK/SK into the conversation;
reuse environment/`hcloud` configured credentials where possible.

### 5. IAM Permissions

See [IAM Policies](references/iam-policies.md) for the least-privilege permissions of
OBS listing/download/upload and, for the optional automation path, FunctionGraph
`functiongraph:function:create` + `functiongraph:trigger:create`.

- **`skill-quality-cli`** — ensured by `bash scripts/ensure_cli.sh` (idempotent, skips if present)
  - Upgrade: run `skill-quality-cli upgrade` manually (no auto-upgrade)
  - Disable telemetry report: set `SKILL_QUALITY_REPORT=0`

## Workflow

```text
User Request → Parse bucket/prefix + rule → obsutil ls (filter image files)
  → hcloud obs cp download → Pillow desensitization (mosaic/blur/region)
  → hcloud obs cp upload to target bucket/prefix → Report per-file results
Optional: setup-trigger → FunctionGraph CreateFunction (auto-desens code)
  → CreateFunctionTrigger (OBS event) → auto pipeline on upload
```

## Core Commands

All commands are executed with the skill script `scripts/obs_image_desens.py`.
Run from the skill directory:

```bash
cd scripts
skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- python3 obs_image_desens.py --help
```

### List candidate images

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- python3 obs_image_desens.py list --bucket {bucket} --prefix {prefix}
```

Lists image files (`.jpg/.jpeg/.png/.bmp/.webp/.gif/.tif/.tiff`) under `obs://{bucket}/{prefix}`.

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--bucket` | Yes | OBS bucket name |
| `--prefix` | No | Object key prefix to filter (default empty = whole bucket) |
| `--show-all` | No | Also list non-image objects |

### One-run desensitization

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- python3 obs_image_desens.py process \
  --source-bucket {source_bucket} \
  --source-prefix {source_prefix} \
  --target-bucket {target_bucket} \
  --target-prefix {target_prefix} \
  --rule {whole|blur|region|region-blur|region-block} \
  [--block-size {block_size}] [--radius {radius}] [--regions {regions}] [--fill {fill}] [--yes]
```

Downloads each matched image, applies the rule, uploads the result to the target bucket/prefix,
and prints a per-file JSON report.

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--source-bucket` | Yes | Source OBS bucket |
| `--source-prefix` | No | Source key prefix (default empty) |
| `--target-bucket` | No | Target bucket (default: same as source) |
| `--target-prefix` | No | Target key prefix (default `desensitized/`) |
| `--rule` | Yes | `whole` (full mosaic), `blur` (Gaussian blur), `region` (region mosaic), `region-blur` (region blur), `region-block` (solid region occlusion) |
| `--block-size` | No | Mosaic pixel block size, default 12 |
| `--radius` | No | Gaussian blur radius, default 8 |
| `--regions` | No | Region(s) `x0,y0,x1,y1[;x0,y0,x1,y1]` for region rules |
| `--fill` | No | Region-block fill color, default black |
| `--yes` | No | Skip interactive confirmation (batch/automation) |

### Create automatic desensitization (FunctionGraph + OBS trigger, optional)

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- python3 obs_image_desens.py setup-trigger \
  --function-name {function_name} \
  --trigger-bucket {bucket} \
  --event-type ObjectCreated \
  --rule whole --block-size 16 \
  --region {region} --project-id {project_id}
```

Creates a FunctionGraph function (inline Python code that desensitizes any image object on
invocation) and an OBS trigger on the bucket. Read the [Parameter Confirmation](#parameter-confirmation)
table below, and confirm with the user before executing — this creates billable cloud resources.

## Parameter Confirmation

### `process` rule matrix

| `--rule` | Effect | Extra parameters |
| ---------- | -------- | ------------------ |
| `whole` | Pixelate the whole image (full mosaic) | `--block-size` |
| `blur` | Gaussian blur across the whole image | `--radius` |
| `region` | Mosaic only the given rectangle region(s) | `--regions`, `--block-size` |
| `region-blur` | Blur only the given rectangle region(s) | `--regions`, `--radius` |
| `region-block` | Occlude the given region(s) with a solid color | `--regions`, `--fill` |

### `setup-trigger` parameters

| Parameter | Required | Description |
| ----------- | ---------- | ------------- |
| `--function-name` | Yes | FunctionGraph function name |
| `--trigger-bucket` | No | OBS bucket the trigger watches (required unless `--no-trigger`) |
| `--event-type` | No | `ObjectCreated`(default)/`Put`/`Post`/`Copy`/`ObjectRemoved` OBS event |
| `--trigger-prefix` | No | Prefix filter for trigger events |
| `--trigger-suffix` | No | Suffix filter for trigger events |
| `--region` | No | Region; default `HUAWEI_REGION` or `cn-north-4` |
| `--project-id` | No | Project ID; default `HUAWEI_PROJECT_ID` |
| `--runtime` | No | Function runtime, default `Python3.9` |
| `--rule` | No | Desensitization rule embedded in the function code (default `whole`) |
| `--block-size` | No | Mosaic block size in the function code |
| `--radius` | No | Blur radius in the function code |
| `--no-trigger` | No | Create function only, skip the OBS trigger |

> **Write operations require confirmation**: `process` (uploads) and `setup-trigger` (creates
> functions/triggers) are mutating actions. Always confirm the plan with the user before running,
> except when the user explicitly passes `--yes` or asked for unattended execution.

## Output Format

`list` prints a JSON object:

```json
{
  "bucket": "example-bucket",
  "prefix": "input",
  "objects": 12,
  "images": ["input/a.png", "input/b.jpg"]
}
```

`process` prints a per-file summary:

```json
{
  "status": "done",
  "source_bucket": "example-bucket",
  "target_bucket": "example-bucket",
  "target_prefix": "desensitized/",
  "total": 2,
  "successful": 2,
  "failed": 0,
  "results": [{"key": "input/a.png", "target": "desensitized/a.png", "status": "success"}]
}
```

## Verification Method

See [Verification Method](references/verification-method.md) for full steps:
download a desensitized object and diff it against the source to confirm the rule was applied.

Quick check — after `process`, compare file hashes:

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- hcloud obs cp obs://{bucket}/{source_key} /tmp/src.png
skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- hcloud obs cp obs://{bucket}/{target_key} /tmp/dst.png
md5sum /tmp/src.png /tmp/dst.png
```

Different hashes (and an obviously pixelated/blurred image) confirm desensitization applied.

## Error Handling

| Error | Likely cause | Resolution |
| ------- | -------------- | ------------ |
| `hcloud obs` credential hint | obsutil AK/SK not configured | Configure `hcloud obs` credentials (AK/SK/endpoint) in the user's terminal |
| `command failed` on `obs cp` | Key not found / permission denied | Verify bucket/key and IAM `obs:object:Get/PutObject` permission |
| `unsupported rule` | Unknown `--rule` value | Use one of `whole, blur, region, region-blur, region-block` |
| `region ... out of image bounds` | Region coordinates exceed image size | Provide coordinates within the image dimensions |
| FSS.0403 (setup-trigger) | No `functiongraph:function:create` permission | Grant FunctionGraph create permission on the IAM policy |
| Missing Pillow | Pillow not installed | `pip install Pillow` |

## Best Practices

1. **List first, then process** — always run `list` to confirm candidates before mutating uploads.
2. **Write to a different prefix** — keep originals untouched; default result prefix `desensitized/`.
3. **Confirm before mutating** — uploading desensitized files overwrites anything at the same key.
4. **Region rules need coordinates** — obtain face/plate bounding boxes from the user or an image
   viewer before running `region*` rules.
5. **Never echo credentials** — AK/SK stay in environment variables / `hcloud` config.

## KooCLI Command Format Standard

`obsutil` (invoked as `hcloud obs …`) follows:

```bash
skill-quality-cli run --skill-name huawei-cloud-obs-image-desens -- hcloud obs <command> <cloud_url> [options...]
```

- `<command>`: `ls` (list buckets/objects), `cp` (upload/download/copy)
- `<cloud_url>`: `obs://<bucket>[/<prefix-or-key>]`
- Region is taken from the configured obsutil endpoint (typically `cn-north-4`); no `--cli-region`
  flag exists under the obs module.

## Reference Documents

- [IAM Policies](references/iam-policies.md)
- [CLI Installation Guide](references/cli-installation-guide.md)
- [Data Flow Diagram](references/dataflow-diagram.md)
- [Verification Method](references/verification-method.md)
- [Acceptance Criteria](references/acceptance-criteria.md)
