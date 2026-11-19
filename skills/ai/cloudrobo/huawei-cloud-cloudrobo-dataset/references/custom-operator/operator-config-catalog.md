> Part of the custom-operator guide. Index: [custom-operator-reference.md](custom-operator-reference.md)
> Siblings: [deploy-mode-comparison.md](deploy-mode-comparison.md) · [interaction-guidelines.md](interaction-guidelines.md) · [verification-report.md](verification-report.md)

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
| `entry.module` + `entry.function` | `ext_metadata.code_dir` (derived) | algorithm | Used to generate entrypoint.py; `""` for 把代码打进镜像 (code in image), customer OBS path for 代码放 OBS、运行时挂载（preset） |
| `inputs[].name` | `ext_metadata.inputs[].name` | algorithm | Input port name |
| `inputs[].input_type` | `ext_metadata.inputs[].input_type` | algorithm | `"DATA"` or `"MODEL"` (NOT `type`) |
| `inputs[].access_method` | `ext_metadata.inputs[].access_method` | algorithm | `"env"` or `"parameter"` (required) |
| `outputs[].name` | `ext_metadata.outputs[].name` | algorithm | Output port name |
| `outputs[].input_type` | `ext_metadata.outputs[].input_type` | algorithm | `"DATA"` or `"MODEL"` (NOT `type`) |
| `outputs[].access_method` | `ext_metadata.outputs[].access_method` | algorithm | `"env"` or `"parameter"` (required) |
| `environment_variables` | `ext_metadata.environment_variables` | algorithm | Array of {name, default, description} |
| `environment_variables[].default` | `ext_metadata.environment_variables[].default` | algorithm | Must be 1–512 chars, non-empty |
| `image.url` (Phase 2 output) | `ext_metadata.engine.image_url` | algorithm | Same SWR URL string, NOT asset ID (把代码打进镜像); preset image URL (代码放 OBS、运行时挂载) |
| image asset `asset_id` (Phase 3 step 1) | `ext_metadata.engine.asset_id` | algorithm | **Image asset id — links the algorithm asset to the created image asset (空间资产-镜像)**; without it the algorithm is NOT linked |
| image asset `latest_version_id` (Phase 3 step 1) | `ext_metadata.engine.asset_version_id` | algorithm | **Image asset version id — MUST accompany `asset_id`** |
| (constant) | `ext_metadata.engine.image_source` | algorithm | `"custom"` — 把代码打进镜像 and 代码放 OBS 并注册算法资产 BOTH use `"custom"` once the algorithm links the image asset; `"preset"` applies only to 代码放 OBS 并直接挂载 (`OBS_ASSETS`, no assets) |
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
| `code_dir` | string | — | 把代码打进镜像路线：`""` (code baked into image); 代码放 OBS 并注册算法资产: customer OBS path starting with workspace `default_obs_path` (required) | — |
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
| `engine.image_source` | string | — | Must be `"custom"` (把代码打进镜像 / 代码放 OBS 并注册算法资产 — links the image asset); `"preset"` only for 代码放 OBS 并直接挂载 (no assets) | — |
| `engine.asset_id` | string | — | Image asset id — **required in 把代码打进镜像 / 代码放 OBS 并注册算法资产** (links the algorithm to the created image asset) | "engine.asset_id required" |
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