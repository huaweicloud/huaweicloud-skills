# Known Issues and Workarounds

> Documented issues encountered during development and testing, with workarounds.

---

## CLI Issues

### 1. Complex Nested Parameters

**Issue**: CreateTrainingJob, CreateAlgorithm, CreateModel, CreateTrainingExperiment, ChangeTrainingExperiment, CreateSaveImageJob require deeply nested parameters that are difficult to pass via CLI flags.

**Workaround**: Use `--cli-jsonInput` with a JSON file:
```bash
hcloud ModelArts CreateTrainingJob --cli-region={region} --cli-jsonInput=/path/to/job.json
```

JSON file must wrap the body in a `{"body": {...}}` envelope:
```json
{
  "body": {
    "metadata": {
      "name": "my-training-job",
      "description": "Training job description"
    },
    "spec": {
      "resource": {
        "flavor_id": "modelarts.vm.cpu.8u",
        "node_count": 1
      }
    },
    "tasks": [
      {
        "role": "worker",
        "task_resource": {
          "flavor_id": "modelarts.vm.cpu.8u",
          "node_count": 1
        },
        "algorithm": {
          "id": "{algorithm_id}"
        }
      }
    ]
  }
}
```

### 2. `--cli-jsonInput` Syntax

**Issue**: Some documentation suggests using `@` prefix for file paths, but hcloud expects a plain file path.

**Workaround**: Use the file path directly without `@` prefix:
```bash
# Correct
hcloud ModelArts CreateTrainingJob --cli-region={region} --cli-jsonInput=/path/to/file.json

# Wrong (will fail)
hcloud ModelArts CreateTrainingJob --cli-region={region} --cli-jsonInput=@/path/to/file.json
```

### 3. Indexed Parameters

**Issue**: Some parameters require indexed format (e.g., `tasks.1.task_resource.node_count`).

**Workaround**: Use dot notation with indices:
```bash
hcloud ModelArts CreateTrainingJob --cli-region={region} \
  --kind=job \
  --metadata.name=my-job \
  --spec.resource.flavor_id=modelarts.vm.cpu.8u \
  --spec.resource.node_count=1
```

For complex indexed params, prefer `--cli-jsonInput`.

---

## API Behavior Issues

### 4. StopTrainingJob State Restrictions

**Issue**: StopTrainingJob can only stop jobs in `creating`, `waiting`, or `running` state. Stopping jobs in other states returns an error.

**Workaround**: Check job status before attempting to stop:
```bash
# Check status first
hcloud ModelArts ShowTrainingJobDetails --cli-region={region} --training_job_id={id}
# Only stop if status is creating/waiting/running
```

### 5. Training Job Logs URL Expiry

**Issue**: `ShowObsUrlOfTrainingJobLogs` returns a temporary OBS URL that expires after approximately 5 minutes.

**Workaround**: Use the URL immediately after retrieval. If expired, call the API again to get a fresh URL.

### 6. Auto Search Trial Early Stop

**Issue**: `ShowAutoSearchTrialEarlyStop` only works on trials that are currently running. Stopping completed or failed trials returns an error.

**Workaround**: Check trial status before attempting early stop.

### 7. CreateModelArtsAgency Idempotency

**Issue**: `CreateModelArtsAgency` may return an error if the agency already exists, but this is not a real failure.

**Workaround**: Treat "already exists" errors as success. The agency is functional regardless.

### 8. ListJobs (v1 API)

**Issue**: `ListJobs` uses the v1 API (`/v1/{project_id}/jobs`) which has different response format from v2 `ListTrainingJobs`.

**Workaround**: Use `ListTrainingJobs` (v2) for new integrations. Only use `ListJobs` for backward compatibility.

---

## SDK Fallback Issues

### 9. SDK Import Path

**Issue**: The SDK module path may vary between SDK versions.

**Workaround**: Verify the correct import path:
```python
# ModelArts v2 SDK
from huaweicloudsdkmodelarts.v2.modelarts_client import ModelArtsClient
from huaweicloudsdkmodelarts.v2.region.modelarts_region import ModelArtsRegion

# ModelArts v1 SDK (for v1 APIs)
from huaweicloudsdkmodelarts.v1.modelarts_client import ModelArtsClient
from huaweicloudsdkmodelarts.v1.region.modelarts_region import ModelArtsRegion
```

### 10. SDK Authentication

**Issue**: SDK requires explicit AK/SK and project_id, while CLI auto-resolves these.

**Workaround**: Read credentials from environment variables:
```python
import os
from huaweicloudsdkcore.auth.credentials import BasicCredentials

credentials = BasicCredentials(
    ak=os.environ.get("HUAWEICLOUD_SDK_AK"),
    sk=os.environ.get("HUAWEICLOUD_SDK_SK"),
    project_id=os.environ.get("HUAWEICLOUD_SDK_PROJECT_ID")
)
```

---

## General Notes

### 11. Region Availability

ModelArts is available in select regions. Verify service availability before using:
- cn-north-4 (Beijing 4)
- cn-north-1 (Beijing 1)
- cn-east-3 (Shanghai 1)
- cn-south-1 (Guangzhou)

### 12. Workspace ID

Most operations accept `--workspace_id` parameter. Use `0` for default workspace. Omit for default behavior.

### 13. Pagination

List operations support `--limit` and `--offset` for pagination. Default limit varies by API (typically 10 or 20). Maximum limit is typically 1000.

### 14. Async Operations

Training job creation is asynchronous. The job status transitions through: `creating` → `waiting` → `running` → `succeeded`/`failed`. Poll `ShowTrainingJobDetails` to monitor progress.


---

## Dedicated Resource Pool Issues

### 15. StopTrainingJob action_type Parameter Values

**Issue**: `StopTrainingJob` parameter `--action_type` does not accept `stop`. Using `stop` returns error:
```
ModelArts.2788: Invalid parameter(action_type must be one of [terminate restart]).
```

**Workaround**: Use `terminate` to stop a job, or `restart` to restart:
```bash
# Correct - terminate a running job
hcloud ModelArts StopTrainingJob --cli-region={region} --training_job_id={id} --action_type=terminate

# Wrong
hcloud ModelArts StopTrainingJob --cli-region={region} --training_job_id={id} --action_type=stop
```

### 16. Dedicated Pool: flavor_id Not Accepted

**Issue**: When creating a training job in a dedicated resource pool, setting `--spec.resource.flavor_id` to the pool's flavor (e.g., `modelarts.vm.cpu.16u64g.d`) returns error:
```
ModelArts.2781: Flavor (modelarts.vm.cpu.16u64g.d) not found.
```

**Root Cause**: Dedicated pool flavors are not registered in the public flavor catalog. The flavor is resolved internally by the pool.

**Workaround**: Only set `--spec.resource.pool_id`, leave `flavor_id` empty. The pool auto-assigns the flavor based on its node pool configuration:
```bash
# Correct - only set pool_id, flavor auto-assigned
hcloud ModelArts CreateTrainingJob --cli-region={region} \
  --kind=job \
  --metadata.name=my-job \
  --algorithm.command="sleep 1000" \
  --algorithm.engine.image_url=dev-custom/pytorch2_7:v3 \
  --spec.resource.pool_id=pool-xxxxx \
  --spec.resource.node_count=1

# Wrong - flavor_id not valid for dedicated pool
hcloud ModelArts CreateTrainingJob --cli-region={region} \
  --spec.resource.flavor_id=modelarts.vm.cpu.16u64g.d \
  --spec.resource.pool_id=pool-xxxxx
```

### 17. UpdateTrainingJob Not a Valid Operation

**Issue**: `UpdateTrainingJob` is not a valid CLI operation. Returns:
```
[USE_ERROR]不支持的operation:UpdateTrainingJob
```

**Workaround**: Use `ChangeTrainingJobDescription` to update job description:
```bash
hcloud ModelArts ChangeTrainingJobDescription --cli-region={region} \
  --training_job_id={id} \
  --description="new description"
```

### 18. CreateModel source_location Format

**Issue**: `CreateModel` parameter `--source_location` does NOT accept `obs://bucket/path/` format. Returns:
```
ModelArts.3037: Parameter source_location: obs://ndy-test/test-model-output/ is invalid.
```

**Workaround**: Use `/bucket/path/` format (without `obs://` prefix):
```bash
# Correct
hcloud ModelArts CreateModel --cli-region={region} \
  --model_name=my-model \
  --model_type=PyTorch \
  --model_version=1.0.0 \
  --source_location=/ndy-test/test-model-output/

# Wrong - obs:// prefix causes ModelArts.3037
hcloud ModelArts CreateModel --cli-region={region} \
  --source_location=obs://ndy-test/test-model-output/
```

### 19. Code Directory Download Path Structure

**Issue**: When using `--algorithm.code_dir=obs://bucket/my-code/`, the code is NOT downloaded to `/home/ma-user/modelarts/user-job-dir/` directly. Instead, the last directory name from the OBS path is preserved as a subdirectory:
```
obs://ndy-test/test-train-code/  →  /home/ma-user/modelarts/user-job-dir/test-train-code/
```

**Workaround**: Include the subdirectory in the command path:
```bash
# Correct - include the OBS directory name in the path
--algorithm.command="python3 /home/ma-user/modelarts/user-job-dir/test-train-code/train.py"

# Wrong - file not found
--algorithm.command="python3 /home/ma-user/modelarts/user-job-dir/train.py"
```

### 20. Custom Image Jobs Require command Parameter

**Issue**: Custom image training jobs (using `engine.image_url`) must include `--algorithm.command`. Using only `--algorithm.boot_file` returns:
```
ModelArts.2806: Custom image jobs engine.image_url and command or engine.engine_name cannot be empty.
```

**Workaround**: Always use `--algorithm.command` for custom image jobs. The `boot_file` parameter is only for built-in engine jobs.

### 21. CLI Command Parameter Quoting Issues

**Issue**: The hcloud CLI has difficulty parsing `--algorithm.command` values that contain spaces or special characters. Errors like `[USE_ERROR]命令中参数的值以'"'结尾时` may occur.

**Workaround**: Use `--cli-jsonInput` with a JSON file for commands containing spaces or special characters:
```json
{
  "body": {
    "algorithm": {
      "command": "python3 /path/to/script.py --arg=value"
    }
  }
}
```

### 22. CreateModel model_type Valid Values

**Issue**: `CreateModel` parameter `--model_type` only accepts specific values.

**Valid values**: `TensorFlow`, `MXNet`, `Caffe`, `Spark_MLlib`, `Scikit_Learn`, `XGBoost`, `Image`, `PyTorch`, `Template`

**Note**: `MindSpore` is NOT a valid value for this parameter.

### 23. CreateSaveImageJob SWR Namespace Requirement

**Issue**: `CreateSaveImageJob` requires a valid SWR (Software Repository for Containers) namespace that the user has access to. Invalid namespace returns:
```
ModelArts.2885: the access of user swr is exception
```

**Workaround**: Ensure the SWR namespace exists and the user has push permissions before calling this API.

### 24. NotifyTrainingJobInformation Parameter Names

**Issue**: The parameter is `--report_type` (not `--notify_type`), and requires value `training-event`. The `--type` parameter is a separate body parameter for the event type.

**Correct usage**:
```bash
hcloud ModelArts NotifyTrainingJobInformation --cli-region={region} \
  --training_job_id={id} \
  --task_id=worker-0 \
  --report_type=training-event \
  --type={event_type}
```

### 25. ChangeAlgorithm metadata.name Required

**Issue**: `ChangeAlgorithm` must include `--metadata.name` parameter, otherwise returns:
```
ModelArts.2788: Invalid parameter
```

**Workaround**: Always include the algorithm name when updating:
```bash
hcloud ModelArts ChangeAlgorithm --cli-region={region} \
  --algorithm_id={id} \
  --metadata.name=my-algorithm \
  --metadata.description="updated description"
```

### 26. CreateSaveImageJob Requires Running Job

**Issue**: `CreateSaveImageJob` only works on training jobs in `running` state. Calling it on a completed job returns:
```
ModelArts.2883: training job secondary_phase is not running
```

**Workaround**: Create a long-running training job (e.g., `command: "sleep 600"`), wait until it reaches `Running/Running` status, then call `CreateSaveImageJob`. The `ShowSaveImageJob` API uses `training_job_id` + `task_id` (no separate save_image_job_id needed):
```bash
# 1. Create long-running job
# 2. Wait until Running/Running
# 3. Save image
hcloud ModelArts CreateSaveImageJob --cli-region={region} \
  --training_job_id={id} --task_id=worker-0 \
  --name=my-image --namespace={swr_namespace} --tag=v1

# 4. Query save status
hcloud ModelArts ShowSaveImageJob --cli-region={region} \
  --training_job_id={id} --task_id=worker-0
# Returns: status=ACTIVE, message="BuildImage,True,Commit successfully|PushImage,True,Push successfully"
```

### 27. CreateAlgorithm OBS Code Directory Prerequisite

**Issue**: `CreateAlgorithm` requires the OBS code directory (`--job_config.code_dir`) to exist and be accessible. Without this prerequisite, the API returns errors:
- `ModelArts.2773`: OBS code directory not found or not accessible
- `ModelArts.2758`: Code startup file path is invalid
- `ModelArts.2810`: Custom image query failure (invalid `image_url`)

**Workaround**: Before calling `CreateAlgorithm`, ensure the OBS code directory is properly prepared:

1. **Using OBS code directory**: Upload training code to an OBS bucket. The directory must exist and be accessible. `ma_algo_configs/defaultConfigs.json` is optional (provides default algorithm configuration but is not required):
   ```
   obs://{bucket}/{code-dir}/
   ├── train.py
   └── ma_algo_configs/          # optional
       └── defaultConfigs.json   # optional
   ```

2. **Using custom image**: Alternatively, provide a valid SWR image URL via `--job_config.engine.image_url` instead of `code_dir`/`boot_file`.

```bash
# Verify OBS path exists before creating algorithm
hcloud OBS ListObjects --bucket={bucket} --prefix={code-dir}/

# Then create algorithm
hcloud ModelArts CreateAlgorithm --cli-region={region} \
  --cli-jsonInput=/path/to/create-algorithm.json
```
