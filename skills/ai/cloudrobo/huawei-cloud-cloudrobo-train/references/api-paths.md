# API Paths

## Source

All API paths are derived from the **OpenAPI YAML** (`cloudrobo_train/api/model-training.yaml`)
— the authoritative trusted source — and cross-verified against **SDK source code**
(`cloudrobo_train.client`) via `_url()` calls. This is trusted
source #1 per the Huawei Cloud Skill Creator specification. No paths are inferred or guessed.

## Base Path

```text
Service: cloudrobo-service
Base URL: https://cloudrobo.{region}.myhuaweicloud.com
Train-task API root: /v1/training/train-tasks
SimRL API root:      /v1/training/rl-tasks/simulation
```

## Endpoint List — Regular Training Tasks

### Task CRUD

| Operation | Method | Path | SDK Method |
| ----------- | -------- | ------ | ------------ |
| Create task | POST | `/v1/training/train-tasks` | `create_train_task(req)` |
| List tasks | GET | `/v1/training/train-tasks` | `list_train_tasks(**params)` |
| Batch delete tasks | POST | `/v1/training/train-tasks/batch-delete` | `batch_delete_train_tasks(execution_ids)` |
| Show task detail | GET | `/v1/training/train-tasks/{task_id}` | `show_train_task(task_id, **params)` |
| Update task | PATCH | `/v1/training/train-tasks/{task_id}` | `update_train_task(task_id, req)` |
| Count tasks by status | GET | `/v1/training/train-tasks/stats` | `count_train_tasks_by_status(workspace_id, user_id=None)` |

### Task Actions

| Operation | Method | Path | SDK Method |
| ----------- | -------- | ------ | ------------ |
| Stop task | POST | `/v1/training/train-tasks/{task_id}/stop` | `stop_train_task(task_id)` |
| Restart task | POST | `/v1/training/train-tasks/{task_id}/restart` | `restart_train_task(task_id, req=None)` |
| Resume task | POST | `/v1/training/train-tasks/{task_id}/resume` | `resume_train_task(task_id)` |
| Save draft | POST | `/v1/training/train-tasks/draft` | `save_draft(req)` |

### Task Monitoring

| Operation | Method | Path | SDK Method |
| ----------- | -------- | ------ | ------------ |
| List stages | GET | `/v1/training/train-tasks/{task_id}/stages` | `list_train_stages(task_id)` |
| Show resource usage | GET | `/v1/training/train-tasks/{task_id}/resource-usage` | `show_resource_usage(task_id, metric, start, end, **params)` |
| List observations | GET | `/v1/training/train-tasks/{task_id}/observability` | `list_observations(task_id, **params)` |
| Get log signed URL | GET | `/v1/training/train-tasks/{task_id}/observability/signed-url` | `get_log_signed_url(task_id, file_source, file_name, **params)` |
| Get log content | GET | `/v1/training/train-tasks/{task_id}/observability/content` | `get_log_content(task_id, **params)` |
| List events | GET | `/v1/training/train-tasks/{task_id}/events` | `list_events(task_id, start_time, end_time, **params)` |

### Checkpoint Management (train-only)

| Operation | Method | Path | SDK Method |
| ----------- | -------- | ------ | ------------ |
| List checkpoints | GET | `/v1/training/train-tasks/{task_id}/checkpoints` | `list_train_checkpoints(task_id, **params)` |
| Register checkpoint | POST | `/v1/training/train-tasks/{task_id}/checkpoints/register` | `register_train_checkpoint(task_id, req)` |

## Endpoint List — Simulation Reinforcement Learning (SimRL)

### SimRL CRUD

| Operation | Method | Path | SDK Method |
| ----------- | -------- | ------ | ------------ |
| Count tasks by status | GET | `/v1/training/rl-tasks/simulation/stats` | `count_sim_rl_tasks_by_status(workspace_id, user_id=None)` |
| List tasks | GET | `/v1/training/rl-tasks/simulation` | `list_sim_rl_tasks(**params)` |
| Create task | POST | `/v1/training/rl-tasks/simulation` | `create_sim_rl_task(req)` |
| Save draft | POST | `/v1/training/rl-tasks/simulation/draft` | `create_sim_rl_task_draft(req)` |
| Show task | GET | `/v1/training/rl-tasks/simulation/{task_id}` | `show_sim_rl_task(task_id)` |
| Update task | PATCH | `/v1/training/rl-tasks/simulation/{task_id}` | `update_sim_rl_task(task_id, req)` |
| Delete task | DELETE | `/v1/training/rl-tasks/simulation/{task_id}` | `delete_sim_rl_task(task_id)` |

### SimRL Actions

| Operation | Method | Path | SDK Method |
| ----------- | -------- | ------ | ------------ |
| Stop task | POST | `/v1/training/rl-tasks/simulation/{task_id}/stop` | `stop_sim_rl_task(task_id)` |
| Restart task | POST | `/v1/training/rl-tasks/simulation/{task_id}/restart` | `restart_sim_rl_task(task_id, req=None, workspace_id=None, task_detail=None)` |
| Copy/clone task | POST | `/v1/training/rl-tasks/simulation/{task_id}/copy` | `copy_sim_rl_task(task_id, req=None, task_detail=None)` |

### SimRL Monitoring

| Operation | Method | Path | SDK Method |
| ----------- | -------- | ------ | ------------ |
| Show resource usage | GET | `/v1/training/rl-tasks/simulation/{task_id}/resource-usage` | `show_sim_rl_task_resource_usage(task_id, metric, start, end, **params)` |
| List stages | GET | `/v1/training/rl-tasks/simulation/{task_id}/stages` | `list_sim_rl_task_stages(task_id)` |
| List events | GET | `/v1/training/rl-tasks/simulation/{task_id}/events` | `list_sim_rl_task_events(task_id, start_time, end_time, **params)` |
| List observations | GET | `/v1/training/rl-tasks/simulation/{task_id}/observability` | `list_sim_rl_task_observations(task_id, **params)` |
| Get log content | GET | `/v1/training/rl-tasks/simulation/{task_id}/observability/content` | `show_sim_rl_task_observations_content(task_id, **params)` |
| Get log signed URL | GET | `/v1/training/rl-tasks/simulation/{task_id}/observability/signed-url` | `show_sim_rl_task_observations_signed_url(task_id, file_source, file_name, **params)` |

> **Note**: SimRL has no `resume` endpoint. `resume-task` is train-only.

## Query Parameters

### List Tasks

| Parameter | Type | Required | Description |
| ----------- | ------ | ---------- | ------------- |
| `train_mode` | string | No | Training mode filter (MODEL_TUNING/TRAIN_FROM_SCRATCH) |
| `status` | string | No | Status filter (RUNNING/FINISHED/FAILED) |
| `offset` | int | No | Pagination offset |
| `limit` | int | No | Pagination limit |

### Show Task Detail

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string (path) | Yes | Task ID (path parameter) |

### Batch Delete Tasks

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| (body) | JSON | Yes | `{"execution_ids": ["id1", "id2"]}` |

### Count Tasks by Status

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workspace_id` | string | Yes | Workspace ID |
| `user_id` | string | No | User ID filter |

### Show Resource Usage

| Parameter | Type | Required | Description |
| ----------- | ------ | ---------- | ------------- |
| `metric` | string enum | Yes | Metric type (14 values: cpu_util/mem_util/gpu_util/...) |
| `start` | int | Yes | Start timestamp (seconds) |
| `end` | int | Yes | End timestamp (seconds) |
| `worker_index` | int | No | Worker node index |
| `step` | int | No | Sample step |

### Get Log Signed URL

| Parameter | Type | Required | Description |
| ----------- | ------ | ---------- | ------------- |
| `file_source` | string enum | Yes | Log type (8 values: EVALUATE/TRAIN/TRAINING_METRICS/...) |
| `file_name` | string | Yes | Log file name |
| `catalog` | string | No | File directory type: logs/metrics |

### Get Log Content

| Parameter | Type | Required | Description |
| ----------- | ------ | ---------- | ------------- |
| `file_name` | string | No | Log file name |
| `log_name_pre` | string | No | Log file name prefix |
| `work_num` | int | No | Multi-node training node index |
| `catalog` | string | No | File directory type: logs/metrics |
| `start_byte` | int | No | Start byte offset |
| `end_byte` | int | No | End byte offset |
| `offset` | int | No | Pagination offset |
| `limit` | int | No | Pagination limit |

### List Events

| Parameter | Type | Required | Description |
| ----------- | ------ | ---------- | ------------- |
| `start_time` | int | Yes | Start timestamp (**milliseconds**) |
| `end_time` | int | Yes | End timestamp (**milliseconds**) |
| `level` | string | No | Event level: Info/Warning/Error |
| `source` | string | No | Event source: K8S/Job/Task |
| `pattern` | string | No | Content match pattern |
| `offset` | int | No | Pagination offset |
| `limit` | int | No | Pagination limit |
| `order` | string | No | Sort order: DESC/ASC |

### Restart Task

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| (body) | JSON | No | Full TrainTaskDto body; CLI `--config`/`--config-file` provides overrides, SDK `req` param provides full body |

### List Checkpoints

| Parameter | Type | Required | Description |
| ----------- | ------ | ---------- | ------------- |
| `task_id` | string (path) | Yes | Task ID |
| `offset` | int | No | Pagination offset (default 0, max 10000) |
| `limit` | int | No | Page size (default 10, 1-50) |
| `order` | string enum | No | Sort order: DESC/ASC |
| `status` | string enum | No | Registration status: UNREGISTERED/PENDING/PROCESSING/SUCCESS/FAILED/EXPIRED |
| `name` | string | No | Checkpoint name fuzzy search |
| `workspace_id` | string | No | Workspace ID |
| `user_id` | string | No | Creator user ID |

### Register Checkpoint

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | string (path) | Yes | Task ID |
| `save_mode` | string enum | No | NEW_VERSION (default) / NEW_MODEL |
| `checkpoint_name` | string | Yes | Checkpoint name |
| `version_name` | string | No | Version label (NEW_VERSION optional, auto-assigned if omitted) |
| `model_name` | string | No | Model name (NEW_MODEL required) |

## Cross-Package API

### List Algorithms (via AssetClient)

| Operation | Method | Path | SDK Method |
|-----------|--------|------|------------|
| List algorithms | GET | (asset service endpoint) | `AssetClient.list_publication_assets(type="algorithm", ...)` |

**Note:** This calls the `cloudrobo-asset-manager` service, not `cloudrobo-service`. The exact
API path is defined in `cloudrobo_asset.client`.

## Verification

To verify these API paths against the SDK source:

```bash
# Extract all _url() calls from client.py
grep "_url(" $(python -c "import cloudrobo_train.client as m; print(m.__file__)")

# Expected output:
# self._url(self._TASKS)                                    # /v1/training/train-tasks
# self._url("/v1/training/train-tasks/batch-delete")
# self._url("/v1/training/train-tasks/stats")
# self._url(f"/v1/training/train-tasks/{task_id}/resume")
# self._url(f"{self._TASKS}/{task_id}/stop")
# self._url(f"{self._TASKS}/{task_id}/restart")
# self._url(f"{self._TASKS}/draft")
# self._url(f"{self._TASKS}/{task_id}")                     # PATCH update
# self._url(f"/v1/training/train-tasks/{task_id}")           # GET show
# self._url(f"{self._TASKS}/{task_id}/stages")
# self._url(f"{self._TASKS}/{task_id}/resource-usage")
# self._url(f"{self._TASKS}/{task_id}/observability")
# self._url(f"{self._TASKS}/{task_id}/observability/signed-url")
# self._url(f"{self._TASKS}/{task_id}/observability/content")
# self._url(f"{self._TASKS}/{task_id}/events")
# self._url(f"{self._TASKS}/{task_id}/checkpoints")
# self._url(f"{self._TASKS}/{task_id}/checkpoints/register")
# self._url("/v1/training/rl-tasks/simulation/stats")
# self._url(self._SIM)                                       # /v1/training/rl-tasks/simulation
# self._url(f"{self._SIM}/draft")
# self._url(f"{self._SIM}/{task_id}")                        # GET show / PATCH update / DELETE delete
# self._url(f"{self._SIM}/{task_id}/stop")
# self._url(f"{self._SIM}/{task_id}/copy")
# self._url(f"{self._SIM}/{task_id}/restart")
# self._url(f"{self._SIM}/{task_id}/resource-usage")
# self._url(f"{self._SIM}/{task_id}/stages")
# self._url(f"{self._SIM}/{task_id}/events")
# self._url(f"{self._SIM}/{task_id}/observability")
# self._url(f"{self._SIM}/{task_id}/observability/content")
# self._url(f"{self._SIM}/{task_id}/observability/signed-url")
```

Where `self._TASKS = "/v1/training/train-tasks"` and `self._SIM = "/v1/training/rl-tasks/simulation"`.
