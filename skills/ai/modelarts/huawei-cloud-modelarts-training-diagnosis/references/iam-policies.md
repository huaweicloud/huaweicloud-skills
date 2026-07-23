# IAM Policies

## Overview

This skill requires **read-only** permissions for ModelArts training job diagnosis APIs. All 6 APIs used by this skill only query information and do not modify any resources.

## Required Permissions

### Permission Summary

| API | Permission Action | Resource |
|-----|------------------|----------|
| ShowTrainingJobDetails | modelarts:trainingJobs:get | modelarts:*:*:trainingJobs/* |
| ListTrainingJobEvents | modelarts:trainingJobs:get | modelarts:*:*:trainingJobs/* |
| ListTrainingJobStages | modelarts:trainingJobs:get | modelarts:*:*:trainingJobs/* |
| ShowTrainingJobLogsPreview | modelarts:trainingJobs:get | modelarts:*:*:trainingJobs/* |
| ShowObsUrlOfTrainingJobLogs | modelarts:trainingJobs:get | modelarts:*:*:trainingJobs/* |
| ListTrainingJobs | modelarts:trainingJobs:list | modelarts:*:*:trainingJobs |

### Minimal Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "modelarts:trainingJobs:get",
        "modelarts:trainingJobs:list"
      ],
      "Resource": [
        "modelarts:*:*:trainingJobs",
        "modelarts:*:*:trainingJobs/*"
      ]
    }
  ]
}
```

**Policy Explanation**:
- `modelarts:trainingJobs:get`: Permission to query details of a specific training job (used by 5 APIs)
- `modelarts:trainingJobs:list`: Permission to list all training jobs (used by ListTrainingJobs)
- Resource scope: All training jobs in the account (`trainingJobs/*`)

## How to Apply the Policy

### Step 1: Create Custom Policy

1. Log in to Huawei Cloud Console
2. Navigate to **IAM Console** → **Permissions** → **Policies**
3. Click **Create Custom Policy**
4. Fill in:
   - **Policy Name**: `ModelArtsTrainingDiagnosisReadOnly`
   - **Policy View**: `JSON`
   - **Policy Content**: Paste the JSON from above
5. Click **OK**

### Step 2: Assign Policy to User

1. Navigate to **IAM Console** → **Users**
2. Find the user who will use this skill
3. Click **Add Permission**
4. Search for `ModelArtsTrainingDiagnosisReadOnly`
5. Select the policy and click **OK**

### Step 3: Verify Permissions

After assigning the policy, verify that the user can call the APIs:

```bash
hcloud ModelArts ListTrainingJobs --cli-region=cn-north-4
```

**Expected result**: Returns HTTP 200 and a list of training jobs (may be empty if no jobs exist).

If you receive `403 Forbidden` or `Insufficient permissions`, verify:
1. The policy is correctly attached to your user
2. The policy JSON matches the minimal policy above
3. The AK/SK in your hcloud config belongs to the correct user

## Permission Failure Handling

If any API returns `403` or `401` during skill execution:

1. **Stop execution** immediately
2. **Display the required permissions** to the user:
   ```
   Permission denied. This skill requires the following IAM permissions:
   - modelarts:trainingJobs:get
   - modelarts:trainingJobs:list
   
   Please create a custom policy with these permissions and attach it to your user.
   See: references/iam-policies.md for detailed instructions.
   ```
3. **Wait for user confirmation** that permissions have been granted
4. **Retry the failed API call** after user confirms

## Security Notes

- This skill only requires **read-only** permissions
- No Create/Update/Delete permissions are needed
- The skill will never modify, stop, or delete any training jobs
- All API calls are GET requests
- Logs may contain sensitive information; the skill only extracts error/traceback lines and does not display full logs

## Regional Considerations

- The policy applies to all regions (resource pattern uses `*:*:*`)
- Ensure the user has access to the specific region where the training jobs are located
- If working with multiple regions, ensure the user has permissions in all target regions
