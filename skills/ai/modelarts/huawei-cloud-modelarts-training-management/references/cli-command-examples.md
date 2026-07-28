# CLI Command Examples — ModelArts Training Management

> Detailed command syntax and examples for all 86 ModelArts training-related CLI APIs.
> Replace `{region}` with actual region (e.g., `cn-north-4`). `project_id` auto-resolved if omitted.

---

## 1. Training Job Management (14 APIs)

### 1.1 CreateTrainingJob — 创建训练作业

```bash
hcloud ModelArts CreateTrainingJob --cli-region={region} \
  --job_name=my-training-job \
  --job_desc="Training job description" \
  --workspace_id=0 \
  --config.1.worker_num=1 \
  --config.1.algorithm.id={algorithm_id} \
  --config.1.algorithm.version=1.0.0 \
  --config.1.flavor_id=modelarts.bm.gpu.v100 \
  --config.1.parameter.1.key=learning_rate \
  --config.1.parameter.1.value=0.001 \
  --config.1.inputs.1.name=data_url \
  --config.1.inputs.1.value=obs://my-bucket/training-data/ \
  --config.1.outputs.1.name=train_url \
  --config.1.outputs.1.value=obs://my-bucket/output/
```

> **Complex params**: For complex nested parameters, use `--cli-jsonInput=/path/to/create-job.json`:
> ```json
> {"body": {"job_name": "my-job", "config": [{"worker_num": 1, "algorithm": {"id": "xxx", "version": "1.0.0"}, "flavor_id": "modelarts.bm.gpu.v100"}]}}
> ```

### 1.2 ListTrainingJobs — 查询训练作业列表

```bash
hcloud ModelArts ListTrainingJobs --cli-region={region} \
  --limit=10 \
  --offset=0 \
  --sort_by=create_time \
  --order=desc \
  --status=running \
  --search_type=job_name \
  --search_value=my-job
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--limit` | No | Max records per page (default 10, max 1000) |
| `--offset` | No | Page offset (default 0) |
| `--sort_by` | No | Sort field: create_time, job_name |
| `--order` | No | Sort order: asc, desc |
| `--status` | No | Job status filter |
| `--search_type` | No | Search field type |
| `--search_value` | No | Search keyword |

### 1.3 ShowTrainingJobDetails — 查询训练作业详情

```bash
hcloud ModelArts ShowTrainingJobDetails --cli-region={region} \
  --training_job_id={training_job_id}
```

### 1.4 StopTrainingJob — 终止训练作业

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts StopTrainingJob --cli-region={region} \
  --training_job_id={training_job_id}
```

> Can only stop jobs in `creating`, `waiting`, or `running` state.

### 1.5 DeleteTrainingJob — 删除训练作业

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts DeleteTrainingJob --cli-region={region} \
  --training_job_id={training_job_id}
```

### 1.6 ChangeTrainingJobDescription — 更新训练作业描述

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts ChangeTrainingJobDescription --cli-region={region} \
  --training_job_id={training_job_id} \
  --job_desc="Updated description"
```

### 1.7 ShowTrainingJobLogsPreview — 查询训练作业日志(预览)

```bash
hcloud ModelArts ShowTrainingJobLogsPreview --cli-region={region} \
  --training_job_id={training_job_id} \
  --task_name=task0 \
  --start_time=2024-01-01T00:00:00Z \
  --end_time=2024-01-02T00:00:00Z \
  --limit=100
```

### 1.8 ShowObsUrlOfTrainingJobLogs — 查询训练作业日志OBS链接

```bash
hcloud ModelArts ShowObsUrlOfTrainingJobLogs --cli-region={region} \
  --training_job_id={training_job_id}
```

> Returns a temporary OBS URL valid for 5 minutes.

### 1.9 ShowTrainingJobMetrics — 查询训练作业运行指标

```bash
hcloud ModelArts ShowTrainingJobMetrics --cli-region={region} \
  --training_job_id={training_job_id} \
  --type=cpu \
  --start_time=2024-01-01T00:00:00Z \
  --end_time=2024-01-02T00:00:00Z
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--training_job_id` | Yes | Training job UUID |
| `--type` | No | Metric type: cpu, gpu, mem, gpuMem |
| `--start_time` | No | Start time (ISO 8601) |
| `--end_time` | No | End time (ISO 8601) |

### 1.10 ShowTrainingJobEngines — 获取训练作业支持的AI框架

```bash
hcloud ModelArts ShowTrainingJobEngines --cli-region={region}
```

### 1.11 ShowTrainingJobFlavors — 获取训练作业支持的规格

```bash
hcloud ModelArts ShowTrainingJobFlavors --cli-region={region} \
  --flavor_type=CPU
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--flavor_type` | No | Flavor type: CPU, GPU, ASCEND |

### 1.12 ShowTrainingQuotas — 获取训练配额

```bash
hcloud ModelArts ShowTrainingQuotas --cli-region={region}
```

### 1.13 NotifyTrainingJobInformation — 训练事件上报

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts NotifyTrainingJobInformation --cli-region={region} \
  --training_job_id={training_job_id} \
  --key=epoch \
  --value=10
```

### 1.14 ListJobs — 查询任务列表

```bash
hcloud ModelArts ListJobs --cli-region={region} \
  --limit=10 \
  --offset=0
```

---

## 2. Algorithm Management (7 APIs)

### 2.1 CreateAlgorithm — 创建算法

```bash
# ⚠️ Write operation — requires user confirmation
# Complex nested params — use --cli-jsonInput
hcloud ModelArts CreateAlgorithm --cli-region={region} \
  --cli-jsonInput=/path/to/create-algorithm.json
```

> JSON example:
> ```json
> {"body": {"name": "my-algorithm", "description": "Algorithm desc", "code_dir": "obs://my-bucket/code/", "boot_file": "obs://my-bucket/code/train.py", "engine_id": "xxx", "parameters": [{"name": "learning_rate", "value": "0.001", "description": "Learning rate"}]}}
> ```

### 2.2 ListAlgorithms — 查询算法列表

```bash
hcloud ModelArts ListAlgorithms --cli-region={region} \
  --limit=10 \
  --offset=0
```

### 2.3 ShowAlgorithmByUuid — 查询指定算法

```bash
hcloud ModelArts ShowAlgorithmByUuid --cli-region={region} \
  --algorithm_id={algorithm_id}
```

### 2.4 ChangeAlgorithm — 更新算法

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts ChangeAlgorithm --cli-region={region} \
  --algorithm_id={algorithm_id} \
  --cli-jsonInput=/path/to/update-algorithm.json
```

### 2.5 DeleteAlgorithm — 删除算法

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts DeleteAlgorithm --cli-region={region} \
  --algorithm_id={algorithm_id}
```

### 2.6 ShowSearchAlgorithms — 获取支持的超参搜索算法

```bash
hcloud ModelArts ShowSearchAlgorithms --cli-region={region}
```

### 2.7 CreateAlgorithmVersionToGallery — 发布算法资产

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts CreateAlgorithmVersionToGallery --cli-region={region} \
  --cli-jsonInput=/path/to/publish-algorithm.json
```

---

## 3. Training Job Tags (3 APIs)

### 3.1 CreateTrainJobTags — 创建训练作业标签

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts CreateTrainJobTags --cli-region={region} \
  --training_job_id={training_job_id} \
  --tags.1.key=environment \
  --tags.1.value=production
```

### 3.2 ShowTrainJobTags — 查询训练作业标签

```bash
hcloud ModelArts ShowTrainJobTags --cli-region={region} \
  --training_job_id={training_job_id}
```

### 3.3 DeleteTrainJobTags — 删除训练作业标签

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts DeleteTrainJobTags --cli-region={region} \
  --training_job_id={training_job_id} \
  --tags.1.key=environment
```

---

## 4. Training Experiments (6 APIs)

### 4.1 CreateTrainingExperiment — 创建训练实验

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts CreateTrainingExperiment --cli-region={region} \
  --cli-jsonInput=/path/to/create-experiment.json
```

> JSON example:
> ```json
> {"body": {"name": "my-experiment", "description": "Experiment desc", "workspace_id": "0"}}
> ```

### 4.2 ListTrainingExperiments — 查询训练实验列表

```bash
hcloud ModelArts ListTrainingExperiments --cli-region={region} \
  --limit=10 \
  --offset=0 \
  --sort_by=create_time \
  --order=desc
```

### 4.3 ShowTrainingExperimentDetails — 查询训练实验详情

```bash
hcloud ModelArts ShowTrainingExperimentDetails --cli-region={region} \
  --experiment_id={experiment_id}
```

### 4.4 DeleteTrainingExperiment — 删除训练实验

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts DeleteTrainingExperiment --cli-region={region} \
  --experiment_id={experiment_id}
```

### 4.5 ChangeTrainingExperiment — 更新训练实验

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts ChangeTrainingExperiment --cli-region={region} \
  --experiment_id={experiment_id} \
  --cli-jsonInput=/path/to/update-experiment.json
```

### 4.6 CheckTrainingExperiment — 校验训练实验名称

```bash
hcloud ModelArts CheckTrainingExperiment --cli-region={region} \
  --experiment_name=my-experiment
```

---

## 5. Training Job Events (7 APIs)

### 5.1 ListTrainingJobEvents — 查询训练作业事件

```bash
hcloud ModelArts ListTrainingJobEvents --cli-region={region} \
  --training_job_id={training_job_id} \
  --limit=10 \
  --offset=0
```

### 5.2 ListTrainingJobStages — 查询训练作业阶段

```bash
hcloud ModelArts ListTrainingJobStages --cli-region={region} \
  --training_job_id={training_job_id}
```

### 5.3 ListTrainingJobTasks — 查询训练作业调度实例

```bash
hcloud ModelArts ListTrainingJobTasks --cli-region={region} \
  --training_job_id={training_job_id}
```

> Returns instance IP, node IP, and scheduling info.

### 5.4 ListEvents — 查询事件列表

```bash
hcloud ModelArts ListEvents --cli-region={region} \
  --limit=10 \
  --offset=0 \
  --sort_by=create_time \
  --order=desc
```

### 5.5 ListEventCategories — 获取事件类型列表

```bash
hcloud ModelArts ListEventCategories --cli-region={region}
```

### 5.6 ListScheduledEvents — 查询计划事件列表

```bash
hcloud ModelArts ListScheduledEvents --cli-region={region} \
  --limit=10 \
  --offset=0
```

### 5.7 AcceptScheduledEvent — 计划事件授权

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts AcceptScheduledEvent --cli-region={region} \
  --event_id={event_id} \
  --action=accept
```

---

## 6. Model Import (6 APIs)

### 6.1 CreateModel — 导入/创建模型

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts CreateModel --cli-region={region} \
  --cli-jsonInput=/path/to/create-model.json
```

> JSON example:
> ```json
> {"body": {"model_name": "my-model", "model_type": "TensorFlow", "model_version": "1.0", "source_location": "obs://my-bucket/model/", "runtime": "tf2.1-python3.7"}}
> ```

### 6.2 ListModels — 查询模型列表

```bash
hcloud ModelArts ListModels --cli-region={region} \
  --limit=10 \
  --offset=0 \
  --model_name=my-model \
  --model_type=TensorFlow \
  --status=normal
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--limit` | No | Max records per page |
| `--offset` | No | Page offset |
| `--model_name` | No | Model name filter |
| `--model_type` | No | Model type filter |
| `--status` | No | Model status filter |

### 6.3 ShowModel — 查询模型详情

```bash
hcloud ModelArts ShowModel --cli-region={region} \
  --model_id={model_id}
```

### 6.4 DeleteModel — 删除模型

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts DeleteModel --cli-region={region} \
  --model_id={model_id}
```

### 6.5 ShowModelEngineAndRuntime — 查询模型支持的引擎和运行时

```bash
hcloud ModelArts ShowModelEngineAndRuntime --cli-region={region}
```

### 6.6 CreateModelArtsAgency — 创建ModelArts委托

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts CreateModelArtsAgency --cli-region={region}
```

> Creates the IAM agency required for ModelArts to access OBS and other services.

---

## 7. Auto Search (7 APIs)

### 7.1 ShowAutoSearchTrials — 查询所有自动搜索trial

```bash
hcloud ModelArts ShowAutoSearchTrials --cli-region={region} \
  --training_job_id={training_job_id} \
  --limit=10 \
  --offset=0
```

### 7.2 ShowAutoSearchPerTrial — 查询指定trial详情

```bash
hcloud ModelArts ShowAutoSearchPerTrial --cli-region={region} \
  --training_job_id={training_job_id} \
  --trial_id={trial_id}
```

### 7.3 ShowAutoSearchParamsAnalysis — 查询超参敏感度分析

```bash
hcloud ModelArts ShowAutoSearchParamsAnalysis --cli-region={region} \
  --training_job_id={training_job_id}
```

### 7.4 ShowAutoSearchParamAnalysisResultPath — 查询超参分析结果路径

```bash
hcloud ModelArts ShowAutoSearchParamAnalysisResultPath --cli-region={region} \
  --training_job_id={training_job_id}
```

### 7.5 ShowAutoSearchTrialEarlyStop — 提前终止trial

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts ShowAutoSearchTrialEarlyStop --cli-region={region} \
  --training_job_id={training_job_id} \
  --trial_id={trial_id}
```

> Only works on running trials.

### 7.6 ShowAutoSearchYamlTemplateContent — 获取yaml模板内容

```bash
hcloud ModelArts ShowAutoSearchYamlTemplateContent --cli-region={region} \
  --template_name=my-template
```

### 7.7 ShowAutoSearchYamlTemplatesInfo — 获取yaml模板信息

```bash
hcloud ModelArts ShowAutoSearchYamlTemplatesInfo --cli-region={region}
```

---

## 8. Training Image Save (2 APIs)

### 8.1 CreateSaveImageJob — 创建训练镜像保存任务

```bash
# ⚠️ Write operation — requires user confirmation
hcloud ModelArts CreateSaveImageJob --cli-region={region} \
  --cli-jsonInput=/path/to/save-image.json
```

> JSON example:
> ```json
> {"body": {"training_job_id": "xxx", "task_name": "task0", "image_name": "my-training-image", "image_type": "PRIVATE", "workspace_id": "0"}}
> ```

### 8.2 ShowSaveImageJob — 查询训练镜像保存任务

```bash
hcloud ModelArts ShowSaveImageJob --cli-region={region} \
  --job_id={job_id}
```

---

## Appendix: Common Parameter Patterns

### Indexed Parameters

```bash
# Multiple config items
--config.1.worker_num=1 \
--config.1.flavor_id=modelarts.bm.gpu.v100 \
--config.2.worker_num=2 \
--config.2.flavor_id=modelarts.bm.gpu.v100

# Multiple tags
--tags.1.key=env \
--tags.1.value=prod \
--tags.2.key=team \
--tags.2.value=ai
```

### JSON Input File

For complex parameters, create a JSON file and reference it:

```bash
hcloud ModelArts <Operation> --cli-region={region} --cli-jsonInput=/path/to/file.json
```

JSON file format:
```json
{
  "body": {
    "key1": "value1",
    "key2": ["item1", "item2"],
    "key3": {"nested_key": "nested_value"}
  }
}
```

### Status Values Reference

| Resource | Valid Status Values |
|----------|-------------------|
| Training Job | creating, waiting, running, succeeded, failed, stopped, terminating, deleted |
| Algorithm | normal, deleting |
| Model | normal, creating, failed, deleting |
| Experiment | creating, running, completed, failed |
| Save Image Job | running, succeeded, failed |
