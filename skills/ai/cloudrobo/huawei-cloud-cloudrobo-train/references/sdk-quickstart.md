# SDK Quick Start (Python)

本文档提供 Python SDK 的完整调用模板，适用于 Agent 直接调用 SDK 而非 CLI 的场景。
所有模板均基于 `cloudrobo_train.client.TrainClient` 和 `cloudrobo_core.sdk`。

## 1. 初始化 Client

```python
from cloudrobo_core.sdk import Config, HttpClient
from cloudrobo_train import TrainClient

config = Config()
http_client = HttpClient(config)
client = TrainClient(http_client)
```

- `Config()` 自动加载 `~/.cloudrobo/config.yaml` + 环境变量（`HUAWEI_CLOUD_AK/SK` 等）
- `HttpClient(config)` 自动用 AK/SK 进行 APIG HMAC-SHA256 签名
- `TrainClient(http_client)` 的 `SERVICE = "cloudrobo-service"`，自动解析 endpoint

**指定配置文件路径：**

```python
config = Config(config_path="/path/to/custom-config.yaml")
```

## 2. 创建微调任务 (MODEL_TUNING)

```python
import json

# algorithm 来自模型版本详情的 actions（见 7.1 节 Step 1-2）
# parameters 来自 algorithm 版本详情的 ext_metadata.hyperparams（见 7.1 节 Step 2）
# cluster_id 从已有任务获取或询问用户（公共池 SHARED / 专属池 DEDICATED）

# Step 1: 从 algorithm 版本详情获取 hyperparams（见 7.1 节）
hyperparams = algo_ver["ext_metadata"]["hyperparams"]

# Step 2: 构造 parameters —— 每项必须含 key+desc+value+constraint，传所有超参
parameters = json.dumps([
    {
        "key": hp["name"],
        "desc": hp.get("description", ""),
        "value": str(hp["default"]),
        "constraint": hp["constraint"]
    }
    for hp in hyperparams
], ensure_ascii=False)

req = {
    "name": "qwen2-sft-finetune",
    "description": "任务描述",
    "train_mode": "MODEL_TUNING",
    "train_method": "SFT",  # 或 FFT / LORA / QLORA / DEEPSPEED，必须大写
    "workspace_id": config.workspace_id,
    "algorithm": {
        "algorithm_asset_id": "<algo-asset-id>",      # 从模型 actions 获取
        "algorithm_version_id": "<algo-version-id>"    # 从模型 actions 获取
    },
    "input_models": [
        {
            "source_type": "PUBLIC_MODEL_ASSET",       # 具身广场; 空间资产用 CUSTOM_MODEL_ASSET
            "model_asset_id": "<base-model-asset-id>",
            "model_name": "<base-model-name>",          # 必填，从查询结果获取
            "version_id": "<base-model-version-id>",
            "version_name": "<base-model-version-name>"  # 必填，如 "v0.0.1"
        }
    ],
    "datasets": [
        {
            "source_type": "PUBLIC_DATASET_ASSET",      # 预制数据; 空间资产用 CUSTOM_DATASET_ASSET; OBS 用 OBS
            "dataset_asset_id": "<dataset-asset-id>",
            "version_id": "<dataset-version-id>",
            "dataset_name": "<dataset-name>"             # 必填，从查询结果获取
        }
    ],
    "spec": "Ascend: 1 * SNT9B2 | 24 vCPUs | 192 GiB",
    "worker_num": 1,
    "cluster_id": "<pool-id>",                          # 资源池 ID，从已有任务获取或询问用户
    "env": "[]",                                        # 环境变量 JSON 字符串，无自定义时传 "[]"
    "parameters": parameters,
    "output_models": [
        {
            "save_mode": "NEW_MODEL",                   # 或 NEW_VERSION / NOT_SAVE（不是 new: true）
            "model_name": "qwen2-sft-output",
            "version_name": "0.0.1",
            "model_type": "vla",
            "strict": False
        }
    ]
}

# 默认静默提交。--verbose 模式: 打印用户友好摘要（非原始 JSON）后直接提交 (无 yes/no)
# 摘要格式见 SKILL.md "Verbose Display Format" 部分
result = client.create_train_task(req)
print(result)
task_id = result.get("id") or result.get("task_id")
```

> **train_method 可选值**: `FFT` / `SFT` / `LORA` / `QLORA` / `DEEPSPEED`（必须大写）
> **必填字段**: `algorithm` 和 `output_models` 即使微调也必填
> **input_models 字段**: `source_type` + `model_asset_id` + `model_name` + `version_id` + `version_name` 均需传入
> **datasets 字段**: `source_type` + `dataset_asset_id` + `version_id` + `dataset_name` 均需传入
> **datasets.source_type**: `PUBLIC_DATASET_ASSET`（预制数据/具身广场）/ `CUSTOM_DATASET_ASSET`（空间资产）/ `OBS`（对象存储，仅需 source_type + url_path）
> **input_models.source_type**: `PUBLIC_MODEL_ASSET`（具身广场）/ `CUSTOM_MODEL_ASSET`（空间资产）
> **output_models.save_mode**: `NEW_MODEL` / `NEW_VERSION` / `NOT_SAVE`（不是 `new: true`）
> **parameters**: JSON 字符串，每项含 `key`+`desc`+`value`+`constraint`，传所有超参（见 7.1 节）
> **cluster_id**: 资源池 ID，公共池 SHARED / 专属池 DEDICATED，从已有任务获取或询问用户
> **env**: 环境变量 JSON 字符串，无自定义时传 `"[]"`

## 3. 创建预训练任务 (TRAIN_FROM_SCRATCH)

```python
import json

req = {
    "name": "llama3-pretrain",
    "train_mode": "TRAIN_FROM_SCRATCH",
    "workspace_id": config.workspace_id,
    "algorithm": {
        "algorithm_asset_id": "<algo-asset-id>",
        "algorithm_version_id": "<algo-version-id>",
        "algorithm_source_type": "PUBLIC_ALGORITHM_ASSET"
    },
    "datasets": [
        {
            "source_type": "CUSTOM_DATASET_ASSET",
            "dataset_asset_id": "<dataset-asset-id>",
            "version_id": "<dataset-version-id>",
            "dataset_name": "<dataset-name>"
        }
    ],
    "spec": "Ascend: 2 * Ascend-910B | 48 vCPUs | 192 GiB",
    "worker_num": 1,
    "cluster_id": "<pool-id>",
    "parameters": json.dumps([
        {"key": "epochs", "value": "10"},
        {"key": "learning_rate", "value": "0.0001"}
    ]),
    "env": "[]",
    "output_models": [
        {"save_mode": "NEW_MODEL", "model_name": "llama3-pretrain-output", "version_name": "0.0.1", "model_type": "PyTorch"}
    ],
    # log_path: 可选，用户指定日志路径时才填
    "log_path": "obs://bucket-name/train-logs/llama3-pretrain/",
    # enable_jupyter: 可选，需要 JupyterLab 访问时设为 True
    "enable_jupyter": True
}

# 静默提交; --verbose 模式: 打印用户友好摘要（非原始 JSON）后直接提交
# 摘要格式见 SKILL.md "Verbose Display Format" 部分
result = client.create_train_task(req)
print(result)
task_id = result.get("id") or result.get("task_id")
```

> **algorithm 字段来源**: 通过 `asset list-publication-assets --type algorithm` 查询，字段映射见
> [task-config-catalog.md](task-config-catalog.md) 的 "Algorithm field mapping" 章节。不要硬编码。

## 4. 创建仿真强化学习任务 (SimRL)

SimRL tasks use a different schema from regular training tasks. Key fields:
`config_mode` (SIMPLE/ADVANCED), `task_set` (from model actions), `simple_params`
(JSON string, SIMPLE mode) or `rl_config_content` (YAML string, ADVANCED mode),
`input_models` (Gallery `PUBLIC_MODEL_ASSET` or Workspace `CUSTOM_MODEL_ASSET`),
`output_models` (NEW_MODEL or NEW_VERSION), `cluster_id` (resource pool), `worker_num`,
`enable_jupyter` (DEDICATED pools only).

### Step 1: Discover model and task set

Models can come from 具身广场 (Gallery) or 空间资产 (Workspace).

```python
from cloudrobo_asset import AssetClient
from cloudrobo_core.sdk import HttpClient, Config

http = HttpClient(Config())
asset = AssetClient(http)

# Path A: Gallery models (具身广场)
models = asset.list_publication_assets(type="model", limit=100)
model_list = models.get("data", [])
source_type = "PUBLIC_MODEL_ASSET"

# Path B: Workspace models (空间资产)
# models = asset.list_assets(workspace_id=config.workspace_id, type="model", limit=100)
# model_list = models.get("data", [])
# source_type = "CUSTOM_MODEL_ASSET"

# Pick a model, then query version details to get actions (task sets)
model = model_list[0]
version_detail = http.get(
    f"{Config().endpoints.get('cloudrobo-asset-manager')}/v1/assets/{model['asset_id']}/versions/{model['latest_version_id']}")
actions = version_detail.get("actions", [])
# actions 每个元素含 action (如 LIBERO_SPATIAL) 和 algorithm 引用
task_set = actions[0].get("action", "LIBERO_SPATIAL") if actions else "LIBERO_SPATIAL"

# For ADVANCED mode: extract yaml_config from ext_metadata
ext_metadata = version_detail.get("ext_metadata", {})
yaml_config = ext_metadata.get("yaml_config", "")  # ADVANCED mode rl_config_content source
```

### Step 2: Discover resource pool

```python
from cloudrobo_resource import ResourceClient
resource = ResourceClient(http)
pools = resource.list_pools(workspace_id=config.workspace_id)
pool_list = pools.get("resources", [])
cluster_id = f'pool-{pool_list[0]["resource_id"]}' if pool_list else None
```

### Step 3: Build and submit SimRL task

#### Scenario A: Gallery model + SIMPLE config + NEW_MODEL output (SHARED pool)

```python
import json

req = {
    "name": "simrl-simple-new-model",
    "workspace_id": config.workspace_id,
    "description": "SimRL SIMPLE with Gallery model, new model output, SHARED pool",
    "config_mode": "SIMPLE",              # SIMPLE = 快速配置
    "task_set": task_set,                 # from model actions (e.g. LIBERO_SPATIAL)
    "simple_params": json.dumps([        # JSON string of [{key, value, desc}]
        {"key": "RL_ALGO", "value": "ppo", "desc": "强化学习算法"},
        {"key": "MAX_EPOCHS", "value": "100", "desc": "训练轮数"},
        {"key": "SAVE_INTERVAL", "value": "20", "desc": "保存间隔"},
        {"key": "TOTAL_NUM_TRAIN_ENVS", "value": "16", "desc": "训练环境数"},
        {"key": "EVAL_NUM_TRAIN_ENVS", "value": "500", "desc": "评估环境数"},
        {"key": "MICRO_BATCH_SIZE", "value": "64", "desc": "微批次大小"},
        {"key": "GLOBAL_BATCH_SIZE", "value": "256", "desc": "全局批次大小"},
        {"key": "ROLLOUT_EPOCH", "value": "2", "desc": "rollout轮数"},
    ]),
    "spec": "ASCEND: 1 * SNT9B2 | 24 vCPUs | 192 GiB",   # uppercase ASCEND
    "cluster_id": cluster_id,            # SHARED pool -> enable_jupyter must be false
    "worker_num": 1,
    "enable_jupyter": False,             # SHARED pool: must be false; DEDICATED pool: optional true
    "input_models": [{
        "source_type": "PUBLIC_MODEL_ASSET",
        "model_asset_id": model["asset_id"],
        "model_name": model["name"],
        "version_id": model["latest_version_id"],
        "version_name": version_detail.get("version", "v0.0.1"),
    }],
    "output_models": [{
        "save_mode": "NEW_MODEL",
        "model_name": "my-simrl-output",
        "version_name": "0.0.1",
        "model_type": "vla",
        "model_asset_id": None,           # null for new model
        "version_id": None,               # null for new model
        "strict": False,
        "skills": [],
    }],
}

# 静默提交; --verbose 模式: 打印用户友好摘要后直接提交
result = client.create_sim_rl_task(req)
print(result)
task_id = result.get("id") or result.get("task_id")
```

#### Scenario B: Workspace model + ADVANCED config + NEW_VERSION output (DEDICATED pool)

```python
# ADVANCED mode: use rl_config_content (YAML string from ext_metadata.yaml_config)
# input_models: CUSTOM_MODEL_ASSET for workspace models
# output_models: NEW_VERSION to add a version to an existing model

req = {
    "name": "simrl-advanced-new-version",
    "workspace_id": config.workspace_id,
    "description": "SimRL ADVANCED with workspace model, new version output, DEDICATED pool",
    "config_mode": "ADVANCED",             # ADVANCED = 用户自定义YAML
    "task_set": task_set,                 # still required in ADVANCED mode
    "rl_config_content": yaml_config,     # YAML string from ext_metadata.yaml_config
    "spec": "ASCEND: 4 * SNT9B2 | 96 vCPUs | 768 GiB",
    "cluster_id": cluster_id,             # DEDICATED pool
    "worker_num": 1,
    "enable_jupyter": True,               # DEDICATED pool: JupyterLab supported
    "input_models": [{
        "source_type": "CUSTOM_MODEL_ASSET",   # workspace model
        "model_asset_id": model["asset_id"],
        "model_name": model["name"],
        "version_id": model["latest_version_id"],
        "version_name": version_detail.get("version", "v0.0.1"),
    }],
    "output_models": [{
        "save_mode": "NEW_VERSION",
        "model_name": "existing-model-name",
        "version_name": "new-version-name",
        "model_type": "vla",
        "model_asset_id": "<existing-model-asset-id>",  # existing model's asset ID
        "version_id": "",                               # empty string "" (not null)
        "strict": False,
        "skills": [                                       # skills array with name + prompt
            {"name": "pick-place", "prompt": "Pick up the object and place it on the target."},
        ],
    }],
}

result = client.create_sim_rl_task(req)
print(result)
task_id = result.get("id") or result.get("task_id")
```

> **SimRL vs Train task differences**:
> - No `algorithm`/`train_mode`/`train_method`/`datasets`/`parameters`/`env`/`log_path` fields
> - Uses `config_mode` + `task_set` + `simple_params` (SIMPLE) or `rl_config_content` (ADVANCED YAML)
> - `input_models` supports `PUBLIC_MODEL_ASSET` (Gallery) and `CUSTOM_MODEL_ASSET` (Workspace)
> - `output_models`: NEW_MODEL (`model_asset_id`/`version_id` = `null`) or
>   NEW_VERSION (`model_asset_id` = existing ID, `version_id` = empty string `""`)
> - `spec` uses uppercase `ASCEND:` (not mixed-case `Ascend:`)
> - `enable_jupyter`: DEDICATED pools only; SHARED/public pools must set `false`
> - `cluster_id` is required (resource pool)
> - SimRL 没有 `resume`，其他 CRUD/监控接口与普通训练任务一一对应

## 5. 草稿工作流

```python
draft_req = {
    "name": "my-draft-task",
    "workspace_id": config.workspace_id
}

draft = client.save_draft(draft_req)
draft_id = draft.get("id") or draft.get("task_id")
print(f"Draft saved: {draft_id}, status: {draft.get('status')}")

full_req = {
    "name": "my-draft-task",
    "train_mode": "MODEL_TUNING",
    "train_method": "LORA",
    "workspace_id": config.workspace_id,
    "input_models": [{"model_asset_id": "<id>", "version_id": "<vid>"}],
    "datasets": [{"source_type": "CUSTOM_DATASET_ASSET", "dataset_asset_id": "<did>"}],
    "spec": "Ascend: 1 * Ascend-910B | 24 vCPUs | 96 GiB"
}

result = client.restart_train_task(draft_id, full_req)
print(result)
```

> `restart_train_task(task_id, req)` 语义为"编辑并重新提交"，接受完整 TrainTaskDto body。

## 6. 轮询与监控

```python
import time

terminal_states = {
    "FINISHED", "FAILED", "RUN_FAILED", "CREATE_FAILED",
    "STOPPED", "STOP_FAILED", "DELETE_FAILED",
    "NOT_EXIST", "ABNORMAL"
}

while True:
    task = client.show_train_task(task_id)
    status = task.get("status")
    print(f"Task {task_id}: {status}")
    if status in terminal_states:
        break
    time.sleep(30)

stages = client.list_train_stages(task_id)
print("Stages:", stages)

import time
end_ts = int(time.time())
start_ts = end_ts - 3600
usage = client.show_resource_usage(task_id, "gpu_util", start_ts, end_ts)
print("Resource usage:", usage)

start_ms = start_ts * 1000
end_ms = end_ts * 1000
events = client.list_events(task_id, start_ms, end_ms, level="Error")
print("Error events:", events)
```

> **时间戳单位差异**: `get-resource-usage` 用**秒**（10 位），`get-events` 用**毫秒**（13 位）。

## 7. 跨包查询 algorithm / dataset

创建任务前通常需要查询 algorithm 和 dataset，这涉及 `cloudrobo-asset` 包：

```python
from cloudrobo_core.sdk import Config, HttpClient
from cloudrobo_asset import AssetClient

config = Config()
http_client = HttpClient(config)
asset_client = AssetClient(http_client)

algorithms = asset_client.list_publication_assets(type="algorithm", limit=20)
for algo in algorithms.get("data", algorithms.get("items", [])):
    print(algo.get("name"), algo.get("asset_id"), algo.get("version_id"))

datasets = asset_client.list_assets(type="dataset", limit=20)
for ds in datasets.get("data", datasets.get("items", [])):
    print(ds.get("name"), ds.get("asset_id"), ds.get("version_id"))
```

> 当 CLI `cloudrobo asset list-assets` 失败时，直接用 SDK HttpClient 调用通常可行
> （见 [Algorithm Asset Access](#) 记忆）。workspace 级别 algorithm 通过 publication
> model actions 发现。

## 7.1 查询 asset 版本详情（获取 hyperparams / algorithm 映射）

微调任务的 algorithm 来自模型版本详情的 `actions` 列表；algorithm 的默认超参来自其版本
详情的 `ext_metadata.hyperparams`。两步查询：

```python
from cloudrobo_core.sdk import Config, HttpClient
import json

config = Config()
http_client = HttpClient(config)
endpoint = config.endpoints.get("cloudrobo-asset-manager")

# Step 1: 查询模型版本详情，从 actions 中定位微调方式对应的 algorithm
model_asset_id = "<base-model-asset-id>"
model_version_id = "<base-model-version-id>"
url = f"{endpoint}/v1/assets/{model_asset_id}/versions/{model_version_id}"
model_ver = http_client.get(url)

# actions 包含 FFT / LORA / ONLINE_DEPLOYMENT，每个含 algorithm.asset_id + version_id
actions = model_ver.get("actions", [])
train_method = "FFT"  # 或 "LORA"，与用户选择的微调方式一致
algo_ref = None
for act in actions:
    if act.get("action") == train_method and act.get("status") == "ENABLE":
        algo_ref = act.get("algorithm", {})
        break

if not algo_ref:
    raise ValueError(f"模型不支持 {train_method} 微调方式")

algo_asset_id = algo_ref["asset_id"]
algo_version_id = algo_ref["version_id"]

# Step 2: 查询 algorithm 版本详情，获取 ext_metadata.hyperparams
url = f"{endpoint}/v1/assets/{algo_asset_id}/versions/{algo_version_id}"
algo_ver = http_client.get(url)
ext = algo_ver.get("ext_metadata", {})

# hyperparams: [{name, default, constraint:{type,editable,required,sensitive,valid_range}, description}]
hyperparams = ext.get("hyperparams", [])
print("=== 默认超参 ===")
for hp in hyperparams:
    print(f"  {hp['name']} = {hp['default']}  ({hp.get('description', '')})")

# 构造 parameters —— 每项必须含 key+desc+value+constraint，传所有超参（含非 required）
parameters = json.dumps([
    {
        "key": hp["name"],
        "desc": hp.get("description", ""),
        "value": str(hp["default"]),           # 用户可修改此值
        "constraint": hp["constraint"]          # 原样复制完整 constraint 对象
    }
    for hp in hyperparams
], ensure_ascii=False)

# algorithm 字段只需 asset_id + version_id（不需要 hidden_main_info）
algorithm = {
    "algorithm_asset_id": algo_asset_id,
    "algorithm_version_id": algo_version_id
}
```

> **API**: `GET /v1/assets/{asset_id}/versions/{version_id}` (cloudrobo-asset-manager)
> **模型版本 actions 结构**: `[{action: "FFT"|"LORA"|"ONLINE_DEPLOYMENT", algorithm: {asset_id, version_id}, status: "ENABLE"|"DISABLE", inherited: bool}]`
> **algorithm ext_metadata 结构**: 含 `engine.image_url`, `command`, `inputs`, `outputs`, `resource`, `hyperparams`, `train_config.support_resume`
> **hyperparams 结构**: `[{name, default, constraint:{type, editable, required, sensitive, valid_type, valid_range}, description}]`
> 预训练任务直接查询 algorithm 资产版本详情，跳过 Step 1。

## 8. 提交行为

默认静默提交，无 confirm。`--verbose/-v` 模式下打印**用户友好摘要**（分组列表/表格，非原始 JSON）
后直接调用 `create_train_task(req)` / `create_sim_rl_task(req)`。摘要格式见 SKILL.md
"Verbose Display Format" 部分。不实现 yes/no 包装函数。

```python
# 默认静默提交
result = client.create_train_task(req)
# --verbose 模式: 打印友好摘要后直接提交 (无 yes/no)
# 摘要模板见 SKILL.md "Verbose Display Format"
# result = client.create_train_task(req)
```

## 9. 常用方法速查

| 操作 | SDK 方法 | 说明 |
|------|----------|------|
| 创建训练任务 | `client.create_train_task(req)` | POST /v1/training/train-tasks |
| 创建 SimRL 任务 | `client.create_sim_rl_task(req)` | POST /v1/training/rl-tasks/simulation |
| 保存草稿 | `client.save_draft(req)` | POST /v1/training/train-tasks/draft |
| 重新提交 | `client.restart_train_task(task_id, req)` | POST /v1/training/train-tasks/{id}/restart |
| 查询任务 | `client.show_train_task(task_id)` | GET /v1/training/train-tasks/{id} |
| 列出任务 | `client.list_train_tasks(**params)` | GET /v1/training/train-tasks |
| 停止任务 | `client.stop_train_task(task_id)` | POST /v1/training/train-tasks/{id}/stop |
| 训练阶段 | `client.list_train_stages(task_id)` | GET /v1/training/train-tasks/{id}/stages |
| 资源使用 | `client.show_resource_usage(task_id, metric, start, end)` | 秒级时间戳 |
| 训练事件 | `client.list_events(task_id, start_time, end_time)` | 毫秒级时间戳 |
| 日志内容 | `client.get_log_content(task_id, **params)` | GET /v1/training/train-tasks/{id}/observability/content |
| 签名 URL | `client.get_log_signed_url(task_id, file_source, file_name)` | 下载日志文件 |
| 任务统计 | `client.count_train_tasks_by_status(workspace_id)` | GET /v1/training/train-tasks/stats |
| 批量删除 | `client.batch_delete_train_tasks(execution_ids)` | body: `{"execution_ids": [...]}` |
| checkpoint 列表 | `client.list_train_checkpoints(task_id, **params)` | GET /v1/training/train-tasks/{id}/checkpoints |
| 注册 checkpoint | `client.register_train_checkpoint(task_id, req)` | POST /v1/training/train-tasks/{id}/checkpoints/register |

> 完整方法列表见 [task-config-catalog.md](task-config-catalog.md) 的 "Three-layer coverage matrix"。
