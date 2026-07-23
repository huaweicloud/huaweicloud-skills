# hcloud Command Templates

> Global parameter description:
> - `--cli-region=cn-north-4` can switch to other regions (e.g., cn-north-7, cn-east-3, etc.)
> - `--cli-output=json` is default; can add `--cli-output=table` for human-readable during debugging
> - `--cli-query="<JMESPath>"` filters fields to reduce output
> - project_id is configured in profile, omitted in commands; after switching regions, need to explicitly pass or update profile

---

## Training Diagnosis Commands

### ShowTrainingJobDetails
Purpose: Training job details. Required: training_job_id.
```bash
hcloud ModelArts ShowTrainingJobDetails \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>"
```

Extract key diagnostic fields:
```bash
hcloud ModelArts ShowTrainingJobDetails \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>" \
  --cli-query="{job_id: metadata.id, name: metadata.name, phase: status.phase, task_statuses: status.task_statuses, failure_analysis: status.failureAnalysisResult}"
```

**Note**: `status.task_statuses[].message` contains the full Python traceback or error message. This is the primary evidence for root cause analysis.

### ListTrainingJobEvents
Purpose: Training error events. Required: training_job_id. Optional: level=Error to focus on errors.
```bash
hcloud ModelArts ListTrainingJobEvents \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --level=Error \
  --limit=100 \
  --training_job_id="<TRAINING_JOB_ID>"
```

Filter by time range (start_time/end_time must be passed in pairs, unit is ms timestamp):
```bash
hcloud ModelArts ListTrainingJobEvents \
  --cli-region=cn-north-4 \
  --level=Error \
  --start_time=1689033600000 \
  --end_time=1689120000000 \
  --training_job_id="<TRAINING_JOB_ID>"
```

### ListTrainingJobStages
Purpose: Stage information. Required: training_job_id.
```bash
hcloud ModelArts ListTrainingJobStages \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>"
```

### ShowTrainingJobLogsPreview
Purpose: Log preview. Required: training_job_id, task_id (from ShowTrainingJobDetails.status.task_statuses[].task_id).
```bash
hcloud ModelArts ShowTrainingJobLogsPreview \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>" \
  --task_id="<TASK_ID>"
```

Note: Logs may contain sensitive information; when outputting diagnosis, only extract key error/traceback lines, do not display full text.

### ShowObsUrlOfTrainingJobLogs
Purpose: OBS complete log temporary link (5 minutes valid). Required: training_job_id, task_id.
```bash
hcloud ModelArts ShowObsUrlOfTrainingJobLogs \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --training_job_id="<TRAINING_JOB_ID>" \
  --task_id="<TASK_ID>"
```

After output, prompt user: Link is valid for 5 minutes, download to local immediately then use editor to review traceback.

### ListTrainingJobs
Purpose: Full scan of abnormal training tasks (Failed/Timeout/Abnormal).
```bash
hcloud ModelArts ListTrainingJobs \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --cli-query="items[?status.phase=='Failed' || status.phase=='Timeout' || status.phase=='Abnormal'].{job_id: metadata.id, name: metadata.name, phase: status.phase}"
```

**Note**: The response uses `items[]` array (not `jobs[]`), and status is accessed via `status.phase` (string values like "Failed", not numeric codes).

---

## Early Exit Principle

**When ShowTrainingJobDetails already contains full traceback**: If `status.task_statuses[].message` contains a complete Python traceback (e.g., FileNotFoundError, ValueError, RuntimeError, CUDA OOM), the root cause is immediately clear at HIGH confidence. In this case, you can skip calling ListTrainingJobEvents, ListTrainingJobStages, ShowTrainingJobLogsPreview, and ShowObsUrlOfTrainingJobLogs.

**Example**: If `status.task_statuses[0].message` shows:
```
Traceback (most recent call last):
  File "train.py", line 42, in <module>
    data = load_checkpoint("/path/to/checkpoint")
FileNotFoundError: [Errno 2] No such file or directory: '/path/to/checkpoint'
```

The root cause (missing checkpoint file) is clear. No need to call additional APIs.

---

## Debugging Tips

### Switch Region
When switching regions, ensure project_id for that region is configured. Can use:
```bash
hcloud ModelArts ShowTrainingJobDetails --cli-region=cn-north-7 --training_job_id="xxx"
```
If corresponding region profile lacks project_id, need to first use `hcloud configure init` or explicitly pass `--project_id`.

### Output Format Switch
- `--cli-output=json` (default, for agent processing)
- `--cli-output=table` (for human reading)
- `--cli-output=tsv` (for spreadsheet import)
