# Verification Method

> How to verify that ModelArts training management CLI commands work correctly.

---

## Verification Strategy

### 1. Read-Only Operations (Safe to Test)

These operations can be tested without side effects:

| Operation | Verification Command | Expected Result |
|-----------|---------------------|-----------------|
| ListTrainingJobs | `hcloud ModelArts ListTrainingJobs --cli-region={region} --limit=1` | JSON with job list or empty array |
| ShowTrainingJobEngines | `hcloud ModelArts ShowTrainingJobEngines --cli-region={region}` | List of engine types |
| ShowTrainingJobFlavors | `hcloud ModelArts ShowTrainingJobFlavors --cli-region={region}` | List of flavor types |
| ShowTrainingQuotas | `hcloud ModelArts ShowTrainingQuotas --cli-region={region}` | Quota info |
| ListAlgorithms | `hcloud ModelArts ListAlgorithms --cli-region={region} --limit=1` | JSON with algorithm list |
| ShowTrainJobTags | `hcloud ModelArts ShowTrainJobTags --cli-region={region} --training_job_id={id}` | Tag list |
| ListTrainingExperiments | `hcloud ModelArts ListTrainingExperiments --cli-region={region} --limit=1` | Experiment list |
| ListEvents | `hcloud ModelArts ListEvents --cli-region={region} --limit=1` | Event list |
| ListEventCategories | `hcloud ModelArts ListEventCategories --cli-region={region}` | Category list |
| ListScheduledEvents | `hcloud ModelArts ListScheduledEvents --cli-region={region} --limit=1` | Scheduled event list |
| ListModels | `hcloud ModelArts ListModels --cli-region={region} --limit=1` | Model list |
| ShowModelEngineAndRuntime | `hcloud ModelArts ShowModelEngineAndRuntime --cli-region={region}` | Engine and runtime list |
| ShowAutoSearchYamlTemplatesInfo | `hcloud ModelArts ShowAutoSearchYamlTemplatesInfo --cli-region={region}` | Template info |

### 2. Write Operations (Require Confirmation)

These operations modify state and should only be tested with explicit user confirmation:

| Operation | Risk Level | Reversible? |
|-----------|------------|-------------|
| CreateTrainingJob | Medium | Yes (delete job) |
| StopTrainingJob | Low | Yes (restart) |
| DeleteTrainingJob | High | No |
| ChangeTrainingJobDescription | Low | Yes |
| CreateAlgorithm | Medium | Yes (delete algorithm) |
| ChangeAlgorithm | Low | Yes |
| DeleteAlgorithm | High | No |
| CreateTrainJobTags | Low | Yes (delete tags) |
| DeleteTrainJobTags | Low | Yes (recreate) |
| CreateTrainingExperiment | Medium | Yes (delete experiment) |
| ChangeTrainingExperiment | Low | Yes |
| DeleteTrainingExperiment | High | No |
| AcceptScheduledEvent | Medium | No |
| CreateModel | Medium | Yes (delete model) |
| DeleteModel | High | No |
| CreateModelArtsAgency | Low | Idempotent |
| ShowAutoSearchTrialEarlyStop | Medium | No |
| CreateSaveImageJob | Medium | No (image saved to SWR) |

### 3. Dependent Operations

Some operations require existing resources:

| Operation | Prerequisite |
|-----------|-------------|
| ShowTrainingJobDetails | Existing training_job_id |
| StopTrainingJob | Job in creating/waiting/running state |
| DeleteTrainingJob | Existing training_job_id |
| ShowTrainingJobLogsPreview | Existing training_job_id |
| ShowTrainingJobMetrics | Existing training_job_id with metrics |
| ShowAlgorithmByUuid | Existing algorithm_id |
| ChangeAlgorithm | Existing algorithm_id |
| DeleteAlgorithm | Existing algorithm_id |
| ShowTrainJobTags | Existing training_job_id with tags |
| ShowTrainingExperimentDetails | Existing experiment_id |
| DeleteTrainingExperiment | Existing experiment_id |
| ChangeTrainingExperiment | Existing experiment_id |
| ListTrainingJobEvents | Existing training_job_id |
| ListTrainingJobStages | Existing training_job_id |
| ListTrainingJobTasks | Existing training_job_id |
| ShowModel | Existing model_id |
| DeleteModel | Existing model_id |
| ShowAutoSearchTrials | Existing training_job_id with auto search |
| ShowAutoSearchPerTrial | Existing training_job_id + trial_id |
| ShowAutoSearchParamsAnalysis | Existing training_job_id with auto search |
| ShowAutoSearchTrialEarlyStop | Running trial |
| ShowAutoSearchYamlTemplateContent | Existing template_name |
| ShowSaveImageJob | Existing job_id in running state (✅ verified) |

---

## Test Execution Steps

### Step 1: Verify CLI Availability

```bash
hcloud --version
hcloud ModelArts ListTrainingJobs --help
```

### Step 2: Test Read-Only Operations

```bash
# Set test region
REGION="cn-north-4"

# Test list operations
hcloud ModelArts ListTrainingJobs --cli-region=$REGION --limit=1
hcloud ModelArts ListAlgorithms --cli-region=$REGION --limit=1
hcloud ModelArts ListTrainingExperiments --cli-region=$REGION --limit=1
hcloud ModelArts ListModels --cli-region=$REGION --limit=1
hcloud ModelArts ListEvents --cli-region=$REGION --limit=1
hcloud ModelArts ListEventCategories --cli-region=$REGION
hcloud ModelArts ListScheduledEvents --cli-region=$REGION --limit=1

# Test metadata operations
hcloud ModelArts ShowTrainingJobEngines --cli-region=$REGION
hcloud ModelArts ShowTrainingJobFlavors --cli-region=$REGION
hcloud ModelArts ShowTrainingQuotas --cli-region=$REGION
hcloud ModelArts ShowModelEngineAndRuntime --cli-region=$REGION
hcloud ModelArts ShowAutoSearchYamlTemplatesInfo --cli-region=$REGION
```

### Step 3: Test Dependent Read Operations

```bash
# Replace with actual IDs from Step 2
JOB_ID="xxx-xxx-xxx"
ALGO_ID="xxx-xxx-xxx"
EXP_ID="xxx-xxx-xxx"
MODEL_ID="xxx-xxx-xxx"

hcloud ModelArts ShowTrainingJobDetails --cli-region=$REGION --training_job_id=$JOB_ID
hcloud ModelArts ShowTrainingJobLogsPreview --cli-region=$REGION --training_job_id=$JOB_ID
hcloud ModelArts ShowTrainingJobMetrics --cli-region=$REGION --training_job_id=$JOB_ID
hcloud ModelArts ListTrainingJobEvents --cli-region=$REGION --training_job_id=$JOB_ID
hcloud ModelArts ListTrainingJobStages --cli-region=$REGION --training_job_id=$JOB_ID
hcloud ModelArts ListTrainingJobTasks --cli-region=$REGION --training_job_id=$JOB_ID
hcloud ModelArts ShowAlgorithmByUuid --cli-region=$REGION --algorithm_id=$ALGO_ID
hcloud ModelArts ShowTrainingExperimentDetails --cli-region=$REGION --experiment_id=$EXP_ID
hcloud ModelArts ShowModel --cli-region=$REGION --model_id=$MODEL_ID
```

### Step 4: Verify Error Handling

```bash
# Test with invalid ID (should return error, not crash)
hcloud ModelArts ShowTrainingJobDetails --cli-region=$REGION --training_job_id=invalid-id
# Expected: error message about invalid job ID

# Test with missing required parameter
hcloud ModelArts ShowTrainingJobDetails --cli-region=$REGION
# Expected: error message about missing training_job_id
```

---

## Success Criteria

| Criterion | How to Verify |
|-----------|---------------|
| CLI commands execute without syntax errors | All commands return valid JSON or clear error messages |
| Read operations return data | List operations return arrays (possibly empty) |
| Write operations require confirmation | Agent prompts user before executing write ops |
| Error handling is graceful | Invalid IDs return error messages, not crashes |
| Region is parameterized | No hardcoded region in any command |
| project_id auto-resolved | Commands work without explicit --project_id |
