# Training Job Diagnosis Flow Details

## Phase 1 - Task Discovery

### Input Classification
1. User provides complete task ID: Skip this phase, go directly to Phase 2
2. User provides name (partial match): Use ListTrainingJobs to query ID + status, match name
3. User provides nothing: Full scan of abnormal task patterns

### Training Task Discovery

**Full scan of abnormal tasks**:
```bash
hcloud ModelArts ListTrainingJobs --cli-region=cn-north-4 --cli-output=json \
  --cli-query="items[?status.phase=='Failed' || status.phase=='Timeout' || status.phase=='Abnormal'].{job_id: metadata.id, name: metadata.name, phase: status.phase}"
```

**Note**: The response uses `items[]` array (not `jobs[]`), and status is a string phase value (e.g., "Failed", "Running", "Success"), not numeric codes.

### Exit Conditions
- No target tasks found: Output "No abnormal training tasks found", end
- User-provided ID does not exist: Output "Task does not exist, please confirm ID and region", end

---

## Phase 2 - Status Assessment

### Training Status Assessment
Call `ShowTrainingJobDetails`, extract the following fields:
- `status.phase` (string) → Compare with status phase values: "Failed", "Running", "Success", "Timeout", "Abnormal"
- `status.task_statuses[].message` → Full Python traceback or error message (primary evidence)
- `status.task_statuses[].exit_code` → Integer exit code (0=success, non-zero=failure)
- `status.task_statuses[].task_id` → Prepare for subsequent log APIs
- `status.failureAnalysisResult.analysis_results[]` → Platform's automatic diagnosis (supplementary evidence)

**Assessment Conclusion Classification**:
- Real fault: `status.phase` in ["Failed", "Timeout", "Abnormal"]
- False alarm: `status.phase` in ["Running", "Success"]
- Pending observation: `status.phase` in ["Initializing"]

### Early Exit Principle

**When ShowTrainingJobDetails already contains full traceback**: If `status.task_statuses[].message` contains a complete Python traceback (e.g., FileNotFoundError, ValueError, RuntimeError, CUDA OOM), the root cause is immediately clear at HIGH confidence. In this case, you can skip calling ListTrainingJobEvents, ListTrainingJobStages, ShowTrainingJobLogsPreview, and ShowObsUrlOfTrainingJobLogs — go directly to Phase 4 analysis.

**When to continue to Phase 3**:
- `status.task_statuses[].message` is empty or vague (e.g., "internal error")
- `status.task_statuses[].exit_code` is non-zero but `message` has no traceback
- `status.failureAnalysisResult` provides hints but no concrete root cause
- Need to determine which stage the job got stuck at

### Exit Conditions
- False alarm: Clearly reply "Task status is normal, no fault", but can continue to ask user about specific symptoms reported
- Pending observation: Recommend re-evaluating later, end this diagnosis

---

## Phase 3 - Information Collection

**Note**: This phase is only reached if Phase 2's early exit condition is not met (i.e., ShowTrainingJobDetails did not contain sufficient traceback evidence).

### Training Information Collection Path

**Main path** (always run):
1. ShowTrainingJobDetails → `status.phase`, `status.task_statuses[].message`, `status.task_statuses[].task_id`, `status.failureAnalysisResult`
2. ListTrainingJobEvents(level=Error) → Error event list
   ```bash
   hcloud ModelArts ListTrainingJobEvents --cli-region=cn-north-4 \
     --level=Error --limit=100 --training_job_id=<JOB_ID>
   ```
3. ListTrainingJobStages → Check which stage is stuck

**Extended path** (decide based on main path results):
4. For each task_id (from `status.task_statuses[].task_id`): ShowTrainingJobLogsPreview → Preview logs (find traceback/error lines)
5. ShowObsUrlOfTrainingJobLogs → Prompt user to download complete logs to local for traceback review (5min link)

---

## Phase 4 - Analysis and Diagnosis

### Inference Principles (CRITICAL)

1. Each inference must point to specific fields returned in Phase 3 as evidence; no speculation allowed
2. One piece of evidence supports one inference; multiple pieces of evidence cross-validation → increases confidence
3. When returned information is vague or contains no explicit errors, output "unable to determine root cause based on current information", enter insufficient information branch
4. Strictly follow the tiered judgment in `references/confidence-rules.md`

### Inference Patterns (by priority)

Match collected information in the following order:

**A. Explicit Python traceback in `status.task_statuses[].message`** → Direct mapping to fix solutions (highest confidence)
- `status.task_statuses[0].message` contains full traceback (e.g., FileNotFoundError, CUDA OOM, ImportError)
- `status.failureAnalysisResult.analysis_results[].description` provides platform's own diagnosis

**B. ListTrainingJobEvents `events[].info`** → Explicit error descriptions
- Event `info` field containing explicit error descriptions (e.g., "training directory does not exist", "OBS path no permission", "image pull failed")

**C. Stage event anomalies** → Infer stuck point root cause
- ListTrainingJobStages where `stage.status`="RUNNING" but `duration` is abnormally long

**D. Multiple evidence combination** → Comprehensive root cause
- Example: GPU 100% + training stage stuck on DataLoad + no traceback in message → Infer data loading deadlock

**E. Insufficient information** → Clearly output "Need to supplement: ..."
- No traceback in `status.task_statuses[].message`
- Critical API calls failed
- Returned information is vague

---

## Phase 5 - Solution Output

### Markdown Output Format

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

### Output When Information is Insufficient

```markdown
## 诊断结论

| 项目 | 值 |
|------|-----|
| 任务 | `<metadata.name>` (`<metadata.id>`) |
| 当前状态 | `<status.phase>` |
| 故障级别 | 疑似异常（信息不足） |

## 根因

当前信息不足以确定根因（置信度：LOW）

## 已收集信息

| API | 关键信息 |
|-----|----------|
| ShowTrainingJobDetails | `status.phase`: `<value>`, `message`: `<value>` |
| ListTrainingJobEvents | <event summary> |
| ListTrainingJobStages | <stage summary> |

## 建议补充信息

1. 调用 `<API>` 获取 `<field>`（原因：<why this information is needed>）
2. 手动检查 `<environment/configuration>`（原因：<API 无法获取的信息>）
3. 建议排查方向：<direction description>
```
