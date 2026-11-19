# User-Facing Interaction Rules

Rules for **what the user sees**. The user is a client delegating work, not an operator
watching the machinery. Internal mechanics (asset/version IDs, task JSON, state-machine
fields, submission transactions) are the Agent's concern and must stay off the user's
screen unless they explicitly ask for details.

This document governs three surfaces: the **execution plan**, the **confirmation round**,
and the **result summary**. The execution itself (commands, polling, checkpointing) is
already specified in `SKILL.md`.

> **Language**: this document is written in English, but everything the user sees must be
> rendered in **the user's own language**. The templates below are English examples —
> translate them, including status words and error explanations, before sending.

---

## 1. Core principle

**Show decisions, hide mechanics.**
The user decides *what* to do. The Agent decides *how* to do it.

- Do not make the user read or approve IDs, image tags, JSON field names, or state names.
- Do not ask a question whose answer has a safe, conventional default.
- Do not narrate internal bookkeeping (reserve / resolve / set-result / show-version checks).
- Do not ask the same thing twice.

### 1.1 调查动作必须可见（Investigation must be visible）

"Hide mechanics" applies to **bookkeeping and internal state**, NOT to **investigation**.
Read-only actions that discover facts about the user's environment or data are things the
user has a right to see happening — they explain *why* the Agent is about to say what it
says. Silently doing them makes the conversation look like magic, and the user cannot tell
whether the Agent actually checked anything.

**Before each batch of read-only investigation, emit one short Chinese line saying what is
being checked and why. Then report the result as a Chinese summary — never make the user
read raw JSON.**

Covered by this rule (announce before running):

| Action | Announcement example |
|---|---|
| Environment preflight (Python / CLI / site / workspace) | 「先检查本地环境和云端连接。」 |
| Directory scan / file inventory | 「先看下数据目录里有什么。」 |
| Operator discovery (`list-publication-assets`) | 「查一下平台上有哪些现成的转换/清洗/评测算子。」 |
| Asset / version lookup | 「查一下这个数据集在云端的状态。」 |
| Name-occupancy check | 「确认一下输出名有没有被占用。」 |
| Reading data metadata (h5/bag headers) | 「读一下数据的元信息，确认帧数和机器人型号。」 |

Not covered (stay silent): reserve/resolve/set-result, heartbeat, state reloads, retries of
already-announced checks, and any command whose only purpose is checkpoint bookkeeping.

Batch related queries into **one** announcement rather than one per command. Never announce
the same check twice in a run.

### 1.2 精简优先（Minimal path first）

Transparency is not verbosity. The cheapest workflow that reaches the user's goal wins;
never run the heavier machinery "for completeness".

Order of preference — stop at the first that fits:

1. **Built-in template** — if the data and goal match `仿真/遥操VLA模型数据处理管线`
   (sim/teleop H5/ROS2/UMI → convert → clean → evaluate), say so in one line and go
   straight to the 8-line plan. Do **not** route it through guided custom creation, do not
   generate `pipeline.yaml` / `pipeline.draft.json` / `pipeline-preview.md`, and do not make
   the user confirm a YAML they will never read.
2. **Guided custom creation** — only when the workflow genuinely differs from the built-in
   template (custom operator, extra/fewer stages, non-standard data stage).
3. **Hand-written YAML** — only when the user supplies or explicitly asks for one.

Additional minimal-path rules:

- Ask **one** question per genuinely open decision; never re-ask something already answered
  or already visible in the data.
- Do not narrate the skill's own stages ("现在进入 Stage 0 / Stage 2.1"). The user sees
  steps by *what they do*, not by their internal stage numbering.
- Do not produce artifacts (drafts, previews, plan files) that the user did not ask for and
  will not use. A config file is a deliverable only when the request is "give me a config".
- When a request can be satisfied in a single confirmation round, do not spread it over
  several turns to "be thorough".
- **Run first, investigate later.** Do not add pre-checks, defensive validation, extra
  confirmation rounds or tests for cases that have not happened. Speed and a simple
  interaction come first; when something actually fails, then open the detailed
  troubleshooting path (logs, failure matrix, edge cases).

### 1.3 不考古（No archaeology — do not mine existing platform history）

**Do not go looking through existing platform resources unless the user asked you to.**
That means: no `list-tasks` / `copy-task` archaeology, no scanning past runs, no digging
through old algorithm assets, no hunting for a "similar image someone used before", no
reading `~/.cloudrobo/pipeline-runs/*` for prior state.

Why: a new pipeline or a new custom operator is created from **the user's stated data,
goal and parameters** — not by reverse-engineering whatever happened to run previously.
Old assets carry stale images, stale commands and stale assumptions; adopting them is
how wrong values get propagated. Searching them also costs many rounds and produces
nothing the user asked for.

Rules:

- **New work uses fresh names and fresh values.** Derive the operator name, output name
  and OBS path from the current request, not from a previous run.
- **Only these lookups are in-scope without being asked:** the exact operator the user
  named (`list-publication-assets --name <exact name>`), the exact dataset the user
  pointed at, and the current workspace (`workspace current`) — because they are required
  to build the task at all.
- **Everything else is opt-in.** "Look at how it was done before", "find an existing image
  we can reuse", "check what other people used" — only when the user says so.
- **A name collision is not a reason to dig.** If a name is taken, propose a new name with
  a timestamp; do not go read the old asset to see what it contained.
- **Resuming is the exception.** `续跑 / 复用 / 接着上次 / continue` explicitly authorizes
  reading that specific prior state — and only that state.
- **An explicit single-point action needs no discovery at all.** When the user names both the
  action and the object ("register this script as an operator", "upload this directory",
  "run this operator on this dataset"), the decision is already made — execute it. Do not
  first check whether a same-name operator exists, whether some image could be reused, or
  what the preset operators cover; those answers cannot change what you were asked to do.
  Test before each query: *would a different result change my next action?* If no, don't run it.
- **A single-point action is not a pipeline.** "上传这批数据" means: run the upload, verify it
  landed, report. It does **not** mean "start a pipeline whose first step is upload". Do not
  `init` a run, write `plan.json`, open the monitor, resolve downstream operators, or propose
  a next stage unless the user asks. Concretely, a standalone upload is two commands:
  `import-asset` → `show-version`. Nothing else.
- **Do not pick an operator the user did not name.** If a step has more than one plausible
  producer — a platform operator *and* a script sitting in the user's project — the choice is
  theirs. Ask once: "这一步用平台现成算子，还是用你目录里的 `<script>`？" Never resolve, query
  or pre-fill a preset operator for a step the user has not specified.

---

## 2. Terminology

Three buckets: **delete**, **translate**, **keep**.

### 2.1 Delete — never shown to the user

`catalog_id` · `version_id` · `asset_id` · `image` / image tag · `envs` ·
`dataset_configs` · `inputs` · `head_spec` · `worker_spec` · `evs_spec` ·
`cluster_type` · `task_framework_type` · `output_type` · `algo_type` ·
`PRESET_ASSETS` / `WORKSPACE_ASSETS` / `OBS_ASSETS` · `BUILD_IN_ASSET` ·
`fail_fast` · `advisory` · `pending_action` · `schema v2` · `reserve-task` /
`resolve-action` / `set-result` · `run_id` · `expect-version` · `DRAFT` /
`RELEASE` (as bare status words) · `POD_PENDING` · `CCE` / `K8S` / `RAY` ·
`catalog` · `workspace_id`

These may appear in a collapsed "technical details" block **only when the user asks**.

### 2.2 Translate — use the right-hand column

| Internal term | User-facing wording |
|---------------|---------------------|
| asset / dataset version | data / dataset |
| operator | processing step |
| DRAFT / RELEASE | draft (ready to use) / published |
| workspace | project space（工作空间） |
| region / `cn-north-7` | never shown; it is environment context, not a decision the user makes |
| OBS path | cloud storage location（云存储路径） |
| version publication | (not applicable — the platform has no publish step for the final dataset; do not raise it) |
| mask / filter | mark problem frames (keep data) / delete problem data |
| POD_PENDING | queued for resources |
| advisory / `fail_fast: false` | informational only, does not affect results |
| built-in template / full workflow | standard 5 steps |
| DAG / `depends_on` / `input_from` / `parallel_group` | 步骤依赖（depends_on）、数据来源（input_from）、并行组（parallel_group）— Chinese-led with English in parens, never bare English |
| `import-asset` | 上传并注册数据集（import-asset） |
| `obs://` path | OBS 路径（obs://） |
| `get-log` / `show-task` / `create-task` etc. | 查看日志（get-log）/ 查看任务（show-task）/ 创建任务（create-task） |
| `asset` + `version` | 资产+版本（asset+version） |
| `4c8g` / `RAY` | 4核8G（4c8g）/ RAY 集群（RAY） |
| `state.json` / `<run_id>` | 状态文件（state.json）/ 运行 ID（run_id） |
| `pipeline.yaml` | 管线配置文件（pipeline.yaml） |
| `workspace` operator | 工作空间自定义算子（workspace 算子） |
| `OBS` 代码镜像 | OBS 挂载代码（不是镜像——OBS 存代码不存镜像） |
| upload & register | upload |
| format conversion | convert format |
| data cleaning | clean |
| data evaluation | evaluate |
| 训练就绪数据 dataset | dataset ready for training |
| custom operator / algorithm asset | your custom processing step |
| onboard an operator | add your step to the platform |
| deploy mode A / B | build an image / use existing runtime (default: use existing) |
| workspace algorithm / OBS algorithm | registered step / directly mounted code |
| `galaxea_r1` (and similar robot enums) | show with Chinese name: 星海图 R1 (galaxea_r1) — see table below |

**Strong rule — no bare English in user-facing text.** When a technical term must appear
(where the user needs to type it, or to disambiguate), lead with Chinese and put English
in parens: "步骤依赖（depends_on）", not bare "depends_on". Never write a sentence in
user-facing text that is mostly English identifiers like "用 pipeline.yaml 把多个算子组成
DAG：depends_on + input_from，支持 parallel_group 并行" — rewrite it as Chinese-led prose
with the English only as parenthetical clarifiers. CLI commands, file names, and JSON keys
in code blocks are exempt; this rule applies to prose the user reads.

**Code/interface identifiers never shown to users.** These belong to the implementation,
not the user experience — never write them in user-facing prose:
`wait-task` · `dataset proc` / `dataset eval` · `list-publication-assets` ·
`reserve-task` / `resolve-action` / `set-result` · `record-inputs` · `pipeline_state.py` ·
`CCE` / `CCE_RAY` / `K8S` / `RAY` · `PRESET_ASSETS` / `WORKSPACE_ASSETS` / `OBS_ASSETS` ·
`BUILD_IN_ASSET` / `UDF_OBS_ASSET` · `DRAFT` / `RELEASE` · `ext_metadata` ·
`task_framework_type` · `resource_pool_type` · `worker_spec` / `head_spec` · `evs_spec` ·
`catalog_id` · `asset_id` / `version_id` · `target_path` / `target_asset_id` /
`target_version_id` · `algo_id` / `algo_name` / `algo_entrance` · `dataset_configs` ·
`envs` / `inputs` / `params` · `depends_on` / `input_from` / `parallel_group` ·
`fail_fast` · `pending_action` · `run_id` · `schema v2` · `POD_PENDING` · `obs://` paths ·
`~/.cloudrobo/pipeline-runs/<run_id>/state.json` · `4c8g` / `2c4g` · `Asset Center`

When describing what these do, use plain Chinese:
- `wait-task` → "轮询任务状态" / "等待任务完成"
- `dataset proc` → "数据处理任务"；`dataset eval` → "数据评测任务"
- `depends_on` / `input_from` / `parallel_group` → "步骤依赖" / "数据来源" / "并行组"
- `CCE` / `CCE_RAY` → "标准集群" / "RAY 集群"
- `4c8g` → "4 核 8G 规格"
- `state.json` checkpoint → "断点续跑的状态文件"
- `PRESET_ASSETS` / `WORKSPACE_ASSETS` / `OBS_ASSETS` → "平台预置算子" / "工作空间算子" / "OBS 挂载代码"
- `DRAFT` / `RELEASE` → "草稿状态" / "已发布状态"
- `Asset Center` → "资产中心"
- `proc` task_config fields → just describe the task, not the JSON

Only when the user explicitly asks "怎么调用" / "命令是什么" / "JSON 怎么写" do you show
the actual identifier in a code block — never in prose.

**Robot model Chinese display names** — when a robot enum appears in a user-facing string,
show the Chinese name alongside the enum (e.g. `星海图 R1 (galaxea_r1)`), not the bare enum.
Known models (from the current `数据转换--ros转LeRobotV3` operator's
`ext_metadata.environment_variables[].valid_range` — re-query before relying on this list,
since the platform updates operator assets):

| Internal enum | 中文展示名 (Chinese display name) |
|---|---|
| `manifest` | 自定义配置（manifest） |
| `galaxea_r1` | 星海图 R1 |
| `galaxea_a1z` | 星海图 A1Z |
| `jaka` | 节卡（JAKA） |
| `moz1` | MOZ 1 |
| `azureloong` | 青龙（AzureLoong） |
| `ur5e` | UR5e（优傲） |

For an unknown model, confirm a Chinese name with the user or keep the English.

### 2.3 Keep — the only words the user needs

Data format (`ros2` / `h5` / `umi`), robot model, processing scope (which steps), and
the output dataset name. Everything else is the Agent's business.

---

## 3. Execution plan

Before any mutating operation, the plan must be shown and confirmed. Show it as **at most
8 lines**. Never print IDs, images, JSON, or state names in the plan body.

### 3.1 Template

```
Standard 5-step processing, est. 15–25 min:
  1. Upload   <path> (<n> trajectories, <size>)
  2. Convert  <format> → training format
  3. Clean    <mark problem frames, keep data / delete problem data>
  4. Evaluate quality + diversity (informational only, does not affect output)
  5. Output   dataset <name>

Resources: <public pool 4c8g (default) / dedicated pool ...>
Needs your decision: <only genuinely open choices, each with a recommendation>

Proceed?
```

**Never put an operator name, task name, stage id, or asset id in the plan body.**
The plan must stay user-intelligible: steps are described by what they do
("upload", "convert", "clean", "evaluate", "output"), not by which operator runs them.
A parenthetical like `（算子：数据转换--ros转LeRobotV3）` is internal mechanics — delete
it from user-facing text.

**Never leak detection internals.** Do not write `repo_id`, `region`, `workspace_id`,
source filenames, or how the inference was made. Detection results are stated in one
line (`Robot model: 星海图 R1 (inferred from data)`), nothing more.

**Output name**: derive from the directory name + a plain suffix the user would expect
(e.g. `<dir>-clean`), never from an internal stage id such as `teleop-clean` or
`convert-lerobotv3`.

### 3.2 Rules

- **Omit defaults from the question list.** If a value uses a safe default, state it on
  the resources/defaults line and move on; do not turn it into a question.
- **Cap the plan at 8 lines.** If a workflow has more stages, group them
  (`1. upload → 2. convert+clean → 3. evaluate`).
- **One expandable section.** Offer "change a step?" or "show technical details" instead
  of printing detail up front.
- **Never** show task names with timestamps, output OBS paths, or operator asset IDs in
  the plan.

### 3.3 Auto-detect instead of asking

**Precondition: the user has already told you the data and the goal (guided creation)
or supplied an input path (execution).** Before that point, do not inspect anything —
ask the Round-1 question in `SKILL.md` §Guided Custom Pipeline Creation.

Once the data is known, inspect what is already knowable:

| Value | How to detect without asking |
|-------|------------------------------|
| Data format | Directory contents: `.db3` / `metadata.yaml` → ros2; `.h5` → h5; UMI layout → umi |
| Robot model | ROS bag topic names / existing manifest yaml; otherwise ask |
| Trajectory count / size | `ls` the directory |
| Existing custom config | Look for `*manifest*.yaml` / `*convert*.yaml` in the data directory |
| Output name | Derive from directory name + pipeline prefix |

Only ask for what cannot be inferred. When inferring, **state the inference and let the
user confirm it in one click**, e.g. `Robot model: galaxea_r1 (inferred from data)`.
State the inference as a conclusion, never as a method — no `repo_id: ...`, no
`从目录名和 manifest 推断` in the user-facing text; that detail stays in your head.

---

## 4. Confirmation

### 4.1 One round, not many

All **independent** decisions must be asked in a **single** round. Only ask a later
question if it genuinely depends on an earlier answer.

```
Round 1 (one batch):  format?, robot?, scope?
  ↓ (only if needed)
Round 2 (rare):       a value that depends on round 1 (e.g. which custom config to mount)
```

Never split independent questions across turns. A typical run needs **one round of ≤4
questions**, each with a recommended default.

### 4.2 Use options, not free text

Confirm with selectable options. Always include a "use all recommended values" choice.
Free-text confirmation such as "plan" or "ok" is ambiguous — do not guess; if the reply
cannot be mapped to an option, ask one short clarifying question.

### 4.3 Authorization boundary

| Must ask (blocking) | Use default silently | Ask once, at the end |
|---------------------|----------------------|----------------------|
| Which data to upload | Resource spec (4c8g) | Whether to keep intermediate data |
| Overwrite an existing same-name dataset | Cleaning strategy (mark, don't delete) | — |
| Large or costly resource usage | Output name | — |
| Irreversible action | Open the monitor (default: open, tell them it can be closed) | — |
| Onboarding a new custom operator | — | — |

The platform does not expose a "publish/share" step for the final dataset — do not ask
about publishing or sharing it.

**Do not over-confirm the pipeline itself.** A custom pipeline is not a form to be approved
field by field. The Agent derives what it can from the stated data and goal, states those
derivations, and asks only about the choices that genuinely change the outcome. Concretely:

- **Ask the user how they want it to run**, don't present a finished config for approval.
  The user knows their data and intent; the Agent's job is to translate that, not to hand
  them a spec to rubber-stamp.
- **Do not re-ask what the user already said.** Path, format, goal, robot model and chosen
  operators come from the conversation.
- **Do not ask about safe defaults** (resource spec, output naming, cleaning strategy unless
  the user raises it). State them once on the defaults line.
- **Reuse only what the user named.** If the user says "use my existing operator X" or "reuse
  this dataset", reuse exactly that. Do not go hunting for other modules, images or assets to
  reuse — that is archaeology (§1.3).
- **One round, ≤4 questions**, each with a recommendation. If the request is fully specified,
  ask nothing and go straight to the plan.

### 4.3.1 Custom operator onboarding is a child plan (must be shown explicitly)

When a pipeline step needs code that no preset/workspace operator covers, onboarding that
operator is a **separate, user-confirmed child plan** under the pipeline parent plan. Never
fold it into the pipeline confirmation, and never start it because the pipeline is blocked.

The child plan the user sees must state, in their language:

```
转换步骤需要把你的本地脚本上云成一个算子。这会做：
  1. 备份原始代码 → <backup path>（原文件不改）
  2. 在工作副本里适配 → <work copy path>
       输入：平台注入数据目录，遍历其中文件，只把 .h5 交给转换
       输出：结果直接落在输出根目录（下游清洗要求该布局）
       其它：修正建库目录约束等会导致失败的地方
  3. 上传代码 → <OBS path>
  4. 注册为算子资产，并做一次试跑验证

运行环境（待你确认）：
  镜像 <由你指定：空间已有镜像资产 / 你提供的 SWR 地址 / 本地构建>
  启动 <interpreter> <entrypoint>

上云方式：<平台已有镜像资产 / 我提供镜像 URL / 本地构建镜像 / 代码放 OBS 挂载>
```

**镜像不由 Agent 推荐。** 不要为了填这一行去扫工作空间的镜像资产；直接问用户，用户点名后
才去查该镜像的地址与版本。依赖是否齐全也要如实说明或请用户确认。

Rules:

- **Adaptation must be visible.** List each adaptation (input contract, output layout, file
  filtering, failure-causing constraints) and why it is needed. "帮你适配一下" is not enough.
- **Backup and upload paths are explicit.** The user must be able to see that the original
  file is untouched and where the copy/upload goes.
- **The deploy method is a question, not a silent default.** Ask: existing image / build an
  image (Docker available) / mount code from OBS. Missing Docker on the local machine is a
  reason to ask, not a reason to decide for the user.
- **Never shop for an image on the user's behalf.** Do not scan workspace image assets,
  past runs, or other people's images to "recommend" one. Ask directly with the three
  options; only look up an image after the user names it. A scanned image is usually the
  wrong runtime anyway, and the scan costs many rounds.
- **Dependency status is stated honestly.** If the image's packages are unverified, say so
  and offer to verify, or let the user name an image they know.
- **Approval of the child plan is required before any copy or upload.** Approval of the
  parent pipeline does not imply approval of the onboarding.

### 4.4 If you ask, wait

Never act on an offer in the same turn you made it. If the user was asked "open the
monitor?", do not also start the monitor. An offer is not an authorization.

### 4.5 Fold the monitor offer into the same round

Instead of a separate turn after plan confirmation, include it in the confirmation batch:

> Open a progress page when done? (default: yes, can be closed anytime)

Opening the monitor needs no extra round-trip.

### 4.6 When to guide envs / inputs configuration

Most envs/inputs have safe defaults — state them on the defaults line and move on. But
when an operator declares **non-trivial** options, guide the user explicitly. A config is
non-trivial (must be guided, not defaulted silently) when any of these is true:

| Trigger | Example | What to do |
|---|---|---|
| The operator's `environment_variables[]` has no `default`, or the default is empty | robot enum with no default | Show valid values from `valid_range`, ask user to pick (one option pre-selected) |
| The inferred value differs from a built-in default and matters for the run | user's data is `galaxea_a1z` but operator default is `manifest` | Surface the inferred value, confirm in one option round |
| A `required: true` input has no built-in `url_path` | required config mount with empty url | Tell the user, ask for the `obs://` path |
| The user explicitly asks to customize a step | "configure the convert env", "mount my own config" | Enter the per-step config round for that step only |

**How to guide (not interrogate):**

1. Read the operator's current `ext_metadata.environment_variables[]` and `inputs[]` at
   discovery time — names/values are dynamic, never hardcode.
2. Translate each option into user language (e.g. robot enum `galaxea_a1z` →
   `星海图 A1Z`, input `CURATION_CONFIG_PATH` → `自定义清洗配置目录`).
3. **Pre-select a recommended value** for each — inferred from data, or the operator
   default — and offer it as the chosen option. The user can accept or pick another.
4. Ask in **the same confirmation round** as the other decisions, not a separate turn.
5. For `inputs` (OBS config mounts): ask only when the operator declares the input AND
   the run needs it (custom config, robot description a chosen metric needs). A
   `required:false` input with a safe built-in default stays silent.
6. Never expose raw JSON keys (`envs`, `inputs`, `dataset_configs`) or field names
   (`ROBOT_CONFIG_PATH`) in the question; describe what the user is choosing
   ("机器人型号？" / "是否使用自定义清洗配置？").

**Example — a1z data, conversion envs:**
```
转换步骤需要确认一项配置：
  机器人型号？ → 星海图 A1Z (galaxea_a1z)（从数据推断，推荐）
                  其他可选：星海图 R1 / 节卡 / UR5e / 自定义配置(manifest)

是否使用以上推荐值？
```

**Example — custom cleaning config via inputs:**
```
清洗步骤支持挂载自定义配置目录：
  是否使用自定义清洗配置？ → 推荐：不使用（用算子默认配置）
                              使用：请提供配置目录的 obs:// 路径
```

After confirmation, the Agent resolves the chosen values into `envs` / `inputs` internally;
the user never sees the JSON.

---

## 5. Progress

During execution, report **one line per stage transition**, nothing else:

```
[1/5] Uploading… 10 files
[1/5] Upload complete (1.5 min)
[2/5] Converting… 3 min elapsed (est. 2–5 min)
[2/5] Convert complete
...
```

Rules:

- **No JSON, no task IDs, no state fields** in progress lines.
- On `POD_PENDING`, say `queued for resources (public pool is busy)`, not `POD_PENDING`.
- If a stage runs long, re-state elapsed and estimate; do not re-post the whole plan.
- Keep all bookkeeping commands (reserve / create / verify / resolve / set-result /
  show-version) silent. Roughly two-thirds of tool calls are internal and must not
  surface.
- **Exception — investigation is visible** (§1.1). If execution needs a *new* read-only
  check not already announced earlier in the run (e.g. a fresh operator query after a
  failure, a version lookup, a name-occupancy check), announce it in one Chinese line
  first. Repeating an already-announced check stays silent.

---

## 6. Errors

When a stage fails, give **one line of cause + one line of action**. Then wait.

```
✗ Cleaning failed: robot description file is missing.
  Retry with the built-in config? (recommended) / show logs / stop
```

Rules:

- Translate the raw error; keep the original message only in a collapsible detail line.
- Always propose a concrete next step, with a recommendation.
- Never dump full logs unprompted. Offer `show logs` as an option.
- A failed **evaluation** is not a failure of the run — say
  `evaluation incomplete (informational only; data was produced)`.

---

## 7. Result summary

Default to a **one-page result**. The detailed template in
`pipeline-summary-template.md` is available on request, not by default.

### 7.1 Default one-page summary

```
✅ Done (19 min)

Data:     <name> (<n> trajectories, cleaned)
Location: <path or "see console">
Reports:  quality <link> · diversity <link> (links valid for 1 hour)

Next: start training on this data?
```

### 7.2 Rules

- **Three things only**: result, where it is, what's next.
- Do not print: task IDs, asset IDs, version IDs, resource specs, cluster types, the
  instantiated YAML, or per-stage tables — unless the user asks.
- Report links are temporary; say so once. Do not paste signed URLs with access keys when
  a console path is enough; prefer the console path and offer the link on request.
- The platform has no "publish/share final dataset" step — never ask about publishing or
  sharing the result. "What's next" suggests training, not publishing.
- On failure or partial result, lead with what succeeded and what is missing.

### 7.3 Expandable detail

Offer a single line: `Need task IDs / full reports / technical details?` — produce the
detailed template only if accepted.

---

## 8. Anti-patterns

These are real mistakes from a past run; do not repeat them.

| Anti-pattern | Why it's wrong | Correct behavior |
|--------------|----------------|------------------|
| 9 questions across 3 turns | Wastes turns, user loses context | 1 turn, ≤4 independent questions |
| Plan with `asset_id`, image tag, `envs` | User can't evaluate it; blind approval | 8-line plan, defaults stated |
| Asked "open monitor?" then opened it | Asked ≠ authorized | Ask, then wait |
| Asked about resource pool / cleaning mode / name prefix | All have safe defaults | State defaults, don't ask |
| Full summary with 8 sections and signed URLs | Overload; leaks tokens | One-page result, detail on demand |
| Guessed "plan" meant "execute" | Ambiguous confirmation | Options, not free text |
| Showed `pending_action` / `version: 21` | Internal mechanics leaked | Silent |
| Assumed a path name verbatim | Name mismatch cost a round | `ls` first, echo back the resolved path |
| Ran preflight / operator / asset queries with zero user-facing explanation | User could not tell anything was checked; felt like magic | One Chinese line before each investigation batch, Chinese summary after |
| Routed a matching sim/teleop request through guided creation and generated 3 config files | Built-in template fit; user got YAML they never wanted | Match template → one line → 8-line plan |
| Narrated "进入 Stage 0 / 查询算子 / 生成草案 / 校验 / 导出" step by step | Skill internals leaked; felt long and bureaucratic | Talk in user terms: 查一下 / 计划如下 / 开始执行 |
| Spread one decision over several turns "to be thorough" | Wastes turns | One round, then act |
| Scanned 57 workspace algorithm assets to pick an image for a new custom operator | User never asked; adopted a stale image/command pair and nearly shipped a wrong runtime | Ask the user for image + command; propose a recommendation, let them edit |
| Mined old tasks / old runs to "see how it was done before" | Archaeology: costs rounds, imports stale assumptions | Fresh names, fresh values; resume only on explicit request |
| Read prior pipeline-runs to reconcile state on a brand-new request | New request has no prior state to reconcile | Start clean; only read state when continuing |
| Turned "上传数据资产" into preflight + dir scan + h5 metadata read + 2 name checks + dry-run + init + monitor + record-inputs | User asked for one action; got a whole pipeline setup and 12 tool calls | Standalone upload = `import-asset` → `show-version` → report. Stop there |
| Pre-resolved the H5→LeRobotV3 operator for a step the user never mentioned, while their own `convert_to_lerobot.py` sat in the same directory | Chose the producer for the user; ignored the obvious alternative | Ask once which producer to use, or wait until the user names the step |
| Passed a single file to `--local-path` | CLI requires a directory; cost a failed round-trip | Check the parent dir has only data, pass the directory |
| Wrote `record-inputs` input as an array | File must be an object keyed by input ID (`{"default": {...}}`) | Use the documented object shape |

---

## 9. Minimal checklist

Before sending anything to the user, check:

- [ ] Every read-only investigation batch was announced in one Chinese line, with a Chinese
      summary of the finding (no raw JSON).
- [ ] The minimal path was chosen: built-in template first if it fits; no config files or
      interview rounds the user did not ask for.
- [ ] No archaeology: I did not scan old tasks, old algorithm assets, old images or prior
      runs unless the user asked or explicitly resumed one.
- [ ] No IDs, images, JSON, or state-machine words in the message.
- [ ] Plan is ≤8 lines; defaults are stated, not asked.
- [ ] All independent questions are in one round, each with a recommended value.
- [ ] Nothing was acted on in the same turn it was offered.
- [ ] Progress is one line per stage; bookkeeping is silent.
- [ ] Summary is one page; detail is offered, not dumped.
- [ ] Every failure comes with a concrete, recommended next step.
- [ ] Everything is rendered in the user's language.

---

## 10. 逐步或调试模式（opt-in）

执行节奏取决于**工作流是否已验证**：

- **内置模板 / 已固化的 YAML**：标准模式（默认，一次确认 → 自动跑完）。用户可用触发词
  "逐步/分步/调试/边跑边看/stepwise/debug" 切换为逐步或调试模式。
- **自定义工作流**：默认就是**逐步跑通**（见 SKILL.md §Build-by-Running）——一次只加一步、
  每步核实产物。这不是 opt-in；算子契约在跑之前是未知的，自动跑完等于把未知留给云端。

逐步或调试模式激活后，会在每个算子**前**确认配置、每个算子**后**看输出——两个暂停点
都生效，用户不需要分别选择 stepwise 还是 debug。

### 10.1 算子前暂停 — 确认配置

计划确认后、每个算子运行前，暂停一次确认该算子的环境变量/输入挂载配置。按 §4.6
规则：读取算子当前配置、用中文展示选项、预选推荐值、一轮问完。

```
[2/5] 转换算子配置（推荐值已预选）：
  机器人型号？ → 星海图 R1（从数据推断，推荐）
  其他可选：星海图 A1Z / 节卡 / UR5e / 自定义配置

是否使用以上推荐值？（是 / 改）
```

规则：
- 只对非平凡配置暂停（按 §4.6 触发条件）；算子全部有安全默认值时跳过暂停，直接宣布该步
- 每个算子只问一轮，不拆多轮
- 暂停用 await-decision 机制；用户选择记录后该算子运行，无需新基础设施

### 10.2 算子后暂停 — 看输出

每个算子到达终态后，暂停展示输出，问继续/调整/停止。暂停发生在记录结果后、下一个算子前。

```
[2/5] 转换完成：
  输出：星海图R1数据-convert（2 条轨迹 → LeRobotV3）
  路径：云存储路径
  帧数：1240 帧

继续下一步？（继续 / 调整配置重跑 / 停止）
```

规则：
- 只展示三件事：输出名、位置、帧数（评测算子用预览链接）
- 不展示任务 ID、JSON、资源规格，除非用户问
- "调整"→ 用新配置重跑该算子（新建任务，确认后）；"停止"→ 停止管线，保留已产出
- 算子失败时仍暂停，展示错误 + 推荐下一步（重试 / 跳过（若为信息性阶段）/ 停止），按 §6

### 10.3 默认（未激活时）

标准模式：一次确认 → 自动跑完 → 一页结果。除非逐步或调试模式激活、或某步真正失败，
否则不插入任何暂停。

---

## 11. Save as template (opt-in)

After a successful run, offer **once** to save the confirmed `pipeline.yaml` as a reusable
template. Default = do not save; never raise it twice.

```
本次运行成功。是否保存为模板供下次复用？（默认：不保存 / 保存为 <name>）
```

Rules:
- Save path: `~/.cloudrobo/pipeline-templates/<name>.yaml`.
- Save the confirmed `pipeline.yaml` + `authoring.output_names`; do NOT persist asset_ids
  or image versions — operators are re-queried fresh before each future run (assets update).
- On reuse: read the template → one-round reconfirm of data source / robot model / output
  name → run. The template carries the workflow shape, not the live operator pointers.
- A saved template is a user file; the built-in `sim-teleop-cleaning.yaml` is separate.
