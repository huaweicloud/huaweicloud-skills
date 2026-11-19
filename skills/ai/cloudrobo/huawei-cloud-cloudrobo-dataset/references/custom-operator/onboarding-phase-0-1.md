> Part of the custom-operator guide. Index: [custom-operator-workflow.md](custom-operator-workflow.md)

## Onboarding Workflow 上架工作流

### Contents 目录

- Overview 概述
- Prerequisites Check 前置条件检查
- Phase 1: Code Adaptation 代码适配
- Phase 0: Deploy Mode & Asset Detection 部署方式与资产检测
- Phase 2: Image Build & Push 镜像构建推送（仅把代码打进镜像；代码放 OBS 跳过本阶段）
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

> **⚠️ Step 1.0 — Back up the original code first.** Before copying, create an explicit
> backup with a timestamped name and record its path:
> ```bash
> mkdir -p "<project>/.workcheck/backup"
> cp "<user source file>" "<project>/.workcheck/backup/<name>.<YYYYMMDDHHmmss>.py"
> ```
> The work copy is **not** a backup — it is disposable and is deleted in Phase 5. State the
> backup path to the user in the pre-create summary. Never edit the user's file in place.

> **⚠️ Adaptation report — required before upload.** Phase 1 changes the code contract.
> Before Phase 1.4 (code delivery) or Phase 2 (image build), report each adaptation to the
> user in their language:
> - input contract (which platform-injected variable, how files are enumerated/filtered)
> - output layout (where results must land, and why the downstream consumer requires it)
> - dataset-creation constraints (e.g. `LeRobotDataset.create` needs a non-existent root —
>   build in staging then merge into the output root)
> - any other fix required for the code to run on the platform
>
> Each item states **what changed and why**. "Code adapted" alone is not acceptable.

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
   - **Filter by item suffix before calling `process()`** — the mounted dataset root often
     contains non-data files (README, `pipeline.yaml`, stray `.py`, uploaded `work-copy/`).
     Collect only the suffixes the operator actually consumes (e.g. `.h5`, `.hdf5`) and
     skip the rest. Passing every file makes `process()` raise `ValueError: not an h5 file`
     on each stray file and fails the whole task (`[DONE] ... success 0, failed 8`).
   - **`OUTPUT_DIR` = `TARGET_DATASET_PATH` or `/output`** — the platform mounts
     `SOURCE_DATASET_PATH` **read-only**; writing `output/` inside it fails with
     `OSError: [Errno 30] Read-only file system`
   - `OUTPUT_DIR.mkdir(parents=True, exist_ok=True)`
   - Dynamic import of the user's `process()` function — resolve `src/` **relative to
     `__file__`** (`Path(__file__).resolve().parent / "src"`), NOT hardcoded
     `/app/src` (把代码打进镜像 bakes code at `/app/src`, 代码放 OBS、运行时挂载 mounts it at
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

> **仅把代码打进镜像时使用。** 代码放 OBS 没有 Dockerfile.

#### Step 1.4: 代码放 OBS、运行时挂载 — Code Delivery to OBS 将代码交付到OBS（代码放 OBS、运行时挂载）

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
   [OBS Upload Guide](obs-upload-guide.md)**):
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

#### Step 1.5: Local Smoke Test 本地先试跑（必须，且需用户确认）

**顺序硬约束：先本地试跑并让用户确认结果，再询问运行时镜像与启动命令。**
试跑验证的是代码逻辑（输入契约、输出布局、建库约束）；镜像与启动命令只有在代码跑通
之后才值得讨论。反过来先问镜像，用户还没看到代码能否工作，等于让用户为一个未验证的
方案做运行时决策。

做法：

1. **先问用户是否允许本地试跑**，并说明将用哪份样本、写到哪个临时目录：
   > 上云前我想先用 `<样本文件>` 在本地跑一遍工作副本，确认能产出合格数据集，
   > 输出写到 `<临时目录>`，不改动原始数据。可以吗？
2. 用户同意后，准备最小样本（单条 episode / 单个文件即可，不要用全量数据）。
3. 用平台同样的环境变量语义本地调用，输出指向临时目录：
   ```bash
   mkdir -p "<project>/.workcheck/localtest"
   SOURCE_DATASET_PATH='{"sample":"<sample dir>"}' \
   TARGET_DATASET_PATH="<project>/.workcheck/localtest" \
     python "<work copy>/entrypoint.py"
   ```
   （若工作副本只暴露 `process()` 而没有 `__main__`，用 entrypoint 或一个临时驱动脚本调用它。）
4. 检查产物：目标目录结构、关键文件（如 `meta/info.json`）、是否残留临时目录、
   帧数/条数是否与样本一致。
5. **把试跑结果（成功/失败、产物结构、耗时）报告给用户并等待确认**，确认后再进入
   Phase 0 询问镜像与启动命令。
6. 试跑目录用独立临时路径；**每次重跑前清空**，否则"目录已存在"类错误会被误判为代码缺陷。
   注意 `LeRobotDataset.create()` 要求根目录不存在，而平台输出根目录已存在——这属于代码
   适配项（staging 建库后合并进输出根），不是试跑环境问题。

边界：

- 本地试跑**不能**验证镜像里的第三方依赖是否存在——本地有 `h5py`/`lerobot` 不代表镜像里有。
  依赖仍需在 Phase 0 与用户确认镜像时一并确认。
- 本地缺依赖时，先说明缺什么、是否要装，不要跳过试跑直接上传。
- 用户明确要求"不本地试跑、直接上云"时尊重，但在子计划里标注该风险。
- **禁止在用户确认试跑结果之前询问镜像、启动命令、OBS 路径等上云参数。**

#### Phase 1 Dry-Run 干跑验证

```bash
# 命令编排见 ../../SKILL.md §Custom Operator Onboarding（组合 client 真实命令）
```

Validates config and generates artifacts without creating the work copy. Useful
for checking config validity before committing to a full onboarding.

### Phase 0: Deploy Mode & Asset Detection 部署方式与资产检测

> **⛔ 进入条件：Step 1.5 的本地试跑已完成且用户已确认结果。**
> 镜像、启动命令、OBS 路径都属于"代码跑通之后才成立的运行时参数"。在用户看到本地
> 试跑结果之前询问这些，等于让用户为未验证的代码做运行时决策。试跑失败时先修代码，
> 不要提前进入本阶段。

> **部署方式必须问一次，不能静默默认。** 这是客户的运行时决策，取决于客户自己的镜像与
> 依赖状况；本机没有 Docker 只是需要询问的理由，不是替客户决定走 OBS 挂载的理由。
> 用一轮问清（推荐值预先选中）：
>
> > 这次上云用哪种方式？
> > - 平台已有镜像资产 → 你告诉我是哪个（我只查这一个）
> > - 我提供镜像 URL → 直接给 SWR 地址
> > - 本地构建镜像 → 本机有 Docker 时把代码和依赖打进镜像（最稳）
> > - 代码放 OBS、运行时挂载 → 快，但镜像必须已含所需依赖
>
> 推荐顺序：客户已有镜像资产/URL > 本机有 Docker 时打进镜像 > 代码放 OBS 挂载。
> 客户回答"都可以/你看着办"时，按上述推荐顺序选第一个成立的并说明理由。
>
> **禁止为了"推荐"去扫工作空间的镜像资产**（全量列举 `--type image`、翻历史资产、比对
> 别人用过的镜像）。镜像选择是客户决策；只有客户点名某个镜像后，才去查它的地址和版本。
> 全量扫描既慢，又常选出依赖不全的运行时。
>
> 仅在以下情况倾向"打进镜像"：
> - 算子需要预设运行时中没有的系统包或原生二进制；
> - 需要预设镜像不具备的 GPU/加速运行时。

Phase 0 记录**部署方式**（必须询问一次，推荐值预选），然后收集决定 Phase 3 分支所需的信息
（首次提交 vs 再次提交）：

- **把代码打进镜像**（内部代号 image-inbuilt，`custom`）：算子代码打进镜像，每次提交都
  重建并推送一个新镜像（代码在镜像内部）
- **代码放 OBS、运行时挂载**（内部代号 OBS-mounted，`preset`）：代码由 **skill 默认**上传到
  OBS（客户也可以自己上传）；skill 收集 OBS 路径 + 容器挂载路径 + 运行时镜像，
  并**完全跳过镜像构建与推送**。运行时验证阶段有两种创建任务的方式（默认「注册成空间里的
  算法资产后引用」，见 Step 0.3；仅当客户明确要求不注册资产、直接挂载 OBS 代码时才切换）：
  - **注册成空间里的算法资产后引用**（`WORKSPACE_ASSETS` + `algo_id`）：任务通过 `algo_id`
    引用阶段 3 创建的算法资产（`image_source=custom`，算法资产通过 `engine.asset_id` +
    `engine.asset_version_id` 关联镜像资产），并通过 `algo_path` + `job_local_path` 挂载
    它的 `code_dir` —— **任务真正消费的是已创建的算法资产**（这就是 `WORKSPACE_ASSETS` 的
    含义：引用工作空间已注册的算法资产；把代码打进镜像的 `custom` 资产用的是同一类型）。
    已验证：即便这种形态，`algo_path` + `job_local_path` 也是**必填**的——漏掉会在运行时
    报 `//entrypoint.py` 不存在。
  - **不注册资产、直接挂载 OBS 代码**（`OBS_ASSETS`，无 `algo_id`）：任务直接挂载客户的
    OBS 路径，不建立资产关联 —— **阶段 3 的资产注册整体跳过**（不创建镜像资产和算法资产）。

#### Step 0.1: Query Existing Assets 查询已有资产

> **OBS算法 (mount OBS code directly): the queries below are optional** — no assets are
> registered, so same-name detection only matters when the customer later switches to
> 空间资产-算法.

**⛔ Scope limit — query by the EXACT operator name only.** These two commands exist solely
to detect a same-name re-submission. They are **not** a license to browse the catalog.

**When the customer has already named the action and the object** ("register this script as
an operator", "onboard this code"), the decision is made — go to Phase 0's deploy-mode
question. Same-name detection is a cheap `--exact-name` call for a name reused from a prior
submission, not a survey of what exists. A fuzzy `--name` scan that returns unrelated
operators (A2D, H5, LeRobot, "data-engineering", …) is a signal you are browsing, not
detecting: stop it and proceed with the customer's request.

Do **NOT**, unless the customer explicitly asks:

- run `list-assets` without `--exact-name` and read through the workspace's other operators;
- open old algorithm assets to copy their `image_url`, `command`, `code_dir` or `envs`;
- hunt for "an image that some earlier operator used" to avoid asking the customer;
- inspect old tasks, old runs or `~/.cloudrobo/pipeline-runs/*` to infer parameters.

**Why this is a hard rule:** a custom operator's **image and start command are the
customer's decision** — they depend on that customer's own runtime, not on whatever
happened to run before. Mining history both wastes rounds and propagates stale, wrong
values.

**Correct behavior:** derive everything from the customer's request; where a value is
genuinely the customer's choice (image, interpreter/entrance, mount path, dependency
availability), present **one recommended form with the risky items marked** and let the
customer edit it. A fresh operator name makes same-name detection trivially negative — do
not go looking for a collision.

```bash
# Image assets (exact name + Data Processing tag) — locate the existing image asset
# id (needed for create-version on re-submission, 把代码打进镜像)
cloudrobo asset list-assets --catalog-id {workspace_catalog_id} --type image --tags "Data Processing" --exact-name {operator-name}
# Same-name algorithm assets (exact name + Data Processing tag) — detect whether this
# operator was already submitted
cloudrobo asset list-assets --catalog-id {workspace_catalog_id} --type algorithm --tags "Data Processing" --exact-name {operator-name}
```

#### Step 0.2: Decision Branch 决策分支

| Condition | Action |
|-----------|--------|
| Deploy mode | **必须问一次**（平台已有镜像资产 / 客户提供镜像 URL / 本地构建 / 代码放 OBS 挂载），推荐值预选；本机无 Docker 只是询问理由。**必须在 Step 1.5 本地试跑经用户确认之后才问** |
| Runtime image | **由客户给出，Agent 不推断**：客户点名的空间镜像资产，或客户粘贴的 SWR 地址。禁止全量扫描镜像资产来找"合适的"；只有客户点名后才查该镜像的地址和版本。**必须在本地试跑确认之后才问** |
| 启动命令 / 解释器路径 | **由客户给出**：镜像内的解释器绝对路径（如 `/home/service/opt/cloudroboh5/bin/python`）+ 入口文件路径。不同镜像解释器位置不同，Agent 不猜；**必须在本地试跑确认之后才问** |
| 把代码打进镜像（无论镜像资产是否已存在） | **Register a new image** — build + push a fresh tag on every run; no "use existing image" question |
| 代码放 OBS、运行时挂载 | Collect **OBS path** (must start with workspace `default_obs_path`, **reuse the existing per-operator directory across verifications**), **container injection path** (`job_local_path`, default if not provided), **preset runtime image**, **code upload mode** — **no docker login / build / push**。**任务创建方式默认 = 空间资产-算法**（Phase 3 注册预设镜像 + 算法资产）。仅当客户明确要求不注册资产、直接挂载代码时才用 OBS算法（`OBS_ASSETS`，无 `algo_id`，Phase 3 跳过） |
| Same-name algorithm asset exists | Record as **re-submission** |
| Same-name algorithm asset does not exist | Record as **first submission** |
| Login command (把代码打进镜像) | **Auto-generate the docker login command** from AK/SK (official SWR long-lived login command, HMAC-SHA256-derived secret); proceed to Phase 2. Only ask the user for a command if generation or login fails |

> **Why auto-generate?** The skill reads AK/SK from `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK`
> or `~/.cloudrobo/config.yaml` and derives the SWR long-lived login command
> (`docker login -u <region>@<AK> -p <HMAC-SHA256(AK, SK)> swr.<region>.myhuaweicloud.com`),
> so no user input is needed in the happy path. The customer is asked for a command
> **only when** auto-generation is impossible (no AK/SK) or the auto-generated login
> fails (`unauthorized` / `Authenticate Error`). In both cases the skill first
> **proactively reminds the customer to configure / update the AK/SK** (see
> `../cli-installation-guide.md` §4.1), then asks for the full command as a fallback.

#### Step 0.3: 代码放 OBS、运行时挂载 — OBS Deployment Info Collection OBS部署信息收集

For 代码放 OBS、运行时挂载, collect and validate (all **confirmed with the customer** in a
conversational way):

0. **任务创建方式 — 默认空间资产-算法，不要问。** 运行时 proc-task 按以下方式引用算法：
   - **空间资产-算法 — use the created algorithm**: task-config uses
     `WORKSPACE_ASSETS` + `algo_id` = the Phase 3 algorithm `asset_id`
     (`image_source=custom`, asset linkage; algorithm `engine.asset_id` +
     `engine.asset_version_id` link the image asset) + `algo_path` = the asset's `code_dir`
     (mount source, **required**) + `job_local_path` (mount path, **required**) +
     **absolute** `algo_entrance` — missing `algo_path`/`job_local_path`
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
   - **默认 —— 自动推导**：`{default_obs_path}{operator-name}/`。说明推导结果后继续；仅当用户想换位置时才问。
   - Expected content at that path after delivery: `entrypoint.py`, `requirements.txt`,
     `src/` (with `user_operator.py`)
2. **代码上传方式** —— **默认由 skill 上传**（用户少操作）。用 OBS client 上传后报告文件与路径
   （见 Step 1.4）。仅当用户想自己上传时才问：
   - **默认 — skill 上传**（见 Step 1.4）；上传前确认一次
   - **备选 — 用户上传**：列出文件与目标路径，用户上传并确认
3. **Container injection path** (`job_local_path`) — where the algorithm directory is
   mounted inside the container (e.g. `/tmp/xxx`):
   - **默认**：`/tmp/cloudrobo/{operator-name}` —— 直接使用并说明；仅当用户想换挂载点时才问
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

#### Step 0.4: Validate the Login Command 校验登录指令（仅把代码打进镜像时）

```bash
# Auto-generated command (from AK/SK), e.g.:
#   docker login -u cn-southwest-2@<AK> -p <login-secret> swr.cn-southwest-2.myhuaweicloud.com
# On auto-generation/login failure, fall back to:
<user-provided docker login ...>
# Expect: Login Succeeded
```

If login fails, ask the user to re-check the command (registry host, user, password) before proceeding.
