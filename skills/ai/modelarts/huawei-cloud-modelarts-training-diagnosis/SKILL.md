---
name: huawei-cloud-modelarts-training-diagnosis
description: |
  Huawei Cloud ModelArts training job fault diagnosis skill. Uses hcloud CLI to call ModelArts training job log/event APIs, analyzes training job failures/timeouts/stuck jobs, locates customer training code issues, and provides diagnosis conclusions with fix suggestions and confidence levels.
  Scenarios: training job failure (status.phase=Failed), timeout (Timeout), abnormal (Abnormal), stuck jobs.
  Triggers: training job failure, training job timeout, training job stuck, ModelArts training diagnosis, 训练任务失败排查, 训练作业异常分析.
tags: [huawei-cloud, modelarts, training, diagnostics, hcloud]
---

# ModelArts Training Job Fault Diagnosis

## Overview

This skill provides automated fault diagnosis for Huawei Cloud ModelArts training jobs. It calls ModelArts log and event APIs via hcloud CLI to collect runtime information, analyzes training job failures/timeouts/stuck jobs, and outputs diagnosis conclusions with fix suggestions and confidence levels.

### Architecture

```
User Input
    ↓
Phase 1: Task Discovery (ListTrainingJobs)
    ↓
Phase 2: Status Assessment (ShowTrainingJobDetails)
    ↓
[Early Exit if traceback found in status.task_statuses[].message]
    ↓ (if no traceback)
Phase 3: Information Collection
    ├─ Main Path: ListTrainingJobEvents, ListTrainingJobStages
    └─ Extended Path: ShowTrainingJobLogsPreview, ShowObsUrlOfTrainingJobLogs
    ↓
Phase 4: Analysis (confidence-based inference)
    ↓
Phase 5: Output (diagnosis report + fix suggestions)
```

### Applicable Scenarios

- Training job failure (status.phase = "Failed")
- Training job timeout (status.phase = "Timeout")
- Training job abnormal (status.phase = "Abnormal")
- Training job stuck (running long time with no progress)
- Resource shortage causing training failure

### Typical Use Cases

- "My training job failed, help me diagnose"
- "Training job is stuck, no progress for hours"
- "Training job timeout, what went wrong?"
- "Scan all failed training jobs in my account"
- "Training job error code 1.015, what does it mean?"

## Prerequisites

### hcloud CLI Installation

- **Version**: 7.2.2 or higher
- **Verification**: `hcloud version` should return version >= 7.2.2
- **Installation guide**: See [references/cli-installation-guide.md](references/cli-installation-guide.md)

### Authentication Configuration

- AK/SK configured in `~/.hcloud/config.json`
- Default region: `cn-north-4`
- `project_id` configured in profile
- `skipSecureVerify=true` (for WSL environment)

**Verification command**:
```bash
hcloud configure list
```

### IAM Permissions

This skill requires **read-only** permissions for ModelArts training APIs.

**Required permissions**: See [references/iam-policies.md](references/iam-policies.md)

**Permission failure handling**:
1. If any API returns 403/401, read `references/iam-policies.md`
2. Display required permissions list and policy JSON to user
3. Guide user to create custom policy in IAM console
4. Pause execution until user confirms permissions are granted

## KooCLI Command Format Standard

All commands follow the standard hcloud format:

```bash
hcloud ModelArts <Operation> --param1=value1 --param2=value2 --cli-region=<region>
```

**Key conventions**:
- Service name: `ModelArts` (PascalCase)
- Operation name: PascalCase (e.g., `ShowTrainingJobDetails`)
- Region parameter: `--cli-region=<value>` (default: `cn-north-4`)
- Output format: `--cli-output=json` (for agent processing)
- JMESPath filtering: `--cli-query="<expression>"` (to reduce output)

**Example**:
```bash
hcloud ModelArts ShowTrainingJobDetails \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>"
```

## Workflow

This skill follows a **5-phase diagnosis workflow**:

### Phase 1: Task Discovery
- If user provides full job ID → skip to Phase 2
- If user provides name → use `ListTrainingJobs` to find ID + status.phase
- If user provides nothing → scan all abnormal jobs (status.phase = "Failed"/"Timeout"/"Abnormal")

### Phase 2: Status Assessment
- Call `ShowTrainingJobDetails` to get job status
- Check `status.phase`: "Failed"/"Timeout"/"Abnormal" = real fault, "Running"/"Success" = false alarm, "Initializing" = pending observation
- Extract `status.task_statuses[].task_id` for subsequent log APIs
- **Early Exit**: If `status.task_statuses[].message` contains full Python traceback, diagnosis can be completed at HIGH confidence without calling Phase 3 APIs

### Phase 3: Information Collection (skipped if early exit applies)
**Main path (always run)**:
1. `ShowTrainingJobDetails` → `status.phase`, `status.task_statuses[].message`, `status.task_statuses[].task_id`, `status.failureAnalysisResult`
2. `ListTrainingJobEvents(level=Error)` → error event list
3. `ListTrainingJobStages` → check which stage is stuck

**Extended path (conditional)**:
4. `ShowTrainingJobLogsPreview` → preview logs (find traceback/error lines)
5. `ShowObsUrlOfTrainingJobLogs` → OBS full log download link (5min valid)

**Detailed flow**: See [references/diagnosis-flow.md](references/diagnosis-flow.md)

## Core Commands

### Task Discovery Commands

**ListTrainingJobs** — Scan all abnormal training jobs
```bash
hcloud ModelArts ListTrainingJobs \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --cli-query="items[?status.phase=='Failed' || status.phase=='Timeout' || status.phase=='Abnormal'].{job_id: metadata.id, name: metadata.name, phase: status.phase}"
```

### Status Assessment Commands

**ShowTrainingJobDetails** — Get job status + error info
```bash
hcloud ModelArts ShowTrainingJobDetails \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>"
```

**Key response fields**:
- `metadata.id`, `metadata.name` — job identifier
- `status.phase` — job status ("Failed", "Running", "Success", etc.)
- `status.task_statuses[].message` — full Python traceback or error message (primary evidence)
- `status.task_statuses[].exit_code` — integer exit code
- `status.task_statuses[].task_id` — task ID for log APIs
- `status.failureAnalysisResult.analysis_results[]` — platform's automatic diagnosis

### Information Collection Commands

**ListTrainingJobEvents** — Get error events
```bash
hcloud ModelArts ListTrainingJobEvents \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --level=Error \
  --limit=100 \
  --training_job_id="<TRAINING_JOB_ID>"
```

**ListTrainingJobStages** — Check stage checkpoints
```bash
hcloud ModelArts ListTrainingJobStages \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>"
```

**ShowTrainingJobLogsPreview** — Preview logs (find traceback)
```bash
hcloud ModelArts ShowTrainingJobLogsPreview \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>" \
  --task_id="<TASK_ID>"
```

**ShowObsUrlOfTrainingJobLogs** — Get OBS full log download link (5min valid)
```bash
hcloud ModelArts ShowObsUrlOfTrainingJobLogs \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>" \
  --task_id="<TASK_ID>"
```

**Complete command templates**: See [references/hcloud-command-templates.md](references/hcloud-command-templates.md)

## Parameter Confirmation

### Training Diagnosis Parameters

| Parameter | Required | Type | Description | Default |
|-----------|----------|------|-------------|---------|
| `training_job_id` | Yes | String | Training job ID (e.g., from ListTrainingJobs) | None |
| `task_id` | Conditional | String | Task ID within training job (from ShowTrainingJobDetails.status.task_statuses[].task_id) | None |
| `--cli-region` | No | String | Huawei Cloud region | `cn-north-4` |
| `--cli-output` | No | String | Output format (json/table/tsv) | `json` |
| `--cli-query` | No | String | JMESPath expression to filter output | None |

**Notes**:
- `task_id` is required for log APIs, obtained from `ShowTrainingJobDetails.status.task_statuses[].task_id`
- Region can be switched (e.g., `cn-north-9`, `cn-east-3`), but `project_id` must be configured for that region
- Logs may contain sensitive information; only extract key error/traceback lines, do not display full logs

## Output Format

This skill outputs diagnosis reports in **Markdown format**.

### Output Template

```markdown
## 诊断结论

| 项目 | 值 |
|------|-----|
| 任务 | `<metadata.name>` (`<metadata.id>`) |
| 当前状态 | `<status.phase>` |
| 故障级别 | Fault / Abnormal / 疑似异常 / 正常 |

## 根因

<一句话描述什么导致了作业失败>（置信度：HIGH/MEDIUM/LOW）

## 修复建议

### 方案 1

1. <step 1>
2. <step 2>

> 注意：以上操作涉及 [只读查询 / 需要用户确认后手动执行的变更]

## 后续步骤

[信息不足时] 当前信息不足以确定根因，建议补充以下信息：
- 调用 `<API>` 获取 `<field>`
- 或手动检查 `<environment/configuration>`
```

**Strict constraint**: Generate the report strictly following the template above. Keep analysis reasoning internal, not in the report.

### Confidence Levels

- **HIGH**: `status.task_statuses[].message` contains full Python traceback with identifiable root cause, or `status.failureAnalysisResult.analysis_results[].description` provides explicit error description, or events contain clear error
- **MEDIUM**: Multiple indirect clues point to same root cause, or `status.task_statuses[].exit_code` non-zero but `message` is empty/vague
- **LOW**: Insufficient information; must output "information insufficient" and list what additional information is needed

**Detailed confidence rules**: See [references/confidence-rules.md](references/confidence-rules.md)

## Verification Method

This skill follows a 3-tier verification approach:

### Installation Verification
```bash
hcloud version
```
**Success criteria**: Returns version >= 7.2.2

### Configuration Verification
```bash
hcloud configure list
```
**Success criteria**: Displays valid AK/SK configuration with region=cn-north-4

### Function Verification
```bash
hcloud ModelArts ListTrainingJobs --cli-region=cn-north-4
```
**Success criteria**: Returns HTTP 200 and training job list

**Detailed verification steps**: See [references/verification-method.md](references/verification-method.md)

## Best Practices

### Early Exit Principle
- If `ShowTrainingJobDetails` returns full Python traceback in `status.task_statuses[].message`, skip Phase 3 APIs (ListTrainingJobEvents, ListTrainingJobStages, ShowTrainingJobLogsPreview, ShowObsUrlOfTrainingJobLogs)
- This saves API calls and speeds up diagnosis when root cause is already clear

### Progressive Diagnosis
- Start with minimal information (job ID only)
- Run Phase 2 first (ShowTrainingJobDetails)
- Only run Phase 3 APIs if Phase 2 results are insufficient (no traceback in message)
- Avoid running all APIs at once; follow the 5-phase workflow

### Evidence-Based Analysis
- Every inference must point to specific fields from API responses
- One evidence supports one inference; multiple evidence cross-validation increases confidence
- When return information is vague or contains no explicit errors, output "unable to determine root cause based on current information"
- **Strictly prohibited**: Guessing root causes without evidence

### Log Handling
- Logs may contain sensitive information (IP addresses, tokens, credentials)
- Only extract key error/traceback lines for diagnosis
- Do not display full logs in output
- For complete logs, use `ShowObsUrlOfTrainingJobLogs` and prompt user to download (5min valid link)

### Region Switching
- Default region is `cn-north-4`
- When switching regions, ensure `project_id` is configured for that region
- Use `hcloud configure init` or explicitly pass `--project_id` if region profile lacks project_id

## Reference Documents

| Document | File | Description |
|----------|------|-------------|
| API Catalog | [references/api-catalog.md](references/api-catalog.md) | 6 training diagnosis APIs, status phases, response structure, event levels |
| Diagnosis Flow | [references/diagnosis-flow.md](references/diagnosis-flow.md) | 5-phase diagnosis workflow in detail with early exit principle |
| Command Templates | [references/hcloud-command-templates.md](references/hcloud-command-templates.md) | Complete hcloud command templates for each API |
| Confidence Rules | [references/confidence-rules.md](references/confidence-rules.md) | Confidence level definitions, evidence mapping, output contracts |
| CLI Installation Guide | [references/cli-installation-guide.md](references/cli-installation-guide.md) | hcloud CLI installation, configuration, verification |
| IAM Policies | [references/iam-policies.md](references/iam-policies.md) | Required IAM permissions and policy JSON |
| Verification Method | [references/verification-method.md](references/verification-method.md) | 3-tier verification steps |
| Acceptance Criteria | [references/acceptance-criteria.md](references/acceptance-criteria.md) | Pass/fail criteria for skill testing |

## Notes

### Security Constraints

1. **Read-only throughout**: Only call GET APIs; never call Create/Update/Delete/Stop
2. **No credential leakage**: Never print AK/SK
3. **User confirmation required**: If fix suggestions involve changes (restart, modify specs), must clearly prompt "requires user confirmation before manual execution"; never auto-execute
4. **Sensitive information masking**: Logs may contain sensitive info; mask sensitive fields before output (e.g., desensitize IPs, do not print complete tokens)

### Scope Limitations

- **Training job diagnosis only**: Does not diagnose Notebook, inference services, or other scenarios
- **No code modification**: Does not modify any business code or resources
- **No fabrication**: Never fabricate root causes without evidence; must be based on API return fields
- **No private data access**: Does not directly read private data in user repositories

### Known Limitations

- Some APIs may have rate limits; if throttled, wait and retry
- Log preview may be truncated; use OBS link for complete logs
- Metrics APIs removed from skill (can show state but cannot diagnose root causes)
- `status.task_statuses[].message` may be empty for some failures; in such cases, Phase 3 APIs become necessary
