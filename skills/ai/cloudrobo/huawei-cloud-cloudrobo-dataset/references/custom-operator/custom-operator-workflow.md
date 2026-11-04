# Custom Operator Workflow 算子执行工作流

## Contents 目录

- [Onboarding Workflow](#onboarding-workflow-上架工作流) — 五阶段上架步骤（Phase 0-4）+ 恢复重试 + 完整示例 + 清理
- [Phase Boundaries](#phase-boundaries-阶段边界) — 阶段边界、确认清单、信息缺失速查、变更操作确认表
- [Garbage Cleanup & Verification Report](#garbage-cleanup--verification-report-垃圾清理与验证报告) — 服务器/平台垃圾清理、验证报告生成
- [Progress Feedback](#progress-feedback-长等待步骤进度反馈) — 长等待步骤清单、create-then-poll、docker push 进度、清理
- [Failure Analysis Guide](#failure-analysis-guide-失败分析指南) — 错误模式矩阵（P0-P3）、根因分析与修复建议
- [OBS Upload Guide](#obs-upload-guide-上传数据到-obs-指南) — OBS 并发分片上传、验证、边界情况
---
## Onboarding Workflow 上架工作流

### Contents 目录

- Overview 概述
- Prerequisites Check 前置条件检查
- Phase 1: Code Adaptation 代码适配
- Phase 0: Deploy Mode & Asset Detection 部署方式与资产检测
- Phase 2: Image Build & Push 镜像构建推送（Mode A only；Mode B 跳过本阶段）
- Phase 3: Asset Registration 资产注册
- Phase 4: Runtime Verification 运行时验证
- Resume & Recovery 恢复与重试
- Interaction Rules 交互规则
- Full Onboarding Example 完整上架示例
- Post-Onboarding 上架后操作
- Work Copy Cleanup 工作副本清理
- Server-Side Local Junk Cleanup 服务器本机垃圾清理（必做）
- Phase Boundary Summary 阶段边界速览

### Overview 概述

The onboarding workflow walks a user through turning their custom data processing
code into a platform-registered algorithm asset. It has three sequential phases,
each building on the previous one's output.

### Prerequisites Check 前置条件检查

Before starting onboarding, verify:

```bash
# 1. cloudrobo CLI installed and configured
cloudrobo --version
cloudrobo workspace current

# 2. Docker Engine running
docker info > /dev/null 2>&1 && echo "Docker OK" || echo "Docker not running"

# 3. AK/SK configured (one of):
echo $HUAWEI_CLOUD_AK  # Environment variables
cat ~/.cloudrobo/config.yaml  # Config file

# 4. Operator source directory structure
ls -la /path/to/operator/
# Expected: src/, requirements.txt, operator_config.yaml
```

> **AK/SK validity check (proactive reminder):** if neither
> `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` nor `~/.cloudrobo/config.yaml` exists, the
> customer has **never configured AK/SK** — the skill must **proactively remind the
> customer to configure it** (see `../cli-installation-guide.md` §4.1) and pause until
> confirmed. If the first authenticated call returns `401` / `unauthorized`, the
> AK/SK is **expired or invalid** — the skill must **proactively remind the customer
> to update it** (regenerate in IAM, refresh env vars / config) and retry.

### Phase 1: Code Adaptation 代码适配

#### Step 1.1: Create Work Copy 创建工作副本

```bash
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
```

**What happens:**
1. CLI creates `/tmp/custom-operator-work-{timestamp}/`
2. Copies `src/`, `requirements.txt`, `operator_config.yaml` to work copy
3. Original source directory is **never modified**
4. Work copy path is saved for `--reuse-workdir` resume

> **Single-file operator adaptation:** if the source directory contains ONLY a `.py`
> file (e.g. `operator.py` with a `process()` function) and no standard structure, the
> skill adapts it in the work copy:
> - `mkdir src/` and copy the `.py` → `src/user_operator.py`
> - Generate `requirements.txt` (empty for pure-stdlib code)
> - Generate `operator_config.yaml` (`name` from the file/dir name,
>   `entry.module=user_operator`, `entry.function=process`, `image.base` from the
>   customer's base image)
> - Generate `entrypoint.py` from `../../templates/entrypoint.py`
> Do **not** error on the missing standard structure.

**Output:**
```
✓ Work copy created: /tmp/custom-operator-work-{timestamp}/
✓ Copied 3 files from source directory
```

#### Step 1.2: Generate entrypoint.py 生成入口文件

**What happens:**
1. Read `operator_config.yaml` → `entry.module` and `entry.function`
2. Generate `entrypoint.py` in work copy with:
   - `SOURCE_DATASET_PATH` environment variable reading (JSON map may contain
     **MULTIPLE datasets** — one task can process up to 10)
   - **Multi-dataset aggregation** — parse the JSON map and collect input items across
     **ALL** mounted dataset directories (do NOT take only the first dataset); each
     dataset root prefers `<path>/input/`, falling back to the root itself (dataset
     asset OBS roots contain a `<version_id>/` subdirectory)
   - **Recursive input walk** (`rglob("*")`, files only) — avoids `IsADirectoryError`
     on nested version-id folders
   - **`OUTPUT_DIR` = `TARGET_DATASET_PATH` or `/output`** — the platform mounts
     `SOURCE_DATASET_PATH` **read-only**; writing `output/` inside it fails with
     `OSError: [Errno 30] Read-only file system`
   - `OUTPUT_DIR.mkdir(parents=True, exist_ok=True)`
   - Dynamic import of the user's `process()` function — resolve `src/` **relative to
     `__file__`** (`Path(__file__).resolve().parent / "src"`), NOT hardcoded
     `/app/src` (Mode A bakes code at `/app/src`, Mode B mounts it at
     `{job_local_path}/src`)
   - Per-item iteration over all collected items (recursive)
   - Output writing (bytes or text): single dataset keeps the original stem name;
     multiple datasets get a `{dataset_index}_` prefix to avoid output collisions
   - Error handling with `traceback.print_exc()`

**Validation:**
- If `entry.module` not found in `src/` → Error: "Module {module} not found in src/"
- If `process()` function not found → Error: "Function {function} not found in module"

#### Step 1.3: Generate Dockerfile 生成Dockerfile

**What happens:**
1. Read `operator_config.yaml` → `image.base`, `dependencies.system_packages`
2. Generate `Dockerfile` in work copy with:
   - `FROM {base_image}` — resolved from `operator_config.yaml image.base` (must be
     reachable from the build environment, e.g. a slim Python image)
   - `WORKDIR /app`
   - `COPY requirements.txt .` — **before src for layer caching**
   - `RUN pip install --no-cache-dir -r requirements.txt`
   - `COPY ./src ./src`
   - `COPY entrypoint.py .`
   - `ENV SOURCE_DATASET_PATH=<fallback-path>` (platform overrides at runtime)
   - `ENTRYPOINT ["python", "/app/entrypoint.py"]`

> **Mode A only.** Mode B has no Dockerfile.

#### Step 1.4: Mode B — Code Delivery to OBS 将代码交付到OBS（Mode B）

After the work copy is ready (with the generated `entrypoint.py`), deliver the code
to the OBS path per the Phase 0 upload mode:

**Option A — the customer uploads (default):**
1. Present the file list and target path:
   ```
   Upload to: {algo_path}
   ├── entrypoint.py
   ├── src/
   └── requirements.txt
   ```
2. Ask the customer to upload with their OBS tools and **confirm when done**; pause
   Phase 3 until confirmed

**Option B — the skill uploads:**
1. **Confirm the upload with the customer** (a mutation that writes to OBS)
2. **Reuse the per-operator OBS directory** — upload into the same
   `{default_obs_path}/{operator-name}/` used before (stable `code_dir`); repeated
   verifications are **incremental updates** — `upload_file/upload_folder` overwrites
   objects with the same key in place
3. Upload the work-copy files via the OBS client (code delivery = 3 files + `src/`,
   serial upload is fine; **large payloads → concurrent sharded upload per
   `§`**):
   ```python
   from cloudrobo_core.sdk.obs_client import OBSClient
   from cloudrobo_core.sdk import Config
   cfg = Config()
   # default endpoint is obs.{region}.myhuaweicloud.com; if unresolvable, use a
   # reachable one, e.g.:
    # cfg.endpoints['cloudrobo-obs'] = 'obs.cn-southwest-2.myhuaweicloud.com'
   obs = OBSClient(cfg, bucket_name='<workspace-bucket>')
   obs.upload_folder('<work-copy-dir>', '<obs-prefix-of-algo_path>')  # idempotent overwrite
   ```
4. Verify: `obs.list_objects(prefix='<obs-prefix>', bucket_name=...)` shows
   `entrypoint.py`, `src/user_operator.py`, `requirements.txt`

**OBS endpoint note 端点说明:** the default `cloudrobo-obs` endpoint is
`obs.{region}.myhuaweicloud.com`; it may fail to resolve on some networks
(NXDOMAIN). Ask the customer for a reachable endpoint (e.g. Guiyang1
`obs.cn-southwest-2.myhuaweicloud.com`) and set it on
`Config.endpoints['cloudrobo-obs']` before any OBS operation.
   - If `system_packages` present: `RUN apt-get update && apt-get install -y ...`

#### Step 1.4: Validate operator_config.yaml 校验配置

**What happens:**
1. Parse YAML → JSON (`operator_config.json` in work copy)
2. Validate required fields: `name`, `image.arch`, `image.device_type`, `entry.*`,
   `inputs`, `outputs`, `environment_variables`
3. Validate constraints: inputs ≤10, outputs ≤5, env_vars ≤90, hyperparams ≤90
4. Validate `SOURCE_DATASET_PATH` is declared in `environment_variables`
5. Fill defaults for optional fields

**Output:**
```
✓ Config validated: 3 inputs, 2 outputs, 5 env vars
✓ operator_config.json written to work copy
```

#### Phase 1 Dry-Run 干跑验证

```bash
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
```

Validates config and generates artifacts without creating the work copy. Useful
for checking config validity before committing to a full onboarding.

### Phase 0: Deploy Mode & Asset Detection 部署方式与资产检测

> **⛔ MANDATORY — the deploy mode MUST be chosen by the customer, first.**
> The very first Phase 0 action is to ask the customer for Mode A or Mode B and wait
> for their explicit answer. **Never infer the mode from any environment clue** (base
> images, existing local/SWR images, historical assets, customer-provided URLs, task
> wording, etc.). If the answer is missing or ambiguous, **re-ask until unambiguous**.
> No Phase 1 work (work copy, entrypoint, Dockerfile/operator_config assembly) may
> start before the mode is confirmed.

Phase 0 first asks the customer to choose the **deploy mode**, then gathers what is
needed to decide the Phase 3 branch (first submission vs re-submission):

- **Mode A — image-inbuilt (`custom`)**: a new image is always built + pushed on every
  run (operator code lives inside the image)
- **Mode B — OBS-mounted (`preset`)**: the **customer uploads the code to OBS
  themselves**; the skill collects the OBS path + container injection path + preset
  runtime image, and **skips image build/push entirely**. Runtime verification then
  creates the proc-task via **one of two customer-chosen ways** (mandatory choice,
  see Step 0.3 — never infer, re-ask until unambiguous):
  - **空间资产-算法 — use the created algorithm (`WORKSPACE_ASSETS` + `algo_id`)**: the task
    references the Phase 3 algorithm asset (`image_source=custom`, algorithm asset links
    the image asset via `engine.asset_id` + `engine.asset_version_id`) via `algo_id` (asset
    linkage) and mounts its `code_dir` via `algo_path` + `job_local_path` — **the task
    truly consumes the created algorithm asset** (this is what `WORKSPACE_ASSETS` means:
    reference a workspace-registered algorithm asset; Mode A `custom` assets use the
    same type). Verified: `algo_path` + `job_local_path` are **required** even here —
    omitting them fails at runtime (`//entrypoint.py` no such file).
  - **OBS算法 — mount the customer OBS code directly (`OBS_ASSETS`, no `algo_id`)**:
    the task mounts the customer OBS path directly, no asset linkage — **Phase 3
    asset registration is skipped** (no image/algorithm assets are created).

#### Step 0.1: Query Existing Assets 查询已有资产

> **OBS算法 (mount OBS code directly): the queries below are optional** — no assets are
> registered, so same-name detection only matters when the customer later switches to
> 空间资产-算法.

```bash
# Image assets (exact name + Data Processing tag) — locate the existing image asset
# id (needed for create-version on re-submission, Mode A)
cloudrobo asset list-assets --catalog-id {workspace_catalog_id} --type image --tags "Data Processing" --exact-name {operator-name}
# Same-name algorithm assets (exact name + Data Processing tag) — detect whether this
# operator was already submitted
cloudrobo asset list-assets --catalog-id {workspace_catalog_id} --type algorithm --tags "Data Processing" --exact-name {operator-name}
```

#### Step 0.2: Decision Branch 决策分支

| Condition | Action |
|-----------|--------|
| Deploy mode not chosen | **对话话术（对客户）**：「请选择算子的部署方式：方式A【镜像内置】代码打包进镜像、每次重新构建推送；方式B【OBS挂载】代码放 OBS、用预设镜像不构建。请问使用哪种方式？」 |
| Mode A (any image-asset state) | **Register a new image** — build + push a fresh tag on every run; no "use existing image" question |
| Mode B | Collect **OBS path** (must start with workspace `default_obs_path`, **reuse the existing per-operator directory across verifications**), **container injection path** (`job_local_path`, default if not provided), **preset runtime image**, **code upload mode** — **no docker login / build / push**; **⛔ then ask the task-creation way: 空间资产-算法 (use the created algorithm, `WORKSPACE_ASSETS` + `algo_id`) or OBS算法 (mount the OBS code directly, `OBS_ASSETS` without `algo_id`)** — mandatory choice, re-ask until unambiguous. 空间资产-算法 → Phase 3 registers preset image + algorithm assets; **OBS算法 → Phase 3 is skipped entirely** (no asset registration) |
| Same-name algorithm asset exists | Record as **re-submission** |
| Same-name algorithm asset does not exist | Record as **first submission** |
| Login command (Mode A) | **Auto-generate the docker login command** from AK/SK (official SWR long-lived login command, HMAC-SHA256-derived secret); proceed to Phase 2. Only ask the user for a command if generation or login fails |

> **Why auto-generate?** The skill reads AK/SK from `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK`
> or `~/.cloudrobo/config.yaml` and derives the SWR long-lived login command
> (`docker login -u <region>@<AK> -p <HMAC-SHA256(AK, SK)> swr.<region>.myhuaweicloud.com`),
> so no user input is needed in the happy path. The customer is asked for a command
> **only when** auto-generation is impossible (no AK/SK) or the auto-generated login
> fails (`unauthorized` / `Authenticate Error`). In both cases the skill first
> **proactively reminds the customer to configure / update the AK/SK** (see
> `../cli-installation-guide.md` §4.1), then asks for the full command as a fallback.

#### Step 0.3: Mode B — OBS Deployment Info Collection OBS部署信息收集

For Mode B, collect and validate (all **confirmed with the customer** in a
conversational way):

0. **Task-creation way (空间资产-算法 / OBS算法) — MANDATORY choice, asked FIRST** — how the
   runtime proc-task will reference the algorithm:
   - **空间资产-算法 — use the created algorithm**: task-config uses
     `WORKSPACE_ASSETS` + `algo_id` = the Phase 3 algorithm `asset_id`
     (`image_source=custom`, asset linkage; algorithm `engine.asset_id` +
     `engine.asset_version_id` link the image asset) + `algo_path` = the asset's `code_dir`
     (mount source, **required**) + `job_local_path` (mount path, **required**) +
     **absolute** `algo_entrance` — verified: missing `algo_path`/`job_local_path`
     fails at runtime (`//entrypoint.py` no such file).
   - **OBS算法 — mount the OBS code directly**: task-config uses
     `OBS_ASSETS` with `algo_name` + `algo_path` (customer OBS path) +
     `job_local_path`, **no `algo_id`**; **Phase 3 asset registration is skipped**
     (no image/algorithm assets — nothing to register).
   - **对话话术（对客户）**：「请选择本算子创建任务时的算法引用方式：**空间资产-算法**【引用已注册的算法资产，任务关联算法资产运行，会执行资产注册】；**OBS算法**【直接挂载 OBS 路径上的代码运行，不关联算法资产，跳过资产注册】。请问使用哪种？」

1. **OBS path** (`code_dir` / `algo_path`) — the algorithm code location:
   - **Must start with the workspace-bound OBS path** — `default_obs_path` from
     `cloudrobo workspace current` (e.g. `obs://z00664168-demo/zwett/`)
   - **Reuse the per-operator directory across verifications** — for a given operator
     always use `{default_obs_path}/{operator-name}/` (stable `code_dir`), do NOT
     create a new timestamped directory; repeated verifications are incremental
     updates into the same path
   - Reject / re-ask if the prefix does not match
   - **对话话术（对客户）**：「请提供 OBS 路径（以 `{default_obs_path}` 开头）。多次验证会复用同一目录 `{default_obs_path}{算子名}/`，只更新代码文件。不提供则我按该规则自动生成。」
   - Expected content at that path after delivery: `entrypoint.py`, `requirements.txt`,
     `src/` (with `user_operator.py`)
2. **Code upload mode** — ask the customer how the generated code reaches OBS:
   - **对话话术（对客户）**：「将生成算子的 `entrypoint.py`、`src/`、`requirements.txt`。代码如何到达 OBS 路径：① 自行上传；② 由我上传（先确认后上传）。选择哪种？」
   - **A: customer uploads** (default) — the skill lists the files + target path;
     the customer uploads and confirms (see Step 1.4)
   - **B: skill uploads** — the skill uploads the work-copy files with the OBS client
     (see Step 1.4); **confirm before uploading**
3. **Container injection path** (`job_local_path`) — where the algorithm directory is
   mounted inside the container (e.g. `/tmp/xxx`):
   - If the customer does not provide one, **use the default**
     `/tmp/cloudrobo/{operator-name}` and inform them
   - **对话话术（对客户）**：「请提供容器内挂载位置（如 `/tmp/xxx`），不提供则默认 `/tmp/cloudrobo/{算子名}`。」
4. **Preset runtime image** (`image_url`) — a runtime image for the job, in
   `swr.{region}.myhuaweicloud.com/{namespace}/{repo}:{tag}` format
5. **OBS endpoint reachability** — the default endpoint is
   `obs.{region}.myhuaweicloud.com`; verify it resolves; if it fails (e.g. NXDOMAIN),
    ask the customer for a reachable endpoint
    (e.g. `obs.cn-southwest-2.myhuaweicloud.com`) to use for OBS operations

> **OBS boundary update:** the skill no longer blindly assumes the customer uploads.
> The customer chooses: **they upload** (skill lists files + path) **or the skill
> uploads** (OBS client, with confirmation). Either way the OBS path is validated
> against the workspace `default_obs_path` and **reused across verifications**.

#### Step 0.4: Validate the Login Command 校验登录指令（Mode A only）

```bash
# Auto-generated command (from AK/SK), e.g.:
#   docker login -u cn-southwest-2@<AK> -p <login-secret> swr.cn-southwest-2.myhuaweicloud.com
# On auto-generation/login failure, fall back to:
<user-provided docker login ...>
# Expect: Login Succeeded
```

If login fails, ask the user to re-check the command (registry host, user, password) before proceeding.

### Phase 2: Image Build & Push 镜像构建推送（Mode A only；Mode B 跳过本阶段）

> **Mode A**: a new image tag is built and pushed on every submission (operator code
> lives inside the image).
> **Mode B**: this phase is **skipped entirely** — no docker login / build / push; the
> customer uploads the algorithm code to OBS themselves.

#### Step 2.0: SWR Login (auto-generated by default)

**What happens:**
1. The skill **auto-generates the docker login command** from AK/SK (official SWR
   long-lived login command):
   ```bash
   # 1) derive login secret: HMAC-SHA256(key=SK, message=AK), hex-encoded
   printf "$AK" | openssl dgst -binary -sha256 -hmac "$SK" \
     | od -An -vtx1 | sed 's/[ \n]//g' | sed 'N;s/\n//'
   # 2) docker login
   docker login -u <region>@<AK> -p <login-secret> swr.<region>.myhuaweicloud.com
   ```
   > **PowerShell note:** `openssl` may not be on `PATH` on Windows. If the derivation
   > command fails (`openssl: command not found`), do NOT treat it as a login failure —
   > use PowerShell's `HMACSHA256` (or ask the customer to provide the endpoint
   > `swr.<region>.myhuaweicloud.com`), or fall through to the customer-provided command.
2. Execute it; confirm output contains "Login Succeeded" before continuing — **do not
   proceed to build/push until login is verified**.

**Login failure (auto-credential generation fails OR `docker login` fails):**

```
✗ SWR login failed
Error: <output>  (e.g. unauthorized / Authenticate Error / connection refused)
```

Report the **reason class** to the customer and walk the fix before retrying:
1. **AK/SK invalid or expired** (`unauthorized` / `Authenticate Error`) → remind the
   customer to regenerate/reconfigure AK/SK (`HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` or
   `~/.cloudrobo/config.yaml`, see `../cli-installation-guide.md` §4.1) and **confirm
   when updated**
2. **SWR service not enabled / IAM permission missing** (e.g. `no permission`,
   `Tenant Guest` errors) → remind the customer to enable SWR in the console and grant
   the AK/SK account SWR access; **bookmark the fix, then re-run**
3. **Region mismatch** (`swr.<region>...` vs the AK/SK's region) → confirm the correct
   region; the login command's registry host must match `CLOUDROBO_REGION`
4. **Network / proxy / docker daemon** (connection refused, TLS error) → check Docker
   daemon and proxy; retry after resolution

After the customer confirms the fix: re-run the auto-generated command once; if it still
fails, **ask the customer for a full `docker login ...` command** (validate it starts
with `docker login` and contains the registry host), execute it, and **require
"Login Succeeded" before continuing**. Never bypass verification or guess a credential.

**Login success:**
```
✓ SWR login succeeded
```

#### Step 2.1: Docker Build Docker构建

```bash
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
```

**What happens:**
1. `cd` to work copy directory
2. **Probe the build network first** (see `custom-operator-reference.md` §Build
   Network): external → plain build; intranet/proxy-fronted → pass
   `--build-arg HTTP_PROXY/HTTPS_PROXY/NO_PROXY` so build-time `pip install` works
   while `dnf` can still reach intranet RPM repos.
3. `docker build -t custom-operator:{tag} .` — tag is timestamp-based
4. Layer caching: if `requirements.txt` unchanged, pip install layer is cached
5. Build timeout: 300s (CPU), 600s (GPU with CUDA)

**Build success:**
```
✓ Docker build succeeded (tag: custom-operator:{tag})
✓ Build time: 45s (layers cached: 3/5)
```

**Build failure:**
```
✗ Docker build failed
Error: COPY failed: file not found in build context: src
→ Check that src/ directory exists in work copy
```

#### Step 2.2: SWR Login (covered by Step 2.0)

SWR login uses the **docker login command auto-generated from AK/SK** (fallback: the
command provided by the user in Phase 0). It is executed once in Step 2.0 and verified
for "Login Succeeded" — the skill auto-generates the login command from the configured
AK/SK so that no user input is required in the happy path.

#### Step 2.3: Tag & Push 标记推送

**What happens:**
1. Tag local image: `docker tag custom-operator:{tag} swr.{region}.myhuaweicloud.com/cloudrobo/custom-operator:{tag}`
2. Push to SWR: `docker push swr.{region}.myhuaweicloud.com/cloudrobo/custom-operator:{tag}`
3. Write SWR URL back to `operator_config.json`:
   - `image.url` = full SWR URL
   - `engine.image_url` = same SWR URL string

**Push success:**
```
✓ Image pushed: swr.cn-southwest-2.xxx.myhuaweicloud.com/cloudrobo/custom-operator:{tag}
✓ image_url written to operator_config.json
```

### Phase 3: Asset Registration 资产注册

> **Branch on the Phase 0 deploy mode + same-name detection:** Mode A first submission
> creates both assets; Mode A re-submission creates an image version and updates the
> algorithm asset's image; Mode B **空间资产-算法** registers the **preset image as an image
> asset** + manages the **algorithm asset** (preset + code_dir), with **no build/push**.
>
> **⛔ Mode B OBS算法 (mount the OBS code directly) SKIPS this phase entirely** — the
> task uses `algo_path` + `image` (SWR URL string) directly and links to **no asset**;
> asset registration would be redundant. Record "Phase 3 skipped" and go straight to
> Phase 4. (空间资产-算法 alone keeps the Phase 0 first/re-submission detection meaningful.)

#### Step 3.1: Mode A — First Submission — Create Image + Algorithm Assets 首次提交

```bash
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
```

> **⚠️ MANDATORY ORDERING: image asset FIRST, algorithm asset SECOND.**
> The algorithm asset's `engine.image_url` references the SWR image that the image
> asset registers. The image asset **MUST be created successfully** before creating
> the algorithm asset — creating the algorithm asset first (before the image asset
> exists) produces an algorithm that references a non-registered image, which causes
> runtime failures (image pull errors, `SWR image not available`).
> If `create-asset --type image` returns `400 SWR image not available`, the image is
> not in SWR — execute `docker login` (auto-generated from AK/SK) + `docker push`
> the image to the SWR URL, then **retry** `create-asset --type image` before
> proceeding to the algorithm asset creation. **Never continue to step 4 if step 3
> failed.**

**What happens:**
1. Read `operator_config.json` from work copy
2. Assemble image asset ext_metadata: `{"arch": "<arch>", "device_type": ["CPU"]}`
   > **Note:** Do NOT include `sub_type` for image assets. The backend auto-enriches
   > `ext_metadata` with `namespace` and `image_size`.
3. **Register image asset FIRST** (this step MUST succeed before step 5):
   ```bash
   # ⚠️ PREREQUISITE: the image MUST be in SWR (docker push if only local).
   #    On 400 "SWR image not available": docker login + docker push, then retry.
   # ⚠️ NAME: --name MUST equal the operator name confirmed in the dialogue (the
   #    name the user was prompted with). Never silently rename or auto-append a
   #    suffix. After creation, show-asset must return exactly that name; if the
   #    backend returns/renames a different name, stop and re-confirm with the user.
   cloudrobo asset create-asset --catalog-id <workspace-catalog-id> \
     --name <operator-name> --type image --url <SWR image URL> \
     --tags "Data Processing" \
     --ext-metadata '{"arch":"<arch>","device_type":["<device-type>"]}'
   ```
   - SDK: `AssetClient.create_asset(req)` → receive `asset_id` (image) + `latest_version_id`
   - **On failure (`400 SWR image not available`):** auto-generate docker login from
     AK/SK (HMAC-SHA256), `docker push` the image to the SWR URL, then **retry** this
     `create-asset --type image` call. Do NOT proceed to the algorithm asset until the
     image asset is created successfully.
4. Assemble the algorithm asset request body:
   ```json
   {
     "catalog_id": "{workspace_catalog_id}",
     "name": "{operator-name}",
     "description": "{operator-description}",
     "type": "algorithm",
     "url": "obs://{workspace-bucket}/{path-prefix}/{operator-name}",
     "tags": ["Data Processing"],
     "ext_metadata": {
       "engine": {
         "image_url": "swr.../{namespace}/{operator-name}:{tag}",
         "image_source": "custom"
       },
       "command": "python entrypoint.py",
       "code_dir": "",
       "inputs": [
         {
           "name": "dataset",
           "input_type": "DATA",
           "access_method": "env",
           "description": "Input dataset"
         }
       ],
       "outputs": [
         {
           "name": "result",
           "input_type": "DATA",
           "access_method": "parameter",
           "description": "Processed output"
         }
       ],
       "environment_variables": [
         {
           "name": "SOURCE_DATASET_PATH",
           "default": "<fallback-path>",
           "description": "Dataset path injected by platform"
         }
       ]
     }
   }
   ```
   > **Critical:** `engine.image_url` = SWR URL string, NOT image asset ID
   > **Critical:** `url` = OBS path within workspace's `default_obs_path`, NOT SWR URL
5. **Create algorithm asset** (AFTER image asset succeeds — do NOT create if step 3 failed):
   ```bash
   # ⚠️ This step depends on step 3 succeeding. The engine.image_url MUST match
   #    the SWR URL registered in the image asset created above.
   cloudrobo asset create-asset --catalog-id <workspace-catalog-id> \
     --name <operator-name> --type algorithm --status DRAFT \
     --tags "Data Processing" \
     --ext-metadata '<assembled ext_metadata from operator_config.json>'
   ```
   - SDK: `AssetClient.create_asset(req)` → receive `asset_id` (algorithm)

#### Step 3.2: Mode A — Re-Submission — Image Version + Update Algorithm Image 再次提交（Mode A）

Triggered when the Phase 0 same-name algorithm query returned an existing asset
(operator code changed and a new image was built in Phase 2).

> **⛔ Re-run after a FAILED verification MUST take this re-submission branch.** Never
> re-execute Step 3.1's `create-asset` when a same-name algorithm asset already exists —
> a second `create-asset` returns `400 The asset name is existed` and, worse, leaves the
> algorithm asset still referencing the OLD image. A common trap: first verification
> fails → rebuild the image (Phase 2) → agent wrongly re-runs **first-submission** assets
> → then `create-task` fails with **HTTP 500** because the algorithm asset's
> `engine.asset_version_id` / `engine.image_url` still point at the stale version.
> Always re-query (`asset list-assets --exact-name`) to confirm the re-submission branch,
> update the linkage, **then** re-create the task (see §Phase 4 for the pre-task checks).

```bash
# 1. Create a new version of the image asset (new SWR URL)
#    No --version needed — the backend derives the version number from the SWR
#    URL's image tag automatically (e.g. tag 20260922165836 → version 20260922165836)
cloudrobo asset create-version --asset-id <existing-image-asset-id> \
  --url <new SWR image URL> \
  --ext-metadata '{"arch":"<arch>","device_type":["<device-type>"]}'
# SDK: AssetClient.create_asset_version(asset_id, req)

# 2. Edit the algorithm asset to point engine.image_url at the new image (NO new
#    algorithm version)
cloudrobo asset update-asset --asset-id <existing-algorithm-asset-id> \
  --ext-metadata '<assembled ext_metadata with engine.image_url = new SWR URL>'
# SDK: AssetClient.update_asset(asset_id, req)
```

**What happens:**
1. The **image asset gains a new version** (the new SWR URL) — old tags/versions are
   retained
2. The **algorithm asset's `engine.image_url` is updated** to the new image — no new
   algorithm version is created; the same algorithm asset now references the new image
3. The algorithm asset request body keeps the same constraints as first submission
   (`engine.image_url` = SWR URL string, `url` = OBS path, no `sub_type` + `tags`
   conflict)

> **⚠️ Do NOT pass `sub_type` together with `tags`** — the API returns
> `400 Invalid parameter: tags` for `type=algorithm` when both are present
> (the predefined tag list for the sub_type filters empty). Omit `sub_type`.

#### Step 3.3: Mode B — OBS-Mounted Algorithm (preset) OBS挂载算法（Mode B，仅空间资产-算法）

> **⛔ Applies to Mode B 空间资产-算法 (use the created algorithm) ONLY.** In OBS算法 (mount
> the OBS code directly) **this step is skipped together with all of Phase 3** — the
> runtime task references `algo_path` + `image` (SWR URL string) and needs no assets.

Mode B uses a **preset runtime image**; the **customer uploads the code to OBS
themselves**. The skill performs **no image build/push**, but the preset runtime
image **must be registered as an image asset** (空间资产-镜像) so the algorithm
asset can link it. **⚠️ The algorithm asset's `engine` MUST carry
`asset_id` (image asset id) + `asset_version_id` (image asset version id) with
`image_source=custom`** — this LINK is what makes the algorithm "use" the created
image asset (verified e2e umi_to_lerobot_v3; reference demo algorithm asset
`72cb8aeb-6257-4f5f-a3e0-0d19d5ed36c5`). Needed only when the task must link to the
created algorithm via `algo_id` (空间资产-算法).

> **⚠️ MANDATORY ORDERING: image asset FIRST, algorithm asset SECOND.**
> The algorithm asset's `engine.image_url` references the preset image's SWR URL,
> and `engine.asset_id` + `engine.asset_version_id` **link it to the image asset**.
> The image asset **MUST be created successfully** before creating the algorithm
> asset — creating the algorithm asset first (before the image asset exists)
> produces an algorithm that references a non-registered image, which causes runtime
> failures (image pull errors, `SWR image not available`).
> If `create-asset --type image` returns `400 SWR image not available`, the preset
> image is not in SWR (only local) — auto-generate `docker login` from AK/SK
> (HMAC-SHA256), `docker push` the preset image to the SWR URL, then **retry**
> `create-asset --type image` before proceeding to the algorithm asset creation.
> **Never continue to step 2 if step 1 failed.**

**First submission** (no same-name algorithm asset) — **two** `create-asset` calls
(**step 1 MUST succeed before step 2**):

```bash
# 1. Register the preset runtime image as an image asset
#    ⚠️ NAME: --name MUST equal the operator name confirmed in the dialogue (the name
#       used by Step 0.1's --exact-name queries for re-submission detection). Never
#       use the SWR repo name as a substitute — the asset query would then miss it
#       and every next run would be mis-detected as a FIRST submission.
#    ⚠️ PREREQUISITE: the preset image MUST be in SWR (docker push if only local).
#       On 400 "SWR image not available": docker login (auto from AK/SK) + docker push, then retry.
#    ⚠️ This step MUST succeed before proceeding to step 2.
cloudrobo asset create-asset --catalog-id <workspace-catalog-id> \
  --name <operator-name> --type image --url <preset-image SWR URL> \
  --tags "Data Processing" \
  --ext-metadata '{"arch":"<arch>","device_type":["<device-type>"]}'
# SDK: AssetClient.create_asset(req) → image_asset_id + latest_version_id
# On 400 "SWR image not available": docker login + docker push <SWR URL>, then retry this call.
# ❌ DO NOT proceed to step 2 if this step failed.

# 2. Create the algorithm asset (AFTER image asset succeeds). ⚠️ The engine MUST
#    LINK the created image asset (空间资产-镜像) via asset_id + asset_version_id
#    (values from step 1's returned image asset_id + latest_version_id), with
#    image_source="custom" (NOT "preset"), plus code_dir = customer OBS path.
#    The engine.image_url MUST match the SWR URL registered in step 1.
#    (Verified e2e umi_to_lerobot_v3: an algorithm asset with only image_url +
#    image_source=preset is NOT linked to the image asset; the reference demo
#    algorithm asset 72cb8aeb links asset_id + asset_version_id with custom.)
cloudrobo asset create-asset --catalog-id <workspace-catalog-id> \
  --name <operator-name> --type algorithm --status DRAFT \
  --url "obs://<workspace-bucket>/<path-prefix>/<operator-name>" \
  --tags "Data Processing" \
  --ext-metadata '{"engine":{"asset_id":"<image-asset-id>","asset_version_id":"<image-asset-version-id>","image_url":"<preset-image>","image_source":"custom"},"command":"python entrypoint.py","code_dir":"<customer-OBS-path>","inputs":[{"name":"dataset","input_type":"DATA","access_method":"env","description":"Input dataset"}],"outputs":[{"name":"result","input_type":"DATA","access_method":"parameter","description":"Processed output"}],"environment_variables":[{"name":"SOURCE_DATASET_PATH","default":"<fallback-path>","description":"Dataset path injected by platform"}]}'
# SDK: AssetClient.create_asset(req) → receive asset_id (algorithm)
```

**Re-submission** (same-name algorithm asset exists):

- **Preset image changed** (new `image_url` differs from the algorithm asset's
  current `engine.image_url`) — two calls:
  ```bash
  # 1. Create a new version of the image asset (the new preset image URL)
  cloudrobo asset create-version --asset-id <image-asset-id> \
    --url <new-preset-image-SWR-URL> \
    --ext-metadata '{"arch":"<arch>","device_type":["<device-type>"]}'

  # 2. Update the algorithm asset (code_dir / image_url / image link) — keep
  #    engine.asset_id + asset_version_id (re-point to the new image version)
  cloudrobo asset update-asset --asset-id <existing-algorithm-asset-id> \
    --ext-metadata '<assembled ext_metadata with engine.image_source=custom, engine.asset_id=<image-asset-id>, engine.asset_version_id=<new-image-version-id> and code_dir=<customer-OBS-path>>'
  # SDK: AssetClient.update_asset(asset_id, req)
  ```
- **Preset image unchanged** (same `image_url`) — a **single** `update-asset`
  updating `code_dir` (no image version, no new algorithm version):
  ```bash
  cloudrobo asset update-asset --asset-id <existing-algorithm-asset-id> \
    --ext-metadata '<assembled ext_metadata with engine.image_source=custom, engine.asset_id=<image-asset-id>, engine.asset_version_id=<image-asset-version-id> and code_dir=<customer-OBS-path>>'
  # SDK: AssetClient.update_asset(asset_id, req)
  ```

**What happens:**
1. **The algorithm asset MUST be linked to the image asset (空间资产-镜像)** — the
   `engine.asset_id` = image asset id (step 1 / create-version target) and
   `engine.asset_version_id` = that image asset's `latest_version_id`. Without
   these two fields the algorithm asset is NOT linked to the image asset (only
   `image_url` + `image_source` are set) — the algorithm does not "use" the
   created image asset. (Verified e2e: reference demo algorithm asset
   `72cb8aeb-6257-4f5f-a3e0-0d19d5ed36c5` links `engine.asset_id` +
   `engine.asset_version_id` with `image_source=custom`.)
2. `image_source` = **`custom`** in Mode B 空间资产-算法 (the image is a workspace-registered
   image asset, not a platform preset) — `code_dir` remains **required** (customer
   OBS path, must start with workspace `default_obs_path`)
3. Optional `boot_file` — a `.py` file under `code_dir`, `obs://` prefix (e.g.
   `obs://<bucket>/<path>/entrypoint.py`)
4. The **preset runtime image is registered as an image asset** in Mode B (first
   submission creates it; re-submission creates a version only when the image changed)
5. The customer provides the OBS path + container injection path (`job_local_path`,
   default if not provided) + preset runtime image in Phase 0; the customer must
   **ensure the code is already uploaded** to the OBS path — an empty path keeps the
   proc-task in `POD_PENDING`
6. The created algorithm asset (`asset_id`) is what **空间资产-算法** tasks reference via
   `algo_id` in Phase 4 (`WORKSPACE_ASSETS` + `algo_id` = this asset id — runtime
   resolves this asset's `code_dir`). **OBS算法** tasks ignore the asset and mount the
   OBS path directly (`OBS_ASSETS`, no `algo_id`).

#### Step 3.4: Verify Assets 验证资产（仅 Mode A / Mode B 空间资产-算法）

> **⛔ Skipped in Mode B OBS算法** — no assets were created (Phase 3 skipped).

**What happens:**
1. Mode A first submission: `GET /v1/assets/{image_asset_id}` and
   `GET /v1/assets/{algorithm_asset_id}` → verify `status` is `DRAFT` or `available`
2. Mode A re-submission: `GET /v1/assets/{image_asset_id}/versions` shows the new tag;
   `GET /v1/assets/{algorithm_asset_id}` shows the updated `engine.image_url`
3. Mode B 空间资产-算法: `GET /v1/assets/{algorithm_asset_id}` → verify
   `engine.image_source=custom`, `engine.asset_id` = image asset id,
   `engine.asset_version_id` = image asset version id, and `code_dir` = customer OBS path
   (all four are required — the algorithm asset MUST be linked to the image asset)
4. Verify `engine.image_url` in algorithm matches the image / preset image
5. Mode A: verify image asset `ext_metadata` has `namespace` and `image_size` (auto-enriched)
6. Verify algorithm asset `tags` includes `"Data Processing"`
7. **Verify BOTH assets' `name` equals the operator name confirmed in the dialogue** —
   a mismatch means the backend auto-renamed or the wrong name was sent; stop and
   re-confirm with the user instead of proceeding to Phase 4

**Success output (Mode A first submission):**
```
✓ Image asset created: {image_asset_id} (status: DRAFT)
✓ Algorithm asset created: {algorithm_asset_id} (status: DRAFT)
✓ image_url consistency verified
✓ Onboarding complete!

Algorithm: {operator-name} ({algorithm_asset_id})
Image: swr.{region}.myhuaweicloud.com/{namespace}/{operator-name}:{tag}
```

**Success output (Mode A re-submission):**
```
✓ Image asset version created: {image_asset_id} → new tag {tag}
✓ Algorithm asset updated: engine.image_url = {new SWR URL}
✓ No new algorithm version created
```

**Success output (Mode B 空间资产-算法):**
```
✓ Image asset created: {image_asset_id} (status: DRAFT)
✓ Algorithm asset created/updated: {algorithm_asset_id} (image_source=custom)
✓ engine.asset_id = {image_asset_id} + engine.asset_version_id = {image_version_id}
  (linked to 空间资产-镜像)
✓ code_dir = {customer OBS path} (verified under workspace default_obs_path)
✓ No image build / push performed
```

### Phase 4: Runtime Verification 运行时验证

After assets are created (Mode A / Mode B 空间资产-算法 — OBS算法 has **no assets** and
enters Phase 4 directly), validate that the operator actually runs by creating a
proc-task (data processing task) with it.

#### Step 4.0: Choose the Dataset Source & Select Input Datasets 选择数据集来源与输入数据集

Input datasets follow the platform's TWO data-source categories — **空间资产-数据**
(workspace data assets, `BUILD_IN_ASSET`) or **OBS存储** (direct `obs://` path,
`UDF_OBS_ASSET`): Source ② (query existing assets) / Source ① (auto-create) under
空间资产-数据, and Source ③ OBS存储 (direct path input) — never fabricated.

**Step 4.0a — ask the dataset SOURCE first (MANDATORY customer choice):**
**对话话术（对客户）**：「请选择本次验证的数据来源：① **空间资产-数据-新建数据集**【您先将数据上传到 OBS（可自行上传或由我上传），我自动创建数据集资产并用于验证】；② **空间资产-数据-复用已有数据集**【从工作空间已有的数据集资产中选择】；③ **OBS存储**【直接输入一个 `obs://` 路径作为输入，**不创建、不引用数据资产**】。请问使用哪种？」→ 回答含糊时重问，并说明：③（OBS存储）不产生数据资产、无需数据集发布 `RELEASE`，但数据必须已在该 OBS 路径就绪；**且该路径必须位于当前工作空间绑定的 OBS 桶内（参考 `default_obs_path`，如 `obs://{default-bucket}/cloudrobo/{workspace_id}/`）—— 不支持其它 OBS bucket**。选③后：先展示 `default_obs_path` 作为参考，校验输入路径的 bucket 一致才继续，不一致拒绝并重问。

> **⚠️ 多数据源 → 单任务（Mode A / Mode B 通用，勿拆任务）**：无论来源①/②/③，用户提供的**多个数据源（多个 OBS 路径 / 多个数据集资产）必须合并到 `dataset_configs` 的多个 entry（≤10 个），最后只创建 1 条 proc-task** —— 任务内算子遍历全部数据源（`SOURCE_DATASET_PATH` JSON map 多 entry，entrypoint/main 算子按数据集索引前缀输出）。**禁止**按每个数据源分别调用 `create-task`（除非用户显式要求"批量"：每条数据源一条任务，此时先与你确认拆分为 N 条任务）。收集流程：上一选择点（每轮一问）→「请提供 OBS 路径/选择数据集」→ 完成后单独一问「还需要添加其他数据源吗？① 继续添加 ② 已完成」。模式 A 与模式 B 的行为完全一致（差异仅在算法引用方式，不影响任务条数）。

> **⚠️ 取消/重发必须先处理已创建的任务（Mode A / Mode B 通用）**：`create-task` 成功后任务即真实运行于平台（PENDING→POD_PENDING→RUNNING…，前端可见并可能计费）。此后若用户要求**取消/修改参数后重发**，**必须先与用户确认删除/停止旧任务**（`delete-task --task-id {task_id}`，不可恢复）；用户确认删除前**禁止创建新任务**。务必展示当前任务状态（如「任务 {id} 运行中」）再询问「是否删除/停止旧任务？① 删除（立即终止并计费停止）② 保留运行 ③ 先查看日志」。同理，任务 RUNNING 期间任何"重跑/重建后再跑"都不得遗留原任务自动续跑。

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

> **Mode B — confirm code upload:** before creating the task, confirm with the
> customer that `entrypoint.py`, `src/`, `requirements.txt` are already uploaded to
> the OBS path (the algorithm asset `code_dir` in 空间资产-算法; = `algo_path` in OBS算法). An
> empty path keeps the task in `POD_PENDING`.

#### Step 4.1: Assemble Task Config 组装任务配置

Map the algorithm asset's fields to `task_config` fields (see the parent
`cloudrobo-dataset` skill's `../task-config-catalog.md` for the full reference):

**Mode A (WORKSPACE_ASSETS):**

| Algorithm asset field | task_config field |
|-----------------------|-------------------|
| `asset_id` (algorithm) | `algo_id` |
| `name` | `algo_name` |
| `ext_metadata.command` | `algo_entrance` |
| `ext_metadata.engine.image_url` | `image` |
| workspace `catalog_id` | `catalog_id` |

**Mode B** — branches by the Phase 0 task-creation way. **`algo_name` is always
required** (the SDK validator requires it for every proc-task):

**空间资产-算法 — use the created algorithm (`WORKSPACE_ASSETS` + `algo_id`):**

| Phase 0 / Phase 3 input | task_config field |
|-------------------------|-------------------|
| Phase 3 algorithm `asset_id` | `algo_id` (**required in 空间资产-算法**, asset linkage) |
| operator name | `algo_name` (**required**) |
| algorithm asset `code_dir` (= customer OBS path) | `algo_path` (**required** — mount source; verified: missing it → `//entrypoint.py` failure) |
| container injection path (or default) | `job_local_path` (**required** — mount path) |
| **absolute** `python3 {job_local_path}/entrypoint.py` | `algo_entrance` (**absolute**; relative `python entrypoint.py` fails) |
| algorithm asset `ext_metadata.engine.image_url` | `image` (preset SWR URL) |
| workspace `catalog_id` | `catalog_id` |

> **空间资产-算法 (`WORKSPACE_ASSETS`) requires `algo_id` + `algo_name` + `algo_path`
> (= asset `code_dir`) + `job_local_path` + absolute `algo_entrance` + `image`**
> — the `algo_id` carries the asset linkage; the runtime still mounts `algo_path`
> exactly like `OBS_ASSETS`. The algorithm asset's `engine.asset_id` +
> `engine.asset_version_id` link it to the created image asset (空间资产-镜像).
> Verified end-to-end (umi_to_lerobot_v3, preset asset, `image_source=custom`).

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
// Mode A
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

// Mode B — 空间资产-算法: use the created algorithm (WORKSPACE_ASSETS + algo_id = Phase 3
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

// Mode B — OBS算法: mount the OBS code directly (OBS_ASSETS, NO algo_id)
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
> dataset). Mode B OBS算法 also confirms `algo_path`
> (customer OBS path, must be under workspace `default_obs_path`) and
> `job_local_path` (default `/tmp/cloudrobo/{operator-name}`); 空间资产-算法 needs only the
> asset's `code_dir` (Phase 3). This skill performs
> **no OBS data browsing** — `dataset_configs.obs_path` comes from the selected
> dataset asset(s) (Source ②) or the customer-provided OBS data path bound via
> `create-version` (Source ①), `output_path` is user-provided, and the
> customer uploads Mode B algorithm code themselves.

> **⚠️ Key constraints:**
> - `output_name` must be **unique per run** — duplicates return
>   `400 The asset name is existed`
> - **空间资产-算法 (`WORKSPACE_ASSETS`)** requires `algo_id` (= Phase 3 algorithm
>   `asset_id`) + `algo_name` + `algo_path` (= asset `code_dir`) + `job_local_path` +
>   absolute `algo_entrance` + `image` (verified e2e — omitting `algo_path`/`job_local_path`
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
> # task_way = "2" | "3"  — from the Phase 0 mandatory choice
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
> **⚠️ `envs` must not contain platform-injected variables (verified, Mode A e2e):**
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
(see §Progress Feedback §Task Creation).

Mode A:
```bash
cloudrobo dataset proc create-task --name <task-name> \
  --algo-type WORKSPACE_ASSETS --task-config "$(cat /tmp/task_config.json)"
```

Mode B — 空间资产-算法 uses `WORKSPACE_ASSETS` (algo_id = Phase 3 asset id); OBS算法 uses
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
engine (see §Failure Analysis Guide):

```bash
cloudrobo dataset proc get-log --task-id <task_id> --file-name job-std-output.log
```

Apply the suggested fix (e.g., add a dependency to `requirements.txt`, fix the output
directory, fix `process()`). **Mode A**: rebuild the image (Phase 2), re-push, then
**take the RE-SUBMISSION asset branch** (Phase 3 Step 3.2 — `create-version` +
`update-asset`; never re-run Step 3.1's `create-asset`). **Mode B**: the customer
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
>    Source ③: path unchanged). See §Failure Analysis Guide → HTTP 500 pattern.

#### Common Issues 常见问题

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| No dataset in workspace | Workspace has no dataset asset | **Remind the user to upload data first** — offer **Source ①** (the skill auto-creates the dataset from the customer OBS path) or see the parent `cloudrobo-dataset` skill; do not fabricate a path |
| Dataset source not chosen | Phase 4 started without the choice | **Ask the customer: ① 空间资产-数据-新建 (auto create dataset asset), ② 空间资产-数据-复用已有资产, or ③ OBS存储 (direct `obs://` path, `UDF_OBS_ASSET`, no dataset asset)?** — re-ask until unambiguous |
| Multiple data sources split into N tasks (should be ONE) | Two or more OBS paths / datasets each got its own `create-task` (Mode A & B both affected) | **Root cause**: the agent looped `create-task` per data source instead of assembling one `dataset_configs` array. **Fix**: collect all sources (multi-select ≤10), build ONE task-config with N `dataset_configs` entries, call `create-task` exactly once; operator processes all N (lerobot logs "Resolved N datasets"). Split into per-dataset tasks ONLY when the user explicitly asks for batch mode (confirm the N-task split first) |
| 取消后旧任务残留运行（重发后出现双任务/前端仍"执行中"） | 用户在任务执行中要求"取消/改参数重开"，Agent 直接创建新任务，未删除旧任务 | **Root cause**: 交互层「取消与恢复」未覆盖 Phase 4 已创建任务的处理——旧任务继续在平台运行。**Fix**: 任何取消/重发前必问「是否删除/停止旧任务 {id}（①删除 ②保留 ③查看日志）」；确认删除后 `delete-task` + `show-task` 验证 `DELETED`，再创建新任务（见边界 4.11 / S12） |
| Source ①: `400 The asset name is existed` | Dataset name already used in the catalog | Use a unique per-run name (timestamp suffix, e.g. `{operator-name}-input-{YYYYMMDDHHMMSS}`) or ask the customer |
| Source ①: task reports "dataset not ready" | Dataset version left in `CREATING`/`DRAFT` | **Publish `RELEASE`**: `cloudrobo asset update-version --asset-id <id> --version-id <vid> --status RELEASE` |
| Source ①: task stuck in `POD_PENDING` | The OBS data path is empty (data not uploaded) | **Remind the customer to upload the raw data files to the OBS path first**; terminate and re-run |
| Multiple datasets in workspace | One task may process several datasets | **Ask the user to multi-select (max 10)**; one `dataset_configs` entry per selected dataset (when exactly one exists, use it by default) |
| Mode B task rejected (missing `algo_name`) | SDK validator requires `algo_name` for every proc-task | Add `algo_name` (空间资产-算法: `WORKSPACE_ASSETS` needs `algo_id` + `algo_name` + `algo_entrance` + `image`; OBS算法: `OBS_ASSETS` needs `algo_name` + `algo_path` + `job_local_path`) |
| Mode B task rejected (OBS算法: missing `algo_path`/`job_local_path`) | SDK validator forces `algo_path` + `job_local_path` for `OBS_ASSETS` | Fill `algo_path` (customer OBS path) + `job_local_path` — never pass a placeholder `algo_id` with `OBS_ASSETS` |
| Mode B task failed with `//entrypoint.py` (空间资产-算法) | `WORKSPACE_ASSETS` missing `algo_path` (mount source) and/or `job_local_path` — runtime mounts empty and runs from `/` | Set `algo_path` = the algorithm asset `code_dir` + `job_local_path` + **absolute** `algo_entrance` (`python3 {job_local_path}/entrypoint.py`); verified e2e (umi_to_lerobot_v3) |
| Mode B task rejected (空间资产-算法: missing `algo_id`) | `WORKSPACE_ASSETS` requires `algo_id` | Set `algo_id` = the Phase 3 algorithm `asset_id` |
| Mode B task stuck in `POD_PENDING` | OBS code path empty (code not uploaded) — OBS算法: direct OBS path; 空间资产-算法: the algorithm asset `code_dir` | **Remind the customer to upload `entrypoint.py` / `src/` / `requirements.txt` to the OBS path first** (空间资产-算法: also verify via `show-asset` that the algorithm `code_dir` points to the populated path); terminate and re-run |
| `400 The asset name is existed` | `output_name` already used by an earlier run | Use a unique per-run `output_name` (e.g. timestamp suffix) |
| `400 Invalid parameter: worker_spec` | `envs` passed as an empty array `"[]"` | Omit `envs` entirely (or pass a non-empty array) |
| `SOURCE_DATASET_PATH is not a valid JSON map` + `INPUT environment variable is not set` | `envs` in task-config includes `SOURCE_DATASET_PATH` with its **fallback `default`** (e.g. `/tmp/source/dataset`), which **overrides/blocks the platform runtime injection** (input is `access_method=env`) | Re-create the task with `envs` that **exclude `SOURCE_DATASET_PATH`** (drop the entry; keep only business vars such as `UMI_PLATFORM`); no image rebuild needed |
| Task stuck in PENDING/RUNNING | Insufficient `worker_spec` resources or image pull error | Check `show-task` and system logs; adjust `worker_spec` with the user |
| `SUCCEEDED` but no output frames | entrypoint wrote into the read-only input path | Write output to `TARGET_DATASET_PATH` / `/output`; Mode A: rebuild and re-push; Mode B: customer updates code on OBS (OBS算法) or `update-asset` the algorithm `code_dir` (空间资产-算法) |
| `[DONE] ... 失败 N > 0` | `process()` raised for some items | Inspect per-item traceback in the log; fix `process()` |
| Mode B: `No module named 'ray'` / other missing deps | `algo_entrance` resolved to the **system** `/usr/bin/python3` (platform PATH has no bundled env) | Use an absolute interpreter path (e.g. `/opt/cloud/3rdComponent/python/bin/python3 {job_local_path}/entrypoint.py`) **after** fixing the preset image permissions (see `custom-operator-reference.md` lessons) |
| Mode B: `stdbuf: failed to run command '<abs-python>': Permission denied` | Platform runs `algo_entrance` as a non-root user; the bundled env lives under a 750 dir (`/opt/cloud/3rdComponent`) | Fix the preset image once: `chmod o+rx /opt/cloud` + `chmod -R o+rX /opt/cloud/3rdComponent`, rebuild/push, update assets |
| Mode B: `No usable temporary directory found in ['/tmp', ...]` | Platform mounts `/tmp` read-only (OBS code mount under `/tmp/cloudrobo`) | Generated entrypoint redirects `TMPDIR` to `TARGET_DATASET_PATH/.cloudrobo-tmp` (already in `../../templates/entrypoint.py`); re-upload entrypoint to OBS and re-run |
| Re-run `create-task` returns **HTTP 500** after a Mode A rebuild | Algorithm asset still references the **old** image version (`engine.image_url`/`engine.asset_version_id` stale after `create-version`/`update-asset` was skipped or mis-run as first-submission), or the failed run's pre-registered `BUILD_IN_ASSET` output asset is stuck `DRAFT`/`CREATING`, or the backend is momentarily re-indexing the just-updated asset | 1) `show-asset` the algorithm asset: verify it points at the **new** image version (re-run Phase 3 Step 3.2 if not, **never** re-`create-asset`); 2) use a **fresh** `output_name` (timestamp suffix) — do not reuse the failed run's; 3) wait ~30 s and retry once; 4) still 500 → capture `trace_id` + system log, contact support |
| Output dataset contains an empty `.cloudrobo-tmp` folder | The old generated entrypoint unconditionally created `TARGET_DATASET_PATH/.cloudrobo-tmp` and set `TMPDIR` there, even when the operator never used temp files | Regenerate `entrypoint.py` from `../../templates/entrypoint.py` (v: prefers writable system `/tmp`; only falls back to the output dir when `/tmp` is read-only, and removes the fallback dir at exit); Mode A rebuild, Mode B re-upload the entrypoint to OBS |
| Single-dataset output is nested under a `{output_name}`-named folder instead of flat | The operator (or an old entrypoint) wrote into `OUTPUT_DIR/<output_name>/` — `output_name` typically matches the dataset asset name (e.g. `lerobot-output-20261021181446`) | Output must be written **flat into `OUTPUT_DIR` root** (`TARGET_DATASET_PATH`) for single-dataset runs; multi-dataset runs use a `{dataset_index}_` prefix only, still no `{output_name}` subfolder. Fix the operator's output dir handling / regenerate the entrypoint |

#### Mode B OBS Code Readiness Check OBS代码就绪检查

> **Applies to OBS算法 (direct OBS mount).** In 空间资产-算法 (use the created algorithm)
> the same check applies to the **algorithm asset's `code_dir`** (the OBS path is
> populated before Phase 3; verify via `show-asset` when the task stays in
> `POD_PENDING`). The diagnostic task below always runs as a OBS算法 task-config.

Before creating a Mode B task, verify the code reached the OBS path (code delivery is
a **small** upload — serial `upload_folder` suffices; the concurrent sharded template
in §OBS Upload Guide applies to large datasets only):

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

### Resume & Recovery 恢复与重试

#### Resume from Failed Phase 从失败阶段恢复

```bash
# Phase 1 completed, Phase 2 failed — resume:
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
# ⚠️ Mode B OBS算法: Phase 3 is skipped — resume goes straight to Phase 4
```

The `--reuse-workdir` flag skips work copy creation and reuses all Phase 1
artifacts. This avoids re-copying user code and re-validating config.

#### Re-run Full Onboarding 重新执行完整上架

If the work copy is stale or config changed significantly:

```bash
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
```

This creates a new work copy with a fresh timestamp.

### Interaction Rules 交互规则

The onboarding command follows these interaction rules:

1. **At most one tool call per turn** — each phase step is a separate action
2. **Display results before asking** — show build output, then ask to proceed
3. **Mutation confirmation** — Phases 2 (push) and 3 (asset creation) are
   mutating operations and require explicit user confirmation
4. **Dry-run first** — for new operators, recommend `--dry-run` before full run
5. **Error handling** — on failure, display the error, suggest fix from
   custom-operator-workflow.md, offer retry or abort

### Full Onboarding Example 完整上架示例

```bash
# 1. Dry-run validation
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
```

### Post-Onboarding 上架后操作

After successful onboarding, the custom operator algorithm is available in the
workspace's asset catalog. It can now be used in proc-tasks:

```bash
# List workspace assets to find the new algorithm
cloudrobo asset list-assets --type algorithm --catalog-id {workspace_catalog_id}

# Create a proc-task using the custom operator
cloudrobo dataset proc create-task \
  --name "test-custom-operator" \
  --algo-type WORKSPACE_ASSETS \
  --task-config '{"algo_entrance":"algo-xyz789ghi012", ...}'
```

See the parent skill (`huawei-cloud-cloudrobo-dataset`) for task creation details.

### Work Copy Cleanup 工作副本清理

The work copy (`/tmp/custom-operator-work-{timestamp}/`) is a **temporary directory**.
Cleanup policy:

- **Success** (Phase 4 verified): auto-clean by default after the run
- **Failure**: retained for `--reuse-workdir` resume; ask the user whether to clean now
  or keep for debugging
- `--keep-workdir` / `--clean-workdir`: retain / force-clean explicitly
- Old copies beyond `max_workdir_count` (default 10) are swept oldest-first every
  `workdir_cleanup_interval`

Cleanup only removes the work-copy directory — the user's original source directory is
never touched. With `workdir_retention: false` in `~/.cloudrobo/config.yaml`, work
copies are auto-cleaned immediately after every run (production hardening).

### Server-Side Local Junk Cleanup 服务器本机垃圾清理（必做）

After the verification ends (success or final failure), **always clean the build
host's local artifacts** — this is not optional (a single verification can leave
3–6 GB of throwaway images). **⚠️ Cleanup scope = ONLY this run's artifacts** — on a
shared Docker daemon the host may also hold the customer's own images/containers:

1. Throwaway/probe/test docker images and the local duplicate of a Mode B preset
   image (after SWR push): `docker rmi <probe>:<tag>` — digest-checked, this run's only
2. This run's exited containers + proven dangling images + build cache:
   `docker rm <recorded-id>` (or label-filtered prune) + per-ID `docker rmi` on
   proven dangling images + `docker builder prune -f` — **never** an unfiltered
   `docker container prune -f` / `docker image prune -af` / `docker system prune`
3. `/tmp` build scratch dirs & logs (`/tmp/preset-image-build/`, `/tmp/build-probe/`,
   `/tmp/preset-build.log`, `/tmp/preset-push.log`, `/tmp/current_workdir_ts`)
4. Work copy: auto-clean on success (see above); keep after a FAILED run for
   `--reuse-workdir`

Guardrails: never remove the SWR-tagged image referenced by the algorithm asset, the
base image, any image/tag/container this run did NOT create, or any file outside
`/tmp`/the work copy. These local-only artifacts need **no customer confirmation**
(unlike platform junk — see `§` §Part 1A/1B).

### Phase Boundary Summary 阶段边界速览

Every phase validates its inputs before starting; missing required information is
**asked from the user**, and every mutating operation requires **explicit confirmation**:

| Phase | Key Inputs | Must Ask When Missing | Mutation Confirmation |
|-------|-----------|------------------------|-----------------------|
| 0 Image decision | workspace_id, catalog_id, image assets list | workspace/catalog_id; docker login command only when auto-generation (from AK/SK) or login fails | — |
| 1 Code adaptation | source dir, operator_config.yaml, src/, requirements.txt | source path, config file, missing fields | — |
| 2 Build & push | work copy, docker daemon, SWR URL, login cmd | base image (pull fail), login cmd (auto-login fail) | docker push |
| 3 Asset creation | image_url, catalog_id, ext_metadata | catalog_id, image_url (do Phase 2 first) | both create-asset calls |
| 4 Runtime verification | algorithm_asset_id, input-dataset source, dataset(s), output_name | dataset source (① 空间资产-数据-新建 / ② 空间资产-数据-复用 / ③ OBS存储 direct path), dataset selection, unique output_name | create-task; Source ①: create-asset `type=dataset` + create-version + update-version RELEASE; Source ③ (OBS存储): **no dataset asset created or referenced** (direct `UDF_OBS_ASSET` entry) |

See `§` for the full boundary matrix.

---
## Phase Boundaries 阶段边界

### Contents 目录

- Overview 概述
- Skill Generality 通用性约定
- OBS Boundary OBS操作边界
- Global Ask-User Checklist 全局确认清单
- Phase 0 — Deploy Mode & Asset Detection 部署方式与资产检测
- Phase 1 — Code Adaptation 代码适配
- Phase 2 — Build & Push 镜像构建推送（Mode A only；Mode B 跳过本阶段）
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
- The only OBS uploads the skill may perform are **confirmed mutations**: Mode B code
  delivery and Phase 4 Source ① data upload (both via the OBS client, confirmed with
  the customer first)

### Global Ask-User Checklist 全局确认清单

Before the pipeline starts and at each phase boundary, confirm with the user:

> **对话话术与确认要点（每轮一问、二次确认话术）的唯一权威定义在
> `custom-operator-reference.md`（§4 高危操作确认清单）** — 本表仅列出"何时必须问/问什么"，
> 不重复维护话术。

| Item | Required Before | Ask When Missing |
|------|-----------------|------------------|
| `workspace_id` | Phase 0 | No default workspace — ask user to run `cloudrobo workspace use --workspace-id <id>` |
| `catalog_id` | Phase 0 / 3 | Not present in `cloudrobo workspace current` output |
| Deploy mode | Phase 0 | **Ask the customer: A (image-inbuilt) or B (OBS-mounted)?** — mandatory choice |
| Mode B: task-creation way (空间资产-算法 / OBS算法) | Phase 0 / 4 | **⛔ Ask the customer: 空间资产-算法 use the created algorithm (`WORKSPACE_ASSETS` + `algo_id` = Phase 3 asset_id) or OBS算法 mount the OBS code directly (`OBS_ASSETS`, no `algo_id`)?** — mandatory choice; re-ask until unambiguous |
| Mode B: OBS path | Phase 0 | **Ask the customer for the OBS path** of their already-uploaded code; must start with workspace `default_obs_path` (used as `code_dir` in 空间资产-算法's Phase 3; directly as `algo_path` in Phase 4) |
| Mode B: container injection path | Phase 0 / 4 | If not provided, **use the default** `/tmp/cloudrobo/{operator-name}` and inform the customer |
| Mode B: preset runtime image | Phase 0 | **Ask the customer** for a `swr.{region}.myhuaweicloud.com/...` image (registered as an image asset in Phase 3 only for 空间资产-算法) |
| AK/SK | Phase 0 | **Never configured (no env vars, no config file) or expired (`401`/`unauthorized`)** — proactively remind the customer to configure / update the AK/SK (see `../cli-installation-guide.md` §4.1) |
| Docker login command | Phase 2 | A new image is always registered (Mode A) — skill **auto-generates** it from AK/SK first; ask the user only when generation/login fails |
| Operator source directory | Phase 1 | Path not provided or does not exist |
| `operator_config.yaml` | Phase 1 | File missing in source directory |
| Base image (`image.base`) | Phase 2 | Pull fails — ask for a reachable image |
| Input dataset source | Phase 4 | **Ask the customer: ① 空间资产-数据-新建数据集 (auto create asset), ② 空间资产-数据-复用已有资产, or ③ OBS存储 (direct `obs://` path, `UDF_OBS_ASSET`, no dataset asset)?** — mandatory choice; re-ask until unambiguous |
| Input dataset | Phase 4 | Source ② finds no workspace dataset — remind the user to upload data first (or switch to Source ①, where the skill auto-creates the dataset) |

### Phase 0 — Deploy Mode & Asset Detection 部署方式与资产检测

**Input prerequisites:** valid `workspace_id` + `catalog_id`; Docker CLI available
(Mode A only).

> **⛔ MANDATORY — the deploy mode MUST be chosen by the customer, first.**
> The very first Phase 0 action is to ask the customer for Mode A or Mode B and wait
> for their explicit answer. **Never infer the mode** from base images, existing
> local/SWR images, historical assets, customer-provided URLs, task wording, or any
> other environment clue. If the answer is missing or ambiguous, **re-ask until
> unambiguous**. No Phase 1 work (work copy, entrypoint, Dockerfile/operator_config
> assembly) may start before the mode is confirmed.

| # | Boundary Condition | Detection | Handling / Ask User |
|---|--------------------|-----------|---------------------|
| 0.1 | No workspace selected | `cloudrobo workspace current` fails or returns no id | **Ask** the user to select/confirm a workspace; abort if declined |
| 0.2 | No `catalog_id` in workspace info | `workspace current` output lacks `asset_catalog_id` | **Ask** the user for the workspace catalog_id |
| 0.3 | Deploy mode not chosen / ambiguous | Customer has not answered, or answers "都可以/你看着办", or agent cannot confirm a clear A or B | **⛔ MUST ask (and re-ask until unambiguous)**: Mode A (image-inbuilt, `custom`) or Mode B (OBS-mounted, `preset`)? **Never infer the mode from any environment clue.** 对话话术：「请选择算子的部署方式：方式A【镜像内置】代码打包进镜像、每次重新构建推送；方式B【OBS挂载】代码放 OBS、用预设镜像不构建。请问使用哪种方式？」 |
| 0.3a | Mode B: task-creation way not chosen / ambiguous | Customer has not answered, or answers "都可以/你看着办" | **⛔ MUST ask (and re-ask until unambiguous)**: 空间资产-算法 (use the created algorithm, `WORKSPACE_ASSETS` + `algo_id` = Phase 3 asset_id) or OBS算法 (mount the OBS code directly, `OBS_ASSETS`, no `algo_id`)? 对话话术：「请选择本算子创建任务时的算法引用方式：**空间资产-算法**【引用已注册的算法资产，任务关联算法资产运行，会执行资产注册】；**OBS算法**【直接挂载 OBS 路径上的代码运行，不关联算法资产，跳过资产注册】。请问使用哪种？」 |
| 0.4 | Mode A: any image-asset state (exist or not) | `list-assets --type image --tags "Data Processing" --exact-name <name>` (any result) | **Always register a new image** — a fresh tag is built and pushed on every run (operator code lives inside the image); no "use existing image" question |
| 0.5 | Mode B: OBS path missing / not under workspace `default_obs_path` | Customer path does not start with workspace `default_obs_path` | **Ask** the customer for the OBS path of their code; reject/re-ask if the prefix does not match |
| 0.5a | Mode B: code upload mode not chosen | Customer has not answered | **对话话术（对客户）**：「生成代码后，由谁上传到 OBS：自行上传，还是由我上传（先确认）？」 |
| 0.5b | Mode B: OBS endpoint unresolvable | `obs.{region}.myhuaweicloud.com` → NXDOMAIN | **对话话术（对客户）**：「默认 OBS 端点无法解析，请提供可达端点（如 `obs.cn-southwest-2.myhuaweicloud.com`）」；set on `Config.endpoints['cloudrobo-obs']` |
| 0.6 | Mode B: container injection path missing | `job_local_path` not provided | **Use the default** `/tmp/cloudrobo/{operator-name}` and inform the customer |
| 0.7 | Mode B: preset runtime image missing / not SWR format | No image provided or regex fails | **Ask** the customer for a preset runtime image in `swr.{region}.myhuaweicloud.com/...` format (registered as an image asset in Phase 3 only for 空间资产-算法) |
| 0.8 | Same-name algorithm asset exists (Mode A / Mode B 空间资产-算法) | `list-assets --type algorithm --tags "Data Processing" --exact-name <name>` returns non-empty | Record as **re-submission** |
| 0.9 | Same-name algorithm asset does not exist (Mode A / Mode B 空间资产-算法) | `list-assets --type algorithm --tags "Data Processing" --exact-name <name>` returns empty | Record as **first submission** (OBS算法: not applicable — Phase 3 skipped) |
| 0.10 | Mode A: auto-generated login command fails | Output ≠ "Login Succeeded" (`unauthorized` / `Authenticate Error` / `no permission`) | **Classify & walk the fix** (Step 2.0 §Login failure): AK/SK invalid/expired, SWR not enabled / IAM permission missing, region mismatch, network — remind the customer to update AK/SK / enable SWR / fix region, confirm when done; **ask** for a full `docker login ...` command; retry with the user-provided command and require `Login Succeeded` |
| 0.11 | Mode A: user-provided login command malformed | Not starting with `docker login`, or no registry host | Point out the missing parts; **ask** for a corrected full command |
| 0.12 | Mode A: user-provided login command fails | Output ≠ "Login Succeeded" (`unauthorized` etc.) | **Remind the customer to update the AK/SK**; ask to re-check host/user/password; retry |
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
| 1.13 | Mode B: skill uploads code to OBS | `OBSClient.upload_folder` to the OBS path | **Confirm with the customer first** (writes to OBS); verify with `list_objects`; if the endpoint is unresolvable, ask for a reachable one. Code = 3 files + `src/` → serial is fine; large payloads → concurrent sharded upload (`§`) |
| 1.14 | Mode B: customer uploads code | Customer chose option A | Present the file list (`entrypoint.py`, `src/`, `requirements.txt`) + target OBS path; **wait for the customer to confirm** before Phase 3 (空间资产-算法) / Phase 4 (OBS算法, Phase 3 skipped) |

### Phase 2 — Build & Push 镜像构建推送（Mode A only；Mode B 跳过本阶段）

**Input prerequisites:** Mode A — valid work copy, Docker daemon running, validated
SWR target URL, docker login command (auto-generated from AK/SK in Phase 0;
user-provided as fallback). **Mode B — skip this phase entirely.**

| # | Boundary Condition | Detection | Handling / Ask User |
|---|--------------------|-----------|---------------------|
| 2.0 | Mode B selected | Phase 0 flag | **Skip this phase** — no docker login / build / push; go straight to Phase 3 (空间资产-算法) / Phase 4 (OBS算法, Phase 3 skipped) |
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

**Input prerequisites:** Mode A — `image_url` (from Phase 2); Mode B **空间资产-算法** —
customer OBS path (`code_dir`); `catalog_id`, validated ext_metadata, and the Phase 0
deploy-mode + first-submission / re-submission flag. **Mode B OBS算法 — skip this
phase entirely** (no assets needed).

| # | Boundary Condition | Detection | Handling / Ask User |
|---|--------------------|-----------|---------------------|
| 3.0 | Mode B OBS算法 selected | Phase 0 flag | **⛔ Skip Phase 3 entirely** — no image/algorithm assets to register; go straight to Phase 4 (asset registration would be redundant for a direct OBS mount) |
| 3.1 | Mode A: `image_url` missing | Phase 3 entry check | Error "complete Phase 2 first" |
| 3.2 | Mode B 空间资产-算法: `code_dir` missing / not under workspace `default_obs_path` | Config check | **Ask** the customer for a valid OBS path under the workspace-bound OBS path |
| 3.3 | `catalog_id` missing | Config check | **Ask** the user for the workspace catalog_id |
| 3.4 | Mode A first submission (no same-name algorithm asset) | Phase 0 flag | Two `create-asset` calls: `type=image` **FIRST** then `type=algorithm` — **image asset MUST succeed before algorithm asset creation** |
| 3.4a | Image asset creation fails (Mode A / Mode B 空间资产-算法) | `create-asset --type image` returns error (e.g. `400 SWR image not available`) | **⛔ DO NOT create the algorithm asset.** Fix the image issue first (docker login + push if `400 SWR image not available`), retry `create-asset --type image` until it succeeds, THEN create the algorithm asset. The algorithm's `engine.image_url` references the image registered by the image asset — creating the algorithm before the image asset exists produces a broken algorithm |
| 3.5 | Mode A re-submission (same-name algorithm asset exists) | Phase 0 flag | `create-version` on the image asset (new SWR URL) + `update-asset` on the algorithm asset (new `engine.image_url`); **no new algorithm version** |
| 3.6 | Mode B 空间资产-算法 first submission | Phase 0 flag | Register the **preset image as an image asset** (`type=image`) **FIRST** — on `400 SWR image not available`: docker login + push + retry — THEN **one** `create-asset --type algorithm` (`image_source=custom`, `engine.asset_id` + `engine.asset_version_id` link the image asset, `code_dir`=OBS path). **Image asset MUST succeed before algorithm asset; algorithm MUST link the image asset** |
| 3.7 | Mode B 空间资产-算法 re-submission | Phase 0 flag | preset image changed → `create-version` on the image asset + `update-asset` on the algorithm asset (keep `engine.asset_id`, re-point `engine.asset_version_id` to the new image version); preset image unchanged → single `update-asset` (`code_dir`, keep both `asset_id`/`asset_version_id`); **no new algorithm version** |
| 3.8 | ext_metadata exceeds a limit | Validation (command 4096 / inputs 10 / outputs 5 / env 90 / hyper 90) | Report field + limit + current count; **ask** user to adjust config |
| 3.9 | Mode B 空间资产-算法: algorithm asset not linked to the image asset | `show-asset` shows `engine` without `asset_id`/`asset_version_id` (or with `image_source=preset`) | **Fix the algorithm asset** — `update-asset` to set `engine.asset_id` + `engine.asset_version_id` (from the image asset) + `image_source=custom`; the algorithm MUST use the created 空间资产-镜像 (verified e2e umi_to_lerobot_v3 / demo asset `72cb8aeb`); do not proceed until linked |
| 3.10 | env var `default` empty | Validation | Error "default format invalid: 1-512 chars"; **ask** user to set a non-empty default |
| 3.11 | `sub_type` + `tags` both passed | Request assembly | Omit `sub_type` (documented 400 workaround); do not ask — apply the fix |
| 3.11a | `create-asset --type image` returns `400 SWR image not available` | Image not actually present in SWR (cleaned up / only local) | **`docker login` + `docker push` the image to the SWR URL, then retry the `create-asset --type image` call** (Mode B preset image; also applies to Mode A after a fresh push) |
| 3.12 | POST /v1/assets (or versions/update) 401 | API response | Error "Authentication failed" — **remind the customer to update the AK/SK** (expired/invalid) and retry |
| 3.13 | POST /v1/assets (or versions/update) 403 | API response | Error "Permission denied"; check `cloudrobo:assets:create`/`update`; ask retry after fix |
| 3.14 | POST /v1/assets (or versions/update) 429 | API response | Exponential backoff (3 attempts); then error and ask retry |
| 3.15 | POST /v1/assets (or versions/update) 500 | API response | Output error code + traceId; ask to contact support |
| 3.16 | Mode A: image asset created, algorithm step fails (first submission) | Second call fails | Keep `image_asset_id`; fix payload; retry only the algorithm call |
| 3.17 | Mode A: image `create-version` succeeds but `update-asset` fails (re-submission) | Second call fails | Image version exists but algorithm still points at the old image; report and ask whether to retry or roll back |
| 3.18 | **Mutation: every create-asset / create-version / update-asset call** | Before each submit | **Confirm with the user** (creating/updating real platform assets) |
| 3.19 | `show-asset` verification fails | Status ≠ DRAFT/available | Report; ask whether to re-verify, recreate, or abort |

### Phase 4 — Runtime Verification 运行时验证

**Input prerequisites:** `algorithm_asset_id` (Mode A); Mode B — the **task-creation
way** (空间资产-算法: `algorithm_asset_id` + OBS path (`algo_path` = asset `code_dir`) +
`job_local_path`, Phase 3 assets exist; OBS算法: customer OBS path + `job_local_path`
only, **Phase 3 skipped — no assets**) plus the chosen **input-dataset source**
(① 空间资产-数据-新建 / ② 空间资产-数据-复用 — user-selected when multiple exist
/ default when exactly one / ③ OBS存储 direct path `UDF_OBS_ASSET` — no asset), a
unique `output_name`.

| # | Boundary Condition | Detection | Handling / Ask User |
|---|--------------------|-----------|---------------------|
| 4.0 | Dataset source not chosen | Phase 4 started without the choice | **⛔ MUST ask (and re-ask until unambiguous): ① 空间资产-数据-新建数据集 (auto create asset), ② 空间资产-数据-复用已有资产, or ③ OBS存储 (direct `obs://` path, `UDF_OBS_ASSET`, no dataset asset)?** — never infer the source. 对话话术：「请选择本次验证的数据来源：① **空间资产-数据-新建数据集**【您先将数据上传到 OBS，我自动创建数据集资产并用于验证】；② **空间资产-数据-复用已有数据集**【从工作空间已有数据集资产中选择】；③ **OBS存储**【直接输入 `obs://` 路径作为输入，不创建、不引用数据资产】。请问使用哪种？」 |
| 4.0a | Source ①: OBS data path missing | Customer provides no path | **Ask** the customer for the raw-data OBS path; confirm the data is already uploaded (the skill may upload a local data dir after confirmation, a mutation — for large datasets use the concurrent sharded upload per `§`, never a serial walk) |
| 4.0e | Source ③ (OBS存储): OBS path missing / malformed / **foreign bucket** / multiple paths | Customer provides no path, a path not starting with `obs://`, a path whose **bucket ≠ workspace-bound bucket** (`default_obs_path` bucket from `cloudrobo workspace current`), or later mentions extra paths | **Ask** for valid `obs://` path(s) — one question per round; format-validate (**no OBS browsing**) **and validate the bucket**: show the workspace `default_obs_path` as reference, **reject & re-ask any foreign-bucket path** (other OBS buckets NOT supported); data must already be in place (empty path → task stuck in `POD_PENDING`). **Multiple paths are collected into ONE task**: each path becomes one `dataset_configs` entry `{"obs_path":"<url>","dataset_type":"UDF_OBS_ASSET"}` (≤10 entries) — **single create-task, never one task per path** |
| 4.0b | Source ①: dataset name duplicate | `400 The asset name is existed` | Use a unique per-run name (timestamp suffix, e.g. `{operator-name}-input-{YYYYMMDDHHMMSS}`) or **ask** the customer |
| 4.0c | Source ①: dataset version not RELEASE | Version status `CREATING`/`DRAFT` | **Always publish `RELEASE`**: `cloudrobo asset update-version --asset-id <id> --version-id <vid> --status RELEASE` — otherwise the task reports "dataset not ready" |
| 4.0d | Source ①: data path empty | Customer confirms data not uploaded / path empty | **Remind the customer to upload the raw data files to the OBS path first**; task would stay in `POD_PENDING` |
| 4.1 | Source ②: no dataset in workspace | `list-assets --type dataset` empty | **Remind the user to upload data first** — offer **Source ①** (skill auto-creates the dataset) or **Source ③ OBS存储** (direct `obs://` path, no asset) or see the parent `cloudrobo-dataset` skill; never proceed with a fabricated path |
| 4.1a | Source ②: dataset selection | `list-assets --type dataset` | **Exactly one → use it by default (no confirmation); multiple → ask the user to multi-select (max 10)** (one task may process multiple datasets) |
| 4.2 | More than 10 datasets selected | Selection exceeds 10 | **Enforce the 10-max limit** — tell the customer the maximum is 10 and ask them to trim |
| 4.3 | Mode B: OBS code not uploaded | Code path empty / customer confirms | **Remind the customer to upload the algorithm code first** (`entrypoint.py` / `src/` / `requirements.txt`) — an empty path keeps the task in `POD_PENDING`; 空间资产-算法: verify the algorithm asset `code_dir` via `show-asset` points to the populated path |
| 4.4 | Dataset URL unknown | `dataset_configs` assembly | Use each selected dataset asset's `url` (from `list-assets`/`show-asset`); if absent, ask the user |
| 4.5 | Multiple datasets selected | `dataset_configs` assembly | **ONE task only**: one `dataset_configs` entry per selected dataset/path (`obs_path`/`asset_id`/`asset_name`/`version_id`; Source ③ OBS存储 entries use only `obs_path` + `dataset_type=UDF_OBS_ASSET`), **all entries in the single task's array (≤10); never one task per dataset** (拆分多条任务仅限用户显式要求批量场景，且需先确认) |
| 4.6 | Mode A task config | `algo_type` | `WORKSPACE_ASSETS` with `algo_id` = algorithm `asset_id` |
| 4.6a | Mode B: task-creation way not chosen | Phase 4 entry check | **⛔ MUST ask (and re-ask until unambiguous): 空间资产-算法 use the created algorithm (`WORKSPACE_ASSETS` + `algo_id`, Phase 3 registers assets) or OBS算法 mount the OBS code directly (`OBS_ASSETS`, no `algo_id`, **Phase 3 skipped — no asset registration**)?** — never infer the way |
| 4.7 | Mode B task config — 空间资产-算法 (use the created algorithm) | `algo_type` | `WORKSPACE_ASSETS` with `algo_id` = Phase 3 algorithm `asset_id` + `algo_name` (**required**) + `algo_path` (= asset `code_dir`, **required**) + `job_local_path` (**required**) + **absolute** `algo_entrance` (`python3 {job_local_path}/entrypoint.py`) + `image` (preset SWR URL). Verified e2e — omitting `algo_path`/`job_local_path` fails with `//entrypoint.py` |
| 4.7a | Mode B task config — OBS算法 (mount the OBS code directly) | `algo_type` | `OBS_ASSETS` with `algo_name` (**required**) + `algo_path` (customer OBS path) + `job_local_path` (default if not provided) + absolute `algo_entrance` + `image` (preset SWR URL); **no `algo_id`** |
| 4.8 | `output_name` duplicate | 400 "The asset name is existed" | Auto-suffix with timestamp, or **ask** the user for a unique name |
| 4.9 | `envs` empty array | Task config contains `"envs": "[]"` | Omit `envs` entirely (400 worker_spec workaround) |
| 4.10 | Task stuck / timeout | `--wait` times out | Report status + elapsed; **ask**: continue waiting / view logs / terminate |
| 4.11 | 任务已创建后取消 / 修改参数重发 | 用户要求取消或"改了参数再创建一个新任务"，且存在已创建任务 `{task_id}`（PENDING/RUNNING 等） | **⛔ 必须先与用户确认删除/停止旧任务**：展示「任务 {id}（{status}）仍在平台运行」→ 询问「是否删除/停止旧任务？① 删除（不可恢复，立即终止）② 保留运行 ③ 先查看日志」→ 选①执行 `delete-task` 并 `show-task` 验证 `DELETED`；**未确认删除前禁止创建新任务**（否则前端残留执行任务 + 重复计费） |
| 4.11a | Task FAILED | Final status FAILED | Run failure analysis on `job-std-output.log`; show cause + fix; Mode A: fix & rebuild image; Mode B: customer fixes code on OBS; **ask**: fix & rerun or abort |
| 4.12 | SUCCEEDED but no output frames | `get-frames` empty | Check `output_name`/`output_path` and entrypoint output dir; fix, rebuild, rerun |
| 4.13 | User log shows failed items | `[DONE] ... 失败 N > 0` | Inspect per-item traceback; **ask** user to fix `process()` and rerun |
| 4.14 | **Mutation: create-task** | Before submitting | **Confirm with the user** (runs real computation, produces an output asset) |
| 4.15 | `task_id` not at top level | Response shape | Read `payload.id` (documented SDK behavior); do not error |
| 4.16 | `create-task` returns HTTP 500 on a re-run after rebuild | Post-image-rebuild task submission fails | Check algorithm asset linkage first (`show-asset`: `engine.image_url`/`engine.asset_version_id` ⇒ **new** image version), use a fresh `output_name`, wait ~30 s, retry once; still 500 → capture `trace_id` + system log, contact support (see §Failure Analysis Guide) |

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
| Deploy mode | 0 | **Ask the customer: A (image-inbuilt) or B (OBS-mounted)?** |
| Mode B: OBS path (`code_dir` / `algo_path`) | 0 / 3 | **Ask the customer** for their already-uploaded OBS path; must start with workspace `default_obs_path` |
| Mode B: container injection path (`job_local_path`) | 0 / 4 | If not provided, **use the default** `/tmp/cloudrobo/{operator-name}` |
| Mode B: preset runtime image | 0 / 3 | **Ask the customer** for a `swr.{region}.myhuaweicloud.com/...` image |
| AK/SK (never configured) | 0 | **Proactively remind the customer to configure the AK/SK** (env vars or `~/.cloudrobo/config.yaml`, see `../cli-installation-guide.md` §4.1); pause until confirmed |
| AK/SK (expired / invalid) | 0 / 2 / 3 | **Proactively remind the customer to update the AK/SK** (regenerate in IAM, refresh config) on `401` / `unauthorized`; do not retry the failed call in a loop |
| Docker login command | 0 / 2 | Skill auto-generates it from AK/SK (official SWR long-lived login command); ask the user for the full command only when generation/login fails |
| Source directory | 1 | Ask user for the correct path |
| `operator_config.yaml` | 1 | Ask user to provide the file |
| Required config fields | 1 | List missing fields; ask user to complete |
| `image.base` (reachable) | 2 | Ask user for a base image their build env can pull |
| `image_url` | 3 | Complete Phase 2 first (Mode A; a new image is always built on every run) |
| Input-dataset source | 4 | **Ask the customer: ① 空间资产-数据-新建数据集 (auto create asset), ② 空间资产-数据-复用已有资产, or ③ OBS存储 (direct `obs://` path, `UDF_OBS_ASSET`, no dataset asset)?** (mandatory) |
| Input dataset (Source ①) | 4 | Ask the customer for the OBS data path; confirm the data is uploaded; auto-create the dataset (create-asset `type=dataset` + create-version + `update-version --status RELEASE`); unique name + `RELEASE` version |
| Input dataset (Source ②) | 4 | Query `list-assets --type dataset`; **none → remind the user to upload (or switch to ① / ③ OBS存储); one → use by default; multiple → ask the user to multi-select** |
| Input dataset (Source ③ OBS存储) | 4 | Ask the customer for a **valid `obs://` path** (format-validated + **bucket must equal the workspace-bound bucket** — `default_obs_path` from `cloudrobo workspace current`; show it as reference, other OBS buckets NOT supported, mismatch → reject & re-ask, no OBS browsing); dataset_configs entry = `{"obs_path":"<url>","dataset_type":"UDF_OBS_ASSET"}`; **no dataset asset, no `RELEASE`, no create-asset** |
| Unique `output_name` | 4 | Ask user or auto-suffix with a timestamp |

### Mutation Confirmation Table 变更操作确认表

> 覆盖性变更（re-submission 的 update-asset / create-version、删除类操作）还须说明
> 「旧版本/旧数据保留或不可恢复的后果」——二次确认话术见 `custom-operator-reference.md`
> §4（本表仅列操作 × 阶段 × 是否需要确认）。

| Operation | Phase | Confirmation |
|-----------|-------|--------------|
| `docker login` / `docker push` (publish image) | 2 | **Required** — confirm before push (Mode A only) |
| `OBSClient.upload_folder` (Mode B skill upload) | 1 | **Required** — writes the generated code to the customer's OBS path |
| `cloudrobo asset create-asset --type image` (Mode A first submission) | 3 | **Required** — creates a real image asset |
| `cloudrobo asset create-asset --type algorithm` (Mode A/B first submission) | 3 | **Required** — creates a real algorithm asset |
| `cloudrobo asset create-version` (Mode A re-submission) | 3 | **Required** — creates a real image asset version |
| `cloudrobo asset update-asset` (Mode A/B re-submission) | 3 | **Required** — updates the algorithm asset's `engine.image_url` / `code_dir` |
| `OBSClient.upload_folder` (Phase 4 Source ① data upload) | 4 | **Required** — writes the customer's raw data to the OBS path |
| `cloudrobo asset create-asset --type dataset` (Phase 4 Source ①) | 4 | **Required** — creates a real dataset asset (Source ③ OBS存储 direct path creates/references NO dataset asset — no confirmation beyond the path itself) |
| `cloudrobo asset create-version` (dataset version, Phase 4 Source ①) | 4 | **Required** — binds the dataset to the customer's OBS data path |
| `cloudrobo asset update-version --status RELEASE` (Phase 4 Source ①) | 4 | **Required** — publishes the dataset version (non-RELEASE → "dataset not ready") |
| `cloudrobo dataset proc create-task` | 4 | **Required** — runs real computation, produces an output asset |
| `cloudrobo dataset proc delete-task` (garbage cleanup) | 4 | **Required** — deletes a failed task record (junk); `show-task` first: name/owner/creation time must belong to this run |
| `cloudrobo asset delete-asset` / `delete-version` (garbage cleanup) | 4 | **Required** — deletes failed-task/stale output datasets or versions; `show-asset` first (name prefix + owner + creation time), list exact names/IDs; **never** the operator's image/algorithm assets or customer datasets |
| Verification-report.md generation | 4 | **Required** — ask the customer whether to generate; only useful info, no trial-and-error steps (see `§` §Part 2) |
| Work copy cleanup | all | Non-destructive to user code — no confirmation needed (but inform) |

---
## Garbage Cleanup & Verification Report 垃圾清理与验证报告

### Contents 目录

- Overview 概述
- Part 1A: Server-Side Local Junk Cleanup 服务器本机垃圾清理（必做）
- Part 1B: Platform Garbage Cleanup 平台垃圾数据清理（询问制）
- Part 2: Verification Report 验证报告（Markdown）
- Relationship 与现有章节的关系

### Overview 概述

Every verification run leaves artifacts in two places: **on the CloudRobo platform**
and **on the build host (server)**. Both must be handled when the verification ends.

**Platform artifacts** (require customer confirmation to delete):

- **Failed proc-tasks** (`FAILED` status) — records of every failed attempt
- **Target dataset assets auto-created by failed tasks** — `create-task` pre-creates
  the output asset (`BUILD_IN_ASSET`) even when the task later fails; these stay as
  `DRAFT`/`CREATING` datasets
- **Historical output datasets** — each successful run also leaves an
  `{operator}-output-{timestamp}` dataset; repeated verifications accumulate them
- **Local work copies** — `/tmp/custom-operator-work-*` (see the work-copy lifecycle)

**Build-host (server) artifacts** (**MUST be cleaned automatically** — they are not
platform assets, only consume server disk):

- Throwaway local Docker images (network probe/test images, local duplicate of a Mode
  B preset image after SWR push, Mode A intermediate tags) — **only this run's**
- Exited containers + dangling images + build cache — **only this run's** (see Part 1A
  safe command set; never blanket `container prune` / `image prune -af` / `system prune`)
- `/tmp` build scratch dirs & logs, and the work copy (on success) — **only this run's**

After verification ends (success or final failure), the skill **MUST execute the
cleanup steps below — cleanup is a mandatory Phase 5 of the onboarding workflow,
NOT optional and never silently skipped**:

1. **Server-side local junk cleanup 服务器本机垃圾清理（必做，无需询问）** — always
   executed, no customer confirmation needed (safe local-only artifacts; see Part 1A)
2. **Platform garbage cleanup 平台垃圾清理（询问制，必问）** — delete this run's
   failed-task junk (and, if the customer wants, stale historical outputs); **the
   cleanup question MUST be asked at the end of every verification** — never finish a
   run without asking (see Part 1B)
3. **Verification report** — generate a concise `verification-report.md` documenting
   the verification result (**only useful information; trial-and-error attempts are
   NOT shown**); ask first

> **⚠️ Completion checklist — every verification run (success OR failure) must reach
> this state before the skill considers the task done:**
>
> | Step | Action | Trigger |
> |------|--------|---------|
> | 1 | Part 1A server-side local junk cleanup (this-run-only docker cleanup, `/tmp` scratch, work copy) | **Always** — no confirmation needed, never skip; scope = this run's artifacts only, customer images/containers untouched |
> | 2 | Part 1B platform junk cleanup question (failed tasks + stale output assets list, then delete on confirmation) | **Always ask** — never finish without asking |
> | 3 | Part 2 verification report (optional, ask first) | Ask |
>
> Missing any of the three means the onboarding workflow is **incomplete**. Failed
> task records (`FAILED` status) and their auto-created target dataset assets are
> platform junk and **must be listed + confirmed + deleted** per Part 1B.

### Part 1A: Server-Side Local Junk Cleanup 服务器本机垃圾清理（必做）

#### Principles 原则

- **Always run after the verification ends** (success or final failure) — this is NOT
  optional and does NOT need customer confirmation (these artifacts only consume build
  host disk; they are not platform assets and deleting them cannot affect the
  onboarded operator or its outputs).
- **Never remove:** the SWR-tagged image the algorithm asset references, the base
  image, the work copy after a **FAILED** run (keep for `--reuse-workdir`), or any
  file outside `/tmp` / the work copy. If the customer wants to keep a local copy of
  the built/preset image, skip its removal.
- **⚠️ Scope = ONLY this verification's artifacts.** On a shared Docker daemon the
  build host may hold the customer's own images, containers, and caches. Every
  cleanup below is limited to artifacts **proven to be produced by THIS run**:
  - **Never `docker rmi` / `docker image prune` a tagged image that this run did not
    build** (covers all customer idle images, tagged or untagged). Before deleting a
    throwaway tag, verify with `docker image inspect <tag> --format '{{.Id}}'` that
    its digest matches the build record; otherwise skip and warn.
  - **Never run an unfiltered `docker container prune -f`** — it removes EVERY exited
    container on the host, including the customer's. Remove only containers whose IDs
    were recorded by this run (`docker rm <id>`), or use
    `--filter label=cloudrobo-verification=<run-id>` when labels were set at `docker run`.
  - **Dangling-image precheck:** run `docker images --filter dangling=true` FIRST and
    inspect the list. Only delete dangling images whose ID/digest is provably from this
    run (usually none — every build product is tagged). Any dangling image of unknown
    origin is kept and reported to the customer — never blanket-pruned.
  - **`docker builder prune` is safe** for image data (it only clears build cache, no
    image is removed; rebuilds are slower afterwards but no data is lost). Note Docker
    has no "created after" filter for prune — `--filter until=<t>` removes OLDER
    entries, so it does NOT narrow cleanup to this run's cache; on a shared daemon the
    cache is expendable either way.

#### Commands 命令

```bash
RUN_ID=<workdir timestamp, e.g. custom-operator-work-20260924154534>

# 0. READ-ONLY precheck — list what exists BEFORE deleting anything
docker images --filter dangling=true --format '{{.ID}}  {{.CreatedSince}}  {{.Size}}'   # dangling-image inventory
docker ps -a --filter status=exited --format '{{.ID}}  {{.Image}}  {{.Names}}'          # exited-container inventory

# 1. throwaway / probe / test images + local preset duplicate (after SWR push) —
#    delete ONLY tags this run built; verify digest first
docker image inspect <probe-image>:<tag> --format '{{.Id}}'   # must equal the recorded build digest
docker rmi <probe-image>:<tag> 2>/dev/null || true
docker image inspect <operator>:fix --format '{{.Id}}'        # same digest check
docker rmi <operator>:fix <operator>:<tmp-tag> 2>/dev/null || true

# 2. exited containers — ONLY this run's containers (recorded IDs or label filter);
#    NEVER `docker container prune -f` without a filter
docker rm <recorded-container-id> 2>/dev/null || true
# or, if containers were started with --label cloudrobo-verification=$RUN_ID:
docker container prune -f --filter "label=cloudrobo-verification=$RUN_ID" 2>/dev/null || true

# 3. dangling images — delete ONLY dangling IDs whose digest matches a build record
#    from this run (per the precheck); unknown-origin dangling images are KEPT and
#    reported. NOTE: `docker image prune` (with or without --filter) targets ALL
#    dangling images on the host — prefer per-ID `docker rmi <id>` over blanket prune.
docker rmi <proven-dangling-image-id> 2>/dev/null || true   # only after digest match
# do NOT run `docker image prune -f` on a shared daemon unless the precheck list is
# empty or every entry is proven to belong to this run

# 4. build cache — SAFE: `docker builder prune` removes NO image, only rebuild cache;
#    rebuild cost is the only side effect, so it may run unfiltered
docker builder prune -f 2>/dev/null || true

# 5. /tmp — ONLY this run's named scratch dirs & logs; never rm anything else in /tmp
rm -rf /tmp/preset-image-build /tmp/build-probe 2>/dev/null || true
rm -f /tmp/preset-build.log /tmp/preset-push.log /tmp/current_workdir_ts 2>/dev/null || true
# work copy: success → auto-clean; FAILED → keep for --reuse-workdir
```

> **⚠️ Anti-mis-deletion rules (apply to every command above):**
> - **Never delete a tagged image this run did not build** — a customer's idle tagged
>   image is NEVER a cleanup target, even on a shared build host.
> - **Never run an unfiltered `docker container prune -f` / `docker image prune -af` /
>   `docker system prune`** — these delete customer artifacts wholesale.
> - **Dangling images of unknown origin are always kept**, never blanket-pruned; list
>   them for the customer instead.
> - When in doubt (shared daemon, can't prove ownership), **skip and warn** rather than
>   delete.

> Full command list & guardrails: `§` §Cleanup & Image
> Housekeeping.

### Part 1B: Platform Garbage Cleanup 平台垃圾数据清理（询问制）

#### Cleanup Principles 清理原则

- **Only delete what THIS skill's verification produced** — never delete:
  - the operator's **algorithm asset** and **image asset** (the onboarding deliverable)
  - the customer's own input datasets
  - the **current successful** output dataset (it is the verification deliverable;
    keep it unless the customer explicitly asks to remove it)
- **Every deletion is confirmed with the customer** (list exactly what will be
  deleted: names + IDs, then ask 确认)
- **⚠️ Verify BEFORE every delete** — `show-asset` / `show-task` must confirm ALL of:
  (a) the object was created **by this verification run** (name prefix
  `{operator}-proc-*` / `{operator}-output-*`, `algo_name` = operator, creation time
  within this run's window), (b) owner = current user, (c) name does **not** match the
  operator's algorithm/image asset names. Any mismatch → **skip and warn**, never
  delete an unverifiable object (a name-prefix match alone is NOT proof of ownership —
  a customer dataset could coincidentally be named `{operator}-output-*`).
- Cleanup targets, by category:

| Junk category | How to find it | 必做校验（任一不符 → 跳过并警告） | Delete command |
|---------------|----------------|-----------------------------------|----------------|
| Failed proc-tasks | `cloudrobo dataset proc list-tasks` → `status=FAILED` created by this verification (name `{operator}-proc-*`, `algo_name` = operator) | `show-task --task-id` → name = `{operator}-proc-*`, `algo_name` = operator, owner = current user, created within this run | `cloudrobo dataset proc delete-task --task-id <task_id>` |
| Target asset of a failed task | the failed task's `target_asset_id` / `target_asset_name` (from `show-task`) | `show-asset --asset-id` → name = the failed task's `target_asset_name`, owner = current user, created within this run, name ≠ operator's algorithm/image asset | `cloudrobo asset delete-asset --asset-id <asset_id>` |
| Stale historical output datasets | `cloudrobo asset list-assets --catalog-id <id> --type dataset` → name matches `{operator}-output-*`, older than the current run | 逐条 `show-asset` → name = `{operator}-output-*`, owner = current user, created before the current run (NOT the customer's own dataset) | `cloudrobo asset delete-asset --asset-id <asset_id>` |
| Local work copies | `/tmp/custom-operator-work-*` | 目录时间戳 = 本次验证的 workdir（绝不清理客户自建目录） | work-copy lifecycle (`--clean-workdir` / retention rules) |

> **Why failed tasks leave junk:** `create-task` pre-creates the output asset
> (`target_asset_id` / `target_asset_name`) at submission time. If the task fails, the
> asset stays as `DRAFT` (or `CREATING`) forever — delete it together with the failed
> task record.

#### Cleanup Flow 清理流程

**On failure (before fixing & re-running):** ask the customer whether to delete the
failed task + its target asset **now**:
- 对话话术：「本次任务失败。是否需要我先清理这条失败任务及其产生的目标数据集资产 `{target_asset_name}`？清理后我再根据日志修复并重新验证。是否清理？① 清理 ② 保留（先排查日志）」

**After the final verification (success or user gives up):**
1. **Server-side local junk cleanup (always, no confirmation)** — remove ONLY this
   run's throwaway docker images (probe/test images, local preset duplicate, Mode A
   intermediate tags), this run's exited containers, proven dangling images / build
   cache, this run's `/tmp` scratch dirs & logs; on success also clean the work copy
   (safe command set — see `§Part 1A §Commands`):
   ```bash
   docker rmi <probe-image>:<tag> 2>/dev/null || true       # digest-checked, this run's only
   docker rm <recorded-container-id> 2>/dev/null || true    # NEVER unfiltered `docker container prune -f`
   docker rmi <proven-dangling-image-id> 2>/dev/null || true # only after precheck digest match
   docker builder prune -f 2>/dev/null || true               # cache only, no image removed
   rm -rf /tmp/preset-image-build /tmp/build-probe 2>/dev/null || true
   rm -f /tmp/preset-build.log /tmp/preset-push.log /tmp/current_workdir_ts 2>/dev/null || true
   ```
   (full list + guardrails: `§` §Cleanup & Image
   Housekeeping)
2. **Platform junk (confirmed)** — ask whether to clean up this run's failed attempts
   and stale outputs:
   - 对话话术：「验证流程结束。是否清理本次验证过程中产生的平台垃圾数据（失败的 N 条任务记录及其输出资产、历史的 M 个旧输出数据集 `{names}`）？清理不会删除算子的算法/镜像资产和本次成功验证的输出。① 全部清理 ② 只清理失败任务 ③ 保留」

**Verify the deletion** after each `delete-asset` / `delete-task`:
```bash
cloudrobo asset show-asset --asset-id <id>       # expect not found / 404
cloudrobo dataset proc show-task --task-id <id>  # expect not found / 404
```

#### Commands 命令

```bash
# delete a failed proc-task record
cloudrobo dataset proc delete-task --task-id <task_id>

# delete a stale/failed target dataset asset (and its versions)
cloudrobo asset delete-asset --asset-id <asset_id>

# delete a single asset version (when only the version, not the asset, is stale)
cloudrobo asset delete-version --asset-id <asset_id> --version-id <version_id>

# dry-run preview before real deletion
cloudrobo asset delete-asset --asset-id <asset_id> --dry-run
```

> **Safe-deletion guardrails:**
> - `delete-asset` removes the whole asset (all versions). Use `delete-version` when
>   only a version is stale (e.g. an intermediate image version on re-submission).
> - Never delete assets whose name matches the **operator name** (image/algorithm
>   assets) — only `{operator}-output-*` datasets and failed-task target assets.
> - Confirm again before any `delete-asset` that was auto-created by a **failed** task
>   if its `target_path` contains files the customer may want.
> - **⚠️ `show-asset` / `show-task` MUST pass before every delete** (see the table
>   above): name prefix + owner = current user + creation time within this run. A
>   name-prefix match alone is NOT proof — `{operator}-output-*` could be a customer
>   dataset. When verification fails, **skip and warn** instead of deleting.
> - **Never batch-delete** (`list-assets` → delete all matches). Confirm the exact
>   names + IDs one by one, then delete. `--dry-run` is your friend for previewing.

### Part 2: Verification Report 验证报告（Markdown）

#### Option & Prompt 选项与询问

After the final verification result is known, ask the customer (optional, default
no):
- 对话话术：「验证已结束（结果：{SUCCEEDED/FAILED}）。是否需要我生成一份《验证报告》Markdown 文档，记录本次验证的算子信息、资产信息和验证结果？报告只包含有用信息，不体现过程中的试错细节。① 生成 ② 不需要」

Only generate when the customer confirms. Report location: the work copy directory
(`/tmp/custom-operator-work-{timestamp}/verification-report.md`) — print the absolute
path and, if the customer wants, copy it next to the operator source directory
(**copying outside the work copy requires confirmation too**).

#### Content Rules 内容规范（只保留有用信息）

**MUST include (useful information):**
- Operator: name, deploy mode (Mode A image-inbuilt / Mode B OBS-mounted), code
  location (image URL or OBS `code_dir`)
- Assets: image asset name/ID + SWR URL + version, algorithm asset name/ID +
  `engine.image_url` + `image_source`, `code_dir`
- Datasets: input dataset name/ID/obs path; output dataset name/ID + target OBS path
- Verification: task name + `task_id`, final status (`SUCCEEDED`), user-log success
  line, output frames summary, duration
- Conclusion: 通过 / 不通过 (and, on success, the output dataset as the deliverable)

**MUST NOT include (trial-and-error noise):**
- Failed attempts, error messages, fix iterations, intermediate images/tags that were
  discarded, deleted junk, or any debugging details
- Only the final, successful state (or, on failure, one final conclusion line)

#### Template 模板

Use `custom-operator-reference.md` — fill every field from the actual
run; omit empty sections. Do not invent values.

### Relationship 与现有章节的关系

- Long-wait/progress heartbeat: `§` §Cleanup & Image
  Housekeeping (local Docker images) — this doc covers **platform** junk (tasks,
  assets)
- Work-copy lifecycle: ../../SKILL.md §Key Concepts (Work copy) & `§`
- Failure analysis before re-run: ../../SKILL.md §Failure Analysis & `§`

---
## Progress Feedback for Long-Running Steps 长等待步骤进度反馈

### Contents 目录

- Overview 概述
- Principle 原则
- Long-Running Steps Checklist 长等待步骤清单
- Task Creation: Create-Then-Poll (NOT `--wait`) 任务创建：创建后轮询
- Docker Push Progress 镜像推送进度
- Cleanup & Image Housekeeping 清理与镜像整理

### Overview 概述

Several steps in this skill take **minutes to tens of minutes**: `docker build`,
`docker push` (large images), OBS code upload, and the Phase-4 proc-task run. The
customer cannot see the terminal, so the skill **MUST** keep them informed with
periodic, timestamped progress messages — otherwise they will think the run is stuck
(deadlocked). **Never leave the customer with a silent gap longer than ~60 s.**

### Principle 原则

Every long-running step follows the same pattern:

1. **Before starting** — tell the customer what will run, how long it typically takes,
   and what the next step is.
   - 对话话术：「接下来会构建并推送算子镜像。构建约需 X 分钟，推送视镜像大小约需 Y 分钟，我会定期同步进度，请稍候。」
2. **During** — emit a progress heartbeat at least every 30–60 s: current timestamp,
   elapsed time, current phase/sub-step, and (when available) numeric progress.
3. **On completion** — report the concrete result (image digest + tag, task id +
   status, output path), then proceed to the next step.
4. **On failure/timeout** — report exactly where it stopped, what was tried, and the
   next action (see `§`).

### Long-Running Steps Checklist 长等待步骤清单

| Step | Typical duration | Progress signal to report |
|------|------------------|---------------------------|
| `docker build` (Mode A) | 2–10 min (heavy deps: longer) | Step N / total (docker prints `Step 1/6 ...`), per-step name; every completed step |
| `docker push` (Mode A) | 5–60+ min for 5–10 GB images | Image size first (`docker images`); then layer push progress (docker prints `layer: Pushed` per layer); estimate remaining by pushed/total layers |
| OBS code upload (Mode B) | seconds–minutes | File count + bytes uploaded, target OBS path |
| `create-task` + poll (Phase 4) | 2–60 min | After create: `task_id` + status `PENDING`; then every poll: status (`PENDING` / `POD_PENDING` / `RUNNING` / `SUCCEEDED` / `FAILED`) + elapsed |
| preset-image push (Mode B, one-off) | same as `docker push` above | same as `docker push` |

### Task Creation: Create-Then-Poll (NOT `--wait`) 任务创建：创建后轮询

**Do NOT use `--wait --timeout`.** It blocks the whole pipeline and gives the
customer no progress; worse, the agent tool may time out and abort while the task is
still running. Instead:

1. **Create without `--wait`**:
   ```bash
   cloudrobo dataset proc create-task --name <task-name> --algo-type OBS_ASSETS \
     --task-config "$(cat /tmp/task_config.json)"
   # task_id is returned in payload.id (not top-level id)
   ```
2. **Poll `show-task` with a progress heartbeat**, e.g. every 20–30 s, max ~2 h. The
   loop is extracted to **`../../scripts/poll-task.sh`**:
   ```bash
   bash scripts/poll-task.sh <task-id> [max-polls 120] [sleep-secs 30]
   # e.g. bash scripts/poll-task.sh $TASK_ID 120 30
   ```
   - Report each poll result to the customer: **对话话术**「任务 `{task_name}` 当前状态 `{status}`，已等待 {elapsed} 分钟。状态含义：PENDING=排队中，POD_PENDING=创建计算节点/拉取镜像中，RUNNING=算子运行中（转换类任务可能持续 10–40 分钟）。」
   - On `RUNNING` for a known-slow operator, extend the poll budget and reassure the
     customer (this is normal, not a hang).
3. **Verify** after `SUCCEEDED` (log + frames) — see `§` §Phase 4 Step 4.3.

> **Alternative: `wait-task` (platform-native progress output).** `cloudrobo dataset
> proc wait-task --task-id <id> --timeout <sec> --interval <sec>` waits and prints
> every status change in real time (a built-in heartbeat). Prefer it when the
> execution tool can stream output without a hard timeout; fall back to the manual
> poll loop above when the tool may abort long-running blocking calls (which is why
> `create-task --wait` is avoided).

### Docker Push Progress 镜像推送进度

Large images (torch/lerobot ≈ 10 GB) push for a long time. Keep the customer informed:

1. **Before push** — report the local image size and the SWR target:
   ```bash
   docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}" <operator-name>:<tag>
   # 对话话术：「镜像大小约 {size}，开始推送到 SWR ...。若大部分层已存在于仓库，推送会很快；全新大镜像可能需要 10–60 分钟。我会持续同步进度。」
   ```
2. **During push** — `docker push` prints per-layer lines. Because the command may be
   captured/buffered, prefer streaming it and reporting at intervals:
   ```bash
   # stream push output to a log, then tail-progress it
   docker push swr.{region}.myhuaweicloud.com/{ns}/{operator}:{tag} > /tmp/push.log 2>&1 &
   PUSH_PID=$!
   # every 30s: count Pushed layers vs total, report to customer
   #   grep -c "Pushed" /tmp/push.log ; tail -1 /tmp/push.log
   wait $PUSH_PID
   ```
   - **对话话术**：「推送中：已推送 {pushed}/{total} 个层。当前耗时 {elapsed} 分钟。`Layer already exists` 表示该层与仓库一致，无需重传（会显著缩短时间）。」
   - Many layers are usually `Layer already exists` on re-push — the delta is tiny.
3. **After push** — report the digest + tag:
   ```
   digest: sha256:...  tag: 20260924154534
   ```
   and proceed to asset registration.

### Cleanup & Image Housekeeping 清理与镜像整理

**This is a MUST-DO step after the verification ends (success or final failure)**, not
an optional extra: a single verification can leave 3–6 GB of throwaway images plus
build scratch dirs on the build host. These are local-only artifacts (no platform
impact), so **run them without waiting for customer confirmation** — except skip
anything the customer explicitly wants to keep.

The authoritative full procedure (keep the final SWR-tagged image, remove THIS run's
throwaway / probe / test images, remove THIS run's exited containers + proven dangling
images + build cache, clean THIS run's `/tmp` scratch dirs, work-copy lifecycle) lives
in `§` §Part 1A — this section only keeps the progress-related
reminders:

- **Image size/progress during cleanup** — report freed space (`docker system df`) and
  which images were removed; never go silent on long `docker image prune`.
- **Keep the final SWR-tagged image** (referenced by the algorithm asset) and the base
  image; the pushed preset-image tag is a **timestamp**
  (`{YYYYMMDDHHMMSS}`, e.g. `...:20260924154534`) — never the base-image version
  string.
- ⚠️ **Never `docker rmi` an image this run did not build** — not the algorithm-asset
  image, not the base image, and NOT any customer idle image (tagged or dangling) on a
  shared host. Every removal is digest-checked against this run's build record.
- ⚠️ Never `docker rmi` an image tag that the algorithm asset still references. If
  cleanup would remove the only local copy of a needed preset image, skip it and warn
  the customer instead. After a **FAILED** run, keep the work copy for
  `--reuse-workdir` debugging (work-copy lifecycle: `§`).

---
## Failure Analysis Guide 失败分析指南

### Contents 目录

- Overview 概述
- Error Pattern Matrix 错误模式矩阵
- Analysis Algorithm 分析算法
- Priority Ordering 优先级排序
- Log Truncation 日志截断
- Usage Example 使用示例
- Common Failure Scenarios 常见失败场景

### Overview 概述

The skill reads a failed task's
`job-std-output.log`, truncates it to 64KB, and matches error patterns against
a priority-ordered list. The first match determines the root cause and fix
suggestion returned to the user.

### Error Pattern Matrix 错误模式矩阵

#### P0 — Critical (Dependency / Build) 关键错误

| # | Pattern (Regex) | Root Cause | Fix Suggestion |
|---|-----------------|------------|----------------|
| 3 | `docker build.*ERROR\|COPY failed` | Dockerfile 构建失败 — The Docker build step failed, usually because a `COPY` source path does not exist in the work copy. | 检查 Dockerfile 中 `COPY` 指令的源路径是否存在于工作副本中。确认 `./src` 目录结构正确，`requirements.txt` 位于正确位置。 |
| 3a | `OSError:\s*\[Errno 30\].*Read-only file system` | 输出目录只读 — The container tried to create `output/` inside the **read-only** input dataset mount (`SOURCE_DATASET_PATH`). The platform mounts input datasets read-only. | 将输出目录改为 `TARGET_DATASET_PATH` 环境变量或 `/output/`，绝不要在输入数据集路径内写文件。修复 `entrypoint.py` 后重新构建推送镜像。 |
| 3b | `IsADirectoryError:\s*\[Errno 21\]` | 目录被当作文件 — The dataset asset OBS root contains a `<version_id>/` subdirectory holding the real files; `iterdir()` treated it as a file. | entrypoint 改用递归遍历 `INPUT_DIR.rglob("*")` 并过滤 `is_file()`，保留相对路径写出。 |

#### P1 — High (Runtime Environment) 运行时环境错误

| # | Pattern (Regex) | Root Cause | Fix Suggestion |
|---|-----------------|------------|----------------|
| 4 | `FileNotFoundError.*SOURCE_DATASET_PATH` | 数据集路径未注入 — The platform did not inject `SOURCE_DATASET_PATH`, or the entrypoint is reading it before the env var is set. | 确认 `entrypoint.py` 已正确读取 `SOURCE_DATASET_PATH` 环境变量。检查 `ext_metadata.env` 中是否声明了 `SOURCE_DATASET_PATH`。如果使用自定义 entrypoint，确保使用 `os.environ.get("SOURCE_DATASET_PATH")` 而非硬编码路径。 |
| 5 | `PermissionError.*output` | 输出目录无写权限 — The container cannot write to the output directory, possibly due to volume mount permissions. | 确认 `OUTPUT_DIR` 已通过 `mkdir(parents=True, exist_ok=True)` 创建。检查容器挂载卷是否有写权限。如使用 OBS 挂载，确认 OBS 桶策略允许写入。 |
| 5a | `stdbuf: failed to run command 'python': Permission denied` | Mode B `algo_entrance` 使用了**相对路径** `python entrypoint.py` — The platform runs the command from `/`, so the relative path and the `python` symlink in the preset image fail. | 将 Mode B 的 `algo_entrance` 改为**绝对路径** `python3 {job_local_path}/entrypoint.py`（如 `python3 /tmp/cloudrobo/text-stats-operator/entrypoint.py`）。 |
| 5b | `No module named 'user_operator'` | Mode B entrypoint 硬编码 `/app/src` 导入 — Mode B mounts the code at `{job_local_path}/src`, not `/app/src`. | entrypoint 的 src 导入改为相对 `__file__`：`sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))`；并确认 OBS 代码含 `src/user_operator.py`。 |
| 5c | `SOURCE_DATASET_PATH is not a valid JSON map` (+ `INPUT environment variable is not set`) | task-config 的 `envs` 包含 `SOURCE_DATASET_PATH` 的 fallback `default`（如 `/tmp/source/dataset`）— The literal placeholder in `envs` **overrides/blocks the platform runtime injection** of the dataset mount path (input is `access_method=env`). | 重建任务时从 `envs` 中**移除 `SOURCE_DATASET_PATH`**（及其他 `access_method=env` 输入端口），仅保留业务变量（如 `UMI_PLATFORM`）；无需重建镜像。 |
| 5d | `create-task` 返回 **HTTP 500**（重建镜像后重跑常见） | 算法资产 `engine.image_url` / `engine.asset_version_id` 仍指向**旧镜像版本**（重建后误走 first-submission 分支重复 `create-asset`，或 `update-asset` 未重指到新版本）；或失败运行预注册的 `BUILD_IN_ASSET` 输出资产停在 `DRAFT`/`CREATING`；或平台正重新索引刚更新的资产 | ① `show-asset` 校验算法资产指向**新**镜像版本（未指向则执行 Phase 3 Step 3.2 的 `create-version`+`update-asset`，**绝不重复 `create-asset`**）；② 使用**全新** `output_name`（时间戳后缀，不复用失败运行的）；③ 等待约 30 s 重试一次；④ 仍 500 → 记录 `trace_id` + 系统日志，联系平台支持 |

#### P2 — Medium (Code Logic) 代码逻辑错误

| # | Pattern (Regex) | Root Cause | Fix Suggestion |
|---|-----------------|------------|----------------|
| 6 | `TypeError:\s*(.+)` | 类型错误 — The `process()` function received an unexpected argument type, or the return value type is unsupported. | 检查 `process()` 入参类型，entrypoint.py 传递的是 `str(item)` 路径字符串。确认返回值为 `str` 或 `bytes`。详情：{0} |
| 7 | `KeyError:\s*'(\w+)'` | 字典键缺失 — The operator code tried to access a dictionary key that doesn't exist. | 检查数据结构，确认键存在后再访问。使用 `.get(key, default)` 替代直接索引。缺失键：'{0}' |

#### P3 — Unknown 未知错误

| # | Pattern | Root Cause | Fix Suggestion |
|---|---------|------------|----------------|
| 8 | (no match) | 未知错误 — The log does not match any known error pattern. | 请查看完整日志并联系平台支持。可使用 `cloudrobo dataset proc download-log --task-id <id>` 下载完整日志。 |

### Analysis Algorithm 分析算法

```python
#!/usr/bin/env python3
"""Failure analysis engine for custom-operator skill."""
import re

ERROR_PATTERNS = [
    # P0 — Critical (Dependency / Build)
    {
        "priority": "P0",
        "pattern": r"ModuleNotFoundError:\s*No module named '(\S+)'",
        "cause": "Python 依赖缺失",
        "fix": "在 requirements.txt 中添加 '{0}' 后重跑 onboard 命令。"
               "Phase 2 docker build 会重新安装依赖。"
    },
    {
        "priority": "P0",
        "pattern": r"ImportError:\s*(.+)",
        "cause": "导入失败",
        "fix": "检查模块路径与 __init__.py，确认 entry.module 配置正确。"
               "错误详情：{0}"
    },
    {
        "priority": "P0",
        "pattern": r"docker build.*ERROR|COPY failed",
        "cause": "Dockerfile 构建失败",
        "fix": "检查 Dockerfile COPY 源路径是否存在于工作副本中。"
               "确认 ./src 目录结构和 requirements.txt 位置。"
    },
    {
        "priority": "P0",
        "pattern": r"OSError:\s*\[Errno 30\].*Read-only file system",
        "cause": "输出目录只读（输入数据集为只读挂载）",
        "fix": "输出目录改为 TARGET_DATASET_PATH 环境变量或 /output/，"
               "绝不在 SOURCE_DATASET_PATH 输入路径内写文件。"
    },
    {
        "priority": "P0",
        "pattern": r"IsADirectoryError:\s*\[Errno 21\]",
        "cause": "数据集资产根目录含 <version_id>/ 子目录，iterdir 将目录当文件",
        "fix": "entrypoint 改用递归遍历 INPUT_DIR.rglob('*') 并过滤 is_file()，"
               "输出保留相对路径。"
    },

    # P1 — High (Runtime Environment)
    {
        "priority": "P1",
        "pattern": r"FileNotFoundError.*SOURCE_DATASET_PATH",
        "cause": "数据集路径未注入",
        "fix": "确认 entrypoint.py 已读取 SOURCE_DATASET_PATH 环境变量。"
               "检查 ext_metadata.env 中是否声明 SOURCE_DATASET_PATH。"
    },
    {
        "priority": "P1",
        "pattern": r"stdbuf: failed to run command 'python': Permission denied",
        "cause": "Mode B algo_entrance 使用了相对路径 python entrypoint.py",
        "fix": "将 Mode B 的 algo_entrance 改为绝对路径："
               "python3 {job_local_path}/entrypoint.py "
               "（如 python3 /tmp/cloudrobo/<operator-name>/entrypoint.py）"
    },
    {
        "priority": "P1",
        "pattern": r"No module named 'user_operator'",
        "cause": "entrypoint 硬编码 /app/src 导入，Mode B 代码挂载在 {job_local_path}/src",
        "fix": "entrypoint 的 src 导入改为相对 __file__："
               "sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))；"
               "并确认 OBS 代码含 src/user_operator.py"
    },
    {
        "priority": "P1",
        "pattern": r"PermissionError.*output",
        "cause": "输出目录无写权限",
        "fix": "确认 OUTPUT_DIR 已 mkdir(parents=True, exist_ok=True)。"
               "检查容器挂载卷写权限，OBS 桶策略允许写入。"
    },
    {
        "priority": "P1",
        "pattern": r"The asset name is existed",
        "cause": "BUILD_IN_ASSET 输出资产名重复",
        "fix": "创建 proc-task 时 output_name 使用唯一值（如带时间戳后缀）。"
    },
    {
        "priority": "P1",
        "pattern": r"(?i)http\s*500|internal server error|create.?task.*500",
        "cause": "重建镜像后重跑 create-task 平台内部错误（多为算法资产仍指向旧镜像版本 / 失败运行的输出资产未清理）",
        "fix": "① show-asset 校验算法资产 engine.image_url/asset_version_id 指向新镜像版本（未指向则执行 "
               "Phase 3 Step 3.2 create-version+update-asset，绝不重复 create-asset）；"
               "② output_name 使用全新时间戳值；③ 等待约 30s 重试一次；"
               "④ 仍 500 → 记录 trace_id + 系统日志，联系平台支持。"
    },

    # P2 — Medium (Code Logic)
    {
        "priority": "P2",
        "pattern": r"TypeError:\s*(.+)",
        "cause": "类型错误",
        "fix": "检查 process() 入参类型，entrypoint.py 传递 str 路径。"
               "确认返回值为 str 或 bytes。详情：{0}"
    },
    {
        "priority": "P2",
        "pattern": r"KeyError:\s*'(\w+)'",
        "cause": "字典键缺失",
        "fix": "检查数据结构，使用 .get(key, default) 替代直接索引。"
               "缺失键：'{0}'"
    },
]

def analyze_failure(log_path="job-std-output.log"):
    """Analyze a failure log and return root cause + fix suggestion.

    Reads the log file, truncates to 64KB, and matches against ERROR_PATTERNS
    in priority order. Returns the first match.

    Args:
        log_path: Path to the job-std-output.log file.

    Returns:
        dict with keys: priority, cause, fix, matched_line.
        If no pattern matches, returns P3 with "contact support" suggestion.
    """
    try:
        with open(log_path, errors="ignore") as f:
            log = f.read()[:65536]  # Truncate to 64KB
    except FileNotFoundError:
        return {
            "priority": "P3",
            "cause": "日志文件未找到",
            "fix": "确认任务 ID 正确，且任务已产生日志。"
                   "使用 list-log-files 先获取可用日志文件列表。",
            "matched_line": ""
        }

    for p in ERROR_PATTERNS:
        m = re.search(p["pattern"], log)
        if m:
            return {
                "priority": p["priority"],
                "cause": p["cause"],
                "fix": p["fix"].format(*m.groups()),
                "matched_line": m.group(0)[:200]
            }

    return {
        "priority": "P3",
        "cause": "未知错误",
        "fix": "请查看完整日志并联系平台支持。"
               "可使用 download-log 下载完整日志。",
        "matched_line": ""
    }
```

### Priority Ordering 优先级排序

Patterns are evaluated **in order** — the first match wins. This means:

1. **P0 patterns are checked first** — if a dependency or build error exists,
   it is the root cause regardless of other errors in the log (which are
   typically downstream consequences).

2. **P1 patterns are checked next** — environment issues like missing
   `SOURCE_DATASET_PATH` or permission errors indicate a configuration problem
   that must be fixed before code-level debugging.

3. **P2 patterns are checked last** — code logic errors (TypeError, KeyError)
   are surfaced only if no environment or dependency issues are found.

4. **P3 is the fallback** — if no pattern matches, the error is unknown and
   the user should download the full log for manual analysis.

### Log Truncation 日志截断

- Only the **first 64KB** of `job-std-output.log` is read.
- This prevents excessive memory usage on large logs.
- Most critical errors appear early in the log (during initialization or
  first item processing).
- If the user needs full log analysis, suggest `download-log` for the
  complete file.

### Usage Example 使用示例

#### CLI

```bash
# Analyze a failed task
cloudrobo dataset proc get-log --task-id <task_id> --file-name job-std-output.log

# With a local log file
cloudrobo dataset proc get-log --task-id <task_id> --file-name job-std-output.log
```

#### Output Format

```json
{
  "priority": "P0",
  "cause": "Python 依赖缺失",
  "fix": "在 requirements.txt 中添加 'torch' 后重跑 onboard 命令。Phase 2 docker build 会重新安装依赖。",
  "matched_line": "ModuleNotFoundError: No module named 'torch'"
}
```

### Common Failure Scenarios 常见失败场景

#### Scenario 1: Missing Python Dependency

**Log excerpt:**
```
Traceback (most recent call last):
  File "/app/entrypoint.py", line 12, in <module>
    from user_operator import process
  File "/app/src/user_operator.py", line 3, in <module>
    import torch
ModuleNotFoundError: No module named 'torch'
```

**Analysis result:**
```json
{
  "priority": "P0",
  "cause": "Python 依赖缺失",
  "fix": "在 requirements.txt 中添加 'torch' 后重跑 onboard 命令。",
  "matched_line": "ModuleNotFoundError: No module named 'torch'"
}
```

**Action:** Add `torch` to `requirements.txt`, re-run the build (see ../../SKILL.md §Custom Operator Onboarding).

#### Scenario 2: Missing SOURCE_DATASET_PATH

**Log excerpt:**
```
Traceback (most recent call last):
  File "/app/entrypoint.py", line 20, in <module>
    INPUT_DIR = Path(DATASET_PATH) / "input"
  File "/usr/lib/python3.x/pathlib.py", line 1005, in __new__
    ...
FileNotFoundError: <dataset-path>/input does not exist
```

**Analysis result:**
```json
{
  "priority": "P1",
  "cause": "数据集路径未注入",
  "fix": "确认 entrypoint.py 已读取 SOURCE_DATASET_PATH 环境变量..."
}
```

**Action:** Verify `ext_metadata.env` includes `SOURCE_DATASET_PATH`, re-onboard if needed.

#### Scenario 2a: envs 中 SOURCE_DATASET_PATH 占位值阻断平台注入

**Log excerpt (verified in Mode A e2e, umi_to_lerobot_v3):**
```
[ENTRY] cwd=/app/src cmd=python3 main.py --operator umitolerobotv3 --platform pika --overwrite
SOURCE_DATASET_PATH is not a valid JSON map.
2026-09-28 11:34:56,942 - ERROR - Error during data conversion INPUT environment variable is not set
[DONE] command exit code: 1
```

**Analysis result:**
```json
{
  "priority": "P1",
  "cause": "task-config 的 envs 中包含 SOURCE_DATASET_PATH 的 fallback default（如 /tmp/source/dataset），该字面量覆盖/阻断了平台运行时注入的 JSON map（输入端口 access_method=env）",
  "fix": "重建任务：从 envs 中移除 SOURCE_DATASET_PATH（及其他 access_method=env 输入端口），仅保留业务变量（如 UMI_PLATFORM=pika）。无需重建镜像。",
  "matched_line": "SOURCE_DATASET_PATH is not a valid JSON map."
}
```

**Action:** Re-create the proc-task with `envs` excluding `SOURCE_DATASET_PATH`.

#### Scenario 3: Type Error in process()

**Log excerpt:**
```
Traceback (most recent call last):
  File "/app/entrypoint.py", line 35, in <module>
    result = process(str(item))
  File "/app/src/user_operator.py", line 15, in process
    data = json.loads(item)
TypeError: the JSON object must be str, bytes or bytearray, not PosixPath
```

**Analysis result:**
```json
{
  "priority": "P2",
  "cause": "类型错误",
  "fix": "检查 process() 入参类型，entrypoint.py 传递 str 路径...",
  "matched_line": "TypeError: the JSON object must be str, bytes or bytearray, not PosixPath"
}
```

**Action:** Fix the `process()` function to handle string path input correctly.

#### Scenario 4: Docker Build Failure

**Log excerpt:**
```
Step 4/7 : COPY ./src ./src
COPY failed: file not found in build context: src
```

**Analysis result:**
```json
{
  "priority": "P0",
  "cause": "Dockerfile 构建失败",
  "fix": "检查 Dockerfile COPY 源路径是否存在于工作副本中...",
  "matched_line": "COPY failed: file not found in build context: src"
}
```

**Action:** Ensure `src/` directory exists in the operator source, re-run onboarding.

---
## OBS Upload Guide 上传数据到 OBS 指南

### Contents 目录

- Overview 概述
- Measured Performance Model 实测性能模型
- Mandatory Rules 强制规则
- Concurrent Upload Template 并发上传模板
- Verification 上传验证
- Boundary Conditions 边界情况
- Relationship to Mode B Code Delivery Mode B 代码交付

### Overview 概述

This skill touches OBS in two places:

1. **Mode B code delivery** — upload the generated `entrypoint.py` / `src/` /
   `requirements.txt` (a handful of files) to the operator's OBS path
2. **Phase 4 Source ① data upload** — get the customer's raw dataset onto OBS so the
   skill can auto-create a dataset asset (can be **thousands of files**)

This guide is the authoritative reference for **how fast OBS uploads actually run**
and **how to upload large file sets without the multi-minute crawl** that a naive
serial upload produces.

### Measured Performance Model 实测性能模型

Measured against a regional OBS endpoint (`obs.{region}.myhuaweicloud.com`) with a 717MB / 14441-file
dataset (pika-umi):

| Metric | Measured value | Implication |
|--------|----------------|-------------|
| Per-request latency (small `putFile`) | **~184 ms / request** | Upload time ≈ **file count × per-request latency** when requests cannot run in parallel |
| Single-connection bandwidth (50MB multipart, 8 segments) | **~9.2 MB/s** | Bandwidth is **NOT** the bottleneck for small files |
| Single-process concurrency ceiling | ~6.5 req/s (8 and 32 threads give the same rate) | The client/endpoint throttles requests per process — adding threads alone does NOT help |
| **Multi-process sharding** (4 procs × 16 threads) | **~25 req/s (4× speedup)** | Sharding across processes breaks the per-process ceiling |

**Rule of thumb:** upload wall-time ≈ `file_count / total_req_s`. A serial upload of
14441 files takes ~44 min; the sharded 4×16 approach finished the same set in
~10 min.

### Mandatory Rules 强制规则

1. **Never serial-upload a large dataset with `OBSClient.upload_folder`** — it walks
   files one by one (~184ms per request). Fine for a handful of code files
   (Mode B), **unacceptable** for large datasets (Phase 4 Source ①).
   Threshold: **> 50 files or > 50MB → use the concurrent approach below.**
   **The default tool is `../../scripts/concurrent_shard_upload.py` — copy it to the
   target host, edit its CONFIG (`SERVER`/`BUCKET`/`PREFIX`/`SRC`), and run it as the
   script's Usage block describes. Do NOT hand-roll a new concurrent implementation,
   do NOT fall back to a serial `upload_folder` walk, and do NOT substitute another
   tool (e.g. `obsutil`) unless the customer explicitly chooses one.**
2. **Before uploading, size the job first:** `du -sh <dir>` and
   `find <dir> -type f | wc -l` — this tells you the expected wall-time
   (`file_count / 25` seconds) and whether to warn the customer about the duration.
3. **Small files (`< 10MB`) → `putFile` from multiple threads.** One request per file.
4. **Large files (`≥ 10MB`) → `uploadFile` multipart** (`partSize=10MB, taskNum=8`),
   which parallelizes segments and reaches ~9MB/s per object.
5. **Shard across processes, not just threads** — each process gets its own
   `ObsClient` and its own share of files (`index % N` round-robin). 4 processes ×
   16 threads is the tested sweet spot; do not exceed ~8 processes.
6. **Never run two uploaders against the same target prefix at the same time** —
   they fight over bandwidth and produce `*.upload_record`/`*.upload_tmp` leftovers.
   Check `ps aux | grep -i upload` first; stop the competing job (after user
   confirmation) before starting a new one.
7. **Filter transient files when collecting** — skip `*.upload_record`,
   `*.upload_tmp`, `*.tmp`, and other OBS-SDK byproducts before counting/uploading.
8. **Verify after upload** — count objects under the target prefix with
   `listObjects` (paged) and compare with the local file count; spot-check sizes.
   A 0-byte `.../uploadTest/` directory placeholder object is normal.

### Concurrent Upload Template 并发上传模板

**The skill uploads datasets (Phase 4 Source ①) by DEFAULT with
`../../scripts/concurrent_shard_upload.py`** — copy the script to the build/edge host,
edit its CONFIG block (`SERVER` / `BUCKET` / `PREFIX` / `SRC`), then launch 4 shards ×
16 threads exactly as its Usage block shows. This is the default for ANY dataset
upload > 50 files / > 50MB; only a customer's explicit alternative choice overrides it.

The script (round-robin sharding, `putFile`/`uploadFile` split at 10MB,
transient-file filtering, progress heartbeat) runs on the build/edge host with
`esdk-obs-python`. Fall back to `cloudrobo_core.sdk.obs_client.OBSClient` only when
the third-party SDK is absent — but then replicate the same sharding logic verbatim
from the script, never a plain serial walk.

```bash
# 1. Size the job & pick the endpoint (default may NXDOMAIN on some networks):
du -sh <data-dir>; find <data-dir> -type f | wc -l
#    reachable endpoint example: https://obs.<region>.myhuaweicloud.com
```

```bash
# 2. Launch shards in the background (4 procs × 16 threads ≈ 25 req/s, tested):
#    edit CONFIG at the top of scripts/concurrent_shard_upload.py first
#    (SERVER / BUCKET / PREFIX / SRC)
export HUAWEI_CLOUD_AK=<ak> HUAWEI_CLOUD_SK=<sk>
for k in 0 1 2 3; do
  nohup python3 scripts/concurrent_shard_upload.py --threads 16 \
    --slice-index "$k" --slice-total 4 > /tmp/obs_up_$k.log 2>&1 &
done
```

```bash
# 3. Verify (rule 8): count objects under the prefix, compare with local count
#    `find <data-dir> -type f | wc -l` — expect the same number (+0-byte dir placeholder).
```

### Verification 上传验证

- **Count parity:** paged `listObjects(prefix=<PREFIX>, marker=..., max_keys=1000)`
  total == local file count (a single 0-byte `<PREFIX>/` placeholder is expected)
- **Spot-check:** compare a few object sizes with `os.path.getsize` of the source
  files
- **Readiness check (Mode B / dataset):** confirm `entrypoint.py`/`src/...`/`requirements.txt`
  (code) or the raw data files are present before creating the proc-task — an empty
  path keeps the task in `POD_PENDING`

### Boundary Conditions 边界情况

| Situation | Handling |
|-----------|----------|
| Endpoint `obs.{region}.myhuaweicloud.com` NXDOMAIN | Ask the customer for a reachable endpoint (e.g. `obs.cn-southwest-2.myhuaweicloud.com`) and set it before any OBS call |
| Another uploader running against the same prefix | Check `ps aux | grep -i upload`; **ask the user to stop it first** (competing jobs fight for bandwidth and leave `*.upload_record` files) |
| `*.upload_record` / `*.upload_tmp` leftovers inside the data dir | Filter them when collecting (rule 7); remove stale ones (`find <dir> -name '*.upload_record' -delete`) |
| Interrupted upload | Re-running is idempotent for the same keys (`putFile`/`uploadFile` overwrite in place); restart the shards |
| Dataset larger than ~5000 files | Expected wall-time ≥ ~3 min — inform the customer and show the progress heartbeat |
| `du -sh` / `find | wc -l` fail (path missing) | Ask the customer for the correct data path before uploading |
| Upload verification mismatch | Re-run the shards (idempotent), then re-verify; report the difference |

### Relationship to Mode B Code Delivery Mode B 代码交付

Mode B delivery is a **small** upload (3 files + `src/`) — the serial
`OBSClient.upload_folder` / `upload_file` is fine there (idempotent overwrite into
the reused operator directory). Apply this guide's concurrent approach **only** when
the payload is large (Phase 4 Source ① datasets, or a customer data set with
> 50 files / > 50MB).

---
