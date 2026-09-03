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
2. **Huawei Cloud AK/SK** configured via hcloud (see Security & Credential Check below)
3. **ModelArts service** enabled in the target region
4. **IAM permissions** — See [references/iam-policies.md](references/iam-policies.md)

### Security & Credential Check

> **⚠️ CRITICAL: This section defines the agent's security boundary. Follow it strictly.**

#### 🔒 Security Rules (MANDATORY)

- 🚫 **NEVER** read, echo, or print AK/SK values (e.g., `cat ~/.hcloud/config.json`, `echo $HW_ACCESS_KEY` is FORBIDDEN)
- 🚫 **NEVER** read or cat credential files such as `~/.hcloud/config.json` or any file that may contain secrets
- 🚫 **NEVER** ask the user to input AK/SK directly in the conversation or command line
- 🚫 **NEVER** execute `hcloud configure set --cli-access-key=... --cli-secret-key=...` — credential configuration is the **user's responsibility**, done outside the agent session
- 🚫 **NEVER** pass `--cli-access-key`/`--cli-secret-key` on **every API call** — they will be exposed in process listings (`ps aux`) for the entire request duration
- ✅ **ALWAYS** use `hcloud configure list` to check credential status (presence check only, not values)
- ✅ If no valid profile exists, **STOP** and instruct the user to configure credentials outside this session
- ✅ **Recommend** using IAM user with minimal permissions instead of main account

#### ✅ Agent Credential Check (the ONLY acceptable check)

```bash
# Step 1: Check credential status — presence only, not values
hcloud configure list
```

- ✅ **Expected**: Shows a valid profile with `mode: AKSK`
- ❌ **If empty/invalid** → Guide the user with the 3-step process below:

  **Step-by-step guidance (copy-paste for the user):**

  > *"No valid credentials found. Please follow these 3 steps in your terminal:"*
  >
  > **① Get your AK/SK**
  > Log in to [Huawei Cloud Console](https://console.huaweicloud.com) → IAM → Access Keys. If you don't have one, click "Create Access Key" and save it securely.
  >
  > **② Run this in your terminal (one-time setup):**
  > ```bash
  > hcloud configure set --cli-access-key=<YOUR_AK> --cli-secret-key=<YOUR_SK>
  > ```
  > *(Replace `<YOUR_AK>` and `<YOUR_SK>` with the values from step ①)*
  >
  > **③ Come back and tell me "configured"**, I'll verify it works.
  >
  > *Note: The `configure set` command stores your credentials in `~/.hcloud/config.json`. After that, all hcloud commands use them automatically — no need to pass AK/SK again.*
  >
  > *Agent: DO NOT execute any `configure set` command yourself.*

#### 🔧 User's Responsibility (for documentation, NOT agent execution)

The user configures credentials **outside the agent session** (in their own terminal):

```bash
# One-time setup — run this in your terminal, NOT in the agent chat
HISTCONTROL=ignorespace
 hcloud configure set --cli-access-key=<YOUR_AK> --cli-secret-key=<YOUR_SK>
```

> ⚠️ **Note**: hcloud CLI does **NOT** read `HW_ACCESS_KEY`/`HW_SECRET_KEY` environment variables (those are for Python SDK only). `hcloud configure set` is the only supported credential configuration method.

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

### Step 2.5: ⚠️ Pre-Flight Check (MANDATORY for Write Operations)

> **Before executing ANY write operation** (Create/Update/Delete/Stop/Change/Patch/Notify/Accept), you MUST:
>
> 1. **Read [references/known-issues.md](references/known-issues.md)** — Scan the relevant section for the target API
> 2. **Apply documented workarounds** — Especially for the following high-risk operations:
>
> | Operation | Critical Issue | Action Required |
> |-----------|--------------|----------------|
> | CreateTrainingJob | Must use v2 `kind/metadata/spec/tasks` format | Use `--cli-jsonInput` with v2 JSON structure |
> | CreateTrainingJob (dedicated pool) | `flavor_id` not accepted for dedicated pools | Omit `flavor_id`, specify `pool_id` instead |
> | CreateAlgorithm | JSON must use nested `metadata` + `job_config` structure | Use `--cli-jsonInput` with correct nesting (see known-issues #27) |
> | CreateAlgorithm | OBS code directory must exist and be accessible | Verify OBS path before calling API |
> | StopTrainingJob | Can only stop jobs in `creating`/`waiting`/`running` state | Check job status first |
> | CreateModel | `source_location` format must be `obs://bucket/path/` | Verify OBS path format |
> | CreateModel | `model_type` must be a valid value | Check known-issues #22 for valid values |
> | CreateSaveImageJob | Requires job in `running` state; SWR namespace required | Verify job status and SWR config |
> | ChangeAlgorithm | Must include `--metadata.name` parameter | Add `metadata.name` to request |
> | NotifyTrainingJobInformation | Parameter names differ from API docs | Check known-issues #24 |
> | UpdateTrainingJob | Not a valid CLI operation | Use `ChangeTrainingJob` instead |
>
> **Skipping this step will cause preventable failures.** Every issue in the table was discovered through real API testing.

### Step 3: Pricing Inquiry (for chargeable operations)

Before executing **chargeable write operations** (CreateTrainingJob on public resource pool, CreateTrainingExperiment), perform a BSS pricing inquiry to show estimated costs to the user.

> **📖 For detailed pricing inquiry procedures, read [references/pricing-inquiry.md](references/pricing-inquiry.md)**

#### Chargeable Operations

| Operation | Needs Inquiry | Condition |
|-----------|--------------|-----------|
| CreateTrainingJob | ✅ Yes | When using **public resource pool** (no `pool_id` specified) |
| CreateTrainingJob | ❌ No | When using **dedicated resource pool** (`pool_id` specified — pool already billed) |
| CreateTrainingExperiment | ✅ Yes | Experiments may launch training jobs with compute costs |
| All other operations | ❌ No | Read operations, deletes, stops, tags, etc. do not incur charges |

#### Inquiry Workflow

```
1. Detect chargeable operation (CreateTrainingJob without pool_id)
2. Extract flavor_id from spec.resource.flavor_id parameter
3. Get project ID via IAM KeystoneListAuthProjects
4. Call BSS ListOnDemandResourceRatings to query on-demand price
5. Calculate estimated cost: unit_price × node_count × estimated_duration
6. Display price table and cost estimate to user
7. Proceed to Step 4 (user confirmation) after showing pricing info
```

#### Quick Pricing Query

Use the helper script for quick price queries:

```bash
# Query single flavor
bash scripts/query-pricing.sh --region cn-north-4 --flavor modelarts.bm.gpu.v100

# Query multiple flavors for comparison
bash scripts/query-pricing.sh --region cn-north-4 --flavor modelarts.bm.gpu.v100 --flavor modelarts.cpu.8u32g --flavor modelarts.bm.ascend910
```

#### BSS Inquiry Parameters (Fixed)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `cloud_service_type` | `hws.service.type.modelarts` | ModelArts service type |
| `resource_type` | `hws.resource.type.modelarts` | ModelArts resource type |
| `usage_measure_id` | `4` | Hour (billing unit) |
| `size_measure_id` | `14` | Instance count |
| BSS API region | `cn-north-1` | BSS API always uses cn-north-1 |

### Step 4: Handle Write Operations

For all write operations (Create/Update/Delete/Stop/Change/Patch/Notify/Accept/Batch), **prompt the user for confirmation before execution**. For chargeable operations, confirmation includes reviewing the pricing information from Step 3.

### Step 5: Generate Console URL (after CreateTrainingJob)

After successfully creating a training job, generate and display the **ModelArts console URL** so the user can directly access the job details in the web console.

#### URL Format

**Training job detail page** (after CreateTrainingJob):

```
https://console.huaweicloud.com/modelarts/?region={region}#/training/detail/{job_id}
```

**Training job list page** (after ListTrainingJobs):

```
https://console.huaweicloud.com/modelarts/?region={region}#/training
```

| Component | Description | Example |
|-----------|-------------|---------|
| `{region}` | The region where the job was created | `cn-north-4` |
| `{job_id}` | Training job ID returned by CreateTrainingJob | `39cefbeb-0d86-46cb-a55a-fe6a62f3529b` |

> **Important**: Use `#/training/detail/{job_id}` for detail and `#/training` for list (new console paths). Do NOT use `#/trainingJobs/details/{job_id}` or `#/trainingJobs` — those are deprecated old console paths.

#### Workflow

```
1. CreateTrainingJob returns job_id in the response
2. Construct console URL: https://console.huaweicloud.com/modelarts/?region={region}#/training/detail/{job_id}
3. Display the URL to the user with a summary of the created job
```

#### Example Output

```
✅ Training job created successfully!

  Job Name:    my-training-job
  Job ID:      39cefbeb-0d86-46cb-a55a-fe6a62f3529b
  Status:      creating
  Region:      cn-north-4

  🔗 Console URL:
  https://console.huaweicloud.com/modelarts/?region=cn-north-4#/training/detail/39cefbeb-0d86-46cb-a55a-fe6a62f3529b
```

> **Note**: The console URL uses hash routing (`#/training/detail/{job_id}`). Do NOT use the old path `#/trainingJobs/details/{job_id}` — it redirects to a deprecated console page. The URL is valid as long as the training job exists and the user has ModelArts access permissions for the region.

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
| Indexed parameter | `--key.1=value1` | `--tasks.1.role=worker` |
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

## Capability Boundary（能力边界）

This skill covers **only** ModelArts training management — 52 APIs across 8 functional domains (see Core Commands above). The following ModelArts capabilities are **NOT supported**:

| Unsupported Domain | Example Operations | Suggestion |
|--------------------|--------------------|------------|
| Notebook (Dev Environment) | CreateNotebook, ListNotebooks, ShowNotebook | Use ModelArts console or dedicated notebook skill |
| Inference Service (Online Service) | CreateService, ListServices, ShowService | Use ModelArts console or inference skill |
| Resource Pool / Cluster | CreateResourcePool, ListResourcePools | Use ModelArts console |
| Workflow Orchestration | CreateWorkflow, ListWorkflows | Use ModelArts console |
| Image Management (SWR) | ListImages, ShowImage | Use SWR console or CLI directly |
| DevServer | CreateDevServer, ListDevServers | Use ModelArts console |
| Workspace Management | CreateWorkspace, ListWorkspaces | Use ModelArts console |

> When receiving requests for the above unsupported capabilities, **explicitly inform the user** that this skill does not support them, and suggest using the ModelArts console (`https://console.huaweicloud.com/modelarts/`) or the relevant dedicated skill.

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
| [references/pricing-inquiry.md](references/pricing-inquiry.md) | BSS on-demand pricing inquiry for training jobs (pre-creation cost estimation) |
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
- **Pricing inquiry**: CreateTrainingJob (public pool) and CreateTrainingExperiment trigger BSS pricing inquiry before execution — see [references/pricing-inquiry.md](references/pricing-inquiry.md)
- **Dedicated resource pool**: Training jobs using a dedicated resource pool (`pool_id` specified) do NOT require pricing inquiry — the pool is already billed
- Region is not hardcoded — uses `{region}` placeholder
- `project_id` is auto-resolved when omitted
- No hardcoded AK/SK in any file — credentials configured via `hcloud configure set` by the user outside the agent session
- Agent must use `hcloud configure list` for credential presence check only — NEVER read/echo AK/SK values
- If no valid credentials found, agent must STOP and guide user through the 3-step configuration process (see Prerequisites section)
- SDK fallback available when CLI encounters bugs
- Complex nested parameters use `--cli-jsonInput` with JSON file
