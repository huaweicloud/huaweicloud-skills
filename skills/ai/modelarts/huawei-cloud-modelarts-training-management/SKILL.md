---
name: "huawei-cloud-modelarts-training-management"
description: "Manage Huawei Cloud ModelArts training jobs and related resources through full lifecycle operations via hcloud CLI. Covers 52 API interfaces across 8 functional domains: training job management, algorithm management, training job tags, training experiments, training job events, model import, auto search (hyperparameter tuning), and training image save. All write operations require user confirmation before execution. Triggers include: \"ModelArts training\", \"训练作业\", \"模型训练\", \"创建训练作业\", \"查询训练作业\", \"停止训练作业\", \"删除训练作业\", \"算法管理\", \"超参配置\", \"training job\", \"training management\", \"create training\", \"ModelArts 训练\", \"训练实验\", \"自动搜索\", \"超参调优\"."
---

# Huawei Cloud ModelArts Training Management

> Full lifecycle management for ModelArts training jobs and related resources via hcloud CLI — 52 API interfaces across 8 functional domains.

---

## Overview

This skill enables users to manage Huawei Cloud ModelArts training jobs and related resources through the `hcloud` CLI. It covers the complete training lifecycle including training job CRUD, algorithm management, training experiments, auto search (hyperparameter tuning), model import, and training image save.

### Architecture

```
User Request → Agent → hcloud ModelArts <Operation> --cli-region={region} [--params] → Huawei Cloud ModelArts API
```

### Applicable Scenarios

- **Training Job Management**: Create, list, show, stop, delete training jobs; query logs, metrics, engines, flavors, quotas
- **Algorithm Management**: Create, list, show, update, delete training algorithms; publish to gallery
- **Training Job Tags**: Create, show, delete tags for training jobs
- **Training Experiments**: Create, list, show, update, delete, check training experiments
- **Training Job Events**: Query job events, stages, tasks; list system events and scheduled events
- **Model Import**: Import, list, show, delete AI models; create ModelArts agency
- **Auto Search**: Query hyperparameter search trials, parameters analysis, yaml templates
- **Training Image Save**: Create and query training job image save tasks

---

## Prerequisites

1. **hcloud CLI** installed and authenticated — Reference: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html
2. **Huawei Cloud AK/SK** configured via hcloud or environment variables
3. **ModelArts service** enabled in the target region
4. **IAM permissions** — See [references/iam-policies.md](references/iam-policies.md)

---

## Workflow

### Step 1: Identify the Operation

Determine which training operation the user needs based on their request:

| User Intent | Operation Category |
|-------------|-------------------|
| Create/list/show/stop/delete training jobs | Training Job Management |
| Create/list/show/update/delete algorithms | Algorithm Management |
| Create/show/delete training job tags | Training Job Tags |
| Create/list/show/update/delete experiments | Training Experiments |
| Query job events, stages, tasks | Training Job Events |
| Import/list/show/delete models | Model Import |
| Query auto search trials, params analysis | Auto Search |
| Save training job image | Training Image Save |

### Step 2: Execute CLI Command

```bash
hcloud ModelArts <Operation> --cli-region={region} [--key=value ...]
```

> `{region}` must be replaced with the actual region, e.g., `cn-north-4`. Do NOT hardcode the region.

### Step 3: Handle Write Operations

For all write operations (Create/Update/Delete/Stop/Change/Patch/Notify/Accept/Batch), **prompt the user for confirmation before execution**.

---

## KooCLI Command Format Standard

```bash
hcloud ModelArts <Operation> --cli-region={region} [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Fixed: `ModelArts` | `ModelArts` |
| Operation name | PascalCase | `ListTrainingJobs`, `CreateTrainingJob` |
| Region parameter | `--cli-region={region}` | `--cli-region=cn-north-4` |
| Simple parameter | `--key=value` | `--training_job_id=xxx` |
| Indexed parameter | `--key.1=value1` | `--config.1.name=cfg1` |
| project_id | Auto-resolved if omitted | Uses configured project ID |

> **Note**: `--project_id` is auto-resolved from authentication credentials if omitted. Include it explicitly only when targeting a specific project.

> **Complex parameters**: For complex nested parameters (e.g., `config`, `spec`), use `--cli-jsonInput=/path/to/file.json`. The JSON file must wrap body in `{"body": {...}}` envelope.

---

## Core Commands

All 52 CLI command examples across 8 functional domains are documented in a separate reference file.

> **📖 For detailed command syntax, parameters, and examples, read [references/cli-command-examples.md](references/cli-command-examples.md)**

### Quick Index

| # | Domain | APIs | Key Operations |
|---|--------|------|----------------|
| 1 | Training Job Management | 14 | CreateTrainingJob, ListTrainingJobs, ShowTrainingJobDetails, StopTrainingJob, DeleteTrainingJob, ShowTrainingJobLogs/Metrics/Engines/Flavors/Quotas |
| 2 | Algorithm Management | 7 | CreateAlgorithm, ListAlgorithms, ShowAlgorithmByUuid, ChangeAlgorithm, DeleteAlgorithm, ShowSearchAlgorithms, CreateAlgorithmVersionToGallery |
| 3 | Training Job Tags | 3 | CreateTrainJobTags, ShowTrainJobTags, DeleteTrainJobTags |
| 4 | Training Experiments | 6 | CreateTrainingExperiment, List/Show/Delete/Change/Check experiments |
| 5 | Training Job Events | 7 | ListTrainingJobEvents/Stages/Tasks, ListEvents/Categories/ScheduledEvents, AcceptScheduledEvent |
| 6 | Model Import | 6 | CreateModel, ListModels, ShowModel, DeleteModel, ShowModelEngineAndRuntime, CreateModelArtsAgency |
| 7 | Auto Search | 7 | ShowAutoSearchTrials/PerTrial/ParamsAnalysis/YamlTemplates, ShowAutoSearchTrialEarlyStop |
| 8 | Training Image Save | 2 | CreateSaveImageJob, ShowSaveImageJob |

> When executing any command, always refer to the reference file for exact parameter names, required/optional flags, and usage patterns.

---

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `{region}` | Yes | Huawei Cloud region | `cn-north-4`, `cn-east-3` |
| `{training_job_id}` | Job ops | Training job UUID | `xxx-xxx-xxx` |
| `{algorithm_id}` | Algorithm ops | Algorithm UUID | `xxx-xxx-xxx` |
| `{experiment_id}` | Experiment ops | Training experiment UUID | `xxx-xxx-xxx` |
| `{model_id}` | Model ops | Model UUID | `xxx-xxx-xxx` |
| `{job_id}` | SaveImage ops | Save image job UUID | `xxx-xxx-xxx` |
| `{project_id}` | No (auto) | Project ID, auto-resolved if omitted | Omit for default |
| `{workspace_id}` | No | Workspace ID | Omit for default workspace |

---

## SDK Fallback

If a CLI operation fails due to a CLI bug, fall back to SDK:

```python
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkmodelarts.v2.modelarts_client import ModelArtsClient
from huaweicloudsdkmodelarts.v2.region.modelarts_region import ModelArtsRegion

credentials = BasicCredentials(ak="{AK}", sk="{SK}", project_id="{project_id}")
client = ModelArtsClient.new_builder() \
    .with_credentials(credentials) \
    .with_region(ModelArtsRegion.value_of("{region}")) \
    .build()
```

---

## Reference Documents

| Document | Description |
|----------|-------------|
| [references/cli-command-examples.md](references/cli-command-examples.md) | Detailed CLI command syntax and examples for all 52 APIs |
| [references/iam-policies.md](references/iam-policies.md) | Least-privilege IAM policies |
| [references/verification-method.md](references/verification-method.md) | Verification and testing methods |
| [references/dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow diagram |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria checklist |
| [references/api-paths.md](references/api-paths.md) | REST API paths from SDK source |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation and authentication guide |
| [references/known-issues.md](references/known-issues.md) | Known issues and workarounds |

---

## Known Issues Summary

- **Complex nested params**: Use `--cli-jsonInput` with JSON file for CreateTrainingJob, CreateAlgorithm, CreateModel, etc.
- **`--cli-jsonInput` syntax**: Use file path directly (no `@` prefix), JSON must be wrapped in `{"body": {...}}`
- **Training job logs**: `ShowObsUrlOfTrainingJobLogs` returns a temporary OBS URL (valid for 5 minutes)
- **StopTrainingJob**: Can only stop jobs in `creating`, `waiting`, or `running` state
- **Auto search**: Trial early stop only works on running trials

> See [references/known-issues.md](references/known-issues.md) for full details.

---

## Notes

- All write operations (Create/Update/Delete/Stop/Change/Patch/Notify/Accept) require user confirmation before execution
- Region is not hardcoded — uses `{region}` placeholder
- `project_id` is auto-resolved when omitted
- No hardcoded AK/SK in any file — credentials read from environment variables
- SDK fallback available when CLI encounters bugs
- Complex nested parameters use `--cli-jsonInput` with JSON file
