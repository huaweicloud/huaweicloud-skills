# Verification Method

This document describes how to verify that the skill is correctly installed and configured.

## Verification Steps

### 1. Verify hcloud CLI Installation

Check that hcloud CLI is installed and meets the minimum version requirement:

```bash
hcloud version
```

**Expected output**: Version >= 7.2.2

If the version is lower, reinstall or upgrade hcloud CLI following the installation guide.

### 2. Verify Authentication Configuration

Check that hcloud CLI is properly configured with AK/SK and region:

```bash
hcloud configure list
```

**Expected output**: Shows configured AK/SK with region set to `cn-north-4` (or your target region)

If not configured, run `hcloud configure init` to set up authentication.

### 3. Verify IAM Permissions

Test that your account has the required read-only permissions for ModelArts training APIs:

```bash
hcloud ModelArts ListTrainingJobs --cli-region=cn-north-4
```

**Expected output**: Returns HTTP 200 with a list of training jobs (may be empty if no jobs exist)

**If you receive 403/401 errors**: Your account lacks the required IAM permissions. See `iam-policies.md` for the exact permission policy needed.

### 4. Verify End-to-End Functionality (Optional)

If you have a test training job ID, verify that all 6 APIs can be called successfully:

```bash
# Replace with your actual training job ID
export TEST_JOB_ID="<your-training-job-id>"

# Test ShowTrainingJobDetails
hcloud ModelArts ShowTrainingJobDetails --cli-region=cn-north-4 --cli-output=json --training_job_id $TEST_JOB_ID

# Test ListTrainingJobEvents
hcloud ModelArts ListTrainingJobEvents --cli-region=cn-north-4 --training_job_id $TEST_JOB_ID --level Error --limit 100

# Test ListTrainingJobStages
hcloud ModelArts ListTrainingJobStages --cli-region=cn-north-4 --training_job_id $TEST_JOB_ID

# Test ShowTrainingJobLogsPreview (requires task_id from ShowTrainingJobDetails response)
# First get task_id from ShowTrainingJobDetails output, then:
# hcloud ModelArts ShowTrainingJobLogsPreview --cli-region=cn-north-4 --training_job_id $TEST_JOB_ID --task_id <task-id>

# Test ShowObsUrlOfTrainingJobLogs (requires task_id)
# hcloud ModelArts ShowObsUrlOfTrainingJobLogs --cli-region=cn-north-4 --training_job_id $TEST_JOB_ID --task_id <task-id>
```

**Expected**: All commands return HTTP 200 with valid JSON responses.

## Common Issues

### Issue 1: "Command not found: hcloud"
**Cause**: hcloud CLI is not installed or not in PATH.
**Solution**: Install hcloud CLI following the installation guide.

### Issue 2: "Authentication failed" or "Invalid AK/SK"
**Cause**: AK/SK configuration is incorrect or expired.
**Solution**: Re-run `hcloud configure init` with correct credentials.

### Issue 3: "403 Forbidden" when calling APIs
**Cause**: Your account lacks the required IAM permissions.
**Solution**: Ask your IAM administrator to attach the policy defined in `iam-policies.md`.

### Issue 4: "Training job not found"
**Cause**: The training job ID is incorrect or the job is in a different region.
**Solution**: Verify the job ID and region. Use `ListTrainingJobs` to find available jobs.

## Success Criteria

The skill is ready to use when:
1. ✅ hcloud version >= 7.2.2
2. ✅ Authentication is configured
3. ✅ IAM permissions are granted
4. ✅ All 6 APIs can be called without errors (if test job is available)
