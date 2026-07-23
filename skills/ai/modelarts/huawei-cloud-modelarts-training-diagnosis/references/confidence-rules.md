# Confidence Level Judgment Rules + Output Contract

## Three-Level Confidence Definition

### HIGH (Confirmed Solution)

Meets one of the following:
1. `status.task_statuses[].message` contains explicit Python traceback (e.g., FileNotFoundError, ValueError, RuntimeError, CUDA OOM), with clear root cause identifiable from the traceback
2. `status.failureAnalysisResult.analysis_results[].description` provides explicit error description (e.g., "training directory does not exist", "OBS path no permission", "image pull failed")
3. ListTrainingJobEvents returns `events[].info` field containing explicit error descriptions
4. ShowTrainingJobLogsPreview contains explicit Python traceback last line, locating to specific code or library exception

**Output method**: Directly provide root cause, provide fix solution, mark "High confidence (based on explicit traceback/error event)".

### MEDIUM (Suggested to Try)

Meets one of the following:
1. Multiple indirect evidence combinations point to same root cause (e.g., GPU usage 100% + training stage stuck on DataLoad for over 30 minutes + no traceback in message)
2. `status.task_statuses[].exit_code` is non-zero but `message` is empty or vague
3. Status phase is abnormal ("Failed"/"Timeout"/"Abnormal") but `status.task_statuses[].message` is empty or contains generic error

**Output method**: Provide "most likely root cause", list suggested solutions, mark "Medium confidence (based on indirect evidence combination)", note "Suggested to try" before each solution.

### LOW (Insufficient Information)

Meets one of the following:
1. Phase 3 APIs return normal but user reports abnormal, and no error fields exist
2. Critical API calls fail (insufficient permissions, network exceptions, etc.), unable to obtain core information
3. Returned information is vague (e.g., `status.task_statuses[].message`="internal error", unable to further locate)

**Output method**: Explicitly output "Insufficient information to determine root cause", list:
- Collected information (for user reference)
- Recommended information to supplement (which APIs need further calls, which environment information needs user manual provision)
- Recommended manual investigation directions

**Strictly prohibited**: Giving "speculative" root causes or "looks like..." solutions when information is insufficient. Must output "Insufficient information" and list specific information needed.

---

## Evidence Field Mapping

### Explicit High Confidence Fields

| Scenario | Field | Meaning | Confidence |
|----------|-------|---------|------------|
| Training | `status.task_statuses[].message` contains "FileNotFoundError" | File path error | HIGH |
| Training | `status.task_statuses[].message` contains "OOM" / "Out of memory" / "CUDA out of memory" | VRAM/memory insufficient | HIGH |
| Training | `status.task_statuses[].message` contains "CUDA" | GPU related error | HIGH |
| Training | `status.task_statuses[].message` contains "ImportError" / "ModuleNotFoundError" | Dependency missing | HIGH |
| Training | `status.task_statuses[].message` contains "ValueError" | Invalid parameter or data | HIGH |
| Training | `status.task_statuses[].message` contains "RuntimeError" | Runtime execution error | HIGH |
| Training | `status.task_statuses[].message` contains "IndexError" | Array/list index out of bounds | HIGH |
| Training | `status.task_statuses[].message` contains "KeyError" | Dictionary key not found | HIGH |
| Training | `status.task_statuses[].message` contains "TypeError" | Type mismatch or invalid operation | HIGH |
| Training | `status.failureAnalysisResult.analysis_results[].description` | Platform's auto-diagnosis | HIGH |

### Indirect Medium Confidence Indicators

| Indicator | Threshold | Implies | Confidence |
|-----------|-----------|---------|------------|
| `status.task_statuses[].exit_code` | Non-zero but `message` empty | Job failed but no traceback captured | MEDIUM |
| ShowTrainingJobStages.stage_status | RUNNING and duration > 1h | Stuck on data loading | MEDIUM |
| ListTrainingJobEvents level=Warning | Has recent alerts | Upstream/downstream faults | MEDIUM |

### Insufficient Information Scenarios

| Scenario | Reason | Handling |
|----------|--------|----------|
| All APIs return normal but user reports abnormal | No abnormal fields | Output "Insufficient information", recommend manual investigation |
| `status.task_statuses[].message` = "internal error" | Error description vague | Output "Insufficient information", recommend viewing complete logs |
| Critical API returns 403/401 | Insufficient permissions | Output "Insufficient information", recommend checking IAM permissions |
| Critical API returns 5xx | Server exception | Output "Insufficient information", recommend retry later or submit ticket |
| API timeout no response | Network issue | Output "Insufficient information", recommend checking network |

---

## Output Contract Templates

### HIGH Confidence Output

```markdown
## 诊断结论

| 项目 | 值 |
|------|-----|
| 任务 | `bert-sentiment-analysis-v2` (`a1b2c3d4-e5f6-...`) |
| 当前状态 | `Failed` |
| 故障级别 | Fault |

## 根因

训练脚本中的数据路径 `/cache/data/train.csv` 不存在（置信度：HIGH）

## 修复建议

### 方案 1

1. 确认 OBS 数据路径是否正确
2. 检查训练脚本中的数据加载路径配置

> 注意：以上操作涉及需要用户确认后手动执行的变更
```

### MEDIUM Confidence Output

```markdown
## 诊断结论

| 项目 | 值 |
|------|-----|
| 任务 | `resnet50-image-classification` (`x9y8z7w6-...`) |
| 当前状态 | `Timeout` |
| 故障级别 | 疑似异常 |

## 根因

数据加载阶段卡死，可能是数据预处理逻辑问题或数据源访问异常（置信度：MEDIUM）

## 修复建议

### 方案 1

1. 检查数据预处理逻辑是否存在死循环
2. 确认 OBS 数据路径访问权限正常

### 方案 2

1. 增加数据加载超时配置
2. 检查数据格式是否符合预期

> 注意：以上操作涉及需要用户确认后手动执行的变更
```

### LOW/Insufficient Information Output

```markdown
## 诊断结论

| 项目 | 值 |
|------|-----|
| 任务 | `custom-training-job` (`m1n2o3p4-...`) |
| 当前状态 | `Abnormal` |
| 故障级别 | 疑似异常（信息不足） |

## 根因

当前信息不足以确定根因（置信度：LOW）

## 已收集信息

| API | 关键信息 |
|-----|----------|
| ShowTrainingJobDetails | `status.phase`: `Abnormal`, `message`: `internal error` |
| ListTrainingJobEvents | 无错误事件 |
| ListTrainingJobStages | 所有阶段状态正常 |

## 建议补充信息

1. 调用 `ShowTrainingJobLogsPreview` 获取完整日志（原因：当前 `message` 字段仅显示 `internal error`，无法定位具体问题）
2. 手动检查训练容器的环境变量配置（原因：API 无法获取容器内部环境信息）
3. 建议排查方向：检查训练脚本的异常捕获逻辑，确认是否有未捕获的异常
```
