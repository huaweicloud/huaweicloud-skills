# Edge Cases 边界场景速查

> 完整边界场景表。主 SKILL.md 仅保留高频硬规则；本文件供异常/边缘场景按需加载。

| Scenario | Handling |
|----------|----------|
| Missing `workspace_id` | Run `cloudrobo workspace use` or use `--workspace-id` |
| Task in non-terminal state | `wait-task` polls until SUCCEEDED/FAILED/DELETED or timeout |
| Log file not found | Falls back to `system-std-output.log` / `job-std-output.log` |
| Large log file | Default 64KB tail; use `--all` or `download-log` |
| Task creation fails | Check algo_type, JSON validity, dataset_configs, resource quota |
| AK/SK not set | Set `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` |
| Algorithm not found | Use `--name` fuzzy search or `--tags` filter |
| eval-task delete | Single delete only; no batch |
| Re-run a task | `copy-task` (neither proc nor eval supports restart) |
| Task events | `get-events --task-id <id> --job-name <name>` (proc/eval) |
| Pipeline input | For eval, set top-level `dataset_path` = proc `target_path` |
| Evaluation report link | OBS temp URL; save/download promptly |
| `envs` format | JSON array string, not object; see `task-config-catalog.md` |
| `catalog_id` mismatch | Use workspace's, not algorithm's |
| `list-assets` params | Provide `--catalog-id` or `--repository-id`; get from `cloudrobo workspace current` |
| Algorithm source | Built-in: `list-publication-assets`; custom: onboard via [Custom Operator Onboarding](../SKILL.md#custom-operator-onboarding) |
| `dataset_configs` | Use asset's `url` field; don't manually concatenate |
| Log query | Get file list first for `file_path`, then fetch content |
| Task deletion | Irreversible |
| Algorithm fields | Extract from `ext_metadata`; don't fabricate |
| Missing optional fields | Skip if no `environment_variables`; use defaults for `worker_spec`; never send the removed `robot_config` (config files are mounted via `inputs`). An outdated client that still requires it must be upgraded, never given a fabricated path |
| Advanced resources | DEDICATED_POOL: query for IDs; Ray: pair cluster/framework types, non-zero head_spec |
| Operator deploy mode | **Default: 代码放 OBS、运行时挂载** — state it in one line and continue; ask only when dependencies clearly exceed the preset runtime or the user asks for a custom image. "都可以/你看着办" → keep the default, do not re-ask (see [Custom Operator Onboarding](../SKILL.md#custom-operator-onboarding)) |
| Operator 代码放 OBS、运行时挂载 task-creation way | **Default: 注册成空间里的算法资产后引用** (`WORKSPACE_ASSETS` + `algo_id` = Phase 3 asset id). Use 不注册资产、直接挂载 OBS 代码 (`OBS_ASSETS`, no `algo_id`, **Phase 3 skipped**) only when the user explicitly asks for it |
| Operator dataset source | **Default: reuse a matching dataset asset; if none, auto-create one** (`BUILD_IN_ASSET`). Use ③ OBS存储（直接输入 `obs://` 路径，`UDF_OBS_ASSET`，不创建、不引用数据资产）only when the user supplies an `obs://` path; ask when several datasets are plausible and a wrong pick is costly (multi-select max 10). ② none → remind upload or switch to ①/③; ③ format-validate `obs://` + **bucket must equal the workspace-bound bucket (`default_obs_path` bucket from `cloudrobo workspace current`) — other OBS buckets NOT supported; show `default_obs_path` as reference, mismatch → reject & re-ask**, data must be ready at the path. **多数据源（≤10）→ 仅 1 条任务**：全部 entry 并入单个 `dataset_configs` 数组，单次 `create-task`；禁止按数据源拆任务（批量拆分仅限用户显式要求且已确认） |
| Operator cancel/re-issue | Task already created (`create-task` returned an id) then user cancels or re-runs with changed params — **must first confirm deleting/stopping the old task**: show `{task_id}` (running) → ask "① 删除（不可恢复）② 保留 ③ 查看日志" → on ① run `delete-task` + verify `DELETED` via `show-task`; **never create a new task before the old one is handled** (boundary 4.11 / S12) |
| Operator boundary | Chained evaluation only (proc→eval); **standalone simulation evaluation → `huawei-cloud-cloudrobo-eval`**; multi-stage data-cleaning pipelines → `huawei-cloud-cloudrobo-data-pipeline`; do not create/chain eval tasks outside this scope |
| Operator asset naming | Image + algorithm assets MUST be created with the operator name confirmed in the dialogue (no silent rename / auto suffix); verify via `show-asset` — mismatch → stop and re-confirm |
| Operator re-run 500 | 把代码打进镜像后的重建 → re-submission branch only (`create-version`+`update-asset`, never re-`create-asset`); `show-asset` must show the algorithm pointed at the NEW image version; fresh `output_name`; wait ~30s and retry once; still 500 → `trace_id` + support |
| Operator output layout | Single-dataset conversion writes **flat** into `TARGET_DATASET_PATH` root (no nested `{output_name}` folder, no `{dataset_index}_` prefix); multi-dataset → prefix only; no `.cloudrobo-tmp` folder left in the output (entrypoint prefers system `/tmp`, cleans the fallback) |
| Operator re-submission | Same-name algorithm asset exists → `create-version` + `update-asset` (把代码打进镜像); 代码放 OBS 并注册算法资产 preset unchanged → single `update-asset`, no image version; **代码放 OBS 并直接挂载 → not applicable (no assets)** |
| Operator `envs` | Must exclude platform-injected `SOURCE_DATASET_PATH` (copying its default blocks runtime injection → task fails) |
| Operator 代码放 OBS、运行时挂载 `algo_entrance` | Use **absolute** `python3 {job_local_path}/entrypoint.py` — relative `python entrypoint.py` fails (`stdbuf: Permission denied`) |
| Operator SWR login | Auto-generated from AK/SK by default (`docker login -u <region>@<AK> -p <HMAC-SHA256(AK,SK)> swr.<region>.myhuaweicloud.com`); **on failure (auto-credential generation or login fails): report the reason class to the customer — invalid/expired AK/SK (`unauthorized`/`Authenticate Error`), SWR service not enabled, IAM user lacks SWR permission, region mismatch, or network/proxy — remind the customer to verify/update AK/SK and confirm SWR access, then ask for a full `docker login` command; only proceed after retry passes with `Login Succeeded`**; `docker logout` after push |
| Operator large upload | Datasets > 50 files / > 50MB **MUST** be uploaded with the default script `scripts/concurrent_shard_upload.py` (copy it to the target host, edit CONFIG `SERVER/BUCKET/PREFIX/SRC`, run 4 shards × 16 threads) — never a serial `upload_folder` walk and never a hand-rolled reimplementation; a different tool only if the customer explicitly chooses it |
| Operator `sub_type`+`tags` | Do not pass `--sub-type` together with `--tags` (400 Invalid parameter: tags) |
| Operator dataset RELEASE | New dataset version must be published `RELEASE` (`CREATING`/`DRAFT` → "dataset not ready") |
