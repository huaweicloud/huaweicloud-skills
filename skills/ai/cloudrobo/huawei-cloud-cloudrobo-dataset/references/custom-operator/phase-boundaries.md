> Part of the custom-operator guide. Index: [custom-operator-workflow.md](custom-operator-workflow.md)

## Phase Boundaries 阶段边界

### Contents 目录

- Overview 概述
- Skill Generality 通用性约定
- OBS Boundary OBS操作边界
- Global Ask-User Checklist 全局确认清单
- Phase 0 — Deploy Mode & Asset Detection 部署方式与资产检测
- Phase 1 — Code Adaptation 代码适配
- Phase 2 — Build & Push 镜像构建推送（仅把代码打进镜像；代码放 OBS 跳过本阶段）
- Phase 3 — Asset Registration 资产注册
- Phase 4 — Runtime Verification 运行时验证
- Work Copy Lifecycle & Cleanup 工作副本生命周期与清理
- Missing-Information Quick Table 信息缺失速查表
- Mutation Confirmation Table 变更操作确认表

### Overview 概述

This document is the authoritative reference for **input prerequisites**, **missing
information handling**, and **user-confirmation points** of every phase. Three rules
govern all phases:

1. **Verify inputs before starting a phase** — never enter a phase without its required
   inputs being present and validated
2. **Ask for missing information** — any required input that is absent must be requested
   from the user; never guess, fabricate, or silently default IDs, paths, or credentials
3. **Confirm every mutation** — docker push, asset creation, and task creation are
   mutating operations and require explicit user confirmation before execution

### Skill Generality 通用性约定

This skill is **generic**. Hardcoded values are limited to **platform-enforced
constraints**; product-semantic defaults and resource sizing are **confirmed with the
user** rather than assumed:

| Value | Category | Handling |
|-------|----------|----------|
| `image_source=custom`, SWR URL regex, `input_type`/`access_method`, env-var array + non-empty `default` (1–512) | Platform constraints | Fixed, keep |
| `tags=["Data Processing"]`, `status=DRAFT` | Product-semantic defaults | Confirm / allow the user to adjust |
| `resource_pool_type` / `cluster_type` / `task_framework_type` | Task-config defaults | Confirm with the user (e.g. `DEDICATED_POOL` needs `resource_id`) |
| `worker_spec` / `worker_num` / `evs_spec` | Resource sizing | **Ask the user** — never assume 4C8G/1 worker |
| `output_name` / `output_path` | Per-run values | Ask the user (unique `output_name`; user-provided `output_path`) |
| `workspace_id` / `catalog_id` / dataset | Dynamic | Query platform / ask the user |

### OBS Boundary OBS操作边界

This skill performs **no OBS data browsing** — it never lists or validates OBS
buckets:

- Input dataset paths come from `cloudrobo asset list-assets --type dataset`
  (Source ②, user-confirmed selection), the customer-provided OBS data path bound
  via `create-version` (Source ①), or a **customer-provided OBS path used directly**
  (Source ③ "OBS存储" `UDF_OBS_ASSET` — format-validated **plus bucket must equal the
  workspace-bound bucket** (`default_obs_path` bucket); never listed), never from
  manual OBS browsing
- `output_path` is **provided by the user** (or derived from workspace info)
- The algorithm-asset `url` (an OBS path within the workspace's `default_obs_path`)
  is derived from workspace information returned by `cloudrobo workspace current` —
  **no OBS API calls are made**
- The only OBS uploads the skill may perform are **confirmed mutations**: 代码放 OBS、运行时挂载 code
  delivery and Phase 4 Source ① data upload (both via the OBS client, confirmed with
  the customer first)

### Global Ask-User Checklist 全局确认清单

Before the pipeline starts and at each phase boundary, confirm with the user:

> **对话话术与确认要点（每轮一问、二次确认话术）的唯一权威定义在
> [interaction-guidelines.md](interaction-guidelines.md)（§4 高危操作确认清单）** — 本表仅列出"何时必须问/问什么"，
> 不重复维护话术。

| Item | Required Before | Ask When Missing |
|------|-----------------|------------------|
| `workspace_id` | Phase 0 | No default workspace — ask user to run `cloudrobo workspace use --workspace-id <id>` |
| `catalog_id` | Phase 0 / 3 | Not present in `cloudrobo workspace current` output |
| Deploy mode | Phase 0 | **必须问一次**（平台已有镜像资产 / 客户提供镜像 URL / 本地构建 / 代码放 OBS 挂载），推荐值预选；本机无 Docker 只是询问理由，不是替客户决定 |
| 代码放 OBS 路线：task-creation way | Phase 0 / 4 | **默认空间资产-算法** —— 仅当客户要求不注册资产、直接挂载代码时才问 |
| 代码放 OBS 路线：OBS path | Phase 0 | **默认 `{default_obs_path}{operator-name}/`** —— 推导并说明；必须以工作空间 `default_obs_path` 开头 |
| 代码放 OBS 路线：container injection path | Phase 0 / 4 | **默认 `/tmp/cloudrobo/{operator-name}`** —— 说明即可 |
| Runtime image (any mode) | Phase 0 | **必须由客户给出**：点名的空间镜像资产，或粘贴的 SWR 地址。Agent 不扫描镜像资产、不推断"合适的"运行时；仅客户点名后查询其地址与版本 |
| AK/SK | Phase 0 | **Never configured (no env vars, no config file) or expired (`401`/`unauthorized`)** — proactively remind the customer to configure / update the AK/SK (see `../cli-installation-guide.md` §4.1) |
| Docker login command | Phase 2 | A new image is always registered (把代码打进镜像) — skill **auto-generates** it from AK/SK first; ask the user only when generation/login fails |
| Operator source directory | Phase 1 | Path not provided or does not exist |
| `operator_config.yaml` | Phase 1 | File missing in source directory |
| Base image (`image.base`) | Phase 2 | Pull fails — ask for a reachable image |
| Input dataset source | Phase 4 | **默认：复用匹配的数据集资产；没有则自动新建。** 仅当用户主动给 `obs://` 路径时才用直挂。多个都可能时才问 |
| Input dataset | Phase 4 | 找不到工作空间数据集 —— 从用户给的数据路径自动新建，不要让用户另行上传 |

### Phase 0 — Deploy Mode & Asset Detection 部署方式与资产检测

**Input prerequisites:** valid `workspace_id` + `catalog_id`; Docker CLI available
(仅把代码打进镜像时使用).

> **部署方式必须问一次，不要静默决定。** 用一轮问清并给出推荐：
> 客户已有镜像资产/镜像 URL > 本机有 Docker 时打进镜像 > 代码放 OBS、运行时挂载。
> 本机没有 Docker 是需要询问的理由，不是替客户选 OBS 挂载的理由。
> 客户说"都可以"时，按上述顺序选第一个成立的并说明理由。
> **镜像由客户给出，不扫描镜像资产去"推荐"**——只有客户点名后才查该镜像的地址和版本。

| # | Boundary Condition | Detection | Handling / Ask User |
|---|--------------------|-----------|---------------------|
| 0.1 | No workspace selected | `cloudrobo workspace current` fails or returns no id | **Ask** the user to select/confirm a workspace; abort if declined |
| 0.2 | No `catalog_id` in workspace info | `workspace current` output lacks `asset_catalog_id` | **Ask** the user for the workspace catalog_id |
| 0.3 | Deploy mode undetermined | 未确认过部署方式 | **必须问一次**：平台已有镜像资产 / 客户提供镜像 URL / 本地构建 / 代码放 OBS 挂载（推荐值预选）。客户说"都可以"时按推荐顺序选并说明。**不得先扫描镜像资产再"推荐"** |
| 0.3a | 代码放 OBS 路线：task-creation way undetermined | 客户明确要求不注册资产、直接挂载代码 | **用 OBS算法**；否则**空间资产-算法（默认）**。不问 |
| 0.4 | 把代码打进镜像路线：any image-asset state (exist or not) | `list-assets --type image --tags "Data Processing" --exact-name <name>` (any result) | **Always register a new image** — a fresh tag is built and pushed on every run (operator code lives inside the image); no "use existing image" question |
| 0.5 | 代码放 OBS 路线：OBS path missing / not under workspace `default_obs_path` | Customer path does not start with workspace `default_obs_path` | **Ask** the customer for the OBS path of their code; reject/re-ask if the prefix does not match |
| 0.5a | 代码放 OBS 路线：code upload mode not chosen | Customer has not answered | **对话话术（对客户）**：「生成代码后，由谁上传到 OBS：自行上传，还是由我上传（先确认）？」 |
| 0.5b | 代码放 OBS 路线：OBS endpoint unresolvable | `obs.{region}.myhuaweicloud.com` → NXDOMAIN | **对话话术（对客户）**：「默认 OBS 端点无法解析，请提供可达端点（如 `obs.cn-southwest-2.myhuaweicloud.com`）」；set on `Config.endpoints['cloudrobo-obs']` |
| 0.6 | 代码放 OBS 路线：container injection path missing | `job_local_path` not provided | **Use the default** `/tmp/cloudrobo/{operator-name}` and inform the customer |
| 0.7 | 代码放 OBS 路线：preset runtime image missing / not SWR format | No image provided or regex fails | **Ask** the customer for a preset runtime image in `swr.{region}.myhuaweicloud.com/...` format (registered as an image asset in Phase 3 only for 空间资产-算法) |
| 0.8 | Same-name algorithm asset exists (把代码打进镜像 / 代码放 OBS 并注册算法资产) | `list-assets --type algorithm --tags "Data Processing" --exact-name <name>` returns non-empty | Record as **re-submission** |
| 0.9 | Same-name algorithm asset does not exist (把代码打进镜像 / 代码放 OBS 并注册算法资产) | `list-assets --type algorithm --tags "Data Processing" --exact-name <name>` returns empty | Record as **first submission** (OBS算法: not applicable — Phase 3 skipped) |
| 0.10 | 把代码打进镜像路线：auto-generated login command fails | Output ≠ "Login Succeeded" (`unauthorized` / `Authenticate Error` / `no permission`) | **Classify & walk the fix** (Step 2.0 §Login failure): AK/SK invalid/expired, SWR not enabled / IAM permission missing, region mismatch, network — remind the customer to update AK/SK / enable SWR / fix region, confirm when done; **ask** for a full `docker login ...` command; retry with the user-provided command and require `Login Succeeded` |
| 0.11 | 把代码打进镜像路线：user-provided login command malformed | Not starting with `docker login`, or no registry host | Point out the missing parts; **ask** for a corrected full command |
| 0.12 | 把代码打进镜像路线：user-provided login command fails | Output ≠ "Login Succeeded" (`unauthorized` etc.) | **Remind the customer to update the AK/SK**; ask to re-check host/user/password; retry |
| 0.13 | List-assets API error (401/403/network) | Command fails | 401 → **remind the customer to update the AK/SK** (expired/invalid) and retry; 403 → remind to update AK/SK permissions; network → report and ask whether to retry or abort |

### Phase 1 — Code Adaptation 代码适配

**Input prerequisites:** operator source directory (with `src/`, `requirements.txt`,
`operator_config.yaml`), writable `/tmp`.

| # | Boundary Condition | Detection | Handling / Ask User |
|---|--------------------|-----------|---------------------|
| 1.1 | Source directory does not exist | Path check fails | Error "Source directory does not exist"; **ask** for the correct path |
| 1.2 | `src/` missing | Directory check | Error; **ask** the user to provide code in the expected structure |
| 1.3 | `requirements.txt` missing | File check | **Warn + confirm**: generate Dockerfile without the pip-install layer? |
| 1.4 | `operator_config.yaml` missing | File check | Error "operator_config.yaml is required"; **ask** for the file |
| 1.5 | Required fields missing | Config validation | Error listing missing fields; **ask** the user to complete them |
| 1.6 | `entry.module` file absent in `src/` | Module check | Error; **ask** for the correct module name |
| 1.7 | `process()` not found | Import/scan check | Error; list expected signature `process(input_path: str) -> str\|bytes`; **ask** to fix code or config |
| 1.8 | `image.base` missing or empty | Config validation | **Ask** the user for a base image (template placeholder not usable) |
| 1.9 | `SOURCE_DATASET_PATH` not declared | Env-var check | Auto-inject with a fallback default; inform the user |
| 1.10 | Copy verification mismatch (SHA-256) | Integrity check | Re-copy once; on repeat failure, error and **ask** user to check source readability |
| 1.11 | Disk full during copy | `No space left on device` | Error; suggest cleaning old work copies first |
| 1.12 | Template generation fails (placeholder missing) | Generation check | Error with the specific template; do not ship a broken entrypoint |
| 1.13 | 代码放 OBS 路线：skill uploads code to OBS | `OBSClient.upload_folder` to the OBS path | **Confirm with the customer first** (writes to OBS); verify with `list_objects`; if the endpoint is unresolvable, ask for a reachable one. Code = 3 files + `src/` → serial is fine; large payloads → concurrent sharded upload ([OBS Upload Guide](obs-upload-guide.md)) |
| 1.14 | 代码放 OBS 路线：customer uploads code | Customer chose option A | Present the file list (`entrypoint.py`, `src/`, `requirements.txt`) + target OBS path; **wait for the customer to confirm** before Phase 3 (空间资产-算法) / Phase 4 (OBS算法, Phase 3 skipped) |

### Phase 2 — Build & Push 镜像构建推送（仅把代码打进镜像；代码放 OBS 跳过本阶段）

**Input prerequisites:** 把代码打进镜像 — valid work copy, Docker daemon running, validated
SWR target URL, docker login command (auto-generated from AK/SK in Phase 0;
user-provided as fallback). **代码放 OBS、运行时挂载 — skip this phase entirely.**

| # | Boundary Condition | Detection | Handling / Ask User |
|---|--------------------|-----------|---------------------|
| 2.0 | 代码放 OBS、运行时挂载 selected | Phase 0 flag | **Skip this phase** — no docker login / build / push; go straight to Phase 3 (空间资产-算法) / Phase 4 (OBS算法, Phase 3 skipped) |
| 2.1 | Docker daemon not running | `docker info` fails | Error "Docker daemon not available"; **ask** user to start Docker, then retry |
| 2.2 | SWR URL invalid | Regex `^swr\.[a-z0-9-]+\.myhuaweicloud\.com/` fails | Reject; **ask** for a corrected target (region/namespace/tag) |
| 2.3 | Base image pull fails | `docker pull` error (not found / network) | **Ask** the user for a base image reachable from their build environment |
| 2.4 | Docker build fails | Build exit ≠ 0 | Show failing step + hint (e.g. COPY path); **ask**: fix & rebuild or abort |
| 2.5 | Build timeout | > 300s CPU / 600s GPU | Report; **ask**: extend timeout, optimize deps, or abort |
| 2.6 | Auto-generated SWR login fails | Output ≠ "Login Succeeded" (`unauthorized` / `Authenticate Error` / `no permission`) | **Classify & walk the fix** (Step 2.0 §Login failure): ① AK/SK invalid/expired → remind the customer to update them and confirm; ② SWR not enabled / IAM permission missing → enable SWR + grant access; ③ region mismatch → confirm `CLOUDROBO_REGION`; ④ network/docker daemon → check connectivity. Re-run auto-login once after the fix; if still failing, **ask for a full `docker login ...` command** and retry — require `Login Succeeded` before continuing |
| 2.7 | SWR push fails — quota | Error mentions quota | Report; **ask**: retry later, skip push (Scenario 3), or abort |
| 2.8 | SWR push fails — network | Connection error | Work copy retained; **ask**: retry or resume later with `--reuse-workdir` |
| 2.9 | SWR push fails — auth | `unauthorized` | **Remind the customer to update the AK/SK** (expired/invalid or lacks SWR access); ask for a new login command |
| 2.10 | Tag collision | Existing same tag | Use timestamp/semantic tag (never overwrite old tags); inform the user |
| 2.11 | **Mutation: push to SWR** | Before `docker push` | **Confirm with the user** (docker build is local, push publishes the image) |
| 2.12 | `image_url` writeback failure | Config write error | Error; work copy retained — fix and resume |

### Phase 3 — Asset Registration 资产注册

**Input prerequisites:** 把代码打进镜像 — `image_url` (from Phase 2); 代码放 OBS、运行时挂载 **空间资产-算法** —
customer OBS path (`code_dir`); `catalog_id`, validated ext_metadata, and the Phase 0
deploy-mode + first-submission / re-submission flag. **代码放 OBS 并直接挂载 — skip this
phase entirely** (no assets needed).

| # | Boundary Condition | Detection | Handling / Ask User |
|---|--------------------|-----------|---------------------|
| 3.0 | 代码放 OBS 并直接挂载 selected | Phase 0 flag | **⛔ Skip Phase 3 entirely** — no image/algorithm assets to register; go straight to Phase 4 (asset registration would be redundant for a direct OBS mount) |
| 3.1 | 把代码打进镜像路线：`image_url` missing | Phase 3 entry check | Error "complete Phase 2 first" |
| 3.2 | 代码放 OBS 并注册算法资产: `code_dir` missing / not under workspace `default_obs_path` | Config check | **Ask** the customer for a valid OBS path under the workspace-bound OBS path |
| 3.3 | `catalog_id` missing | Config check | **Ask** the user for the workspace catalog_id |
| 3.4 | 把代码打进镜像的首次提交 (no same-name algorithm asset) | Phase 0 flag | Two `create-asset` calls: `type=image` **FIRST** then `type=algorithm` — **image asset MUST succeed before algorithm asset creation** |
| 3.4a | Image asset creation fails (把代码打进镜像 / 代码放 OBS 并注册算法资产) | `create-asset --type image` returns error (e.g. `400 SWR image not available`) | **⛔ DO NOT create the algorithm asset.** Fix the image issue first (docker login + push if `400 SWR image not available`), retry `create-asset --type image` until it succeeds, THEN create the algorithm asset. The algorithm's `engine.image_url` references the image registered by the image asset — creating the algorithm before the image asset exists produces a broken algorithm |
| 3.5 | 把代码打进镜像的再次提交 (same-name algorithm asset exists) | Phase 0 flag | `create-version` on the image asset (new SWR URL) + `update-asset` on the algorithm asset (new `engine.image_url`); **no new algorithm version** |
| 3.6 | 代码放 OBS 并注册算法资产 first submission | Phase 0 flag | Register the **preset image as an image asset** (`type=image`) **FIRST** — on `400 SWR image not available`: docker login + push + retry — THEN **one** `create-asset --type algorithm` (`image_source=custom`, `engine.asset_id` + `engine.asset_version_id` link the image asset, `code_dir`=OBS path). **Image asset MUST succeed before algorithm asset; algorithm MUST link the image asset** |
| 3.7 | 代码放 OBS 并注册算法资产 re-submission | Phase 0 flag | preset image changed → `create-version` on the image asset + `update-asset` on the algorithm asset (keep `engine.asset_id`, re-point `engine.asset_version_id` to the new image version); preset image unchanged → single `update-asset` (`code_dir`, keep both `asset_id`/`asset_version_id`); **no new algorithm version** |
| 3.8 | ext_metadata exceeds a limit | Validation (command 4096 / inputs 10 / outputs 5 / env 90 / hyper 90) | Report field + limit + current count; **ask** user to adjust config |
| 3.9 | 代码放 OBS 并注册算法资产: algorithm asset not linked to the image asset | `show-asset` shows `engine` without `asset_id`/`asset_version_id` (or with `image_source=preset`) | **Fix the algorithm asset** — `update-asset` to set `engine.asset_id` + `engine.asset_version_id` (from the image asset) + `image_source=custom`; the algorithm MUST use the created 空间资产-镜像; do not proceed until linked |
| 3.10 | env var `default` empty | Validation | Error "default format invalid: 1-512 chars"; **ask** user to set a non-empty default |
| 3.11 | `sub_type` + `tags` both passed | Request assembly | Omit `sub_type` (documented 400 workaround); do not ask — apply the fix |
| 3.11a | `create-asset --type image` returns `400 SWR image not available` | Image not actually present in SWR (cleaned up / only local) | **`docker login` + `docker push` the image to the SWR URL, then retry the `create-asset --type image` call** (代码放 OBS、运行时挂载 preset image; also applies to 把代码打进镜像 after a fresh push) |
| 3.12 | POST /v1/assets (or versions/update) 401 | API response | Error "Authentication failed" — **remind the customer to update the AK/SK** (expired/invalid) and retry |
| 3.13 | POST /v1/assets (or versions/update) 403 | API response | Error "Permission denied"; check `cloudrobo:assets:create`/`update`; ask retry after fix |
| 3.14 | POST /v1/assets (or versions/update) 429 | API response | Exponential backoff (3 attempts); then error and ask retry |
| 3.15 | POST /v1/assets (or versions/update) 500 | API response | Output error code + traceId; ask to contact support |
| 3.16 | 把代码打进镜像路线：image asset created, algorithm step fails (first submission) | Second call fails | Keep `image_asset_id`; fix payload; retry only the algorithm call |
| 3.17 | 把代码打进镜像路线：image `create-version` succeeds but `update-asset` fails (re-submission) | Second call fails | Image version exists but algorithm still points at the old image; report and ask whether to retry or roll back |
| 3.18 | **Mutation: every create-asset / create-version / update-asset call** | Before each submit | **Confirm with the user** (creating/updating real platform assets) |
| 3.19 | `show-asset` verification fails | Status ≠ DRAFT/available | Report; ask whether to re-verify, recreate, or abort |

### Phase 4 — Runtime Verification 运行时验证

**Input prerequisites:** `algorithm_asset_id` (把代码打进镜像); 代码放 OBS、运行时挂载 — the **task-creation
way** (空间资产-算法: `algorithm_asset_id` + OBS path (`algo_path` = asset `code_dir`) +
`job_local_path`, Phase 3 assets exist; OBS算法: customer OBS path + `job_local_path`
only, **Phase 3 skipped — no assets**) plus the chosen **input-dataset source**
(① 空间资产-数据-新建 / ② 空间资产-数据-复用 — user-selected when multiple exist
/ default when exactly one / ③ OBS存储 direct path `UDF_OBS_ASSET` — no asset), a
unique `output_name`.

| # | Boundary Condition | Detection | Handling / Ask User |
|---|--------------------|-----------|---------------------|
| 4.0 | Dataset source undetermined | Phase 4 started without a decision | **默认：复用匹配的数据集资产；没有则从数据路径自动新建。** 仅当用户主动给 `obs://` 路径时才直挂（`UDF_OBS_ASSET`）。多个都可能时才问 |
| 4.0a | Source ①: OBS data path missing | Customer provides no path | **Ask** the customer for the raw-data OBS path; confirm the data is already uploaded (the skill may upload a local data dir after confirmation, a mutation — for large datasets use the concurrent sharded upload per [OBS Upload Guide](obs-upload-guide.md), never a serial walk) |
| 4.0e | Source ③ (OBS存储): OBS path missing / malformed / **foreign bucket** / multiple paths | Customer provides no path, a path not starting with `obs://`, a path whose **bucket ≠ workspace-bound bucket** (`default_obs_path` bucket from `cloudrobo workspace current`), or later mentions extra paths | **Ask** for valid `obs://` path(s) — one question per round; format-validate (**no OBS browsing**) **and validate the bucket**: show the workspace `default_obs_path` as reference, **reject & re-ask any foreign-bucket path** (other OBS buckets NOT supported); data must already be in place (empty path → task stuck in `POD_PENDING`). **Multiple paths are collected into ONE task**: each path becomes one `dataset_configs` entry `{"obs_path":"<url>","dataset_type":"UDF_OBS_ASSET"}` (≤10 entries) — **single create-task, never one task per path** |
| 4.0b | Source ①: dataset name duplicate | `400 The asset name is existed` | Use a unique per-run name (timestamp suffix, e.g. `{operator-name}-input-{YYYYMMDDHHMMSS}`) or **ask** the customer |
| 4.0c | Source ①: dataset version not RELEASE | Version status `CREATING`/`DRAFT` | **Always publish `RELEASE`**: `cloudrobo asset update-version --asset-id <id> --version-id <vid> --status RELEASE` — otherwise the task reports "dataset not ready" |
| 4.0d | Source ①: data path empty | Customer confirms data not uploaded / path empty | **Remind the customer to upload the raw data files to the OBS path first**; task would stay in `POD_PENDING` |
| 4.1 | Source ②: no dataset in workspace | `list-assets --type dataset` empty | **Remind the user to upload data first** — offer **Source ①** (skill auto-creates the dataset) or **Source ③ OBS存储** (direct `obs://` path, no asset) or see the parent `cloudrobo-dataset` skill; never proceed with a fabricated path |
| 4.1a | Source ②: dataset selection | `list-assets --type dataset` | **Exactly one → use it by default (no confirmation); multiple → ask the user to multi-select (max 10)** (one task may process multiple datasets) |
| 4.2 | More than 10 datasets selected | Selection exceeds 10 | **Enforce the 10-max limit** — tell the customer the maximum is 10 and ask them to trim |
| 4.3 | 代码放 OBS 路线：OBS code not uploaded | Code path empty / customer confirms | **Remind the customer to upload the algorithm code first** (`entrypoint.py` / `src/` / `requirements.txt`) — an empty path keeps the task in `POD_PENDING`; 空间资产-算法: verify the algorithm asset `code_dir` via `show-asset` points to the populated path |
| 4.4 | Dataset URL unknown | `dataset_configs` assembly | Use each selected dataset asset's `url` (from `list-assets`/`show-asset`); if absent, ask the user |
| 4.5 | Multiple datasets selected | `dataset_configs` assembly | **ONE task only**: one `dataset_configs` entry per selected dataset/path (`obs_path`/`asset_id`/`asset_name`/`version_id`; Source ③ OBS存储 entries use only `obs_path` + `dataset_type=UDF_OBS_ASSET`), **all entries in the single task's array (≤10); never one task per dataset** (拆分多条任务仅限用户显式要求批量场景，且需先确认) |
| 4.6 | 把代码打进镜像 task config | `algo_type` | `WORKSPACE_ASSETS` with `algo_id` = algorithm `asset_id` |
| 4.6a | 代码放 OBS 路线：task-creation way undetermined | Phase 4 entry check | **默认空间资产-算法**（`WORKSPACE_ASSETS` + `algo_id`，Phase 3 注册资产）。仅当客户明确要求直挂时才用 `OBS_ASSETS`（Phase 3 跳过） |
| 4.7 | 代码放 OBS、运行时挂载 task config — 空间资产-算法 (use the created algorithm) | `algo_type` | `WORKSPACE_ASSETS` with `algo_id` = Phase 3 algorithm `asset_id` + `algo_name` (**required**) + `algo_path` (= asset `code_dir`, **required**) + `job_local_path` (**required**) + **absolute** `algo_entrance` (`python3 {job_local_path}/entrypoint.py`) + `image` (preset SWR URL). Omitting `algo_path`/`job_local_path` fails with `//entrypoint.py` |
| 4.7a | 代码放 OBS、运行时挂载 task config — OBS算法 (mount the OBS code directly) | `algo_type` | `OBS_ASSETS` with `algo_name` (**required**) + `algo_path` (customer OBS path) + `job_local_path` (default if not provided) + absolute `algo_entrance` + `image` (preset SWR URL); **no `algo_id`** |
| 4.8 | `output_name` duplicate | 400 "The asset name is existed" | Auto-suffix with timestamp, or **ask** the user for a unique name |
| 4.9 | `envs` empty array | Task config contains `"envs": "[]"` | Omit `envs` entirely (400 worker_spec workaround) |
| 4.10 | Task stuck / timeout | `--wait` times out | Report status + elapsed; **ask**: continue waiting / view logs / terminate |
| 4.11 | 任务已创建后取消 / 修改参数重发 | 用户要求取消或"改了参数再创建一个新任务"，且存在已创建任务 `{task_id}`（PENDING/RUNNING 等） | **⛔ 必须先与用户确认删除/停止旧任务**：展示「任务 {id}（{status}）仍在平台运行」→ 询问「是否删除/停止旧任务？① 删除（不可恢复，立即终止）② 保留运行 ③ 先查看日志」→ 选①执行 `delete-task` 并 `show-task` 验证 `DELETED`；**未确认删除前禁止创建新任务**（否则前端残留执行任务 + 重复计费） |
| 4.11a | Task FAILED | Final status FAILED | Run failure analysis on `job-std-output.log`; show cause + fix; 把代码打进镜像路线：fix & rebuild image; 代码放 OBS 路线：customer fixes code on OBS; **ask**: fix & rerun or abort |
| 4.12 | SUCCEEDED but no output frames | `get-frames` empty | Check `output_name`/`output_path` and entrypoint output dir; fix, rebuild, rerun |
| 4.13 | User log shows failed items | `[DONE] ... 失败 N > 0` | Inspect per-item traceback; **ask** user to fix `process()` and rerun |
| 4.14 | **Mutation: create-task** | Before submitting | **Confirm with the user** (runs real computation, produces an output asset) |
| 4.15 | `task_id` not at top level | Response shape | Read `payload.id` (documented SDK behavior); do not error |
| 4.16 | `create-task` returns HTTP 500 on a re-run after rebuild | Post-image-rebuild task submission fails | Check algorithm asset linkage first (`show-asset`: `engine.image_url`/`engine.asset_version_id` ⇒ **new** image version), use a fresh `output_name`, wait ~30 s, retry once; still 500 → capture `trace_id` + system log, contact support (see [Failure Analysis Guide](failure-analysis-guide.md)) |

### Work Copy Lifecycle & Cleanup 工作副本生命周期与清理

The work copy `/tmp/custom-operator-work-{timestamp}/` is **temporary** and must be
cleaned up after the pipeline finishes.

#### Default Cleanup Policy 默认清理策略

| Outcome | Cleanup Action |
|---------|----------------|
| Success (Phase 4 verified) | **Auto-clean** — delete the work copy after the run |
| Failure at any phase | **Retain** for `--reuse-workdir` resume; ask the user: clean now or keep for debugging |
| `--keep-workdir` | Retain after the run (development/debugging) |
| `--clean-workdir` | Force-clean after the run |

#### Cleanup Rules 清理规则

1. Cleanup deletes **only the work-copy directory** the skill created — the user's
   original source directory is never touched
2. When retained copies exceed `max_workdir_count` (default 10), the **oldest** are
   removed first
3. The sweep runs at `workdir_cleanup_interval` (default 3600s) — stale copies are
   removed even if a run was interrupted (e.g. crash, network drop)
4. If cleanup fails (files locked, e.g. by Docker on Windows), log a warning and
   continue — the work copy is not critical once the image is pushed; retry on next run
5. With `workdir_retention: false` in `~/.cloudrobo/config.yaml`, work copies are
   auto-cleaned immediately after every run (production hardening — operator code may
   contain sensitive logic)

#### Cleanup Boundary Conditions 清理边界条件

| # | Boundary Condition | Handling |
|---|--------------------|----------|
| C.1 | Cleanup succeeds | Confirm with a one-line message; exit code 0 |
| C.2 | Cleanup fails (locked files) | Warning (non-blocking); schedule retry on next run |
| C.3 | Work copies exceed `max_workdir_count` | Remove oldest first; log which were removed |
| C.4 | `--reuse-workdir` after cleanup | Error "Work copy directory does not exist"; start fresh from Phase 1 |
| C.5 | Disk space low during cleanup sweep | Sweep all copies matching a min-age threshold; inform the user |
| C.6 | `--keep-workdir` conflicts with `workdir_retention: false` | Config wins — copy is cleaned; inform the user |

### Missing-Information Quick Table 信息缺失速查表

| Missing Information | Phase | Action |
|---------------------|-------|--------|
| `workspace_id` | 0 | Ask user to run `cloudrobo workspace use` |
| `catalog_id` | 0 / 3 | Ask user for the workspace catalog_id |
| Deploy mode | 0 | **Ask the customer**: 把代码打进镜像（代码和依赖一起构建进镜像），还是代码放 OBS、运行时挂载（代码上传 OBS，任务运行时挂载进已有镜像）？ |
| 代码放 OBS 时的 OBS 代码路径 (`code_dir` / `algo_path`) | 0 / 3 | **Ask the customer** for their already-uploaded OBS path; must start with workspace `default_obs_path` |
| 代码放 OBS 时的容器挂载路径 (`job_local_path`) | 0 / 4 | If not provided, **use the default** `/tmp/cloudrobo/{operator-name}` |
| 代码放 OBS 时的运行时镜像 | 0 / 3 | **Ask the customer** for a `swr.{region}.myhuaweicloud.com/...` image (never scan image assets to pick one) |
| AK/SK (never configured) | 0 | **Proactively remind the customer to configure the AK/SK** (env vars or `~/.cloudrobo/config.yaml`, see `../cli-installation-guide.md` §4.1); pause until confirmed |
| AK/SK (expired / invalid) | 0 / 2 / 3 | **Proactively remind the customer to update the AK/SK** (regenerate in IAM, refresh config) on `401` / `unauthorized`; do not retry the failed call in a loop |
| Docker login command | 0 / 2 | Skill auto-generates it from AK/SK (official SWR long-lived login command); ask the user for the full command only when generation/login fails |
| Source directory | 1 | Ask user for the correct path |
| `operator_config.yaml` | 1 | Ask user to provide the file |
| Required config fields | 1 | List missing fields; ask user to complete |
| `image.base` (reachable) | 2 | Ask user for a base image their build env can pull |
| `image_url` | 3 | Complete Phase 2 first (把代码打进镜像; a new image is always built on every run) |
| Input-dataset source | 4 | **Default: ① 空间资产-数据-新建数据集 (auto create asset) when nothing matches, ② 复用已有资产 when exactly one matches; use ③ OBS存储 (direct `obs://` path, `UDF_OBS_ASSET`) only when the customer supplies the path.** Ask only when several datasets are plausible and a wrong pick is costly |
| Input dataset (Source ①) | 4 | Ask the customer for the OBS data path; confirm the data is uploaded; auto-create the dataset (create-asset `type=dataset` + create-version + `update-version --status RELEASE`); unique name + `RELEASE` version |
| Input dataset (Source ②) | 4 | Query `list-assets --type dataset`; **none → remind the user to upload (or switch to ① / ③ OBS存储); one → use by default; multiple → ask the user to multi-select** |
| Input dataset (Source ③ OBS存储) | 4 | Ask the customer for a **valid `obs://` path** (format-validated + **bucket must equal the workspace-bound bucket** — `default_obs_path` from `cloudrobo workspace current`; show it as reference, other OBS buckets NOT supported, mismatch → reject & re-ask, no OBS browsing); dataset_configs entry = `{"obs_path":"<url>","dataset_type":"UDF_OBS_ASSET"}`; **no dataset asset, no `RELEASE`, no create-asset** |
| Unique `output_name` | 4 | Ask user or auto-suffix with a timestamp |

### Mutation Confirmation Table 变更操作确认表

> 覆盖性变更（re-submission 的 update-asset / create-version、删除类操作）还须说明
> 「旧版本/旧数据保留或不可恢复的后果」——二次确认话术见 [interaction-guidelines.md](interaction-guidelines.md)
> §4（本表仅列操作 × 阶段 × 是否需要确认）。

| Operation | Phase | Confirmation |
|-----------|-------|--------------|
| `docker login` / `docker push` (publish image) | 2 | **Required** — confirm before push (仅把代码打进镜像时使用) |
| `OBSClient.upload_folder` (代码放 OBS、运行时挂载 skill upload) | 1 | **Required** — writes the generated code to the customer's OBS path |
| `cloudrobo asset create-asset --type image` (把代码打进镜像的首次提交) | 3 | **Required** — creates a real image asset |
| `cloudrobo asset create-asset --type algorithm` (把代码打进镜像 / 代码放 OBS 并注册算法资产 的首次提交) | 3 | **Required** — creates a real algorithm asset |
| `cloudrobo asset create-version` (把代码打进镜像的再次提交) | 3 | **Required** — creates a real image asset version |
| `cloudrobo asset update-asset` (把代码打进镜像 / 代码放 OBS 并注册算法资产 的再次提交) | 3 | **Required** — updates the algorithm asset's `engine.image_url` / `code_dir` |
| `OBSClient.upload_folder` (Phase 4 Source ① data upload) | 4 | **Required** — writes the customer's raw data to the OBS path |
| `cloudrobo asset create-asset --type dataset` (Phase 4 Source ①) | 4 | **Required** — creates a real dataset asset (Source ③ OBS存储 direct path creates/references NO dataset asset — no confirmation beyond the path itself) |
| `cloudrobo asset create-version` (dataset version, Phase 4 Source ①) | 4 | **Required** — binds the dataset to the customer's OBS data path |
| `cloudrobo asset update-version --status RELEASE` (Phase 4 Source ①) | 4 | **Required** — publishes the dataset version (non-RELEASE → "dataset not ready") |
| `cloudrobo dataset proc create-task` | 4 | **Required** — runs real computation, produces an output asset |
| `cloudrobo dataset proc delete-task` (garbage cleanup) | 4 | **Required** — deletes a failed task record (junk); `show-task` first: name/owner/creation time must belong to this run |
| `cloudrobo asset delete-asset` / `delete-version` (garbage cleanup) | 4 | **Required** — deletes failed-task/stale output datasets or versions; `show-asset` first (name prefix + owner + creation time), list exact names/IDs; **never** the operator's image/algorithm assets or customer datasets |
| Verification-report.md generation | 4 | **Required** — ask the customer whether to generate; only useful info, no trial-and-error steps (see [garbage-cleanup-report.md](garbage-cleanup-report.md) §Part 2) |
| Work copy cleanup | all | Non-destructive to user code — no confirmation needed (but inform) |

---