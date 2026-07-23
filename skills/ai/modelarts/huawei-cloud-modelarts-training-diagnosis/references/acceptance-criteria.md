# Acceptance Criteria

This document defines the pass/fail criteria for testing the huawei-cloud-modelarts-training-diagnosis skill.

## Installation Verification

### Test 1: hcloud CLI Version Check

**Command**:
```bash
hcloud version
```

**Pass Criteria**:
- Returns version >= 7.2.2
- Command exits with code 0

**Fail Criteria**:
- Returns version < 7.2.2
- Command not found
- Any non-zero exit code

---

### Test 2: Configuration Verification

**Command**:
```bash
hcloud configure list
```

**Pass Criteria**:
- Displays at least one configured profile
- Shows valid AK/SK (not empty)
- Default region is set (typically cn-north-4)
- Command exits with code 0

**Fail Criteria**:
- No profiles configured
- Missing AK/SK
- Missing region configuration
- Any non-zero exit code

---

## Permission Verification

### Test 3: IAM Permission Check

**Command**:
```bash
hcloud ModelArts ListTrainingJobs --cli-region=cn-north-4
```

**Pass Criteria**:
- Returns HTTP 200
- JSON response contains `items` array (may be empty)
- No permission errors (403/401)
- Command exits with code 0

**Fail Criteria**:
- HTTP 403 Forbidden
- HTTP 401 Unauthorized
- Error message containing "permission" or "unauthorized"
- Any non-zero exit code

---

## Functional Verification

### Test 4: Full Scan of Abnormal Training Jobs

**Command**:
```bash
hcloud ModelArts ListTrainingJobs --cli-region=cn-north-4 --cli-output=json --cli-query="items[?status.phase=='Failed' || status.phase=='Timeout' || status.phase=='Abnormal'].{job_id: metadata.id, name: metadata.name, phase: status.phase}"
```

**Pass Criteria**:
- Returns HTTP 200
- JSON response is valid (parseable)
- Returns array of jobs (may be empty if no abnormal jobs exist)
- Each job object contains `job_id`, `name`, `phase` fields

**Fail Criteria**:
- HTTP error response
- Invalid JSON output
- Missing required fields

---

### Test 5: Show Training Job Details

**Prerequisite**: A valid training job ID (from Test 4 or user-provided)

**Command**:
```bash
hcloud ModelArts ShowTrainingJobDetails --cli-region=cn-north-4 --cli-output=json --training_job_id="<JOB_ID>"
```

**Pass Criteria**:
- Returns HTTP 200
- JSON response contains `metadata.id`, `metadata.name`, `status.phase`, `status.task_statuses`, `status.failureAnalysisResult` fields
- If job has tasks, `status.task_statuses` array contains objects with `task_id`, `exit_code`, `message` fields

**Fail Criteria**:
- HTTP 404 Not Found (invalid job ID)
- HTTP error response
- Missing required fields
- Invalid JSON output

---

### Test 6: List Training Job Events

**Prerequisite**: A valid training job ID

**Command**:
```bash
hcloud ModelArts ListTrainingJobEvents --cli-region=cn-north-4 --cli-output=json --level=Error --limit=100 --training_job_id="<JOB_ID>"
```

**Pass Criteria**:
- Returns HTTP 200
- JSON response contains `events` array (may be empty)
- Each event object contains `level`, `type`, `info`, `occur_time` fields

**Fail Criteria**:
- HTTP error response
- Invalid JSON output
- Missing required fields

---

### Test 7: List Training Job Stages

**Prerequisite**: A valid training job ID

**Command**:
```bash
hcloud ModelArts ListTrainingJobStages --cli-region=cn-north-4 --cli-output=json --training_job_id="<JOB_ID>"
```

**Pass Criteria**:
- Returns HTTP 200
- JSON response contains `stages` array (may be empty)
- Each stage object contains `stage_name`, `status`, `duration` fields

**Fail Criteria**:
- HTTP error response
- Invalid JSON output
- Missing required fields

---

### Test 8: Show Training Job Logs Preview

**Prerequisite**: A valid training job ID and task_id (from Test 5, field `status.task_statuses[].task_id`)

**Command**:
```bash
hcloud ModelArts ShowTrainingJobLogsPreview --cli-region=cn-north-4 --cli-output=json --training_job_id="<JOB_ID>" --task_id="<TASK_ID>"
```

**Pass Criteria**:
- Returns HTTP 200
- JSON response contains `log` field (may be empty string)
- JSON response contains `next_marker` field

**Fail Criteria**:
- HTTP error response
- Invalid JSON output
- Missing required fields

---

### Test 9: Show OBS URL of Training Job Logs

**Prerequisite**: A valid training job ID and task_id (from Test 5, field `status.task_statuses[].task_id`)

**Command**:
```bash
hcloud ModelArts ShowObsUrlOfTrainingJobLogs --cli-region=cn-north-4 --cli-output=json --training_job_id="<JOB_ID>" --task_id="<TASK_ID>"
```

**Pass Criteria**:
- Returns HTTP 200
- JSON response contains `obs_url` field
- `obs_url` is a valid URL string (starts with https://)

**Fail Criteria**:
- HTTP error response
- Invalid JSON output
- Missing `obs_url` field
- Invalid URL format

---

## End-to-End Diagnosis Test

### Test 10: Complete Diagnosis Workflow

**Prerequisite**: At least one abnormal training job exists (status.phase = "Failed"/"Timeout"/"Abnormal")

**Steps**:
1. Run Test 4 to find an abnormal job
2. Run Test 5 to get job details (check `status.task_statuses[].message` for traceback)
3. If `status.task_statuses[].message` contains full traceback, diagnosis can be completed at HIGH confidence without further API calls
4. Otherwise, run Test 6 to get error events
5. Run Test 7 to get stage information
6. If needed, run Test 8 to preview logs
7. Generate diagnosis output following the contract in SKILL.md

**Pass Criteria**:
- All API calls succeed (HTTP 200)
- Diagnosis output contains all required sections (Markdown format):
  - `## 诊断结论` (with table containing task/status/fault level)
  - `## 根因分析` (with confidence level per root cause)
  - `## 修复建议` or `## 建议补充信息`
- Root cause includes confidence level (HIGH/MEDIUM/LOW)
- Root cause references specific API fields and values

**Fail Criteria**:
- Any API call fails
- Missing required output sections
- No confidence level specified
- Root cause does not reference specific API fields

---

## Overall Acceptance Summary

**Skill is accepted if**:
- ✅ All installation tests pass (Tests 1-2)
- ✅ Permission test passes (Test 3)
- ✅ At least one functional test passes (Tests 4-9)
- ✅ End-to-end test passes if abnormal jobs exist (Test 10)

**Skill is rejected if**:
- ❌ Any installation test fails
- ❌ Permission test fails
- ❌ All functional tests fail
- ❌ End-to-end test fails (when abnormal jobs exist)

---

## Notes

- Tests 4-9 may pass with empty results if no training jobs exist in the account. This is acceptable.
- Test 10 is only required if abnormal training jobs exist. If no abnormal jobs exist, skip this test.
- All tests must use the correct region (cn-north-4 or user-configured region).
- All JSON outputs must be valid and parseable.
- **Early exit principle**: If `status.task_statuses[].message` contains full Python traceback in Test 5, skip Tests 6-8 and proceed directly to diagnosis output.
