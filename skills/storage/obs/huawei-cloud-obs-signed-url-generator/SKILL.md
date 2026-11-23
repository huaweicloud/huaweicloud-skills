---
name: huawei-cloud-obs-signed-url-generator
description: |
  Generate OBS (Object Storage Service) signed temporary download URLs with
  configurable expiration, custom HTTP methods (GET/HEAD), custom headers,
  query parameters, temporary AK/SK + SecurityToken support, and image
  processing capabilities (resize, crop, rotate, compress, slim, effects,
  watermark, format conversion, image info, multi-operation composite).
  触发词: OBS签名URL, OBS签名下载链接, 生成签名URL, 带签名下载, 临时下载链接, OBS临时授权, 分享OBS对象, OBS对象分享, 图片处理URL, 缩略图URL, 图片压缩URL, 图片水印URL, 图片格式转换URL, OBS signed URL, generate signed URL, obs presigned url, temporary download url, obs share link, image processing url, obs thumbnail url, obs signed download
tags:
  - obs
  - signed-url
  - image-processing
  - python-sdk
  - temporary-access
---

# OBS Signed URL Generator

## Overview

This skill generates OBS (Object Storage Service) signed temporary download URLs using the Python SDK (`esdk-obs-python`). It enables secure third-party access to OBS objects without exposing permanent AK/SK credentials, and supports image processing operations via the `x-image-process` query parameter.

**Key capabilities:**
- Basic signed URL generation with configurable expiration (default 3600s)
- Support for GET and HEAD HTTP methods
- Custom request headers and query parameters participating in signature
- Temporary AK/SK + SecurityToken authentication
- Image processing signed URLs: resize, crop, rotate, compress, slim, effects, watermark, format conversion, image info, and multi-operation composite processing

**Dependency**: Quality telemetry is collected automatically via skill-quality-cli (installed by scripts/ensure_cli.sh if absent).

## Prerequisites

- **Python 3.8+** with `esdk-obs-python` package installed — verify with `python3 -c "from obs import ObsClient"`
- **OBS credentials** — AK/SK obtained from Huawei Cloud Console (IAM > My Credentials > Access Keys). Read from environment variables: `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, `OBS_ACCESS_KEY_ID`, `OBS_SECRET_ACCESS_KEY`, or `HUAWEICLOUD_SDK_AK`, `HUAWEICLOUD_SDK_SK`
- **OBS endpoint** — the endpoint corresponding to your bucket's region (e.g., `obs.cn-north-4.myhuaweicloud.com`)
- **Optional: SecurityToken** — for temporary credentials, set `SECURITY_TOKEN` or `HUAWEICLOUD_SDK_SECURITY_TOKEN` environment variable
- **skill-quality-cli** — ensured by bash scripts/ensure_cli.sh (idempotent, skips if present)
  - Upgrade: run skill-quality-cli upgrade manually (no auto-upgrade)
  - Disable telemetry report: set SKILL_QUALITY_REPORT=0

## Workflow

1. **Initialize OBS Client** — Create `ObsClient` instance with AK/SK (or temporary AK/SK + SecurityToken) and endpoint
2. **Prepare Parameters** — Specify bucket name, object key, HTTP method, expiration, optional headers/query params
3. **Generate Signed URL** — Call `obs_client.createSignedUrl()` to obtain the signed URL
4. **Image Processing (Optional)** — Add `x-image-process` query parameter for image operations
5. **Return URL** — The signed URL is ready for third-party temporary access

## Core Commands

> **⚠️ Mandatory: every hcloud command in this skill MUST be wrapped with skill-quality-cli run --skill-name huawei-cloud-obs-signed-url-generator --** — bare hcloud calls are strictly forbidden.

### 1. Basic Signed URL Generation (GET)

```bash
# Generate a signed download URL for an OBS object
python3 scripts/generate_signed_url.py \
  --bucket-name "my-bucket" \
  --object-key "path/to/object.txt" \
  --method GET \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com"
```

### 2. Signed URL with HEAD Method (Metadata Query)

```bash
# Generate a signed URL for HEAD request (retrieve object metadata)
python3 scripts/generate_signed_url.py \
  --bucket-name "my-bucket" \
  --object-key "path/to/object.txt" \
  --method HEAD \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com"
```

### 3. Signed URL with Temporary AK/SK + SecurityToken

```bash
# Generate a signed URL using temporary credentials
python3 scripts/generate_signed_url.py \
  --bucket-name "my-bucket" \
  --object-key "path/to/object.txt" \
  --method GET \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com" \
  --security-token "$SECURITY_TOKEN"
```

### 4. Image Resize Signed URL

```bash
# Generate a signed URL with image resize (100x200)
python3 scripts/generate_signed_url.py \
  --bucket-name "my-bucket" \
  --object-key "photo.jpg" \
  --method GET \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com" \
  --image-process "image/resize,w_100,h_200"
```

### 5. Image Compress Signed URL

```bash
# Generate a signed URL with image compression (quality 85)
python3 scripts/generate_signed_url.py \
  --bucket-name "my-bucket" \
  --object-key "photo.jpg" \
  --method GET \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com" \
  --image-process "image/quality,q_85"
```

### 6. Image Watermark Signed URL

```bash
# Generate a signed URL with text watermark
python3 scripts/generate_signed_url.py \
  --bucket-name "my-bucket" \
  --object-key "photo.jpg" \
  --method GET \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com" \
  --image-process "image/watermark,text_aGVsbG8gV29ybGQ,size_50,color_FF0000"
```

### 7. Multi-Operation Composite Processing

```bash
# Generate a signed URL with sequential image processing (resize | compress | format)
python3 scripts/generate_signed_url.py \
  --bucket-name "my-bucket" \
  --object-key "photo.jpg" \
  --method GET \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com" \
  --image-process "image/resize,w_200,h_200|image/quality,q_85|image/format,png"
```

### 8. Custom Headers and Query Parameters

```bash
# Generate a signed URL with custom headers and query parameters
python3 scripts/generate_signed_url.py \
  --bucket-name "my-bucket" \
  --object-key "path/to/object.txt" \
  --method GET \
  --expires 3600 \
  --server "obs.cn-north-4.myhuaweicloud.com" \
  --headers '{"Content-Type": "text/plain"}' \
  --query-params '{"versionId": "G00111401201878AFF"}'
```

### 9. Inline Python SDK Usage

```bash
python3 -c "
from obs import ObsClient
import os

ak = os.getenv('ACCESS_KEY_ID', '')
sk = os.getenv('SECRET_ACCESS_KEY', '')
server = 'obs.cn-north-4.myhuaweicloud.com'

obs_client = ObsClient(access_key_id=ak, secret_access_key=sk, server=server)

resp = obs_client.createSignedUrl(
    method='GET',
    bucketName='my-bucket',
    objectKey='photo.jpg',
    expires=3600,
    queryParams={'x-image-process': 'image/resize,w_100,h_200'}
)
print('Signed URL:', resp['signedUrl'])
print('Headers:', resp['actualSignedRequestHeaders'])
"
```

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| bucket-name | Yes | OBS bucket name | my-bucket |
| object-key | Yes | Object key (path in bucket) | path/to/object.txt |
| method | No | HTTP method (GET/HEAD), default GET | GET |
| expires | No | URL expiration in seconds, default 3600 | 3600 |
| server | Yes | OBS endpoint URL | obs.cn-north-4.myhuaweicloud.com |
| security-token | No | Temporary security token for temp AK/SK | (token string) |
| image-process | No | Image processing command string | image/resize,w_100,h_200 |
| headers | No | Custom headers as JSON string | {"Content-Type":"text/plain"} |
| query-params | No | Custom query params as JSON string | {"versionId":"xxx"} |

## Image Processing Commands Reference

| Operation | Command Format | Example |
|-----------|---------------|---------|
| Resize | `image/resize,w_{width},h_{height}` | `image/resize,w_100,h_200` |
| Crop | `image/crop,w_{width},h_{height},g_{position}` | `image/crop,w_100,h_100,g_se` |
| Rotate | `image/rotate,{angle}` | `image/rotate,90` |
| Compress | `image/quality,q_{quality}` or `image/quality,Q_{quality}` | `image/quality,q_85` |
| Slim | `image/slim` | `image/slim` |
| Brightness | `image/bright,b_{value}` | `image/bright,b_50` |
| Contrast | `image/contrast,d_{value}` | `image/contrast,d_50` |
| Sharpen | `image/sharpen,s_{value}` | `image/sharpen,s_50` |
| Blur | `image/blur,r_{radius},s_{sigma}` | `image/blur,r_3,s_2` |
| Text Watermark | `image/watermark,text_{base64},size_{size},color_{color}` | `image/watermark,text_aGVsbG8,size_50,color_FF0000` |
| Image Watermark | `image/watermark,image_{base64}` | `image/watermark,image_aW1hZ2U=` |
| Format Convert | `image/format,{format}` | `image/format,png` |
| Image Info | `image/info` | `image/info` |
| Composite | `{cmd1}|{cmd2}|{cmd3}` | `image/resize,w_100\|image/quality,q_85` |

## Reference Documents

- [references/iam-policies.md](references/iam-policies.md) — Least-privilege IAM policies for OBS signed URL generation
- [references/cli-installation-guide.md](references/cli-installation-guide.md) — KooCLI and skill-quality-cli installation guide
- [references/image-processing-guide.md](references/image-processing-guide.md) — Detailed image processing command reference
- [references/dataflow-diagram.md](references/dataflow-diagram.md) — Mermaid data flow diagram
- [references/verification-method.md](references/verification-method.md) — Verification method details
- [references/acceptance-criteria.md](references/acceptance-criteria.md) — Acceptance criteria
- [references/test-report.md](references/test-report.md) — AICLI test verification report (24/24 spec checks + 12/12 functional tests passed)
- [references/security-scan-report.md](references/security-scan-report.md) — Security scan report by skill-audit (0 errors, 2 false-positive warnings)

## KooCLI Command Format Standard

This skill primarily uses the Python SDK (`esdk-obs-python`) for OBS signed URL generation. KooCLI is not directly used for signed URL operations. If KooCLI is needed for OBS bucket/object queries, the standard format is:

`hcloud OBS <Operation> --cli-region=<region> [--key=value ...]`

- **Service name**: OBS (exact KooCLI Service name, uppercase)
- **Operation name**: PascalCase (e.g., ListBuckets, ShowObject)
- **Region parameter**: `--cli-region=<value>` (e.g., `--cli-region=cn-north-4`)
