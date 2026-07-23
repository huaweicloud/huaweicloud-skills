# ModelArts Training Job Diagnosis API Catalog

## Training Diagnosis APIs

| API | Method | Purpose | Required Parameters | Key Return Fields |
|-----|--------|---------|---------------------|-------------------|
| ShowTrainingJobDetails | GET | Job status + errors | project_id, training_job_id | metadata.id, metadata.name, status.phase, status.task_statuses[].{task_id, exit_code, message}, status.failureAnalysisResult.analysis_results[] |
| ListTrainingJobEvents | GET | Error events | project_id, training_job_id | events[].{level, type, info, occur_time} |
| ListTrainingJobStages | GET | Stage checkpoints | project_id, training_job_id | stages[].{stage_name, status, duration} |
| ShowTrainingJobLogsPreview | GET | Log preview | project_id, training_job_id, task_id | log, next_marker |
| ShowObsUrlOfTrainingJobLogs | GET | OBS full log link | project_id, training_job_id, task_id | obs_url (5min valid) |
| ListTrainingJobs | POST | Full list | project_id | items[].{metadata.id, metadata.name, status.phase} |

## Common Conventions

- All APIs use `hcloud ModelArts <Operation>` prefix
- Required `--cli-region` defaults to profile configuration (cn-north-4)
- `--project_id` is configured in profile and can be omitted; after switching regions, need to explicitly pass or update profile
- Output unified as `--cli-output=json`
- JMESPath filtering uses `--cli-query`

## Status Phase Reference

### Training Status (String Phase Values)

| Phase Value | Meaning | Diagnosis Target |
|-------------|---------|------------------|
| Initializing | Initializing | No |
| Running | Running | No |
| Success | Success | No |
| Failed | Failed | **Yes** |
| Stopped | Stopped | No |
| Timeout | Timeout | **Yes** |
| Abnormal | Abnormal | **Yes** |

**Note**: The API returns `status.phase` as a string value, not numeric codes. Use string comparison in JMESPath queries (e.g., `status.phase=='Failed'`).

### Response Structure

The API response follows this structure:

```json
{
  "metadata": {
    "id": "<training_job_id>",
    "name": "<training_job_name>"
  },
  "status": {
    "phase": "Failed|Running|Success|...",
    "task_statuses": [
      {
        "task_id": "<task_id>",
        "exit_code": 1,
        "message": "<full Python traceback or error message>"
      }
    ],
    "failureAnalysisResult": {
      "analysis_results": [
        {
          "description": "<platform auto-diagnosis description>",
          "solution": "<platform suggested solution>",
          "document_link": "<related documentation URL>"
        }
      ]
    }
  }
}
```

### Key Fields for Diagnosis

- `status.phase`: Job status (use for filtering abnormal jobs)
- `status.task_statuses[].message`: Full Python traceback or error message (primary evidence for root cause)
- `status.task_statuses[].exit_code`: Integer exit code (0=success, non-zero=failure)
- `status.task_statuses[].task_id`: Task ID within the job (required for log APIs)
- `status.failureAnalysisResult.analysis_results[]`: Platform's automatic diagnosis (supplementary evidence)
- `metadata.id`: Training job ID
- `metadata.name`: Training job name

### Training Event Levels

| Value | Meaning | Purpose |
|-------|---------|---------|
| Info | Information | Normal process tracking |
| Warning | Warning | Potential issues, recommended to monitor |
| Error | Error | **Core filtering value for fault diagnosis** |
