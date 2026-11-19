> Part of the custom-operator guide. Index: [custom-operator-workflow.md](custom-operator-workflow.md)

### Phase 4: Runtime Verification 运行时验证

After assets are created (把代码打进镜像 / 代码放 OBS 并注册算法资产 — OBS算法 has **no assets** and
enters Phase 4 directly), validate that the operator actually runs by creating a
proc-task (data processing task) with it.

#### Step 4.0: Choose the Dataset Source & Select Input Datasets 选择数据集来源与输入数据集

Input datasets follow the platform's TWO data-source categories — **空间资产-数据**
(workspace data assets, `BUILD_IN_ASSET`) or **OBS存储** (direct `obs://` path,
`UDF_OBS_ASSET`): Source ② (query existing assets) / Source ① (auto-create) under
空间资产-数据, and Source ③ OBS存储 (direct path input) — never fabricated.

**Step 4.0a — 按推荐来源，仅在含糊时问：**

不要把三选一菜单直接甩给用户。套用推荐并说明：

1. 若恰好有一个匹配的已有数据集 → **复用（默认）**。
2. 否则从用户给的数据路径**自动新建**数据集。
3. 仅当用户主动提供 `obs://` 路径、或明确要求不创建资产时，才用 **OBS存储直挂**（`UDF_OBS_ASSET`）。

只有多个数据集都可能且选错代价高时才问。若要问，用用户语言描述结果，不要抛平台标签。

> **OBS存储（③）约束：** 不创建数据资产、无需 `RELEASE`，但数据必须已在该路径就绪，且
> **路径必须位于当前工作空间绑定的 OBS 桶内** —— 对照 `default_obs_path`
> （如 `obs://{default-bucket}/cloudrobo/{workspace_id}/`）；不支持其它 OBS bucket。
> bucket 不一致时展示 `default_obs_path` 并重问。

> **⚠️ 多数据源 → 单任务（两条路线通用，勿拆任务）**：无论来源①/②/③，用户提供的**多个数据源（多个 OBS 路径 / 多个数据集资产）必须合并到 `dataset_configs` 的多个 entry（≤10 个），最后只创建 1 条 proc-task** —— 任务内算子遍历全部数据源（`SOURCE_DATASET_PATH` JSON map 多 entry，entrypoint/main 算子按数据集索引前缀输出）。**禁止**按每个数据源分别调用 `create-task`（除非用户显式要求"批量"：每条数据源一条任务，此时先与你确认拆分为 N 条任务）。收集流程：上一选择点（每轮一问）→「请提供 OBS 路径/选择数据集」→ 完成后单独一问「还需要添加其他数据源吗？① 继续添加 ② 已完成」。把代码打进镜像与代码放 OBS 的行为完全一致（差异仅在算法引用方式，不影响任务条数）。

> **⚠️ 取消/重发必须先处理已创建的任务（两条路线通用）**：`create-task` 成功后任务即真实运行于平台（PENDING→POD_PENDING→RUNNING…，前端可见并可能计费）。此后若用户要求**取消/修改参数后重发**，**必须先与用户确认删除/停止旧任务**（`delete-task --task-id {task_id}`，不可恢复）；用户确认删除前**禁止创建新任务**。务必展示当前任务状态（如「任务 {id} 运行中」）再询问「是否删除/停止旧任务？① 删除（立即终止并计费停止）② 保留运行 ③ 先查看日志」。同理，任务 RUNNING 期间任何"重跑/重建后再跑"都不得遗留原任务自动续跑。

**Source ① — create a NEW dataset from OBS data (auto):**
1. Collect the customer's **OBS data path** — confirm the raw data is already
   uploaded. If the skill uploads a local data directory (a mutation, confirm first),
   **size it first** (`du -sh <dir>` + `find <dir> -type f | wc -l`) and:
   - **≤ 50 files / ≤ 50MB** → serial `OBSClient.upload_folder` is fine;
   - **> 50 files / > 50MB → upload with the DEFAULT script
     `../../scripts/concurrent_shard_upload.py`** (copy it to the target host, edit
     CONFIG `SERVER/BUCKET/PREFIX/SRC`, launch 4 shards × 16 threads; see the OBS
     Upload Guide) — never a serial walk, never a hand-rolled reimplementation.
2. **AUTO-create the dataset asset** (mutations — confirm with the customer first):
   ```bash
   cloudrobo asset create-asset --catalog-id {workspace_catalog_id} \
     --name {unique-dataset-name} --type dataset --ext-metadata '{"annotation_status":true}'
   cloudrobo asset create-version --asset-id {dataset-asset-id} --url "{obs-data-path}"
   cloudrobo asset update-version --asset-id {dataset-asset-id} \
     --version-id {version-id} --status RELEASE
   ```
   - `annotation_status` is **required** for `type=dataset`; unique name (timestamp
     suffix avoids `400 The asset name is existed`); version **MUST be `RELEASE`**
     (CREATING/DRAFT → "dataset not ready")
3. Build the `dataset_configs` entry from the creation results (`obs_path` = customer
   OBS path, `asset_id`, `asset_name` = `--name`, `version_id`); repeat for up to 10
   datasets

**Source ② — reuse an existing workspace dataset:**

```bash
cloudrobo asset list-assets --catalog-id {workspace_catalog_id} --type dataset
```

1. **Customer-specified dataset (highest priority)** → when the customer explicitly
   specifies a dataset asset (by name or asset_id), use it **directly** — **no OBS
   content inspection, no extra confirmation**; take
   `obs_path`/`asset_id`/`asset_name`/`version_id` from the asset query and build
   `dataset_configs` immediately
2. **No dataset found** → remind the user to **upload data first** (or switch to
   Source ① — the skill auto-creates the dataset from the customer OBS path); do not
   proceed with a made-up path
3. **Exactly one dataset** → **use it by default, no confirmation needed**
4. **Multiple datasets** → **MUST enable multi-select in the interaction** — one task
   may process **multiple datasets, up to 10 max**; never restrict the user to a
   single choice; enforce the 10-max limit and ask the customer
   to trim if they select more
5. Each selected asset's `url` (plus `asset_id`/`asset_name`/`version_id` for
   `BUILD_IN_ASSET`) becomes one `dataset_configs` entry

**Source ③ — OBS存储 (platform "OBS storage" option; direct `obs://` path input, no dataset asset):**

```text
- Ask the customer for ONE OR MORE OBS data paths as input (not assets): each must
  start with `obs://`; validate the format only — **no OBS browsing/listing**
  (data-readiness is the customer's responsibility; an empty path keeps the task in
  `POD_PENDING`). Collect them one question per round, then ask "还需要添加其他 OBS
  路径吗？① 继续添加 ② 已完成" before moving on.
- ⚠️ **Workspace-bound bucket constraint (MANDATORY, re-ask until it matches):** the
  path's **bucket MUST equal the workspace-bound OBS bucket** — the bucket of
  `default_obs_path` from `cloudrobo workspace current`
  (e.g. `obs://{default-bucket}/cloudrobo/{workspace_id}/`). **Other OBS buckets are
  NOT supported.** Always show the workspace `default_obs_path` as the reference: 对话话术
  「OBS 路径必须位于当前工作空间绑定的桶 `obs://{default-bucket}/` 下（完整参考路径
  `{default_obs_path}`），不支持其它 OBS 桶。请提供该桶内的数据路径。」 Parse
  `obs://<bucket>/...`, compare `<bucket>` with the `default_obs_path` bucket, **reject
  and re-ask on mismatch** — never submit a task with a foreign-bucket `obs_path`.
- dataset_configs = one entry per path, each `{"obs_path": "<url>", "dataset_type": "UDF_OBS_ASSET"}`
  — ONLY `obs_path` + `dataset_type`; omit `asset_id`/`asset_name`/`version_id` (the
  backend rejects included-but-empty asset fields). **ALL entries go into ONE task's
  `dataset_configs` (≤10 entries); create-task is called exactly ONCE.**
- **No dataset asset is created or referenced — no `create-asset type=dataset` mutation,
  no `RELEASE` step, no dataset-source confirmation beyond the path itself.**
- The entrypoint template treats entries as a multi-dataset run: single entry → flat
  single-dataset output; multiple entries → `{dataset_index}_` prefix, all converted by
  the SAME task (verified: lerobot `main.py` logs "Resolved N datasets from
  SOURCE_DATASET_PATH" with N = number of entries).
- ⛔ NEVER split one multi-source input into several tasks — the observed regression
  "two OBS paths → two tasks" violates the platform contract (one task, N entries).
  Only an explicit user request for per-dataset batch tasks justifies N tasks (confirm first).
```

> **代码放 OBS、运行时挂载 — confirm code upload:** before creating the task, confirm with the
> customer that `entrypoint.py`, `src/`, `requirements.txt` are already uploaded to
> the OBS path (the algorithm asset `code_dir` in 空间资产-算法; = `algo_path` in OBS算法). An
> empty path keeps the task in `POD_PENDING`.

#### Step 4.1: Assemble Task Config 组装任务配置

Map the algorithm asset's fields to `task_config` fields (see the parent
`cloudrobo-dataset` skill's `../task-config-catalog.md` for the full reference):

**把代码打进镜像（WORKSPACE_ASSETS）:**

| Algorithm asset field | task_config field |
|-----------------------|-------------------|
| `asset_id` (algorithm) | `algo_id` |
| `name` | `algo_name` |
| `ext_metadata.command` | `algo_entrance` |
| `ext_metadata.engine.image_url` | `image` |
| workspace `catalog_id` | `catalog_id` |

**代码放 OBS、运行时挂载** — branches by the Phase 0 task-creation way. **`algo_name` is always
required** (the SDK validator requires it for every proc-task):

**空间资产-算法 — use the created algorithm (`WORKSPACE_ASSETS` + `algo_id`):**

| Phase 0 / Phase 3 input | task_config field |
|-------------------------|-------------------|
| Phase 3 algorithm `asset_id` | `algo_id` (**required in 空间资产-算法**, asset linkage) |
| operator name | `algo_name` (**required**) |
| algorithm asset `code_dir` (= customer OBS path) | `algo_path` (**required** — mount source; verified: missing it → `//entrypoint.py` failure) |
| container injection path (or default) | `job_local_path` (**required** — mount path) |
| **literal absolute** entry path, e.g. `python3 /opt/operator/entrypoint.py` | `algo_entrance` (**absolute AND resolved**; relative `python entrypoint.py` fails) |

> **⚠️ `{job_local_path}` in this document is a placeholder for the Agent, never for the platform.**
> The platform does NOT substitute it. `algo_entrance="python3 {job_local_path}/entrypoint.py"`
> fails with `python3: can't open file '.../{job_local_path}/entrypoint.py': [Errno 2]`.
> Always substitute the concrete `job_local_path` value (e.g. `/opt/operator`) before
> `create-task`, and use the same literal in the algorithm asset's `ext_metadata.command`.
>
> **⚠️ Dependencies:** OBS-mounted code does not install `requirements.txt`. The image must
> already contain every imported package (`h5py`, `numpy`, `Pillow`, `lerobot`, …), else the
> task fails with `ModuleNotFoundError`. Pre-check before choosing the OBS-mounted path; if
> missing, build the code into the image with `RUN pip install -r requirements.txt`.
| algorithm asset `ext_metadata.engine.image_url` | `image` (preset SWR URL) |
| workspace `catalog_id` | `catalog_id` |

> **空间资产-算法 (`WORKSPACE_ASSETS`) requires `algo_id` + `algo_name` + `algo_path`
> (= asset `code_dir`) + `job_local_path` + absolute `algo_entrance` + `image`**
> — the `algo_id` carries the asset linkage; the runtime still mounts `algo_path`
> exactly like `OBS_ASSETS`. The algorithm asset's `engine.asset_id` +
> `engine.asset_version_id` link it to the created image asset (空间资产-镜像).
> Requires `image_source=custom` plus both linkage fields.

**OBS算法 — mount the OBS code directly (`OBS_ASSETS`, no `algo_id`):**

| Phase 0 input | task_config field |
|---------------|-------------------|
| operator name | `algo_name` (**required**) |
| customer OBS path (= `code_dir`) | `algo_path` |
| container injection path (or default) | `job_local_path` |
| **absolute path** `python3 {job_local_path}/entrypoint.py` | `algo_entrance` (**absolute**; relative `python entrypoint.py` → `stdbuf` Permission denied) |
| preset runtime image | `image` |
| workspace `catalog_id` | `catalog_id` |

> **OBS算法 (`OBS_ASSETS`) requires `algo_name` + `algo_path` + `job_local_path`**
> (SDK validator), with **no `algo_id`**.

Values marked *(confirm)* are **defaults to confirm with the user**, not hardcoded:

```json
// 把代码打进镜像
{
  "algo_type": "WORKSPACE_ASSETS",
  "algo_id": "<algorithm_asset_id>",
  "algo_name": "<operator-name>",
  "algo_entrance": "python entrypoint.py",
  "image": "swr.{region}.myhuaweicloud.com/{ns}/{operator-name}:{tag}",
  "catalog_id": "<workspace catalog_id>",
  "resource_pool_type": "PUBLIC_POOL",
  "cluster_type": "CCE",
  "task_framework_type": "K8S",
  "dataset_configs": "[{\"obs_path\":\"<selected dataset url 1>\",\"dataset_type\":\"BUILD_IN_ASSET\",\"asset_id\":\"<dataset asset id 1>\",\"asset_name\":\"<dataset asset name 1>\",\"version_id\":\"<version id 1>\"},{\"obs_path\":\"<selected dataset url 2>\",...}]",
  "output_type": "BUILD_IN_ASSET",
  "output_path": "<user-provided obs:// path>",
  "output_name": "<user-confirmed unique output name>",
  "head_spec": {"cpu": 0, "memory": 0, "gpu": 0, "npu": 0},
  "worker_spec": "<user-confirmed cpu/memory/gpu/npu>",
  "worker_num": "<user-confirmed worker count>",
  "evs_spec": "<user-confirmed evs spec>"
}

// 代码放 OBS、运行时挂载 — 空间资产-算法: use the created algorithm (WORKSPACE_ASSETS + algo_id = Phase 3
// asset_id; algo_id = asset linkage). algo_path (= asset code_dir) + job_local_path
// are REQUIRED (verified — omitting them fails with //entrypoint.py no such file).
// algo_entrance MUST be ABSOLUTE python3 {job_local_path}/entrypoint.py.
{
  "algo_type": "WORKSPACE_ASSETS",
  "algo_id": "<algorithm_asset_id>",
  "algo_name": "<operator-name>",
  "algo_path": "obs://<workspace-bucket>/<path>/<operator-name>/",
  "job_local_path": "/tmp/cloudrobo/<operator-name>",
  "algo_entrance": "python3 /tmp/cloudrobo/<operator-name>/entrypoint.py",
  "image": "swr.{region}.myhuaweicloud.com/{ns}/{preset-image}:{tag}",
  "catalog_id": "<workspace catalog_id>",
  "resource_pool_type": "PUBLIC_POOL",
  "cluster_type": "CCE",
  "task_framework_type": "K8S",
  "dataset_configs": "[{\"obs_path\":\"<selected dataset url 1>\",\"dataset_type\":\"BUILD_IN_ASSET\",\"asset_id\":\"<dataset asset id 1>\",\"asset_name\":\"<dataset asset name 1>\",\"version_id\":\"<version id 1>\"}]",
  "output_type": "BUILD_IN_ASSET",
  "output_path": "<user-provided obs:// path>",
  "output_name": "<user-confirmed unique output name>",
  "head_spec": {"cpu": 0, "memory": 0, "gpu": 0, "npu": 0},
  "worker_spec": "<user-confirmed cpu/memory/gpu/npu>",
  "worker_num": "<user-confirmed worker count>",
  "evs_spec": "<user-confirmed evs spec>"
}

// 代码放 OBS、运行时挂载 — OBS算法: mount the OBS code directly (OBS_ASSETS, NO algo_id)
{
  "algo_type": "OBS_ASSETS",
  "algo_name": "<operator-name>",
  "algo_path": "obs://<workspace-bucket>/<path>/<operator-name>/",
  "job_local_path": "/tmp/cloudrobo/<operator-name>",
  "algo_entrance": "python3 /tmp/cloudrobo/<operator-name>/entrypoint.py",
  "image": "swr.{region}.myhuaweicloud.com/{ns}/{preset-image}:{tag}",
  "catalog_id": "<workspace catalog_id>",
  "resource_pool_type": "PUBLIC_POOL",
  "cluster_type": "CCE",
  "task_framework_type": "K8S",
  "dataset_configs": "[{\"obs_path\":\"<selected dataset url 1>\",\"dataset_type\":\"BUILD_IN_ASSET\",\"asset_id\":\"<dataset asset id 1>\",\"asset_name\":\"<dataset asset name 1>\",\"version_id\":\"<version id 1>\"}]",
  "output_type": "BUILD_IN_ASSET",
  "output_path": "<user-provided obs:// path>",
  "output_name": "<user-confirmed unique output name>",
  "head_spec": {"cpu": 0, "memory": 0, "gpu": 0, "npu": 0},
  "worker_spec": "<user-confirmed cpu/memory/gpu/npu>",
  "worker_num": "<user-confirmed worker count>",
  "evs_spec": "<user-confirmed evs spec>"
}
```

> **Parameters confirmed with the user (no hardcoding):** `resource_pool_type`
> (`DEDICATED_POOL` needs `resource_id`), `worker_spec`, `worker_num`, `evs_spec`,
> `output_name` (unique per run), `output_path`, and the **input-dataset source**
> (① create a NEW dataset from OBS data — auto create-asset `type=dataset` +
> create-version + `update-version --status RELEASE`; or ② reuse an existing
> dataset). 代码放 OBS 并直接挂载 also confirms `algo_path`
> (customer OBS path, must be under workspace `default_obs_path`) and
> `job_local_path` (default `/tmp/cloudrobo/{operator-name}`); 空间资产-算法 needs only the
> asset's `code_dir` (Phase 3). This skill performs
> **no OBS data browsing** — `dataset_configs.obs_path` comes from the selected
> dataset asset(s) (Source ②) or the customer-provided OBS data path bound via
> `create-version` (Source ①), `output_path` is user-provided, and the
> customer uploads 代码放 OBS、运行时挂载 algorithm code themselves.

> **⚠️ Key constraints:**
> - `output_name` must be **unique per run** — duplicates return
>   `400 The asset name is existed`
> - **空间资产-算法 (`WORKSPACE_ASSETS`)** requires `algo_id` (= Phase 3 algorithm
>   `asset_id`) + `algo_name` + `algo_path` (= asset `code_dir`) + `job_local_path` +
>   absolute `algo_entrance` + `image` (omitting `algo_path`/`job_local_path`
>   fails with `//entrypoint.py` no such file). **OBS算法 (`OBS_ASSETS`)**
>   requires `algo_name` + `algo_path` + `job_local_path`, **no `algo_id`** (do not
>   pass an empty/placeholder `algo_id` — either a real UUID or omit the field)
> - `envs` (from `ext_metadata.environment_variables`) must be a **non-empty JSON
>   string array**; omit the field entirely when there are no env vars — an empty
>   `"envs": "[]"` is rejected with `400 Invalid parameter: worker_spec`
> - `head_spec`/`worker_spec` must contain `cpu` and `memory` (add `gpu`/`npu` as
>   `0` when unused; the SDK validates only `cpu`/`memory`)
> - `dataset_configs` must contain at least one dataset — one entry per selected
>   dataset, using each selected dataset asset's `url` as `obs_path` (query via
>   `cloudrobo asset list-assets --type dataset`; multiple datasets are supported)

> **⚠️ Assemble task-config with Python, never by hand-escaping in bash.**
> `dataset_configs` is a **JSON-string-inside-JSON-string** (`"[{...}]"`), so shell
> `\"` escapes are error-prone — a broken escape yields an invalid task-config that
> `--dry-run` does NOT catch (it only fails at real submission). Recommended
> construction (verified pattern):
> ```python
> import json, time
> # task_way = "2" | "3"  — from the Phase 0 decision (default "2")
> # Both ways need algo_path + job_local_path + ABSOLUTE algo_entrance (verified).
> # 空间资产-算法: WORKSPACE_ASSETS + algo_id (asset linkage, algo_path = asset code_dir)
> # OBS算法: OBS_ASSETS, no algo_id
> task_config = {
>     "algo_name": "<operator-name>",
>     "algo_path": "obs://<workspace-bucket>/<path>/<operator-name>/",
>     "job_local_path": "/tmp/cloudrobo/<operator-name>",
>     "algo_entrance": "python3 /tmp/cloudrobo/<operator-name>/entrypoint.py",
>     "image": "swr.<region>.myhuaweicloud.com/<ns>/<preset-image>:<tag>",
>     "catalog_id": "<workspace catalog_id>",
>     "resource_pool_type": "PUBLIC_POOL",
>     "cluster_type": "CCE",
>     "task_framework_type": "K8S",
>     # dataset_configs is a STRING containing a JSON array — use json.dumps
>     # BUILD_IN_ASSET (Source ①/②): full entry with asset linkage fields
>     "dataset_configs": json.dumps([{
>         "obs_path": "<dataset url 1>", "dataset_type": "BUILD_IN_ASSET",
>         "asset_id": "<dataset asset id 1>", "asset_name": "<dataset name 1>",
>         "version_id": "<dataset version id 1>",
>     }]),
>     # UDF_OBS_ASSET (Source ③ = platform "OBS存储", direct path, no dataset asset):
>     #   {"obs_path": "obs://<bucket>/<path>/", "dataset_type": "UDF_OBS_ASSET"}
>     #   — ONLY these two keys; do NOT include asset_id/asset_name/version_id (even
>     #   empty strings are rejected by the backend).
>     "output_type": "BUILD_IN_ASSET",
>     "output_path": "obs://<bucket>/<output-path>",
>     "output_name": f"operator-output-{time.strftime('%Y%m%d%H%M%S')}",
>     "head_spec": {"cpu": 0, "memory": 0, "gpu": 0, "npu": 0},
>     "worker_spec": {"cpu": 4, "memory": 8, "gpu": 0, "npu": 0},
>     "worker_num": 1, "evs_spec": 0,
> }
> if task_way == "2":
>     task_config["algo_type"] = "WORKSPACE_ASSETS"
>     task_config["algo_id"] = "<algorithm_asset_id>"   # 空间资产-算法: reference the created algorithm asset
> else:
>     task_config["algo_type"] = "OBS_ASSETS"
> # ⚠️ MULTIPLE data sources → ONE task: dataset_configs holds ALL entries (≤10) in the
> #    single array above; create-task is called exactly once (never loop it per dataset).
> #    The operator receives "Resolved N datasets" from the platform-injected JSON map.
> json.dump(task_config, open("/tmp/task_config.json", "w"))
> # validate + pass to CLI:
> #   python3 -c "import json; json.load(open('/tmp/task_config.json'))"
> #   cloudrobo dataset proc create-task --name <task-name> \
> #     --algo-type {WORKSPACE_ASSETS|OBS_ASSETS} \
> #     --task-config "$(cat /tmp/task_config.json)"   # NO --wait — poll instead (see Step 4.2)
> ```
>
> **⚠️ `envs` must not contain platform-injected variables (verified, 把代码打进镜像端到端验证):**
> `SOURCE_DATASET_PATH` is injected by the platform at runtime (input declared with
> `access_method=env`). Building `envs` from `ext_metadata.environment_variables` and
> keeping `SOURCE_DATASET_PATH` with its fallback `default` (e.g. `/tmp/source/dataset`)
> makes the container read that **literal placeholder instead of the injected JSON
> map**, so the operator fails immediately with:
> ```
> SOURCE_DATASET_PATH is not a valid JSON map.
> ERROR - Error during data conversion INPUT environment variable is not set
> ```
> **Fix pattern:** filter `envs` to drop `SOURCE_DATASET_PATH` (and any other
> `access_method=env` input port); keep only business variables such as `UMI_PLATFORM`:
> ```python
> envs = [{"key": "UMI_PLATFORM", "value": "pika",
>          "description": "UMI data source platform adapter"}]
> if envs:
>     task_config["envs"] = json.dumps(envs)
> ```

#### Step 4.2: Create the Task 创建任务（创建后轮询）

**⚠️ Do NOT use `--wait --timeout`** — create WITHOUT `--wait`, then poll
`show-task` every 20–30 s with a progress heartbeat until `SUCCEEDED`/`FAILED`
(see [Progress Feedback](progress-feedback.md) §Task Creation).

把代码打进镜像路线：
```bash
cloudrobo dataset proc create-task --name <task-name> \
  --algo-type WORKSPACE_ASSETS --task-config "$(cat /tmp/task_config.json)"
```

代码放 OBS、运行时挂载 — 空间资产-算法 uses `WORKSPACE_ASSETS` (algo_id = Phase 3 asset id); OBS算法 uses
`OBS_ASSETS` (algo_path + job_local_path, no algo_id). The CLI `--algo-type` must
match the assembled task-config's `algo_type`:
```bash
cloudrobo dataset proc create-task --name <task-name> \
  --algo-type {WORKSPACE_ASSETS|OBS_ASSETS} --task-config "$(cat /tmp/task_config.json)"
```

- `task_id` is returned in `payload.id` (not a top-level `id`)
- Poll with a heartbeat: `cloudrobo dataset proc show-task --task-id <task_id>`
  every 20–30 s; report status (`PENDING` / `POD_PENDING` / `RUNNING` /
  `SUCCEEDED` / `FAILED`) + elapsed to the customer — the loop is extracted to
  **`../../scripts/poll-task.sh`**:
  ```bash
  bash ../../scripts/poll-task.sh <task_id> 120 30
  # 对话话术：「任务当前状态 {STATUS}（PENDING=排队 / POD_PENDING=创建节点拉镜像 /
  # RUNNING=运行中，转换类任务可能持续 10–40 分钟），已等待 {elapsed} 分钟，请稍候。」
  ```
- On `FAILED` → Step 4.4 (failure analysis). On `SUCCEEDED` → Step 4.3 (verify).

#### Step 4.3: Verify Success 验证成功

```bash
cloudrobo dataset proc get-log --task-id <task_id> --file-name job-std-output.log
# --prefix is REQUIRED: use the output path minus the bucket (obs://<bucket>/)
cloudrobo dataset proc get-frames --task-id <task_id> --prefix <output-path-minus-bucket>
```

**Success criteria:**
- Task status = `SUCCEEDED`
- User log shows `[DONE] Processed N items, success N, failed 0` (the legacy Chinese
  form `[DONE] 共处理 N 项，成功 N，失败 0` also counts as success)
- Output frames list is non-empty

#### Step 4.4: On Failure 失败处理

If the task reaches `FAILED`, fetch `job-std-output.log` and run the failure analysis
engine (see [Failure Analysis Guide](failure-analysis-guide.md)):

```bash
cloudrobo dataset proc get-log --task-id <task_id> --file-name job-std-output.log
```

Apply the suggested fix (e.g., add a dependency to `requirements.txt`, fix the output
directory, fix `process()`). **把代码打进镜像**: rebuild the image (Phase 2), re-push, then
**take the RE-SUBMISSION asset branch** (Phase 3 Step 3.2 — `create-version` +
`update-asset`; never re-run Step 3.1's `create-asset`). **代码放 OBS、运行时挂载**: the customer
updates the code on OBS (OBS算法 — then re-run Phase 4; 空间资产-算法
— also `update-asset` the algorithm `code_dir` if the path changed), no image rebuild.

> **⚠️ Before re-creating the task after a rebuild:**
> 1. Re-query the algorithm asset (`asset show-asset`) and confirm
>    `engine.image_url` / `engine.asset_version_id` point at the **new** image version
>    (a stale linkage is the #1 cause of an HTTP 500 on the re-run `create-task`).
> 2. Use a **fresh `output_name`** (timestamp suffix — never reuse the failed run's;
>    the failed run's pre-registered `BUILD_IN_ASSET` output asset is stuck `DRAFT`).
> 3. If `create-task` still returns **HTTP 500**: wait ~30 s and retry **once** (the
>    backend may be re-indexing the just-updated algorithm asset); still 500 → capture
>    `trace_id` + system log and hand off to platform support.
> 4. Every re-run must also re-validate the input dataset (`RELEASE` for Source ①/②;
>    Source ③: path unchanged). See [Failure Analysis Guide](failure-analysis-guide.md) → HTTP 500 pattern.

#### Common Issues 常见问题

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| No dataset in workspace | Workspace has no dataset asset | **Remind the user to upload data first** — offer **Source ①** (the skill auto-creates the dataset from the customer OBS path) or see the parent `cloudrobo-dataset` skill; do not fabricate a path |
| Dataset source not chosen | Phase 4 started without the choice | **Ask the customer: ① 空间资产-数据-新建 (auto create dataset asset), ② 空间资产-数据-复用已有资产, or ③ OBS存储 (direct `obs://` path, `UDF_OBS_ASSET`, no dataset asset)?** — re-ask until unambiguous |
| Multiple data sources split into N tasks (should be ONE) | Two or more OBS paths / datasets each got its own `create-task` (把代码打进镜像与代码放 OBS 两种情况 both affected) | **Root cause**: the agent looped `create-task` per data source instead of assembling one `dataset_configs` array. **Fix**: collect all sources (multi-select ≤10), build ONE task-config with N `dataset_configs` entries, call `create-task` exactly once; operator processes all N (lerobot logs "Resolved N datasets"). Split into per-dataset tasks ONLY when the user explicitly asks for batch mode (confirm the N-task split first) |
| 取消后旧任务残留运行（重发后出现双任务/前端仍"执行中"） | 用户在任务执行中要求"取消/改参数重开"，Agent 直接创建新任务，未删除旧任务 | **Root cause**: 交互层「取消与恢复」未覆盖 Phase 4 已创建任务的处理——旧任务继续在平台运行。**Fix**: 任何取消/重发前必问「是否删除/停止旧任务 {id}（①删除 ②保留 ③查看日志）」；确认删除后 `delete-task` + `show-task` 验证 `DELETED`，再创建新任务（见边界 4.11 / S12） |
| Source ①: `400 The asset name is existed` | Dataset name already used in the catalog | Use a unique per-run name (timestamp suffix, e.g. `{operator-name}-input-{YYYYMMDDHHMMSS}`) or ask the customer |
| Source ①: task reports "dataset not ready" | Dataset version left in `CREATING`/`DRAFT` | **Publish `RELEASE`**: `cloudrobo asset update-version --asset-id <id> --version-id <vid> --status RELEASE` |
| Source ①: task stuck in `POD_PENDING` | The OBS data path is empty (data not uploaded) | **Remind the customer to upload the raw data files to the OBS path first**; terminate and re-run |
| Multiple datasets in workspace | One task may process several datasets | **Ask the user to multi-select (max 10)**; one `dataset_configs` entry per selected dataset (when exactly one exists, use it by default) |
| 代码放 OBS、运行时挂载 task rejected (missing `algo_name`) | SDK validator requires `algo_name` for every proc-task | Add `algo_name` (空间资产-算法: `WORKSPACE_ASSETS` needs `algo_id` + `algo_name` + `algo_entrance` + `image`; OBS算法: `OBS_ASSETS` needs `algo_name` + `algo_path` + `job_local_path`) |
| 代码放 OBS、运行时挂载 task rejected (OBS算法: missing `algo_path`/`job_local_path`) | SDK validator forces `algo_path` + `job_local_path` for `OBS_ASSETS` | Fill `algo_path` (customer OBS path) + `job_local_path` — never pass a placeholder `algo_id` with `OBS_ASSETS` |
| 代码放 OBS、运行时挂载 task failed with `//entrypoint.py` (空间资产-算法) | `WORKSPACE_ASSETS` missing `algo_path` (mount source) and/or `job_local_path` — runtime mounts empty and runs from `/` | Set `algo_path` = the algorithm asset `code_dir` + `job_local_path` + **absolute** `algo_entrance` (`python3 {job_local_path}/entrypoint.py`) |
| 代码放 OBS、运行时挂载 task rejected (空间资产-算法: missing `algo_id`) | `WORKSPACE_ASSETS` requires `algo_id` | Set `algo_id` = the Phase 3 algorithm `asset_id` |
| 代码放 OBS、运行时挂载 task stuck in `POD_PENDING` | OBS code path empty (code not uploaded) — OBS算法: direct OBS path; 空间资产-算法: the algorithm asset `code_dir` | **Remind the customer to upload `entrypoint.py` / `src/` / `requirements.txt` to the OBS path first** (空间资产-算法: also verify via `show-asset` that the algorithm `code_dir` points to the populated path); terminate and re-run |
| `400 The asset name is existed` | `output_name` already used by an earlier run | Use a unique per-run `output_name` (e.g. timestamp suffix) |
| `400 Invalid parameter: worker_spec` | `envs` passed as an empty array `"[]"` | Omit `envs` entirely (or pass a non-empty array) |
| `SOURCE_DATASET_PATH is not a valid JSON map` + `INPUT environment variable is not set` | `envs` in task-config includes `SOURCE_DATASET_PATH` with its **fallback `default`** (e.g. `/tmp/source/dataset`), which **overrides/blocks the platform runtime injection** (input is `access_method=env`) | Re-create the task with `envs` that **exclude `SOURCE_DATASET_PATH`** (drop the entry; keep only business vars such as `UMI_PLATFORM`); no image rebuild needed |
| Task stuck in PENDING/RUNNING | Insufficient `worker_spec` resources or image pull error | Check `show-task` and system logs; adjust `worker_spec` with the user |
| `SUCCEEDED` but no output frames | entrypoint wrote into the read-only input path | 把输出写到 `TARGET_DATASET_PATH` / `/output`；把代码打进镜像路线则重建并重新推送；代码放 OBS 路线则由客户更新 OBS 上的代码（不注册资产时），或 `update-asset` 更新算法资产的 `code_dir`（注册资产时） |
| `[DONE] ... 失败 N > 0` | `process()` raised for some items | Inspect per-item traceback in the log; fix `process()` |
| 代码放 OBS 路线：`No module named 'ray'` / other missing deps | `algo_entrance` resolved to the **system** `/usr/bin/python3` (platform PATH has no bundled env) | Use an absolute interpreter path (e.g. `/opt/cloud/3rdComponent/python/bin/python3 {job_local_path}/entrypoint.py`) **after** fixing the preset image permissions (see [deploy-mode-comparison.md](deploy-mode-comparison.md) lessons) |
| 代码放 OBS 路线：`stdbuf: failed to run command '<abs-python>': Permission denied` | Platform runs `algo_entrance` as a non-root user; the bundled env lives under a 750 dir (`/opt/cloud/3rdComponent`) | Fix the preset image once: `chmod o+rx /opt/cloud` + `chmod -R o+rX /opt/cloud/3rdComponent`, rebuild/push, update assets |
| 代码放 OBS 路线：`No usable temporary directory found in ['/tmp', ...]` | Platform mounts `/tmp` read-only (OBS code mount under `/tmp/cloudrobo`) | Generated entrypoint redirects `TMPDIR` to `TARGET_DATASET_PATH/.cloudrobo-tmp` (already in `../../templates/entrypoint.py`); re-upload entrypoint to OBS and re-run |
| Re-run `create-task` returns **HTTP 500** after a 把代码打进镜像后的重建 | Algorithm asset still references the **old** image version (`engine.image_url`/`engine.asset_version_id` stale after `create-version`/`update-asset` was skipped or mis-run as first-submission), or the failed run's pre-registered `BUILD_IN_ASSET` output asset is stuck `DRAFT`/`CREATING`, or the backend is momentarily re-indexing the just-updated asset | 1) `show-asset` the algorithm asset: verify it points at the **new** image version (re-run Phase 3 Step 3.2 if not, **never** re-`create-asset`); 2) use a **fresh** `output_name` (timestamp suffix) — do not reuse the failed run's; 3) wait ~30 s and retry once; 4) still 500 → capture `trace_id` + system log, contact support |
| Output dataset contains an empty `.cloudrobo-tmp` folder | The old generated entrypoint unconditionally created `TARGET_DATASET_PATH/.cloudrobo-tmp` and set `TMPDIR` there, even when the operator never used temp files | Regenerate `entrypoint.py` from `../../templates/entrypoint.py` (v: prefers writable system `/tmp`; only falls back to the output dir when `/tmp` is read-only, and removes the fallback dir at exit); 把代码打进镜像后的重建, 代码放 OBS、运行时挂载 re-upload the entrypoint to OBS |
| Single-dataset output is nested under a `{output_name}`-named folder instead of flat | The operator (or an old entrypoint) wrote into `OUTPUT_DIR/<output_name>/` — `output_name` typically matches the dataset asset name (e.g. `lerobot-output-20261021181446`) | Output must be written **flat into `OUTPUT_DIR` root** (`TARGET_DATASET_PATH`) for single-dataset runs; multi-dataset runs use a `{dataset_index}_` prefix only, still no `{output_name}` subfolder. Fix the operator's output dir handling / regenerate the entrypoint |

#### 代码放 OBS、运行时挂载 OBS Code Readiness Check OBS代码就绪检查

> **Applies to OBS算法 (direct OBS mount).** In 空间资产-算法 (use the created algorithm)
> the same check applies to the **algorithm asset's `code_dir`** (the OBS path is
> populated before Phase 3; verify via `show-asset` when the task stays in
> `POD_PENDING`). The diagnostic task below always runs as a OBS算法 task-config.

Before creating a 代码放 OBS、运行时挂载 task, verify the code reached the OBS path (code delivery is
a **small** upload — serial `upload_folder` suffices; the concurrent sharded template
in [OBS Upload Guide](obs-upload-guide.md) applies to large datasets only):

1. **Prefer direct OBS listing** (when the OBS endpoint is resolvable — else ask the
   customer for a reachable one, e.g. `obs.cn-southwest-2.myhuaweicloud.com`):
   ```python
   from cloudrobo_core.sdk.obs_client import OBSClient
   from cloudrobo_core.sdk import Config
   cfg = Config()
   # cfg.endpoints['cloudrobo-obs'] = '<reachable-obs-endpoint>'
   obs = OBSClient(cfg, bucket_name='<workspace-bucket>')
   objs = obs.list_objects(prefix='<obs-prefix-of-algo_path>', bucket_name='<workspace-bucket>')
   # expect entrypoint.py, src/user_operator.py, requirements.txt
   ```
2. **Fallback — diagnostic task** (when OBS cannot be listed directly): a short
   `algo_entrance` prints the mount directory:
   ```json
   // diagnostic task-config
   { "algo_type": "OBS_ASSETS", "algo_name": "<operator-name>",
     "algo_path": "<customer OBS path>", "job_local_path": "/tmp/cloudrobo/<operator-name>",
     "algo_entrance": "python3 -c \"import os;print(sorted(os.listdir('/tmp/cloudrobo/<operator-name>')))\"",
     "image": "<preset image>", "catalog_id": "<catalog_id>",
     "dataset_configs": "[...]", "output_type": "BUILD_IN_ASSET",
     "output_path": "<obs://...>", "output_name": "<unique>", ... }
   ```

Expected mount content: `entrypoint.py`, `src/` (with `user_operator.py`),
`requirements.txt`, `operator_config.yaml`. Missing `src/user_operator.py` or a stale
entrypoint explains import failures — ask the customer to re-upload (or the skill
re-uploads if the customer chose skill upload).
