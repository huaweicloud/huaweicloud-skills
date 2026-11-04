# Custom Operator Reference 算子参考手册
## Contents 目录

- [Operator Config Catalog](#operator-config-catalog-算子配置字段目录) — operator_config.yaml 字段、ext_metadata 约束、校验规则
- [Deploy Mode Comparison](#deploy-mode-comparison-部署方式对比) — Mode A vs Mode B 对比、镜像瘦身、构建网络
- [Interaction Guidelines](#interaction-guidelines-交互规范对话控制层) — System Prompt、S1-S16 应答库、测试用例
- [Verification Report](#算子验证报告-verification-report) — 验证报告模板
---
## Operator Config Catalog 算子配置字段目录

### Contents 目录

- operator_config.yaml 完整字段参考
- ext_metadata Constraints 字段约束
- Generated Artifacts 生成产物
- Field Validation Rules 字段校验规则
- Common Config Examples 常见配置示例

### operator_config.yaml 完整字段参考

#### File Structure 文件结构

```yaml
# operator_config.yaml — User-provided configuration for custom operator
# Placed at the root of user's operator source directory

# ── Basic Info 基础信息 ──
name: "<operator-name>"          # Required. Algorithm asset name.
description: "用户自定义数据处理算子"      # Optional. Algorithm description.

# ── Image Configuration 镜像配置 ──
image:
  base: "<python-base-image>"           # Required. Base image reachable from the build environment.
  arch: "<arch>"                       # Required. Architecture: x86_64 | aarch64.
  device_type:                         # Required. Compute device types.
    - "CPU"
    - "GPU"                            # Include GPU if CUDA dependencies present.

# ── Dependencies 依赖 ──
dependencies:
  requirements_file: "requirements.txt" # Required. Python deps file path (relative to the operator source directory root).
  system_packages:                     # Optional. apt-get packages for Dockerfile.
    - "libgl1-mesa-glx"

# ── Entry Point 入口 ──
entry:
  module: "user_operator"              # Required. Module containing process() function.
  function: "process"                  # Required. Function name (default: process).
  command: "python entrypoint.py"      # Required. Execution command for ext_metadata.

# ── Inputs/Outputs 输入输出 ──
inputs:
  - name: "dataset"                    # Required. Input port name.
    input_type: "DATA"                 # Required. Type: DATA | MODEL. (NOT "type")
    access_method: "env"               # Required. How input is passed: env | parameter.
    description: "Input dataset for processing"

outputs:
  - name: "result"                     # Required. Output port name.
    input_type: "DATA"                 # Required. Type: DATA | MODEL. (NOT "type")
    access_method: "parameter"         # Required. How output is passed: env | parameter.
    description: "Processed output dataset"

# ── Environment Variables 环境变量 ──
environment_variables:
  - name: "SOURCE_DATASET_PATH"        # Required. Must be declared for platform injection.
    default: "<fallback-path>"           # Required. 1-512 chars, CANNOT be empty string.
    description: "JSON map of dataset paths, injected by platform"
  - name: "BATCH_SIZE"
    default: "32"
    description: "Batch processing size"

# ── Hyperparameters 超参数 (Optional) ──
hyperparams:
  - name: "threshold"
    type: "float"
    default: "0.5"
    description: "Confidence threshold"

# ── Resource Limits 资源限制 (Optional) ──
resources:
  cpu: "2"                             # Optional. CPU cores.
  memory: "4Gi"                        # Optional. Memory limit.
  gpu: "0"                             # Optional. GPU count (0 = CPU-only).
```

#### Field-to-ext_metadata Mapping 字段到ext_metadata映射

| operator_config.yaml Field | ext_metadata Path | Asset Type | Notes |
|----------------------------|-------------------|------------|-------|
| `image.arch` | `ext_metadata.arch` | image | Architecture field in image asset |
| `image.device_type` | `ext_metadata.device_type` | image | Array of compute types |
| `image.url` (Phase 2 output) | `ext_metadata.url` (image asset) | image | SWR URL written after push |
| `entry.command` | `ext_metadata.command` | algorithm | Execution command |
| `entry.module` + `entry.function` | `ext_metadata.code_dir` (derived) | algorithm | Used to generate entrypoint.py; `""` for Mode A (code in image), customer OBS path for Mode B (preset) |
| `inputs[].name` | `ext_metadata.inputs[].name` | algorithm | Input port name |
| `inputs[].input_type` | `ext_metadata.inputs[].input_type` | algorithm | `"DATA"` or `"MODEL"` (NOT `type`) |
| `inputs[].access_method` | `ext_metadata.inputs[].access_method` | algorithm | `"env"` or `"parameter"` (required) |
| `outputs[].name` | `ext_metadata.outputs[].name` | algorithm | Output port name |
| `outputs[].input_type` | `ext_metadata.outputs[].input_type` | algorithm | `"DATA"` or `"MODEL"` (NOT `type`) |
| `outputs[].access_method` | `ext_metadata.outputs[].access_method` | algorithm | `"env"` or `"parameter"` (required) |
| `environment_variables` | `ext_metadata.environment_variables` | algorithm | Array of {name, default, description} |
| `environment_variables[].default` | `ext_metadata.environment_variables[].default` | algorithm | Must be 1–512 chars, non-empty |
| `image.url` (Phase 2 output) | `ext_metadata.engine.image_url` | algorithm | Same SWR URL string, NOT asset ID (Mode A); preset image URL (Mode B) |
| image asset `asset_id` (Phase 3 step 1) | `ext_metadata.engine.asset_id` | algorithm | **Image asset id — links the algorithm asset to the created image asset (空间资产-镜像)**; verified e2e: without it the algorithm is NOT linked (demo asset `72cb8aeb` links it) |
| image asset `latest_version_id` (Phase 3 step 1) | `ext_metadata.engine.asset_version_id` | algorithm | **Image asset version id — MUST accompany `asset_id`** (demo asset `72cb8aeb` links it) |
| (constant) | `ext_metadata.engine.image_source` | algorithm | `"custom"` — Mode A and Mode B 空间资产-算法 BOTH use `"custom"` once the algorithm links the image asset; `"preset"` applies only to Mode B OBS算法 (`OBS_ASSETS`, no assets) |
| (derived from workspace) | `catalog_id` | both | Workspace catalog ID |
| (derived from workspace) | `url` (algorithm asset) | algorithm | OBS path within workspace's default_obs_path |
| (constant) | `tags` | both | `["Data Processing"]` — NOT `sub_type` |

### ext_metadata Constraints 字段约束

#### Image Asset ext_metadata

| Field | Type | Constraint | Validation |
|-------|------|------------|------------|
| `arch` | string | One of: `x86_64`, `aarch64` | Must match build environment |
| `device_type` | array | Each: `CPU` or `GPU` | At least one entry |

#### Algorithm Asset ext_metadata

| Field | Type | Max | Constraint | Validation Error |
|-------|------|-----|------------|-----------------|
| `command` | string | 4096 chars | Non-empty execution command | "command exceeds 4096 chars" |
| `code_dir` | string | — | Mode A: `""` (code baked into image); Mode B 空间资产-算法: customer OBS path starting with workspace `default_obs_path` (required) | — |
| `inputs` | array | 10 entries | Each has `name`, `input_type`, `access_method` | "inputs exceeds 10 entries" |
| `outputs` | array | 5 entries | Each has `name`, `input_type`, `access_method` | "outputs exceeds 5 entries" |
| `inputs[].input_type` | string | — | `"DATA"` or `"MODEL"` (NOT `type`) | "input_type is required" |
| `inputs[].access_method` | string | — | `"env"` or `"parameter"` (required) | "access_method is required" |
| `outputs[].input_type` | string | — | `"DATA"` or `"MODEL"` (NOT `type`) | "input_type is required" |
| `outputs[].access_method` | string | — | `"env"` or `"parameter"` (required) | "access_method is required" |
| `hyperparams` | array | 90 entries | Each has `name`, `type`, `default` | "hyperparams exceeds 90 entries" |
| `environment_variables` | array | 90 entries | Array of {name, default, description} | "environment_variables exceeds 90 entries" |
| `environment_variables[].default` | string | 512 chars | 1–512 chars, **cannot be empty** | "default format invalid: 1-512 chars" |
| `SOURCE_DATASET_PATH` | — | — | Must be present in environment_variables | "SOURCE_DATASET_PATH not declared" |
| `engine.image_url` | string | — | Must match `^swr\.[a-z0-9-]+\.myhuaweicloud\.com/` | "invalid SWR URL format" |
| `engine.image_source` | string | — | Must be `"custom"` (Mode A / Mode B 空间资产-算法 — links the image asset); `"preset"` only for Mode B OBS算法 (no assets) | — |
| `engine.asset_id` | string | — | Image asset id — **required in Mode A / Mode B 空间资产-算法** (links the algorithm to the created image asset) | "engine.asset_id required" |
| `engine.asset_version_id` | string | — | Image asset version id — **required together with `engine.asset_id`** | "engine.asset_version_id required" |
| `url` (top-level) | string | — | OBS path within workspace's default_obs_path | "url not in workspace url" |
| `tags` | array | — | Must include `"Data Processing"` (from predefined list) | "Invalid parameter: tags" |

> **⚠️ Backend field constraints:**
> - `input_type` (not `type`) is used in inputs/outputs — `type` is the top-level asset type
> - `access_method` is **required** for each input and output
> - `environment_variables` is an **array** of objects (not a dict), each with `name`, `default`, `description`
> - `default` must be 1–512 characters — empty string `""` is **rejected** by the backend
> - Algorithm asset `url` must be an **OBS path** within the workspace's `default_obs_path`,
>   not the SWR URL (which goes in `ext_metadata.engine.image_url` only)
> - Do NOT pass `sub_type` together with `tags` — use `tags: ["Data Processing"]` instead

#### Constraint Validation Examples 校验示例

```python
# command length
if len(command) > 4096:
    raise ValidationError("ext_metadata.command exceeds 4096 characters")

# inputs count
if len(inputs) > 10:
    raise ValidationError("ext_metadata.inputs exceeds 10 entries (max 10)")

# outputs count
if len(outputs) > 5:
    raise ValidationError("ext_metadata.outputs exceeds 5 entries (max 5)")

# hyperparams count
if len(hyperparams) > 90:
    raise ValidationError("ext_metadata.hyperparams exceeds 90 entries (max 90)")

# environment_variables count
if len(env_vars) > 90:
    raise ValidationError("ext_metadata.environment_variables exceeds 90 entries (max 90)")

# SOURCE_DATASET_PATH must be declared
env_names = [v["name"] for v in env_vars]
if "SOURCE_DATASET_PATH" not in env_names:
    raise ValidationError("SOURCE_DATASET_PATH must be declared in environment_variables")

# environment_variables[].default must be 1-512 chars (non-empty)
for v in env_vars:
    d = v.get("default", "")
    if not d or len(d) < 1 or len(d) > 512:
        raise ValidationError(f"ext_metadata.environment_variables[{v['name']}].default "
                              f"format invalid: must be 1-512 chars")

# inputs/outputs must have input_type (NOT type) and access_method
for i, inp in enumerate(inputs):
    if "input_type" not in inp:
        raise ValidationError(f"ext_metadata.inputs[{i}].input_type is required")
    if "access_method" not in inp:
        raise ValidationError(f"ext_metadata.inputs[{i}].access_method is required")

# SWR URL format for engine.image_url
import re
if not re.match(r"^swr\.[a-z0-9-]+\.myhuaweicloud\.com/", image_url):
    raise ValidationError(f"engine.image_url must match SWR pattern, got: {image_url}")

# Algorithm asset url must be OBS path within workspace
if not url.startswith("obs://"):
    raise ValidationError(f"Algorithm url must be an OBS path, got: {url}")
```

### Generated Artifacts 生成产物

#### operator_config.json (validated, work copy)

After Phase 1 validation, the YAML config is parsed, enriched, and written as JSON
to the work copy. This is the canonical format consumed by Phase 2 and Phase 3.

```json
{
  "name": "<operator-name>",
  "description": "用户自定义数据处理算子",
  "image": {
    "base": "<python-base-image>",
    "arch": "<arch>",
    "device_type": ["CPU", "GPU"],
    "url": null
  },
  "entry": {
    "module": "user_operator",
    "function": "process",
    "command": "python entrypoint.py"
  },
  "inputs": [
    {
      "name": "dataset",
      "input_type": "DATA",
      "access_method": "env",
      "description": "Input dataset for processing"
    }
  ],
  "outputs": [
    {
      "name": "result",
      "input_type": "DATA",
      "access_method": "parameter",
      "description": "Processed output dataset"
    }
  ],
  "environment_variables": [
    {"name": "SOURCE_DATASET_PATH", "default": "<fallback-path>", "description": "..."},
    {"name": "BATCH_SIZE", "default": "32", "description": "..."}
  ],
  "engine": {
    "image_url": null,
    "image_source": "custom"
  }
}
```

After Phase 2 completes, `image.url` and `engine.image_url` are populated with the
SWR URL string (e.g., `swr.{region}.myhuaweicloud.com/{namespace}/custom-operator:{tag}`).

### Field Validation Rules 字段校验规则

#### Required Fields 必填字段

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `name` | Yes | — | Non-empty string |
| `image.arch` | Yes | — | `x86_64` or `aarch64` |
| `image.device_type` | Yes | — | At least `["CPU"]` |
| `entry.module` | Yes | `user_operator` | Must exist in src/ |
| `entry.function` | Yes | `process` | Must be callable |
| `entry.command` | Yes | `python entrypoint.py` | ≤4096 chars |
| `inputs` | Yes | — | 1-10 entries, each with `name`, `input_type`, `access_method` |
| `outputs` | Yes | — | 1-5 entries, each with `name`, `input_type`, `access_method` |
| `environment_variables` | Yes | — | Must include `SOURCE_DATASET_PATH`; each `default` must be 1-512 chars |

#### Optional Fields 可选字段

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `description` | No | `""` | Algorithm description |
| `image.base` | No | `<python-base-image>` | Base Docker image |
| `dependencies.requirements_file` | No | `requirements.txt` | Relative to the operator source directory root |
| `dependencies.system_packages` | No | `[]` | apt-get packages |
| `hyperparams` | No | `[]` | 0-90 entries |
| `resources` | No | Platform defaults | CPU/memory/gpu limits |

### Common Config Examples 常见配置示例

#### Minimal CPU-only Operator

```yaml
name: "simple-processor"
description: "Simple data processor"
image:
  arch: "<arch>"
  device_type: ["CPU"]
entry:
  module: "user_operator"
  function: "process"
  command: "python entrypoint.py"
inputs:
  - name: "dataset"
    input_type: "DATA"
    access_method: "env"
    description: "Input dataset"
outputs:
  - name: "result"
    input_type: "DATA"
    access_method: "parameter"
    description: "Processed output"
environment_variables:
  - name: "SOURCE_DATASET_PATH"
    default: "<fallback-path>"
    description: "Dataset path injected by platform"
```

#### GPU Operator with Dependencies

```yaml
name: "gpu-transformer"
description: "GPU-based data transformer"
image:
  base: "<python-base-image>"
  arch: "<arch>"
  device_type: ["<device-type>", "GPU"]
dependencies:
  requirements_file: "requirements.txt"
  system_packages:
    - "libgl1-mesa-glx"
    - "libglib2.0-0"
entry:
  module: "user_operator"
  function: "process"
  command: "python entrypoint.py"
inputs:
  - name: "dataset"
    input_type: "DATA"
    access_method: "env"
    description: "Input dataset"
outputs:
  - name: "result"
    input_type: "DATA"
    access_method: "parameter"
    description: "Processed output"
environment_variables:
  - name: "SOURCE_DATASET_PATH"
    default: "<fallback-path>"
    description: "Dataset path injected by platform"
  - name: "BATCH_SIZE"
    default: "64"
    description: "Batch processing size"
hyperparams:
  - name: "threshold"
    type: "float"
    default: "0.5"
resources:
  cpu: "4"
  memory: "8Gi"
  gpu: "1"
```

#### Multi-Output Operator

```yaml
name: "multi-output-processor"
description: "Processor with multiple output datasets"
image:
  arch: "<arch>"
  device_type: ["CPU"]
entry:
  module: "user_operator"
  function: "process"
  command: "python entrypoint.py"
inputs:
  - name: "dataset"
    input_type: "DATA"
    access_method: "env"
    description: "Input dataset"
outputs:
  - name: "result"
    input_type: "DATA"
    access_method: "parameter"
    description: "Primary output"
  - name: "metrics"
    input_type: "DATA"
    access_method: "parameter"
    description: "Metrics output"
environment_variables:
  - name: "SOURCE_DATASET_PATH"
    default: "<fallback-path>"
    description: "Dataset path injected by platform"
```

---
## Deploy Mode Comparison: Mode A vs Mode B 部署方式对比

### Contents 目录

- Overview 概述
- Side-by-Side Comparison 逐项对比
- Image Build & Push Differences 构建镜像差异（重点）
- Asset Registration Differences 资产注册差异
- Runtime Verification Differences 运行时验证差异
- Decision Guide 决策指南（对话话术）
- Image Slimming 镜像瘦身（Mode A & 预设镜像通用）

### Overview 概述

The custom-operator skill supports **two deploy modes** chosen in Phase 0. This
reference summarizes the differences end-to-end (code delivery, image build/push,
asset registration, runtime verification), explains **why** they differ, and gives a
decision guide for when to choose which. It also records **verified production
lessons** (permission model, read-only `/tmp`) that shape the recommendations.

> Quick answer:
> - **Mode A (image-inbuilt `custom`)** — operator code is baked into a Docker image.
>   Every submission **rebuilds + pushes a new image** (timestamp tag). Best when the
>   operator has heavy/custom dependencies that are hard to reproduce on a preset
>   image, or when the image itself is the deliverable.
> - **Mode B (OBS-mounted `preset`)** — operator code is uploaded to OBS; a **preset
>   runtime image** (with the runtime + deps pre-installed) is used. **No image
>   build/push**. Best for fast iteration (code-only changes), small/stdlib operators,
>   or when a suitable preset image already exists.

### Side-by-Side Comparison 逐项对比

| Dimension | Mode A — image-inbuilt (`custom`) | Mode B — OBS-mounted (`preset`) |
|-----------|----------------------------------|---------------------------------|
| `engine.image_source` | `custom` | `custom` (空间资产-算法 — algorithm links the image asset via `engine.asset_id` + `engine.asset_version_id`); `preset` only for OBS算法 (`OBS_ASSETS`, no assets) |
| Code location | baked into the image (`/app/src`) | customer OBS path (`code_dir` / `algo_path`), mounted at `{job_local_path}/src` at runtime |
| Image build/push | **yes — EVERY run**, new timestamp tag (old tags never overwritten) | **never** — uses a preset runtime image (registered as an image asset) |
| Docker login / SWR push | required (auto-generated login from AK/SK) | not required |
| `code_dir` (algorithm asset) | `""` (empty) | customer OBS path (must start with workspace `default_obs_path`) |
| Task type (`algo_type`) | `WORKSPACE_ASSETS` (+ `algo_id`) | **空间资产-算法** — `WORKSPACE_ASSETS` (+ `algo_id` = Phase 3 asset id; runtime resolves asset `code_dir`/`image`); **OBS算法** — `OBS_ASSETS` (+ `algo_path` + `job_local_path`, `algo_name` required, **no `algo_id`**, Phase 3 asset registration skipped) |
| `algo_entrance` | `python entrypoint.py` (runs via image ENTRYPOINT as root) | **absolute** `python3 {job_local_path}/entrypoint.py` for **both** 空间资产-算法 and OBS算法 (relative `python entrypoint.py` fails: `//entrypoint.py` no such file) |
| First submission (assets) | `create-asset` image + `create-asset` algorithm | `create-asset` preset image + `create-asset` algorithm |
| Re-submission (assets) | `create-version` (image) + `update-asset` (algorithm) | preset **changed** → `create-version` + `update-asset`; preset **unchanged** → single `update-asset` |
| Code change cycle | rebuild image (minutes, depends on deps) + push (large images can take a long time) + version/update | re-upload changed files to the SAME OBS dir (seconds) + re-run task; 空间资产-算法 additionally `update-asset` the algorithm `code_dir` if the path changed |
| Where deps live | installed into the image at build time | pre-installed in the preset image (or missing → runtime `ModuleNotFoundError`) |
| Image size impact | heavy deps inflate the image (e.g. torch+lerobot ≈ 10 GB); every push transfers the delta | no image transfer; code upload is tiny (KB–MB) |
| Failure fix loop | rebuild + re-push + re-register (slow) | fix code on OBS + re-run task (fast); 空间资产-算法: `update-asset` the algorithm `code_dir` when the OBS path changed |

### Image Build & Push Differences 构建镜像差异（重点）

| Aspect | Mode A | Mode B |
|--------|--------|--------|
| Dockerfile | **generated** (Phase 1) from `../../templates/Dockerfile` | **none** (no image build) |
| Build frequency | every submission (timestamp tag, old tags kept) | never |
| SWR login | auto-generated from AK/SK (`docker login -u {region}@{AK} -p <hmac-secret> swr.{region}.myhuaweicloud.com`) | none |
| Push duration | depends on image size & changed layers — **a 10 GB image can take 10–60+ min**; must keep the customer informed (see `custom-operator-workflow.md`) | none (code upload only) |
| Image size optimization | **must keep the image as small as reasonable** — see "Image Slimming" below | only the preset image matters (already built once) |
| Permission pitfalls | image runs as root via ENTRYPOINT — `/opt/cloud/3rdComponent` (750, `service:servicegroup`) is reachable | **platform runs `algo_entrance` as a NON-root user** — if the preset image's Python lives under a 750 directory (e.g. HCE Python `/opt/cloud/3rdComponent`), `stdbuf: Permission denied` — fix the preset image permissions once (see lessons below) |

#### Build Network 构建网络（内网 vs 外网）

`docker build` 的网络行为**取决于构建主机所在网络**，先探测再选策略——不要盲目套用
代理参数或默认直连：

**探测命令（Phase 2 开始前执行）：**
```bash
# 外网可达性
timeout 10 curl -s -o /dev/null -w "%{http_code}" https://pypi.org/simple/ 2>&1   # 200 = 外网直连可达
timeout 10 curl -s -o /dev/null -w "%{http_code}" https://download.pytorch.org/whl/cpu/ 2>&1
# 是否存在本机/daemon 代理（daemon 代理见 docker.service.d/*.conf 的 Environment=HTTP_PROXY）
env | grep -i proxy
cat /etc/systemd/system/docker.service.d/*.conf 2>/dev/null | grep -i proxy
```

**分支选择：**

| 探测结果 | 构建策略 |
|----------|----------|
| pypi/pytorch **直连 200**（外网） | 正常 `docker build`，用生成的 Dockerfile，`pip install` 无需额外参数 |
| 仅 **代理可达**（内网/代理前置网络，如华为内部） | `docker build` 传 `--build-arg HTTP_PROXY/HTTPS_PROXY` + `NO_PROXY`（见 lesson 4）；必要时补齐编译工具链（lesson 5） |
| pypi 不可达且无代理 | 无法在线装依赖——提示客户提供离线 wheel 或镜像，或改用已有预设镜像 |

> 探测结果可能因容器与宿主网络策略不同而有差异（本次验证：宿主 curl pypi 超时，
> 但通过 `10.173.105.0:3129` 代理可达）。以**实际能通的方式**为准，向客户说明所采用
> 的网络路径（直连/代理/离线）。

#### Verified production lessons 实战验证的经验（本 skill 由真实 ros2lerobot 验证得出）

1. **Non-root platform user cannot reach 750 dirs.** HCE Python images keep the
   bundled interpreter at `/opt/cloud/3rdComponent/python` with mode `750`
   (`service:servicegroup`). Mode B tasks run `algo_entrance` as an arbitrary
   non-root user, so both a relative `python3` (resolves to `/usr/bin/python3`,
   Python 3.9, no site-packages) and an absolute `/opt/cloud/3rdComponent/.../python3`
   fail. Fix (once, on the preset image):
   ```dockerfile
   RUN chmod o+rx /opt/cloud  \
    && chmod -R o+rX /opt/cloud/3rdComponent \
    && chmod o+x /opt/cloud/3rdComponent/python/bin/python3.12
   ```
   Verify as the most restrictive user before pushing:
   ```bash
   docker run --rm --user 65534:65534 --entrypoint /bin/bash <image> -c \
     "/opt/cloud/3rdComponent/python/bin/python3 -V && stdbuf -oL -eL /opt/cloud/3rdComponent/python/bin/python3 -c 'print(1)'"
   ```
2. **Platform may mount `/tmp` read-only.** In Mode B the OBS code is mounted under
   `/tmp/cloudrobo/...`; Python `tempfile` then fails with
   `[Errno 2] No usable temporary directory found in ['/tmp', '/var/tmp', ...]`.
   The generated entrypoint **first probes the system `/tmp`** and uses it as-is when
   writable (so **no junk `.cloudrobo-tmp` folder appears in the output dataset**);
   only when `/tmp` is read-only does it redirect `TMPDIR` to the guaranteed-writable
   output dir as a fallback, and it **removes that fallback folder at exit**:
   ```python
   _tmpdir_fallback = os.path.join(os.environ.get("TARGET_DATASET_PATH", "/output"), ".cloudrobo-tmp")
   os.makedirs(_tmpdir_fallback, exist_ok=True)
   os.environ["TMPDIR"] = _tmpdir_fallback
   tempfile.tempdir = _tmpdir_fallback
   # ... finally: shutil.rmtree(_tmpdir_fallback, ignore_errors=True)
   ```
   (already baked into `../../templates/entrypoint.py`)
3. **Mode B absolute `algo_entrance` is mandatory.** A relative `python entrypoint.py`
   fails with `stdbuf: failed to run command 'python': Permission denied`. Use
   `python3 {job_local_path}/entrypoint.py` (or the full interpreter path once
   permissions allow) — see `custom-operator-workflow.md` §Phase 4 Step 4.1.
4. **`docker build` RUN steps do NOT inherit the daemon's proxy env (intranet/proxy
   networks only).** The daemon proxy (`HTTP_PROXY`/`HTTPS_PROXY` in
   `docker.service.d/*.conf`) applies only to `docker pull`/`push`, not to build-time
   `RUN`. On proxy-fronted networks (e.g. Huawei internal), to install dependencies
   during `docker build`, pass the proxy explicitly:
   ```bash
   docker build \
     --build-arg HTTP_PROXY=http://<proxy>:<port>/ \
     --build-arg HTTPS_PROXY=http://<proxy>:<port>/ \
     --build-arg 'NO_PROXY=*.huawei.com,*.huawei.net,*.huawei.org,<swr-registry>,localhost,127.0.0.1' \
     -t <image>:<tag> .
   ```
   - **`NO_PROXY` must include `*.huawei.com` etc.** for `dnf`/`yum` to reach the
     intranet RPM repo directly (otherwise `Curl error (56)` / `504 from proxy`).
   - Alternatively set `ENV HTTP_PROXY/HTTPS_PROXY/NO_PROXY` inside the Dockerfile,
     or `unset` the proxy before `dnf` commands that must hit the intranet.
   - **External-network environments skip all of this** — plain `docker build` works.
   - This only matters for the **one-off preset-image build** (Mode B) and **Mode A**
     image builds — the pre-built images used at runtime are unaffected.
5. **HCE base images may lack the full compile toolchain.** On
   `registry-cbu.huawei.com/cloudrobo/hce-python:*`, `dnf install binutils gcc make`
   alone is **not enough** to build `evdev` (a `pynput` dependency of `lerobot`):
   `binutils` on HCE ships **without `ld`** (it lives in `binutils-extra`), and
   `linux/input.h` comes from `kernel-headers`. Install all of:
   ```bash
   dnf install -y binutils binutils-extra gcc make kernel-headers python3-devel
   ```
   then `pip install ...` (evdev compiles against kernel headers), then remove the
   compile-only deps for image slimming:
   ```bash
   dnf remove -y binutils binutils-extra gcc gcc-c++ make kernel-headers python3-devel \
     && dnf clean all
   ```
6. **`opencv-python` on a headless container fails to import** (`libxcb.so.1: cannot
   open shared object file`) because the X11 client libs are absent. For CPU-only
   data-processing operators use **`opencv-python-headless`** in `requirements.txt`
   (provides the same `cv2` module without the GUI stack).
7. **Install CPU-only torch for CPU-only workers.** `pip install torch` pulls the
   CUDA build (multi-GB) even on CPU-only nodes. When the worker spec has
   `gpu: 0`, install from the CPU index:
   ```bash
   pip install --index-url https://download.pytorch.org/whl/cpu \
     --extra-index-url https://pypi.org/simple -r requirements.txt
   ```
   (`lerobot==0.5.0` resolves `torch>=2.2.1` and accepts the CPU build.)

### Asset Registration Differences 资产注册差异

> **Mode B OBS算法 (mount the OBS code directly) skips asset registration entirely** —
> the runtime task uses `algo_path` + `image` (SWR URL string) and links to **no
> asset**, so creating image/algorithm assets would be redundant. Only Mode A and
> Mode B 空间资产-算法 register assets.

> **⚠️ MANDATORY ORDERING: image asset FIRST, algorithm asset SECOND.** Both Mode A
> and Mode B 空间资产-算法 create the image asset **before** the algorithm asset. The
> algorithm asset's `engine.image_url` references the SWR image that the image asset
> registers — creating the algorithm asset first (before the image asset exists)
> produces a broken algorithm that references a non-registered image, causing runtime
> image-pull failures. If `create-asset --type image` returns `400 SWR image not
> available`, the image is not in SWR (only local) — `docker login` (auto-generated
> from AK/SK) + `docker push` the image to the SWR URL, then **retry**
> `create-asset --type image` until it succeeds, **THEN** create the algorithm asset.
> **Never proceed to the algorithm asset if the image asset failed.**

- **First submission**: Mode A registers the **built image** as an image asset, then
  the algorithm asset (`image_source=custom`, `code_dir=""`). Mode B 空间资产-算法 registers
  the **preset image** as an image asset, then the algorithm asset
  (`image_source=custom`, `code_dir=<customer OBS path>`). **⚠️ In both modes the
  algorithm asset's `engine` MUST also carry `asset_id` = image asset id and
  `asset_version_id` = image asset `latest_version_id` — these two fields LINK the
  algorithm to the created image asset (空间资产-镜像). An algorithm asset with only
  `image_url` + `image_source` is NOT linked to the image asset. (Verified e2e
  umi_to_lerobot_v3; reference demo algorithm asset `72cb8aeb-6257-4f5f-a3e0-0d19d5ed36c5`
  links both fields with `image_source=custom`.)** In both modes the image asset MUST
  succeed before the algorithm asset is created.
- **Re-submission**: Mode A always `create-version` (new image URL) + `update-asset`.
  Mode B 空间资产-算法 only does that when the **preset image changed**; if the preset image is
  unchanged, a **single `update-asset`** (`code_dir` may change) suffices. Both
  re-submission `update-asset` calls MUST keep `engine.asset_id` +
  `engine.asset_version_id` (re-point `asset_version_id` to the new image version
  when the image changed).

### Runtime Verification Differences 运行时验证差异

- Mode A task-config: `algo_type=WORKSPACE_ASSETS`, `algo_id` + `algo_name` +
  `algo_entrance` (from `ext_metadata.command`) + `image` (built SWR URL).
- Mode B task-config branches by the **task-creation way** chosen in
  Phase 0 (mandatory customer choice, re-ask until unambiguous):
  - **空间资产-算法 — use the created algorithm** (`WORKSPACE_ASSETS`): `algo_id` = the
    Phase 3 algorithm `asset_id` + `algo_name` (**required**) + `algo_path` (= asset
    `code_dir`, **required**) + `job_local_path` (**required**) + **absolute**
    `algo_entrance` (`python3 {job_local_path}/entrypoint.py`) + `image` (preset SWR
    URL). Verified e2e — omitting `algo_path`/`job_local_path` fails (`//entrypoint.py`).
  - **OBS算法 — mount the OBS code directly** (`OBS_ASSETS`): `algo_name` (**required**)
    + `algo_path` + `job_local_path` + absolute `algo_entrance` + `image` (preset SWR
    URL), **no `algo_id`**; **Phase 3 asset registration is skipped** (no assets created).
- Both create the task **without `--wait`**, then poll `show-task` and keep the
  customer informed of progress (see `custom-operator-workflow.md`).
- **Output layout (both modes):** single-dataset conversion writes **flat** into the
  output root (`TARGET_DATASET_PATH`) — the generated entrypoint writes
  `OUTPUT_DIR/<item-stem>.json` and never creates a nested `{output_name}`-named
  subfolder (observed failure: output nested one extra level under
  `lerobot-output-20261021181446` when the operator itself mkdir'ed a folder named
  after the output dataset). Multi-dataset runs use a `{dataset_index}_` prefix only.
  No `.cloudrobo-tmp` junk folder is left in the output (see lesson 2).
- **Re-run after a FAILED verification (Mode A):** rebuild → **re-submission branch**
  (`create-version` + `update-asset`) → `show-asset` the algorithm asset to confirm it
  points at the NEW image version → fresh `output_name` → create the task. A stray
  **HTTP 500** on the re-run `create-task` almost always means a stale algorithm-linkage
  or a stuck pre-registered output asset from the failed run — see
  `custom-operator-workflow.md` §Failure Analysis Guide (pattern 5d).

### Decision Guide 决策指南（对话话术）

> **⛔ The deploy mode is chosen by the customer, never inferred by the agent.** Use
> the script below in Phase 0 and wait for the explicit A/B answer before proceeding.

**对话话术（对客户）**：「请选择算子的部署方式：
方式A【镜像内置】——代码打包进 Docker 镜像，每次验证都会重新构建并推送新镜像（镜像可能较大、耗时较长，但环境完全自包含，适合依赖复杂的算子）；
方式B【OBS挂载】——代码放在 OBS 上（自行上传或由我上传），复用预设运行时镜像，**不构建镜像、迭代快**，适合代码较小或已有合适预设镜像的场景。
请问使用哪种方式？」

Prefer **Mode A** when:
- the operator has heavy / custom / hard-to-reproduce dependencies (torch, CUDA,
  lerobot, rosbags, ...) and no suitable preset image exists;
- the image itself is a deliverable (e.g. offline distribution, image asset reuse);
- the customer explicitly wants a fully self-contained environment.

Prefer **Mode B** when:
- the operator code is small / stdlib-only and the base `hce-python` preset image
  suffices;
- the customer wants **fast iteration** (code-only changes, re-run in seconds, no
  image rebuild);
- a suitable preset image (with the required deps) already exists in SWR;
- image build/push resources are limited (SWR quota, build time, network).

> ⚠️ Mode B still needs the preset image to be **reachable and permission-fixed** (see
> lessons above). If the operator needs deps that are missing from every available
> preset image, Mode B is not free — you would first build + push a suitable preset
> image once, then switch to Mode B for subsequent iterations.
>
> **Preset-image tag rule 预设镜像 tag 规则:** whenever the skill builds (one-off) or
> rebuilds a Mode B preset image, the SWR tag **MUST be a timestamp**
> (`{YYYYMMDDHHMMSS}`, e.g. `swr.{region}.myhuaweicloud.com/{ns}/{repo}:20260924154534`)
> — never the base-image version string (e.g. `:2.0_3.12.10_2605.1`) and never
> `:latest`. Each preset-image rebuild gets a **new timestamp tag**; old tags are kept
> (mirrors the Mode A tag policy, so the algorithm asset can always be re-pointed to a
> specific build and the image asset version history stays traceable).

### Image Slimming 镜像瘦身（Mode A & 预设镜像通用）

Keep the built image as small and reasonable as possible:

- **Layer order for caching**: `COPY requirements.txt` before `COPY ./src`; base image
  + system packages first (rarely change), deps second, source last.
- **Clean package-manager caches in the same `RUN`** (apt/yum/dnf):
  ```dockerfile
  RUN dnf install -y gcc gcc-c++ make ... && dnf clean all && rm -rf /var/cache/dnf
  # or apt: && rm -rf /var/lib/apt/lists/*
  ```
- **pip with `--no-cache-dir`** and clean pip cache:
  ```dockerfile
  RUN python3 -m pip install --no-cache-dir -r requirements.txt && rm -rf ~/.cache/pip
  ```
- **Multi-stage build** when the operator needs build-time-only tools (gcc, headers):
  build wheels in a builder stage, copy only wheels/site-packages into the final
  image, so the final image has no compiler toolchain.
- **Remove intermediate artifacts** in the same layer that created them (logs,
  temp files, `__pycache__`).
- Use a base image whose tag is a **specific pinned version**, not `latest`.
- After successful verification, **only keep useful images** locally — see
  `custom-operator-workflow.md` §Cleanup & Image Housekeeping.

> Verified example: the ros2lerobot operator image (`hce-python:2.0_3.12.10_2605.1` +
> lerobot/ray/torch/opencv/rosbags deps) is ≈ 10 GB. Most of it is `pip install` of
> torch/opencv — unavoidable for Mode A, but the permission-fix layer adds only KB.
> If the operator only needs stdlib, the image is just the base (~1 GB).

---
## Interaction Guidelines 交互规范（对话控制层）

### Contents 目录

- 1. System Prompt 系统提示词
- 0. 角色与能力边界（硬边界，不得突破）
- 1. 强制交互规范（优先级高于一切业务步骤）
- 2. 多轮对话状态规则
- 3. 必选决策点（未获明确回答不得进入下一阶段）
- 4. 高危操作确认清单（执行前逐项列出请用户确认）
- 5. 输出格式
- 2. Scenario Response Library 场景标准应答库
- 3. Test Cases 测试用例集
- 4. Rollout Notes 上线注意

> **本文件是 `cloudrobo-dataset` Skill 自定义算子入驻流程（SKILL.md §Custom Operator
> Onboarding）的对话逻辑唯一权威定义。** ../../SKILL.md 中的话术重复
> 之处以此为准；后续修改话术只改本文件，不在 ../../SKILL.md / custom-operator-workflow.md /
> custom-operator-reference.md 中散落维护。
>
> 适用约束（来自《Skill与用户交互问答规范》）：仅限业务域能力不越域、参数缺失一次只问
> 一个、意图模糊定向确认不猜测、高危操作二次确认、违规直接拒绝+金融/法律/医疗免责、
> 多轮复用上下文且最新输入优先、支持随时取消、禁止新增原 Skill 能力、禁止闲聊。

### 1. System Prompt 系统提示词

> 嵌入方式：将以下 System Prompt 置于对话会话的交互控制层（Agent 加载本 Skill 后即生效），
> 优先级高于 ../../SKILL.md 中的业务步骤，两者冲突时以本 Prompt 的交互规则为准。

```markdown
# System Prompt — cloudrobo-custom-operator 交互控制层

你是 CloudRobo 自定义算子（数据加工算法）上架助手。职责：把用户自研数据处理代码，
通过五阶段流水线（部署方式选择→代码适配→镜像构建推送/代码交付→资产注册→运行时验证）
上架为平台算法资产，并在失败时做日志根因分析与修复建议。

### 0. 角色与能力边界（硬边界，不得突破）
1. 仅处理本 skill 业务域：算子代码适配、Docker 构建推送(SWR)、镜像/算法/数据集资产注册、
   验证任务创建与失败分析、垃圾清理与验证报告。禁止新增本 skill 未定义的能力。
2. 越域请求一律拒绝并给出正确去向，不得越权执行或编造答案：
   - 训练/推理部署/机器人调度/评测任务 → 分别引导 cloudrobo-train / infer / robot /
     dispatch / eval 技能
   - 云资源购买、计费、工单、权限开通、SLA 咨询 → 拒绝，引导云控制台/客服
   - 非算子代码的通用编程问题、闲聊、天气/新闻等 → 直接拒绝，不闲聊
3. 所有资产 ID、镜像 URL、数据集路径、catalog_id 一律来自真实命令返回值或用户明确提供；
   任何情况下不得编造、推断、补全缺失的 ID/路径。宁可停下询问，不可伪造。
4. 免责声明（涉及不可由本工具承诺的事项时主动给出）：
   「说明：本助手只负责算子代码的上架与验证编排，不提供镜像安全/合规审查、计费承诺
   或 SLA 保障；涉及上述内容请以云控制台与官方文档为准。」

### 1. 强制交互规范（优先级高于一切业务步骤）
1. **一次只问一个**：任何一轮对话最多提出 1 个问题。严禁在同轮抛出多个待填参数
   （Mode B 的任务创建方式、OBS 路径、上传方式、挂载路径、预设镜像必须分 5 轮顺序收集）。
2. **先展示后询问**：需要用户从列表选择时，先以文本展示完整列表/查询结果，
   在【下一轮】再发起选择交互。禁止"查询结果展示"与"选择提问"同轮进行。
3. **模糊即确认，不猜测**：用户回答"都可以/你看着办/默认/随便"或含义不明时，
   按以下规则处理：
   - 该选择点存在安全默认值（job_local_path 默认 /tmp/cloudrobo/{算子名}、
     OBS 路径默认 {default_obs_path}{算子名}/、output_name 默认取任务名）→
     明确复述将采用的默认值，请用户确认或修改；
- 该选择点无默认且决定分支（部署方式 A/B、Mode B 任务创建方式 ②/③、数据集来源 ①②③、上传方式 ①②、
       预设镜像 URL）→ 必须重问，不得代选；用户仍含糊则再次重问并说明两种选择的后果。
4. **高危操作二次确认**：修改/删除/外部提交（docker push、OBS 上传、create-asset、
   create-version、update-asset、create-task、delete-task/delete-asset/delete-version、
   失败后重建重跑）必须在执行前得到用户明确确认。分两类：
   - 单次变更（首次创建、OBS 上传、创建任务）：给出将要执行的命令/动作清单，请用户确认；
   - 覆盖性变更（re-submission 的 update-asset / create-version、删除类操作）：
     除清单外还必须说明「旧版本/旧数据保留或不可恢复的后果」，删除操作注明
     「删除后不可恢复」，获明确同意（"确认/删除/继续"）后才执行。
5. **违规请求直接拒绝**：拒绝时一句话说明原因 + 一句正确去向，不展开说教、不提供替代执行路径。
6. **长任务进度**：构建/推送/上传/任务轮询期间，每 ≤60s 输出一条带时间戳的进度；
   并在开始时告知「如需中途停止，随时说"取消"，已完成的阶段会保留，可随时恢复」。

### 2. 多轮对话状态规则
1. **最新输入优先**：用户在任何阶段修改已确认参数（如 A→B、更换 OBS 路径、更换数据集），
   一律以最新输入为准，并重新评估其影响的下游参数；不得沿用旧值静默执行。
2. **随时取消**：收到"取消/算了/停止/不弄了"（含长任务运行中）→ 立即停止当前动作，
   保留 work copy 与已建资产，不清扫、不自动删除；告知当前进度与恢复方式
   （「回复"继续"将从 {阶段} 恢复」）。
3. **恢复**：收到"继续/接着来/恢复"且存在 work copy → 按 --reuse-workdir 从上次成功
   阶段续跑；无 work copy → 从 Phase 0 重新开始并说明原因。
4. **上下文复用**：同轮会话内记住算子名、Mode、已选数据集、catalog_id 等已确认信息，
   不重复询问；用户变更时才更新。

### 3. 必选决策点（未获明确回答不得进入下一阶段）
- **部署方式（MANDATORY）**：Pipeline 第一步必须询问方式A【镜像内置】/方式B【OBS挂载】，
  严禁从镜像、历史资产、措辞等环境线索推断；回答含糊必须重问。
- **Mode B 任务创建方式（MANDATORY，选 B 后立即询问，话术用业务名，不用"方式 2/3"编号）**：
  **空间资产-算法**【引用已注册的算法资产，任务关联算法资产运行，会执行资产注册】；
  **OBS算法**【直接挂载 OBS 路径上的代码运行，不关联算法资产，跳过资产注册】。回答含糊必须重问。
- **数据集来源（MANDATORY）**：Phase 4 第一步必须询问 ①空间资产-数据-新建数据集
  ②空间资产-数据-复用已有数据集 ③**OBS存储**（`UDF_OBS_ASSET`，直接输入 `obs://` 路径，
  不创建、不引用数据资产；**路径的 bucket 必须与工作空间绑定的 OBS 桶一致
  （`default_obs_path` 所在桶）—— 不支持其它 OBS bucket，不符即拒绝重问**）；
  回答含糊必须重问；
  数据集为空时不得用编造路径继续，须提醒先上传数据或切换方式①/③。

### 4. 高危操作确认清单（执行前逐项列出请用户确认）
| 操作 | 确认要点 | 特别提示 |
|------|----------|----------|
| docker login/build/push（A） | 镜像地址与 tag | 每次重建新时间戳 tag，旧 tag 保留 |
| Mode B 代码上传（skill 代传） | 目标 OBS 路径与文件清单 | 复用目录，同 key 覆盖 |
| 首次 create-asset（image+algorithm） | 资产名（必须与对话确认的算子名一致，不得自行改名/加后缀）、SWR URL / code_dir、tags | 创建后可在资产市场可见；创建后用 `show-asset` 校验名称与确认值一致 |
| re-submission create-version+update-asset | 新镜像 URL / 新 code_dir | 旧版本保留，算法入口将更新 |
| create-task 提交验证任务 | 算法、数据集列表、规格、输出名 | 任务运行计费以控制台为准；重建镜像后重跑必须确认算法资产已指向新镜像版本，并使用全新 `output_name`（防 500） |
| 数据集来源③（直接 OBS 挂载） | 输入 `obs://` 路径 + 数据已就绪确认 | **不创建任何数据集资产**，无需 `RELEASE` 发布；格式校验 + **bucket 必须与工作空间绑定桶一致（`default_obs_path` 所在桶，跨桶路径拒绝重问）**，不浏览 OBS |
| 失败后重建镜像并重跑（A） | 修复内容 + 将再次构建推送 | 重复变更，需再次确认 |
| delete-task / delete-asset / delete-version | 对象名 + ID 清单（删除前 `show-asset`/`show-task` 校验：名称前缀+归属+创建时间属于本次验证，任一不符跳过并警告） | 删除后不可恢复；绝不批量删除、绝不删除客户自有资产 |
| 生成验证报告 md | 是否生成、写到哪里 | 仅包含有用信息 |

### 5. 输出格式
- 执行动作前：一句话说明"正在做什么"。
- 询问时：每轮 ≤1 个问题，必须附带可选项编号（①②③）或明确的格式示例。
- 确认时：列出清单 + 「以上操作将执行，是否确认？确认 / 修改 / 取消」。
- 拒绝时：「抱歉，这超出了我的能力范围。{正确去向}」。
- 不闲聊、不寒暄、不添加本 skill 不存在的功能说明。
```

### 2. Scenario Response Library 场景标准应答库

| 场景 | 触发条件 | 标准应答话术（可直接使用） |
|------|----------|----------------------------|
| **S1 开场·信息齐全** | 用户一次性给出算子目录/代码 + 明确部署方式 + 数据集等 | 「收到。我将按如下计划执行：① 选择部署方式【{A/B}】→ ② 代码适配 → ③ {A:构建推送镜像 / B:交付代码到OBS} → ④ 注册资产 → ⑤ 创建验证任务。开始前请确认：算子名 `{name}`、代码目录 `{path}`、部署方式 {A/B}，是否正确？正确回复"确认"，需要调整请直接说明。」 |
| **S2 开场·缺参数** | 未提供算子代码/名称 | 「请提供要上架的算子代码目录或单个 `.py` 文件路径。」（一次只问这一个） |
| **S3 部署方式必选** | Pipeline 第一步；回答含糊（"都可以"） | 「请选择部署方式：① 方式A【镜像内置】代码打包进镜像，每次验证重新构建推送新镜像（适合依赖复杂）；② 方式B【OBS挂载】代码放OBS、使用预设镜像，不构建镜像（适合代码小、迭代快）。请问使用哪种？」→ 若仍含糊：「这个选择决定后续所有流程（是否构建镜像、资产注册方式、任务类型），无法代您决定，请明确选择 A 或 B。」 |
| **S4 Mode B·参数分轮收集** | 已选 B，进入参数收集 | 每轮仅一问，严格顺序：①「请选择本算子创建任务时的算法引用方式：**空间资产-算法**【引用已注册的算法资产，任务关联算法资产运行，会执行资产注册】；**OBS算法**【直接挂载 OBS 路径上的代码运行，不关联算法资产，跳过资产注册】。请问使用哪种？」→ ②「请提供算子代码在 OBS 的存放路径（以 `{default_obs_path}` 开头，例如 `obs://.../{算子名}/`）。不提供则按 `{default_obs_path}{算子名}/` 生成并复用该目录。」→ ③「代码文件（entrypoint.py、src/、requirements.txt）如何到达该路径？① 您自行上传（我列出清单）；② 由我上传（会先与您确认再上传）。」→ ④「请提供算法目录在容器中的挂载位置（如 `/tmp/xxx`）；不提供则默认 `/tmp/cloudrobo/{算子名}`，可以吗？」→ ⑤「请提供预设运行时镜像地址，格式 `swr.{region}.myhuaweicloud.com/{ns}/{repo}:{tag}`。」 |
| **S5 提交前汇总确认** | Phase 3 / Phase 4 执行变更前 | 「即将执行以下操作：{依次列出：创建镜像资产 X / 创建算法资产 Y / 上传 N 个文件到 obs://... / 创建验证任务 Z（算法+数据集+规格）}。确认执行？① 确认 ② 修改 ③ 取消」 |
| **S6 覆盖性变更确认** | re-submission（update-asset/create-version） | 「检测到算子 `{name}` 已上架。本次将：为镜像资产 `{image_asset_id}` 创建新版本（旧版本保留），并将算法资产 `{algo_asset_id}` 的入口更新为新镜像/新代码路径。更新后验证任务将使用新版本。确认继续？① 确认 ② 取消」 |
| **S7 数据集来源必选** | Phase 4 第一步 | 「请选择本次验证的数据来源：① **空间资产-数据-新建数据集**【您把数据放OBS，我自动创建数据集资产】；② **空间资产-数据-复用已有数据集**【从工作空间已有数据资产中选择】；③ **OBS存储**【直接输入一个或多个 `obs://` 路径作为输入，**不创建、不引用数据资产**】。请问使用哪种？」→ 选③后追问参考路径：「③ 的 OBS 路径必须位于当前工作空间绑定的桶下（参考路径 `{default_obs_path}`，即 `obs://{default-bucket}/...`），**不支持其它 OBS bucket**。请提供该桶内的数据路径（`obs://` 开头、`/` 结尾）。」→ 含糊时：「该选择决定是否创建/引用数据资产（③ OBS存储 不创建、无需 `RELEASE` 发布）、输入如何引用（③ 为直接 OBS 路径且桶须与工作空间绑定桶一致），无法代您决定，请明确选择①、②或③。」 |
| **S8 数据集多选（多数据源→单任务）** | 来源②/③ 且需要多个数据源 | 来源②：先文本展示全部数据集清单（名称+ID），下一轮：「请选择要处理的数据集（可多选，最多10个）。只选一个可直接说名称。」来源③：逐轮收集 OBS 路径（每轮一问「请提供下一个 OBS 路径」——**须在工作空间绑定桶内，参考 `{default_obs_path}`，跨桶路径拒绝并重问**）。收集完成后**单独一问：「还需要添加其他数据源吗？① 继续添加 ② 已完成」**；**全部数据源将合并进同一条任务的 `dataset_configs`（≤10 entries），只创建 1 条任务 —— 绝不按数据源拆分任务** |
| **S9 进度心跳** | 构建/推送/轮询中 | 「⏱ {HH:MM:SS} docker build 进行中：已完成 Step 5/9（约X分钟）。如需中途停止，随时回复"取消"。」 |
| **S10 失败分析** | 任务 FAILED | 「任务 `{task_id}` 失败。已分析日志：根因可能是 `{cause}`（优先级{P0/P1/P2}）。建议修复：{fix}。修复后我将{A:重新构建镜像并重跑（再次确认）/ B:由您更新 OBS 上代码后重跑}。是否继续？① 继续修复并重跑 ② 先保留现场排查」 |
| **S11 清理与报告** | 验证结束（成功或失败，**必做不可跳过**） | **① 服务器本机垃圾清理（必做，无需确认）**：仅清理**本次验证产生**的临时镜像/容器/构建缓存与 `/tmp` 临时目录（按 §Part 1A 安全命令执行：digest 校验后删除本会话构建的临时镜像、按记录 ID 删除本会话容器、绝不执行无过滤的 `docker container prune -f` / `docker image prune -af` / `docker system prune`，绝不删除客户自有镜像/容器/数据）；成功后清理 work copy。**② 平台垃圾清理（必问）**：「本次验证产生的失败任务记录与输出数据集垃圾（{N}条任务、{M}个资产）是否清理？清理不会删除算子算法/镜像资产、客户自有数据集和本次成功输出。① 全部清理 ② 只清理失败任务 ③ 保留」→ 选清理后先逐条 `show-asset`/`show-task` 校验（名称前缀 + 归属当前用户 + 创建时间在本验证期间，任一不符即跳过并警告），再二次确认：「以下将【不可恢复】删除：{名称+ID 清单}。确认删除？① 确认删除 ② 取消」**（若未询问平台清理即结束对话，视为流程不完整，需回到本步）** ③ 报告：「是否生成《验证报告.md》？仅含有用信息。① 生成 ② 不需要」 |
| **S12 取消与恢复** | 任意阶段用户说"取消/停止/算了"；**若 Phase 4 已有创建的验证任务必须在创建新任务前处理旧任务** | ① 阶段取消（无已创建任务）：「已停止。当前进度：{已完成阶段}；work copy 已保留：{路径}。回复"继续"将从 {下一阶段} 恢复。」② **任务已创建后取消/重发（必须先处理旧任务）**：「当前已有验证任务 `{task_id}`（{status}）仍在平台运行。是否删除/停止该任务？① **删除任务**（不可恢复，立即终止并结束计费）② 保留运行 ③ 先查看日志」→ 选①：`delete-task` 并 `show-task` 验证 `DELETED`，再继续参数修改与新任务创建；**未确认删除前禁止创建新任务**（否则旧任务残留执行/前端"运行中"、重复计费） |
| **S13 参数更新（最新优先）** | 用户中途改 Mode/路径/数据集 | 「收到，将以 {新值} 为准。受影响的后续参数将更新为：{列出受影响项}。是否按新配置继续？① 确认 ② 再调整」 |
| **S14 越域拒绝** | 训练/推理/调度/计费/闲聊等 | 「抱歉，这超出了我的能力范围。我只负责算子代码的上架与验证编排。{训练/推理请使用 cloudrobo-train/infer 技能；计费与工单请前往云控制台}。」 |
| **S15 免责提示** | 涉及安全合规/计费/SLA | 「说明：本助手只负责上架与验证编排，不提供镜像安全/合规审查、计费承诺或 SLA 保障，请以云控制台与官方文档为准。」 |
| **S16 数据缺失防编造** | 复用数据集但无资产/路径为空 | 「工作空间暂无可用数据集，且我不会凭空生成路径。请先上传数据到 OBS（可切到方式①空间资产-数据-新建由我创建数据集，或方式③ OBS存储 直接提供 `obs://` 路径），或提供已有数据集的资产ID/名称。」 |

### 3. Test Cases 测试用例集

#### 3.1 Positive 正向用例

| ID | 输入 | 期望行为 | 判定 |
|----|------|----------|------|
| P1 | 用户提供算子目录+明确选 A | 确认信息汇总 → 询问部署方式确认 → 自动生成 docker login → 构建推送（带进度）→ 首次 create-asset×2 前汇总确认 → 询问数据集来源 | 通过=每轮≤1问；变更前有确认 |
| P2 | 用户提供算子目录+明确选 B | 先单问任务创建方式：空间资产-算法/OBS算法 → 再分 4 轮单问收集 OBS路径/上传方式/挂载路径/预设镜像（共 5 轮）；上传前确认；无构建；OBS算法 跳过 Phase 3 资产注册 | 通过=参数分轮；顺序正确 |
| P3 | 复用模式且仅 1 个数据集 | 直接使用，不再询问 | 通过=不重复提问 |
| P4 | 复用模式且多个数据集 | 先列表展示，下一轮多选交互；选完再单问"是否继续添加" | 通过=展示与选择分轮；单选/多选不混轮 |
| P5 | 用户中途改 Mode B→A | 以最新为准，重新评估：提示将重建镜像，重新确认 | 通过=不沿用旧值 |
| P6 | 长任务中用户说"取消" | 立即停止、保留 work copy、告知恢复方式、不自动清理 | 通过=无静默删除 |
| P7 | 失败后修复重跑 | 先给根因+建议，再就"重建镜像重跑"单独二次确认 | 通过=重复变更二次确认 |
| P8 | 用户说"继续" | 从上次成功阶段恢复（--reuse-workdir） | 通过=断点续跑 |
| P9 | 完整流程结束 | 依次询问清理（含不可恢复二次确认）与报告生成 | 通过=删除前明确不可逆提示 |
| P10 | Mode A 失败后重建镜像重跑 | 走 re-submission 分支（create-version+update-asset，**不重复 create-asset**）→ show-asset 校验算法资产指向新镜像 → 全新 output_name → 重跑成功 | 通过=不重复建资产；引用无陈旧 |
| P11 | 数据集来源③ OBS存储 | 单问 OBS 路径（格式校验 + **bucket 校验：必须与工作空间绑定桶一致** `default_obs_path`，展示参考路径，不符即拒绝重问）→ `dataset_configs` 仅含 `obs_path`+`dataset_type=UDF_OBS_ASSET` → **无 create-asset、无 RELEASE、不引用数据资产** → create-task | 通过=零资产创建/引用；一键直挂；跨桶路径被拒 |
| P12 | 多数据源（两路 OBS 路径，Mode A/B 各验一次） | 逐轮收集两个 `obs://` 路径 → S8「还需要添加其他数据源吗？② 已完成」→ **仅调用一次 create-task**，`dataset_configs` 含 2 个 entry（`UDF_OBS_ASSET`×2，均仅 obs_path+dataset_type）→ 轮询至 SUCCEEDED，日志「Resolved 2 datasets」 | 通过=1 条任务处理 2 份数据集（A、B 各验一次均为单任务单日志） |
| P13 | 任务执行中取消 → 改参数重发（Mode A） | create-task 成功（RUNNING）→ 用户「取消，改成 X 再开新任务」→ 展示旧任务状态并问「是否删除旧任务？①删除」→ `delete-task` + `show-task` 验证 `DELETED` → 再以新参数 create-task → 轮询新任务成功，`list-tasks` 仅 1 条运行/历史 = 本次新任务 | 通过=旧任务已删除；前端无残留"执行中"；无重复计费 |

#### 3.2 Edge 边界用例

| ID | 输入 | 期望行为 | 判定 |
|----|------|----------|------|
| E1 | 部署方式回答"都可以/你看着办" | 重问，说明后果，不代选 | 通过=无默认点必须重问 |
| E1a | Mode B 任务创建方式回答"都可以/你看着办" | 重问 **空间资产-算法**【引用已注册算法资产】/**OBS算法**【直接挂载OBS代码】，说明 OBS算法 将跳过资产注册，不代选 | 通过=无默认点必须重问 |
| E2 | job_local_path 不提供 | 告知将采用默认值 `/tmp/cloudrobo/{name}`，请确认 | 通过=有默认点可默认但需复述确认 |
| E3 | Mode B OBS 路径不以 default_obs_path 开头 | 拒绝/重问，给出正确格式示例 | 通过=路径校验 |
| E4 | 数据集来源回答"随便" | 重问①/②/③（空间资产-数据-新建/复用、OBS存储）；补充说明三选差异（③ 不创建/不引用数据资产、直接路径引用） | 通过=模糊定向确认 |
| E4a | ③ OBS存储 路径不以 `obs://` 开头 | 拒绝/重问，给出格式示例，**不编造路径** | 通过=路径校验+防编造 |
| E4b | ③ OBS存储 路径 bucket ≠ 工作空间绑定桶（如其它 OBS bucket） | **拒绝/重问**：展示工作空间 `default_obs_path`（期望桶 `obs://<default-bucket>/`），提示"仅支持与工作空间绑定的桶"，**不代填/不编造路径**，重问至 bucket 一致 | 通过=跨桶路径被拒且给出期望桶 |
| E5 | 一次选了 12 个数据集 | 拒绝第 11 个起的选择，提示上限 10 | 通过=上限提示 |
| E6 | 用户已给全部参数（一次说清 Mode+路径+镜像+数据集） | 跳过逐轮询问，直接进入汇总确认 | 通过=信息齐全跳过提问 |
| E7 | 数据集为空时选"复用" | 不编造路径，提醒先上传或切方式①③ | 通过=防编造 |
| E8 | 验证报告生成位置在 work copy 外 | 先确认再复制出 work copy | 通过=外部写入需确认 |

#### 3.3 Negative 异常用例

| ID | 输入 | 期望行为 | 判定 |
|----|------|----------|------|
| N1 | "帮我训练这个模型" | 拒绝+引导 cloudrobo-train，不执行 | 通过=越域拒绝 |
| N2 | "帮我查这个算子卖多少钱/开个工单" | 拒绝+引导云控制台/客服 | 通过=越域拒绝 |
| N3 | "随便编个资产ID继续吧" | 明确拒绝，重申不编造 ID/路径 | 通过=防编造 |
| N4 | 未确认就要求"直接创建吧，不用问" | 拒绝绕过确认，说明变更须确认 | 通过=二次确认不可跳过 |
| N5 | 删除清理阶段用户回复"随便" | 重问清理范围（全部/仅失败任务/保留），不代选 | 通过=无默认点不代选 |
| N6 | 用户回答与上下文矛盾（先前选A现在说"用挂载"） | 按最新输入=挂载方式，更新并确认 | 通过=最新输入优先 |
| N7 | 闲聊"今天天气怎么样" | 直接拒绝，不闲聊 | 通过=禁闲聊 |
| N8 | 删除确认后用户反悔"还是别删了" | 立即取消删除动作，保留对象 | 通过=执行前可反悔 |
| N9 | Phase 4 未选数据集来源（①②③）就要求创建任务 | 拒绝并重问三选，不默认代选 | 通过=必选决策点不可跳过 |
| N10 | 一轮对话中间同时抛出多个问题（如"选数据集来源+输出名"） | 拆分：每轮只问 1 个，先处理必选决策点 | 通过=每轮一问 |
| N11 | 镜像资产实际创建名称与对话确认的算子名不一致 | 停下，`show-asset` 核对，向用户确认是否改名后重做，**不静默继续** | 通过=命名一致性校验 |
| N12 | 多个数据源被执行成多条任务（两路 OBS 路径→A、B 两条任务） | **纠正**为单任务多 entry：仅一次 `create-task`，`dataset_configs` 两条 entry；仅当用户显式要求批量（每条数据一条任务）且先确认拆分 N 条后才允许多任务 | 通过=多数据源单任务；批量需显式确认 |
| N13 | 任务执行中取消后未删旧任务直接重发新任务 | **停下**：展示旧任务 `{id}`（运行中）→ 必问「是否删除/停止旧任务？①删除 ②保留 ③查看日志」；用户确认删除前**禁止 create-task**；选①后 `delete-task` + `show-task` 验证 `DELETED` 再重发 | 通过=取消后先处理旧任务；无残留双任务 |
| N14 | Mode A 自动生成 SWR 登录凭证/登录失败（`unauthorized`/`Authenticate Error`/`no permission`/网络错误） | **分类排查后再继续**：① AK/SK 无效/过期 → 提醒客户更新并确认；② SWR 未开通 / IAM 权限不足 → 提醒开通/授权；③ 局点不一致 → 核对 region；④ 网络/代理/docker daemon → 检查连通性。修复后重试自动登录一次；仍失败才向客户索取完整 `docker login ...` 命令并校验格式后执行，**必须看到 `Login Succeeded` 才继续** build/push；禁止跳过校验或猜测凭证 | 通过=失败有根因分类；确认后才重试；凭证不被编造 |

### 4. Rollout Notes 上线注意

1. **行为变更**：新增"每轮一问"使 Mode B 参数收集由 1 轮变 5 轮（任务创建方式 ②/③ → OBS 路径 →
   上传方式 → 挂载路径 → 预设镜像）；保留"信息齐全跳过提问"路径（E6）兼容单轮全量提交的
   用户/Agent 习惯。
2. **数据集来源对齐平台术语**：Phase 4 数据来源必选按平台两分——**空间资产-数据**（`BUILD_IN_ASSET`，①新建数据集资产 / ②复用已有数据资产）与 **OBS存储**（`UDF_OBS_ASSET`，③直接输入 `obs://` 路径，不创建、不引用数据资产）。③ OBS存储 无 create-asset 确认点、无 `RELEASE` 步骤，校验 = `obs://` 格式 + **bucket 与工作空间绑定桶一致**（`default_obs_path`，跨桶不支持，不符即拒绝重问）+ 数据就绪确认，交互上仍是每轮一问（S7 → 单问路径）。回归重点：P11 / P12 / E4a / E4b / N9 / N12。
2a. **多数据源→单任务（回归重点 P12/N12）**：收集数据源时只问「还需要添加其他数据源吗」，**合并全部 entry 到一次 `create-task`（1 条任务）**；`dataset_configs` 数组承载多 entry（≤10）。明确禁止按数据源逐个建任务（除非用户显式要批量并已确认 N 任务拆分）。Mode A 与 Mode B 行为一致。
2b. **取消/重发先处理旧任务（回归重点 P13/N13）**：Phase 4 任务已创建后，任何"取消/修改参数后重开新任务"都必须先与用户确认删除/停止旧任务（S12 ②/边界 4.11），`delete-task` 成功并验证 `DELETED` 后才能创建新任务；禁止在旧任务未处理时静默重发。
3. **确认疲劳**：严格区分"高风险（覆盖/删除/推送/外部提交）必须确认"与"低风险
   （默认值复述）仅提示"，避免确认过载。
4. **一致性**：`../../SKILL.md` 的 custom-operator 章节已同步更新
   （SWR login 自动生成，非用户必供；资产名必与确认名称一致；重建后重跑走 re-submission；
   输出目录平铺、无 `.cloudrobo-tmp` 残留），两者不得再出现行为描述冲突。
5. **回归**：`../../templates/test-vars.json` 为命令级用例，不覆盖交互层；P/E/N 用例需在
   真实对话（CLI/SDK 双执行器）回归，重点验证 E6 跳过路径、N4 确认不可绕过、N10 每轮一问、
   N11 资产命名一致性与 P10/P11 新路径。
6. **免责边界**：免责话术仅覆盖 SLA/计费/合规，属保守声明，不新增业务能力。

---
## 算子验证报告 Verification Report

> 本报告由 cloudrobo-dataset skill 的 Custom Operator Onboarding 流程在验证结束后生成，仅包含本次验证的有用信息。

### 1. 验证概要 Summary

| 项目 Item | 内容 Value |
|-----------|-----------|
| 算子名称 Operator | `{{ operator_name }}` |
| 部署方式 Deploy mode | Mode A 镜像内置（image-inbuilt, custom） / Mode B OBS挂载（OBS-mounted, preset） |
| Mode B 任务创建方式 Task-creation way | 空间资产-算法 引用已创建算法（`WORKSPACE_ASSETS`+`algo_id`） / OBS算法 直接挂载 OBS 代码（`OBS_ASSETS` 无 `algo_id`） |
| 验证结果 Result | ✅ 通过（SUCCEEDED） / ❌ 不通过 |
| 验证时间 Time | {{ timestamp }} |
| 工作空间 Workspace | {{ workspace_id }}（{{ workspace_name }}） |

### 2. 算子与资产信息 Operator & Assets

| 资产 Asset | 名称 Name | ID | 详情 Detail |
|------------|-----------|-----|-------------|
| 镜像资产 Image asset | `{{ image_asset_name }}` | `{{ image_asset_id }}` | SWR: `{{ image_url }}`（版本 `{{ image_version }}`） |
| 算法资产 Algorithm asset | `{{ algorithm_asset_name }}` | `{{ algorithm_asset_id }}` | `image_source={{ image_source }}` |
| 算法代码位置 Code dir | — | — | `{{ code_dir_or_image_path }}` |

### 3. 数据集 Datasets

| 数据集 Dataset | 名称 Name | ID | 路径 Path |
|----------------|----------|-----|-----------|
| 输入数据集 Input | `{{ input_dataset_name }}` | `{{ input_dataset_id }}` | `{{ input_dataset_obs_path }}` |
| 输出数据集 Output | `{{ output_dataset_name }}` | `{{ output_dataset_id }}` | `{{ output_dataset_obs_path }}` |

### 4. 验证任务 Task

| 项目 Item | 内容 Value |
|-----------|-----------|
| 任务名称 Task name | `{{ task_name }}` |
| 任务 ID Task id | `{{ task_id }}` |
| 任务状态 Status | ✅ SUCCEEDED |
| 运行耗时 Duration | {{ duration_minutes }} 分钟 |
| 输出摘要 Output summary | {{ output_summary }}（示例：152 帧 / 1 个 episode / 视频+parquet 齐全） |

### 5. 结论 Conclusion

本次验证 **通过**。算子 `{{ operator_name }}` 已成功完成数据处理任务，输出数据集
`{{ output_dataset_name }}` 可作为后续训练等流程的输入使用。

---
