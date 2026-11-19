---
name: huawei-cloud-cloudrobo-data-pipeline
description: |
  Guide users to create or revise custom CloudRobo pipelines for sim/teleop VLA model training
  data — generate validated pipeline.yaml drafts from natural-language requirements without
  hand-written YAML. Compose workflows from selected preset and workspace algorithm assets, with
  optional OBS processing operators. Offer sim/teleop conversion → cleaning → evaluation as an
  explicitly selected template (内置模板名：仿真/遥操VLA模型数据处理管线，版本式命名如
  仿真/遥操VLA模型数据处理管线-26.10.0001), with dynamic operator discovery, CLI-only Agent task submission,
  artifact handoff and local Web monitoring via a Python SDK backend.
  Triggers include: 创建自定义管线, 引导配置管线, 帮我设计管线, 生成pipeline.yaml,
  修改管线步骤, custom pipeline builder, 仿真数据处理, 遥操数据清洗, 数据管线,
  数据转换, 数据清洗, 数据评测, 训练就绪数据, 仿真/遥操VLA模型数据处理管线, data pipeline,
  打开管线监控, 打开监控网站, pipeline monitor, web monitor.
version: 2.8.0
date: 2026-10-31
tags:
  - huawei-cloud-cloudrobo
  - data-pipeline
  - data-cleaning
  - data-processing
  - data-evaluating
  - pipeline-orchestration
  - sim-teleop
  - training-ready
---

# CloudRobo Data Pipeline Orchestration Skill

For end-user walkthroughs of authoring, execution, Web pages and recovery, see the
[User Guide](references/user-guide.md).

## 0. Context budget — read references on demand

This file is the always-loaded core. The `references/` files are **not** loaded unless you
open them, so opening one costs context for the rest of the session. Follow these rules:

| Situation | Read |
|---|---|
| About to submit a proc/eval task | `references/stage-execution.md` — **only the stage you are running** |
| Need the full task_config template / field tables | `references/task-config-catalog.md` (look up the section, don't read whole) |
| About to call `pipeline_state.py init --plan`, or need YAML/plan structure | `references/pipeline-templates.md` §YAML Structure / §Full plan.json example |
| Authoring a custom workflow | `references/custom-pipeline-authoring.md` |
| Deciding what the user sees | `references/user-facing-interaction.md` |
| A task failed / need retry guidance | `references/fault-recovery.md` |
| Web monitoring | `references/web-monitor.md` |

Rules:

- **Never open more than one reference file in the same step** unless the task genuinely
  needs both. Read the section you need, not the whole file.
- **Do not pre-read** references "just in case". Open them at the moment the step requires.
- `references/user-guide.md`, `references/web-monitor-test-report.md`,
  `references/acceptance-criteria.md`, and `references/dataflow-diagram.md` are
  **documentation for humans**. Do not read them to execute a run.
- If context is already tight, prefer a targeted `grep` over a full-file read.
- When a reference file grows past ~400 lines, split it rather than appending.

**Key features:**
- **Standard mode** (default): one confirmation round → auto-run to completion; minimal
  interruption for the common case.
- **Stepwise/Debug mode** (opt-in, trigger words "逐步/分步/调试/stepwise/debug"): pause
  before each operator to confirm its `envs`/`inputs` config, AND/OR after each operator to
  show its output (path, frame count, preview link) and ask continue / adjust / stop. For
  custom pipelines, unfamiliar operators, or first-time runs. Stepwise and debug can
  combine.
- **Save as template**: after a successful run, offer once to save the confirmed
  `pipeline.yaml` to `~/.cloudrobo/pipeline-templates/<name>.yaml` for reuse; the saved
  template re-queries operators before each future run (asset IDs are not trusted across
  runs).
- Local Web monitoring, checkpoint resume, fault recovery, and dynamic operator discovery.

> **User-facing interaction is governed by
> [User-Facing Interaction Rules](references/user-facing-interaction.md).** Everything the
> user sees — the execution plan, the confirmation round, progress lines and the result
> summary — follows that document: show decisions, hide mechanics; one confirmation round;
> one-line progress; a one-page result. Internal terms (asset/version IDs, image tags,
> `envs`, `dataset_configs`, `fail_fast`, `POD_PENDING`, `pending_action`, state versions)
> never appear unless the user asks for technical detail.
>
> **Two rules override the default "hide mechanics" instinct:**
> 1. **Investigation is visible** (§1.1). Before each batch of read-only checks —
>    environment preflight, directory scans, operator discovery, asset/version lookups,
>    name-occupancy checks, data-metadata reads — emit **one short Chinese line** saying
>    what is being checked and why, then report the finding as a Chinese summary (never raw
>    JSON). Bookkeeping stays silent; investigation does not.
> 2. **Minimal path first** (§1.2). Pick the cheapest workflow that reaches the goal:
>    built-in template → guided creation → hand-written YAML, stopping at the first that
>    fits. A sim/teleop request matching the built-in template goes straight to the 8-line
>    plan — no guided-creation interview, no `pipeline.yaml`/draft/preview files the user
>    never asked for. Never narrate internal stage numbering ("进入 Stage 0", "查询算子",
>    "生成草案").
> 3. **An explicit single-point action needs no discovery** (§1.3). When the user names both
>    the action and the object ("register this script as an operator", "upload this
>    directory"), execute it directly. Do not pre-check same-name operators, reusable
>    images, or what preset operators cover — none of those results change the requested
>    action. Before any query ask: *would a different answer change my next step?* If no,
>    don't run it.

> Compose and run the user's selected operator workflow. The 仿真/遥操(sim/teleop) processing chain
> is an optional template. **Agent orchestration uses CLI commands. The optional Web backend uses the
> Python SDK for platform queries and confirmed within-step task creation; the browser calls local HTTP APIs.**

For **full-pipeline** execution requests such as “submit local data to the data pipeline”, keep input
preparation inside this run: confirm the full plan → `init` using the **original** local/OBS/asset
source → offer/open this run's monitor → prepare inputs with Asset Center → `record-inputs` → submit
ready tasks. Reading the asset skill early does not authorize importing before these steps.
Uploading creates an input asset; it does not turn this run's original `source_type: local`
into `asset`, or make its upload step skipped. Only assets already supplied for reuse at
the start of this run qualify for that not-applicable state.

> **⚠️ A single-point request is not a pipeline.** When the user asks only for one action —
> "上传这批数据" / "上传数据资产" / "register this directory" — do exactly that action and stop.
> Do **not** resolve downstream operators, do not `init` a run plan, do not create `plan.json`,
> do not run the monitor offer, and do not propose a next stage unless the user asks.
> The upload itself is: one `import-asset` call (+ one `show-version` to confirm it landed).
> Everything in the following sections about plans, checkpoints and monitors applies to a
> **multi-step pipeline run**, never to a standalone upload. See
> [User-Facing Interaction Rules §1.3](references/user-facing-interaction.md#13-不考古no-archaeology--do-not-mine-existing-platform-history).

---

## Overview

### Pipeline Stages

Clarify input and goal → select operators and dependencies → validate compatible data
handoffs → review/export → confirm execution → prepare input as needed → run the declared
workflow → verify the selected data output and reports.

Only the built-in 仿真/遥操VLA模型数据处理管线 template uses Stage 0→5 below: parse → upload/register →
convert → clean → evaluate → output. Custom workflows may consist entirely of preset
operators, workspace algorithms, or a mixture; conversion, cleaning and evaluation are
chosen according to the user's goal and the actual operator contracts.

### Execution Modes

| Mode | User Intent Example | What it does |
|------|-------------------|--------|
| **Built-in pipeline** | "use the 仿真/遥操VLA模型数据处理管线 template" | Run the full standard 5-step flow (upload → convert → clean → evaluate → output) on your local or OBS data; no YAML needed. Built-in template name: 仿真/遥操VLA模型数据处理管线 (versioned, e.g. 仿真/遥操VLA模型数据处理管线-26.10.0001); file `templates/sim-teleop-cleaning.yaml` |
| **Build-by-running custom pipeline (default for custom)** | "创建个自定义管线，指导我一步步构建" / "用这批数据调试" / "先接转换，再接清洗" | **Run one step at a time on real data, fix what breaks, then freeze the proven chain into `pipeline.yaml`.** The YAML is the *record* of a working run, not an up-front prerequisite. See [Build-by-Running](#build-by-running-custom-pipeline) |
| **Guided custom creation / revision (plan-first)** | "design a pipeline, don't run it" / "show me the YAML" / "add a step to this existing YAML" | Ask a few questions, then generate a `pipeline.yaml` + editable draft + preview **without executing**; execute only if you say so. Use when the user explicitly wants config-only, or is revising an existing YAML |
| **Continue from existing data** | "I already have converted/cleaned data; just add evaluation" | Skip the already-done steps, run only the steps you select on data you already have |
| **Open monitoring** | "open the monitor site" / "show current pipeline monitoring" | Open the local Web page that tracks each pipeline run in real time — shows current step, progress, and results for runs you've started; nothing is created or submitted |
| **Stepwise/Debug mode** | "逐步跑" / "分步配置每个算子" / "调试模式" / "边跑边看" / "stepwise" / "debug" | Same pause points as Build-by-Running, applied to a **template/standard** run that would otherwise auto-run to completion. Opt-in for template runs; for custom workflows the pauses are already the default, so this only adds explicit per-operator config confirmation. |

### Mode Routing (critical)

Route by **what the data and goal actually are**, not by which trigger word the user
happened to type. Apply §1.2 minimal-path-first:

1. **Does the built-in template fit?** The template covers sim/teleop raw data
   (H5/ROS2/UMI) → convert → clean → evaluate → output, with the operator set already
   published. If the user's data and goal match this shape, **say so in one line and go
   straight to the 8-line execution plan** — even when the request was phrased as
   "创建自定义管线" / "引导创建" / "设计管线". Generating three config files for a workflow
   the template already expresses is exactly the verbosity §1.2 forbids.
2. **Does it genuinely differ?** A workflow needing a custom/workspace operator, extra or
   removed stages, a non-standard input stage or a multi-branch merge goes to
   **Build-by-Running** by default (see below) — not to a YAML-first interview.
3. **Config-only or YAML revision?** "不执行/先出 YAML/给现有管线加一步" → Guided custom
   creation (plan-first), no execution.
4. **User supplied a YAML?** Parse it directly.

When the request is ambiguous ("跑个管线" with no data detail), ask ONCE, with a
recommendation based on the data: "这批数据用标准流程（转换 → 清洗 → 评测）就行，还是有
特殊步骤？" — do not present the built-in/guided split as a formal menu.

**Never ask the user to choose between "template" and "custom" as a naming question.**
The user cares about the outcome; the routing decision is the Agent's job.

### Build-by-Running Custom Pipeline

**A custom pipeline is proven by running it, not by writing YAML first.** Real operator
contracts (accepted feature dtypes, required mounts, env enums, output layout) are
discovered by execution; several are invisible until a task actually runs. So for custom
workflows:

1. **Run one step at a time.** Upload/register the input, run the first operator, verify
   its real artifact, then add the next. Do not compose a five-stage plan and discover
   the third stage's contract violation after the first two hours of compute.
2. **Verify each artifact against the next operator's contract before submitting it.**
   Not just "task SUCCEEDED" — inspect what was actually produced (feature dtypes, layout,
   required files) and compare with what the consumer declares. A task can succeed and
   still hand downstream an input it will reject.
3. **Fix by changing the producer, not by hand-editing the artifact.** When a downstream
   operator rejects upstream output, repair the producing operator and re-run it. Do not
   patch the dataset by hand to make it pass — the pipeline must reproduce from scratch.
4. **Freeze only after the chain runs end to end.** Then write `pipeline.yaml` from the
   *verified* run: real operator names, real `envs`, real handoff. Offer to save it as a
   template once (§11). A YAML written before the first run is a guess; one written after
   is a reproducible recipe.

Per-step interaction follows [User-Facing Interaction Rules](references/user-facing-interaction.md)
§10 (confirm before a step whose config is non-trivial, show the artifact after a step,
ask continue/adjust/stop). Build-by-Running is *not* opt-in — it is the default shape for
custom workflows, because the unknowns are exactly the operator contracts.

### Uploading Local Data

When a pipeline needs to upload local data, the Agent uses the **Asset Center skill**
(`huawei-cloud-cloudrobo-asset`) — its `import-asset` command handles both the cloud
upload and the dataset registration in one step. The Agent preserves this pipeline's
confirmed workspace, input directory, dataset name and naming choices.

- **Local directory**: `cloudrobo asset import-asset --local-path ...` uploads and
  registers the dataset together. Do not look for generic OBS tools, `obsutil`, `aws s3`,
  raw storage APIs or custom upload scripts, then register the same data again.
- **Existing `obs://` source**: register it as an asset (do not re-upload); pass the OBS
  URL to `create-version`, not to `--local-path`.
- **Existing asset/version**: verify and reuse it; do not re-create.
- **Standalone upload** ("上传这批数据"): run `import-asset` → `show-version` → report. No
  plan, no `init`, no monitor, no operator lookup. `import-asset` auto-creates the asset,
  version and upload in one call; a name collision is handled by the CLI's own naming, and
  is not a reason to pre-scan the catalog. See the scope gate in
  [Execution Plan Confirmation](#execution-plan-confirmation-mandatory--for-multi-step-runs-only).
- **As part of a confirmed multi-step plan**: upload starts after the plan is confirmed and
  the monitor-opening offer has been made. Reuse that approval for unchanged import scope;
  do not re-ask just because the asset skill was loaded.
- After import in a multi-step run, record the actual asset/version IDs, verify with
  `show-version`, then call `record-inputs` on the **same run initialized before import**.
  Keep the original `source_type` and `local_path`/`obs_path`; add registration metadata
  rather than rebuilding the plan as an existing-asset run. A returned ID alone does not
  prove the files finished uploading. On partial failure, use the asset skill's recovery
  with the verified IDs and original confirmed input; do not blindly create another
  asset/version, delete an incomplete version or publish RELEASE.

If the companion skill is not installed in a standalone environment, keep using the same
asset CLI workflow documented here and report that limitation; a separate OBS tool is
not a prerequisite.

> **Ordering comes from operator contracts:** validate each upstream format and output
> against its consumer. LeRobot evaluation requires compatible data, not a mandatory
> cleaning ancestor. Do not insert conversion or cleaning merely to match the template.

### Data Flow Contract & Skip-Stage Input

For the built-in template, each stage's output feeds the next as shown below. For custom
workflows, pass each declared proc input as an ordered `dataset_configs` entry, each eval
input as matching top-level fields plus one `dataset_configs` entry, and take final data
from `pipeline.output.from_stage`. Recommend a single dataset per branch (not a proc
restriction); a merge-capable proc operator may consume A and B's datasets and produce one.
Use ordered `input_from` for data sources and `depends_on` for waiting gates. Evaluation
accepts one dataset; merge first if evaluation needs the combined result. Verify multi-input
count, order, formats and single-dataset output against the actual operator.

> **"SUCCEEDED" is not "handoff-compatible".** Before submitting a downstream step, inspect
> the produced artifact itself, not just the task status: confirm the layout, feature
> declarations and required files against what the consumer enforces. An operator's
> declared contract is often looser than what its implementation actually accepts, and a
> task can report SUCCEEDED while handing downstream an input that will be rejected.
> When they conflict, fix the **producer** and re-run it; never hand-patch the artifact.

Existing processed data can be supplied as an asset, OBS directory or local directory; only
perform the upload/registration required by that source, without adding template stages.

| From → To | Handoff Values |
|-----------|----------------|
| Stage 0 → 1 | `source_type`, `obs_path` / `local_path` / `asset_id`+`version_id`, `data_source_type`, `robot_type` |
| Stage 1 → 2 | `dataset_asset_id`, `dataset_version_id`, dataset name, dataset OBS path (from `show-version`) |
| Stage 2 → 3 | Conversion `target_path`, `target_asset_id`, `target_version_id`, `<conversion output_name>` → cleaning `dataset_configs` |
| Stage 3 → 4 | Cleaning `target_path`, `target_asset_id`, `target_version_id`, `<cleaning output_name>` → eval top-level fields + single-item `dataset_configs` with `version_id`; optional `inputs` config mounts |
| Stage 4 → 5 | Per-member eval `task_id` / `status` / `target_report_path` and report links; 训练就绪数据 path = cleaning `target_path` |

If a required handoff value is missing, ask the user. A missing version or asset name can
be resolved with `cloudrobo asset list-versions --asset-id <id> --sort-key created_at
--sort-dir desc --limit 1` and `cloudrobo asset show-asset --asset-id <id>`; confirm with
the user.

---

## Prerequisites

**Authoring only needs Python 3.9+.** During guided custom creation — before the user has
stated the data and the goal — do **not** run `cloudrobo config get region`,
`cloudrobo workspace current`, environment preflight, or any asset/task query. Ask the
Round-1 question in
[Guided Custom Pipeline Creation](#guided-custom-pipeline-creation) first.

Local authoring requires only Python 3.9+; no cloud authentication or available operator
is needed to save a clearly marked draft. The following prerequisites apply **only when
executing the pipeline** (resolving real platform metadata or submitting tasks), not when
merely creating local files.

1. **CloudRobo CLI** installed + authenticated via `cloudrobo config set ak <ak> sk <sk>` or
   `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` — see
   [CLI Installation Guide](references/cli-installation-guide.md)
2. **workspace_id** set via `cloudrobo workspace use --workspace-id <id>` (or pass
   `--workspace-id` to `create-task`)
3. Raw data available: local directory, registered asset, or OBS path
4. Resource pool with available quota for data processing tasks (see Resource spec in
   Step 2.3)
5. The required operators are published in the current CloudRobo site (checked at
   discovery time; see Step 2.1)
6. IAM permissions for asset, dataset proc/eval and OBS operations — see
   [IAM Policies](references/iam-policies.md)

### Execution Environment Preflight

**Only when needed.** A standalone `import-asset` / `show-version` / monitor-open does **not**
need a preflight — just run the command; if it fails on auth or a missing CLI, report that.
Run this preflight when the task requires a **local script** (custom operator adaptation,
`pipeline_state.py`, `custom_pipeline.py`) or when you are about to **resolve a multi-step
execution plan** against the platform.

**Announce before running** (§1.1): 「先检查本地环境和云端连接。」 Then report a one-line
Chinese summary (interpreter found / CLI available / current site) — not the raw output.

Before the first local script, identify the actual shell (Git Bash, PowerShell, or other),
select an available Python interpreter and verify it really runs Python 3.9+. Accept
Miniconda's `python`; do not assume `python3` or `py -3` exists. Reuse the verified
interpreter for subsequent scripts. Examples below use `python3` as notation; adapt the
launcher and shell syntax before executing. Git Bash paths use quoted forward slashes,
e.g. `cd 'C:/Users/name/My Project/skill'`. Detailed shell examples and checks are in the
[CLI Installation Guide](references/cli-installation-guide.md#environment-preflight).

**Never use `which`** — it is absent on Windows Git Bash and aborts the whole command
chain. Use `command -v` (Bash/Git Bash) or `Get-Command` (PowerShell), and tolerate
missing binaries with `|| echo NOT_FOUND` so a missing tool does not fail the chain.

Before resolving a real execution plan, run `cloudrobo config get region`; this reads
local configuration, not a live check. Cross-check the intended CloudRobo site against
available workspace/endpoint information, including explicit intranet endpoint overrides.
If the command is unavailable, the value is missing, or sources conflict, ask the user
before real execution; never infer the CloudRobo site from an SWR image URL or silently
change configuration. Note the site source in the plan explanation. A local draft may
leave the site unresolved; opening existing monitoring does not require this preflight.

---

## Workflow

### Open Monitoring Only

For “open the monitor site”, “open pipeline monitoring” or equivalent requests, go directly to
[Local Web Monitoring](#local-web-monitoring) and the default-opening rules
in [Web Monitor](references/web-monitor.md). This request authorizes starting/reusing the
local service and opening the browser; do not first ask whether to use demo or real mode.

> **An offer is not an authorization.** If you *ask* whether to open the monitor, you must
> wait for the answer before launching it. Do not ask and launch in the same turn.

- Use the real run ID and runs-root already established in the conversation, if present.
- With no established run ID, open the real run list without `--run`. An empty runs-root
  is valid: show the empty list and explain that there are no local runs yet.
- Opening the site does not require creating a pipeline, confirming an execution plan,
  initializing sample run records, or having cloud credentials merely to view an empty list.
- Use `--demo` only when the user explicitly asks for a demo, simulated data, or the offline
  website experience. Missing cloud access, missing run IDs or an empty list are not
  reasons to recommend or silently switch to demo mode.
- Only clarify a genuinely unresolved target (for example, conflicting user-specified
  runs-roots); multiple existing runs can be selected on the run-list page.

### Requested Processing Skip

The Web offers “跳过…” for an unsubmitted single-input proc stage. It records an
`awaiting_decision.kind: skip` request; it does not immediately mark the stage skipped
or submit downstream tasks. Existing advisory evaluation skip remains a direct action.

**Agent responsibility boundary**: on a skip request the Agent only performs **technical compatibility verification** — check that the stage's original input (asset/version/path) is compatible with the current CLI input contract of every direct downstream operator. The Agent **must not** reject a skip for business reasons such as "user goal", "训练就绪数据 requires it" or "business need"; the user's explicit skip in the Web UI takes precedence over the Agent's business inference. Verification is limited to "can downstream consume this input" and excludes judgments such as "is this data suitable for training".

On reading such a request, inspect [processing skip](references/web-monitor.md#processing-skip):
verify the exact original asset/version/path and every direct downstream operator's
current CLI input contract (including each eval member and merge input position).
Unknown compatibility requires clarification or verification, never a guessed approval.

**Skip rules (two cases)**:
- **A conversion stage cannot be skipped**: raw H5/ROS2/UMI data must be converted to LeRobotV3 because the preset cleaning/evaluation operators require LeRobotV3 input. Raw data cannot bypass conversion.
- **A cleaning/evaluation stage may be skipped when downstream is compatible**: cleaning consumes the conversion output (already LeRobotV3), not raw data. When the downstream operators (e.g. quality-eval/diversity-eval) accept LeRobotV3 input, compatibility verification passes and the skip **should be approved** (`--decision skip`).

**Example: compatibility verified → approve the skip** (operator descriptions must come from the current `list-publication-assets` result; do not reuse the wording below):
- clean stage input = convert output (LeRobotV3 format) ✓
- downstream quality-eval description explicitly accepts LeRobotV2.1 or LeRobotV3 datasets ✓
- downstream diversity-eval: same ✓
- Conclusion: compatibility verified → approve with `--decision skip`, recording the compatibility note and the initial-input mapping (convert's asset/version/path)

After verification use `pipeline_state.py resolve-skip` with the latest state version,
explicit compatibility note and any verified initial-input mapping. Incompatible input
must keep the stage (`--decision keep`); explain the specific contract.

**Concurrent version conflicts**: the Web UI and the Agent may act concurrently, so a "state version changed" error from `resolve-skip` is expected, not a bug. Refresh the state (`show`) and retry `resolve-skip` with the latest version; do not abandon the request because of a version conflict.

An applied bypass records `bypassed: true`, `status: SKIPPED` and the original dataset's
name/path/asset/version. Follow that recorded handoff instead of submitting the skipped
stage or inventing its output. Multiple-input merge stages, submitted tasks, and downstream
already submitted/finished are not eligible. Completion reports skipped processing as a
warning and must not claim that conversion/cleaning or a new data version was produced.

### Stage 0: Pipeline Parsing

Determine pipeline source and parse the pipeline definition.

#### Guided Custom Pipeline Creation

**Round 1 is fixed. Until the user has stated the data and the goal, do not scan
directories, read data files, run preflight, or query the platform.** Ask only:

> 你希望处理什么数据、得到什么结果？如果已有想用的算子，请告诉我名称和顺序。

**Then default to [Build-by-Running](#build-by-running-custom-pipeline):** run the first
step on the real data, verify its artifact, then add the next. Do **not** open with a
multi-stage YAML for confirmation — the operator contracts are not yet known.

Read [Guided Custom Pipeline Authoring](references/custom-pipeline-authoring.md) for the
interview details and the freeze-into-YAML step, and reuse information already given.
Collect missing choices just-in-time as each step comes up (data stage/source, params,
resources, failure policy). Do not ask the user to write YAML or silently choose the full
built-in template. Only when the user explicitly says "不执行/先出 YAML/给现有管线加一步"
do you produce `pipeline.yaml` + draft + preview up front instead.

Only after the user answers may you inspect the stated path and discover candidate
preset/workspace operators for that goal. Do not prefill stages, data formats, robot type,
quality/diversity evaluation, or output names; a custom workflow does not require custom
operator code.

**Custom steps — reuse or create.** When the user wants a processing step that no preset
operator covers, ask **once**, in the same confirmation round:

> This step needs custom code. Use an existing custom operator from your project space, or
> add a new one now? (default: use an existing one if any exists)

- **Reuse an existing custom operator** → set the stage's `operator_source: workspace` and
  resolve it with `cloudrobo asset list-assets --catalog-id <id> --type algorithm
  --tags "Data Processing" --name "<fragment>"`. Show the matches by **name only** (no
  asset IDs); if there is exactly one match, use it and state so.
- **Add a new one now** → the pipeline is the **parent** plan; onboarding the operator is a
  **child** plan that must be presented and confirmed on its own before any code is copied
  or uploaded. Do not start onboarding inside the pipeline confirmation round, and never
  treat "the pipeline needs it" as approval to onboard.

  Sequence (mandatory):

  1. Write the child plan (see
     [Custom Operator Onboarding Handoff](references/custom-pipeline-authoring.md#custom-operator-onboarding-handoff))
     and get explicit approval.
  2. Only then **invoke the `huawei-cloud-cloudrobo-dataset` skill via the Skill tool** — a
     mandatory cross-skill delegation, not a documentation reference. The dataset skill owns
     the 自定义算子上云 execution (code backup, code adaptation, image build/OBS mount,
     asset registration, runtime verification, cleanup). Do not hand-roll those steps or
     generate the files yourself.
  3. When it returns the registered algorithm asset, resume the parent pipeline plan.

  If the user has no preference and no existing operator matches, **ask** whether to onboard
  a new one — do not onboard on their behalf just because the pipeline is blocked. The
  onboarded workspace algorithm asset is usable in `DRAFT` status — do not publish it to
  `RELEASE` and do not prompt the user to publish.

Use `scripts/custom_pipeline.py` to check/export the JSON choices assembled from the
conversation. Deliver pipeline.yaml, pipeline.draft.json and pipeline-preview.md. Drafts
can be saved offline with unresolved fields explicitly listed; local validity does not
verify live operators. Preserve existing files and do not invent asset IDs, image versions,
env names or input declarations.

Creating local files is the requested action: finish that work without an extra approval
gate. A creation-only request ends with these artifacts; it does not authorize cloud
submission, asset registration, version publishing or initializing a confirmed Web run.
If execution was requested, continue into the existing Stage 0 discovery/plan confirmation,
carrying authoring.resources/output_names/upstream into task configuration and monitor
planning; the detailed guide describes the handoff.

#### Built-in Pipeline (Template)

Load `templates/sim-teleop-cleaning.yaml` whenever the data and goal match its shape —
an **explicit** "用内置模板" request, OR a sim/teleop request whose workflow is exactly
raw H5/ROS2/UMI → convert → clean → evaluate → output. Per §1.2, matching the template
must not be routed through guided creation just because the user said "创建管线".

Announce the match in one line ("这批数据走标准流程就行，不用单独配管线"), then go
straight to the execution plan. Only fall back to guided creation when the user needs a
step the template lacks.

Follow [User-Facing Interaction Rules](references/user-facing-interaction.md): detect what
can be detected, then confirm in **one round**.

- **Announce detection** (§1.1): one line — 「先看下数据目录，确认格式和机器人型号。」
  then state the findings in Chinese. Do not scan silently.
- **Detect first**: input source (look at the path), `data_source_type` from directory
  contents, `robot_type` from topic names / existing manifest.
- **Ask only what cannot be detected** — typically just the input path if not given, and
  any genuinely ambiguous robot type. State inferences for confirmation
  (`Robot model: galaxea_r1 (inferred from data)`), rendered in the user's language
  with a Chinese display name where applicable (see
  [User-Facing Interaction Rules §Terminology](references/user-facing-interaction.md#terminology)).
- **Do not ask** about the resource pool (default public pool 4c8g), the cleaning strategy
  (default: mark problem frames, don't delete), or the output name (derive from the
  directory name + pipeline prefix). State them on the defaults line.
- Ask whether to open the progress page in the **same round** (default: open). The
  platform has no "publish/share final dataset" step — do not ask about publishing or
  sharing the result.

`data_source_type` (h5/ros2/umi) is an input format label — the operator is explicitly
specified in pipeline.yaml.

#### Custom Pipeline

User provides a `pipeline.yaml` → parse directly, no template loading needed.
When a companion pipeline.draft.json is present, read its authoring resources, step roles,
output names and partial-input handoff too; check that its pipeline matches the YAML, and
resolve any mismatch with the user's current edits. The companion is configuration, not
execution authorization. Missing resources or custom-step roles are collected in Stage 0.

> **No `type` field**: There is no type selector in pipeline.yaml. Natural-language custom
> creation uses the guided flow above; an explicit built-in-template request loads that
> template. Existing YAML is parsed directly.

#### Build Stage DAG

Parse `stages[]` and `depends_on` to build a topological order:

- `depends_on` describes waiting gates. Without `input_from`, an omitted dependency uses
  the previous stage; one dependency also supplies the legacy data input.
- `input_from` lists actual data sources in order: stage IDs for proc outputs, or
  `input:<id>` for initial datasets (`input:default` for one unnamed legacy input).
  When provided without `depends_on`, its stage references become waiting dependencies.
  With explicit `depends_on`, include every referenced producer; control-only gates are
  permitted. Multiple dependencies without `input_from` require clarification, not guessing.
- Multiple initial datasets use unique input IDs and explicit branch bindings; each is
  registered/verified separately. See the [multi-input example](references/custom-pipeline-authoring.md#multi-input).
- `parallel_group` stages submit all members before waiting; cloud execution may overlap,
  subject to resource scheduling. Separate stages sharing a dependency can also run in parallel.
- Circular dependencies → error, ask user to fix

For custom workflows, resolve each stage's selected `operator_source` independently:
`preset` → marketplace algorithm, `workspace` → workspace algorithm asset,
`obs` → user-provided processing code/image. Use `kind: proc` or `kind: eval` for task
dispatch; eval tasks reference preset/workspace assets and have no `--algo-type` flag.
Query subtype and input/output contracts rather than inferring them from a stage ID.
Verify formats for every edge before executing; add an adapter step only when needed and
accepted by the user. Eval reports are not data inputs for subsequent processing tasks.

`pipeline.output.from_stage` identifies the proc stage whose verified data is delivered;
`pipeline.output.asset_name` names that task's output. The helper resolves a unique last
proc stage automatically based on data consumption, not control-only gates. Multiple
unmerged output branches require an explicit final selection; merging is an explicit proc step. Other proc output names are recorded in `authoring.output_names`.
Eval-only workflows deliver reports and preserve the input dataset instead of inventing
a new data output. The Web output check waits for all terminal workflow branches.

#### Submit Ready Branches Before Waiting

Use one task graph and one ready queue for every workflow. The local adapter expands
`parallel_group` members into task nodes and group waiting edges to all members; saved YAML
and Web grouping stay compatible. After registration, submission or result update, call
`pipeline_state.py --run <run_id> ready-tasks`:
- `action=submit` → submit returned ready nodes before polling; resolve + re-query after each
  (queue is a snapshot, not a reservation)
- `action=reconcile` → resolve the existing transaction first
- `action=poll` → no ready task remains; short CLI status rounds on active tasks
- `decide`/`blocked` → relevant decision/input/manual check needed;
  `readonly`/`stopped` → no submission

For each create: `reserve A → create A (without --wait) → verify with show-task → resolve A`,
then immediately do the same for ready B. Resolve records the task ID while pending/running;
do not wait for execution success to release the transaction. The single pending-action
protocol prevents concurrent creates but never holds the slot for the cloud task's runtime.

**Full CLI chain** (reserve-task → create-task → verify → resolve-action → wait-task →
set-result): see the complete 7-step example in
[Web Monitor §parallel-submission](references/web-monitor.md#parallel-submission).

When the user requests parallel A/B from the same registered dataset, bind both with
`input_from: ["input:default"]` (or the chosen initial ID); do not omit B's binding and
accidentally inherit A as its dependency. Distinct branches may select distinct initial
datasets. A downstream merge explicitly waits for both A/B outputs.

Only wait when no currently ready task remains unsubmitted. With independent branches in
flight, query all active task IDs in a short CLI show-task round (about every 15 s), record
changed results/heartbeats and re-evaluate ready steps each round. Avoid a 300-second
single-task wait that delays another newly ready branch. Cloud resource shortages may still
queue an already submitted B; report its task ID/status separately from an Agent-delayed
submission.

#### Execution Plan Confirmation (Mandatory — for multi-step runs only)

**Scope gate first.** This rule applies when the user has asked for a **pipeline** (two or more
stages, or "run the whole flow"). It does **not** apply to a standalone action:

| User asked for | Do | Do NOT |
|---|---|---|
| "上传这批数据" / "upload this dataset" | `import-asset` once, confirm with `show-version`, report | resolve operators, `init`, monitor, propose next stage |
| "用 X 算子处理这批数据" (one named step) | submit that one task after confirming its config | plan the remaining stages for them |
| "建个管线 / 跑完整流程 / 转换+清洗+评测" | resolve the stages and show the plan | — |

For a multi-step run, before **any** mutating operation (`create-asset` / `create-version` /
`import-asset` / `update-version` / `create-task`), resolve the operators (Steps 2.1, 3.1, 4.1) and show the
user the plan. **Follow
[User-Facing Interaction Rules](references/user-facing-interaction.md)** — the user-facing
plan is **at most 8 lines** and contains no IDs, image tags, JSON fields or state names.
The plan body must not contain operator names, stage ids, task names, region/site info,
workspace info, or detection internals (repo ids, source filenames, inference methods) —
describe each step by what it does (upload / convert / clean / evaluate / output), not by
which operator runs it. The output dataset name is derived from the directory name with a
plain suffix (e.g. `<dir>-clean`), never from an internal stage id like `teleop-clean`.

**Never choose an operator for the user.** When a step could be served by more than one
producer — a preset operator *and* a script the user already has in their project (e.g. a
`convert_to_lerobot.py` next to the data) — the choice is the user's. If the user did not
name the operator for that step, ask **once**, in the same confirmation round:
> 转换这一步用平台现成的转换算子，还是用你目录里的 `convert_to_lerobot.py`？
Do not resolve, pre-select or pre-fill a preset operator for a step the user never specified.

The Agent must still resolve and hold internally: input source and assets/versions to be
created; per stage the resolved operator, `--algo-type`, `envs` and `inputs` mounts;
resource pool type and specs; task names, output names and paths. Be able to show them on
request.

**What the user sees** — the 8-line plan template, the one-round confirmation rules, and
the "detect before asking" requirement are all in
[User-Facing Interaction Rules §3–§4](references/user-facing-interaction.md). Follow that
document; it is the single source for the plan format.

Non-negotiable:

- Proceed only after explicit user confirmation. Re-confirm if any value changes later
  (e.g. a smaller flavor after a resource queue, or a new task after `FAILED`).

After confirmation, save the instantiated plan as JSON and initialize schema v2 with
`python3 scripts/pipeline_state.py --run <run_id> init --plan <resolved-plan.json>`.
Use the input source supplied for this run, even when registration IDs become available
later. For a local directory, preserve `source_type: local` and `local_path`; IDs need not
exist at init. Do not import first to fill those IDs, reclassify the result as an existing
asset, or create a second run when moving from input preparation to conversion.
The monitor was already offered in the confirmation round. If the user accepted it (or had
already asked for it), start/reuse the service and open this run **before** Stage 1 input
upload/registration or any task submission. If they declined or did
not answer, do not open a browser — no response means no browser launch, not execution
failure. Never offer the monitor again on retries, wait segments or checkpoint recovery.
Local init does not establish successful cloud submission; the page can already show the
confirmed plan and pending/not-applicable input preparation without a task ID.

### Stage 1: Data Upload & Registration

Use [Uploading Local Data](#uploading-local-data): read the Asset Center
skill for local imports and asset/version operations. This is input preparation, not a
reason to switch to a generic OBS command workflow.
Prepare input data based on `source_type` from pipeline inputs. In every case, capture
`asset_id` / `version_id` from the command output and read the version with `show-version`.

**Case A: Registered Asset (`source_type: asset`)**

When all inputs were supplied as existing assets/versions for reuse at the start of this
run, the monitor retains `upload` as
SKIPPED with a not-applicable reason; do not upload/register again or treat this as an
advisory failure. Still verify the actual version/path and any required RELEASE status.
An asset created by this run's local import or OBS registration belongs to Case B/C;
its completed upload/registration is **SUCCEEDED / registered**, never skipped.
Local input requires upload + registration; OBS input requires registration only. These
preparation steps and plan/output checks do not create proc/eval tasks.

```bash
# asset_id / version_id given → read directly; otherwise find the dataset first
cloudrobo workspace current   # Get asset_catalog_id
cloudrobo asset list-assets --catalog-id <catalog_id> --type dataset --name "<dataset_name>"
cloudrobo asset list-versions --asset-id <asset_id> --sort-key created_at --sort-dir desc --limit 1
cloudrobo asset show-version --asset-id <asset_id> --version-id <version_id>
```

**Case B: OBS Path (`source_type: obs`)**

```bash
cloudrobo workspace current   # Get asset_catalog_id
cloudrobo asset create-asset --catalog-id <catalog_id> --name "<dataset_name>" --type dataset --ext-metadata '{"annotation_status":true}'
cloudrobo asset create-version --asset-id <asset_id> --url "<obs_path>"
cloudrobo asset show-version --asset-id <asset_id> --version-id <version_id>
```

**Case C: Local Directory (`source_type: local`)**

Follow the asset skill's local-import workflow. `import-asset` handles both upload and
registration; do not add a separate OBS upload or repeat `create-asset/create-version`
after a successful import. The commands below are that same asset CLI path:

```bash
cloudrobo workspace current   # Get asset_catalog_id
cloudrobo asset import-asset --catalog-id <catalog_id> --type dataset --name "<dataset_name>" --local-path "<local_path>" --ext-metadata '{"annotation_status":true}'
cloudrobo asset show-version --asset-id <asset_id> --version-id <version_id>
```

> **⚠️ Upload ONLY the actual data files — never the whole working directory.**
> `--local-path` accepts a single file or a folder; a folder is uploaded **entirely,
> recursively**. If the user's data sits in a project directory that also holds scripts,
> `pipeline.yaml`, `plan.json`, `work-copy/`, READMEs, etc., passing the directory uploads
> all of it and the operator's `process()` is later called on every stray file.
> Before importing:
> 1. List the directory and identify the real data files (here: `.h5`).
> 2. If the directory contains non-data files, **stage the data files in a clean temporary
>    folder first** (copy only the data files there) and import that folder, or import the
>    file(s) one by one.
> 3. Verify after import that the version contains only the expected files.
> Creating a staging folder is a local copy operation; state the staging path in the plan.

**Version handoff**: read the exact version with `show-version` and verify its path and
status. A verified `DRAFT` input is consumed by the platform as-is; do not raise
publication of the input version with the user. If a downstream failure is verified to be
caused by a release-status requirement on the input, treat it as an operator limitation
and report it; do not proactively publish. Other failures (path, permission, format,
unfinished upload) are not reasons to change version status.
Versions such as `CREATING` or unknown states still need readiness checks.

The dataset OBS path passed to Stage 2 is the version `url` from `show-version` — do not
concatenate paths manually.
Persist every verified initial dataset (asset ID, exact version, actual name and version
URL) with `pipeline_state.py --run <run_id> record-inputs --inputs-file <resolved-inputs.json>
--expect-version <current_state_version>` before downstream submission; see
[input registration](references/web-monitor.md#record-inputs). It completes the upload
bookmark only after all inputs have registration metadata. Do not write only
`{"status":"SUCCEEDED"}` for upload, leave verified IDs only in conversation/task configs,
or flatten multiple datasets into upload's single target fields.

> **⚠️ `record-inputs` file shape:** the file is a **JSON object keyed by input ID**, not an
> array. For a single unnamed input the key is `default`:
> ```json
> {"default": {"asset_id": "...", "version_id": "...", "asset_name": "...", "obs_path": "obs://..."}}
> ```
> Each value may contain **ONLY** these four keys —
> `asset_id`, `version_id`, `asset_name`, `obs_path`. An array, or adding extras (`source_type`,
> `local_path`, `data_source_type`, …), fails with
> `JSON 文件必须包含对象` / `输入登记每项必须且只能包含 asset_id、version_id、asset_name、obs_path`. The original
> source/locality stays in `state.inputs` from `init`, not in this file. Also pass
> `--expect-version` (read it from `show` first) or the command errors out.
>
> **⚠️ All `pipeline_state.py` file arguments (`--result`, `--inputs-file`, `--config`) take
> FILE PATHS.** Inline JSON (`--result '{"status":"FAILED"}'`) fails with
> `[Errno 22] Invalid argument`. Write the JSON to a file, pass the path.
>
> **⚠️ Windows/Git Bash:** prefer writing task_config to a `.json` file and passing
> `--task-config "$(cat file.json)"`; avoid nested-quote inline JSON that the shell mangles.

### Stage 2: Format Conversion (Built-in Template Reference)

Stages 2–4 below document the optional 仿真/遥操VLA模型数据处理管线 template's concrete operators and CLI
examples. Custom workflows use their declared operators and dependencies; these numbered
steps are not mandatory stages and must not be inserted automatically.

Convert raw data to LeRobotV3 format. The conversion operator is specified explicitly
via `operator` (exact Chinese name) or `operator_id` (asset_id) in pipeline.yaml —
`data_source_type` (h5/ros2/umi) is the input data format label, not an auto-selection
mechanism.

#### Step 2.1: Discover Conversion Operator

**Announce first** (§1.1): 「查一下平台上现成的转换算子。」 Then report which operator was
found and its robot options — not the raw JSON.

`data_source_type` maps to the expected operator name as a guide only:
`h5`→`数据转换--H5转LeRobotV3`, `ros2`→`数据转换--ros转LeRobotV3`,
`umi`→`数据转换--UMI转LeRobotV3`. Discover with a Chinese name fragment:

```bash
cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "H5转LeRobotV3"
# or --name "ros转LeRobotV3" / --name "UMI转LeRobotV3"
```

Match the result against the stage's exact `operator` name (or `operator_id`). If `--tags`
returns nothing, retry with `--sub-type data_processing --name "<fragment>"`.

> **Operator not found → stop**: if the required operator is not returned in the current
> CloudRobo site, stop and tell the user. Never silently substitute another operator;
> continue only if the user explicitly changes the stage `operator` / `operator_id`.

> **Dynamic discovery — query fresh every time**: never hardcode asset IDs and **never
> reuse operator info (image/algo_id/command/inputs) from a previous run** — the platform
> updates assets (new image versions, fixed commands) and a stale image can silently fail.
> Re-run `list-publication-assets` before every submission and use the **current** result;
> confirm unique match, else ask user.

#### Step 2.2–2.4: Build and Submit

**Read [Stage Execution Detail](references/stage-execution.md) now** — it holds the field
mapping, `inputs` mount rules, required `task_config` fields, resource specs, submission
command, and the wait/extract procedure for all proc stages.

Non-negotiable rules that stay here (they apply before you open that file):

- Every operator field (`algo_id` / `algo_name` / `algo_entrance` / `image` / `envs` /
  `inputs`) comes from the **current** `list-publication-assets` result.
- `envs` and `inputs` are JSON-array **strings**, not native objects; names must exist in the
  operator's `environment_variables` / `inputs` declarations.
- Submit **without** `--wait`, record the `task_id`, then wait.
- Input `dataset_configs` uses the Stage 1 asset and the version `url` from `show-version`.
- Output `output_name` = the conversion output name confirmed in the plan.
- `SUCCEEDED` → extract `target_path` / `target_asset_id` / exact `target_version_id` and
  verify with `show-version`. Timeout → re-run `wait-task`, do not resubmit. `FAILED` /
  `DELETED` → diagnose with `get-log`, then create a **new** task after user confirmation
  (see [Fault Recovery](references/fault-recovery.md)).

### Stage 3: Data Cleaning

Run the single `数据清洗` (data cleaning) operator on the converted LeRobotV3 dataset.
The operator runs the following sub-checks:

- **Outlier detection** — extreme value detection (极值检测)
- **Anomaly detection** — action mutation detection (动作突变检测)
- **State-action consistency check**
- **FK correction**
- **Base-frame alignment**
- **Blur frame detection**

These sub-check names are descriptive only — they are not pipeline.yaml keys. A custom
cleaning config can be supplied via the operator's `CURATION_CONFIG_PATH` input when the
operator exposes it (it does in the current release).

> **Verify the input against what this operator actually enforces before submitting.**
> Its declared `ext_metadata` can be looser than its implementation; a task may also fail
> after already writing partial output, so read the log tail rather than judging by the
> presence of a report directory.

#### Step 3.1: Discover Cleaning Operator

```bash
cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "数据清洗"
```

> **Operator name**: match the exact `数据清洗` name (or `operator_id`) and confirm a unique
> match. If it is not found, apply the "Operator not found → stop" rule from Step 2.1.

#### Step 3.2–3.3: Build, Submit, Extract

Same mechanics as Stage 2 — follow [Stage Execution Detail](references/stage-execution.md)
§Stage 3. Cleaning-specific points:

- **Input**: `dataset_configs` from Stage 2's `target_path` / `target_asset_id` /
  `target_version_id` / `<conversion output_name>`.
- **envs**: dynamic from the operator's `environment_variables` (e.g. `mode` = cleaning
  strategy, `robot` = robot type). Map `robot_type` to an enumerated value
  ([Robot type mapping](#robot-type-mapping)).
- **inputs**: optional `CURATION_CONFIG_PATH` from stage `params.inputs`.
- **Output**: `output_name` = `pipeline.output.asset_name` (训练就绪数据集名).

### Stage 4: Data Evaluation

Run quality evaluation + diversity evaluation (both depend on cleaning output). The two
evaluations run as separate tasks on the cleaned dataset.

#### Step 4.1: Discover Evaluation Operators

```bash
cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "质量评测"
cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "多样性评测"
```

Match the exact names `数据集质量评测-LeRobot` / `数据集多样性评测-LeRobot` (or `operator_id`).
If `--tags` returns nothing, retry with `--sub-type data_evaluating --name "<fragment>"`;
if still not found, apply the "Operator not found → stop" rule.

#### Step 4.2–4.4: Build, Submit, Wait, Fetch Reports

Follow [Stage Execution Detail](references/stage-execution.md) §Stage 4 — it holds the eval
`task_config` template, input fields, mount rules, submission commands, wait procedure and
report fetching.

Points that stay here:

- Eval tasks use `dataset eval create-task` (no `--algo-type`).
- Both eval tasks take the **same** cleaned input: top-level dataset fields + a single-item
  `dataset_configs` carrying the exact cleaning `target_version_id`.
- `robot_config` is removed — config directories go through the operator's declared
  `inputs`. A CLI demanding `robot_config` is outdated; upgrade it.
- Submit both **without** `--wait` before waiting on either; reserve/create/resolve for the
  first, then the second immediately.
- Evaluation is informational only — a failed evaluation does not block the final
  training-ready dataset.

### Stage 5: Output

After the pipeline reaches the end (or stops at a terminal state), output the result to the
user. **Follow [User-Facing Interaction Rules](references/user-facing-interaction.md)** —
default to a **one-page result**; the detailed template is offered on request, not dumped.

**Default one-page result:**

```
✅ Done (<duration>)

Data:     <name> (<n> trajectories, cleaned)
Location: <path or "see console">
Reports:  quality <link> · diversity <link> (links valid for 1 hour)

Next: start training on this data?
```

Render this in the user's language before sending.

Rules:

- **Three things only**: result, where it is, what's next. Do not print task IDs, asset
  IDs, version IDs, resource specs, cluster types, the instantiated YAML, or per-stage
  tables unless the user asks.
- Offer detail with one line (`Need task IDs / full reports / technical details?`) and produce the full
  [Pipeline Summary Template](references/pipeline-summary-template.md) only if accepted.
- Report links are temporary; say so once. Prefer a console path over a signed URL; offer
  the link on request rather than pasting access keys unprompted.
- **Save as template** (opt-in): after a successful run, offer once to save the confirmed
  `pipeline.yaml` to `~/.cloudrobo/pipeline-templates/<name>.yaml` for reuse; default = do
  not save, never raise twice. See
  [Save as template rules](references/user-facing-interaction.md#11-save-as-template-opt-in).
- **Stepwise / Debug modes** (opt-in): activated only by trigger words ("逐步/分步/stepwise"
  / "调试/边跑边看/debug"); never offered proactively. See
  [Stepwise and Debug modes](references/user-facing-interaction.md#10-逐步或调试模式opt-in).
- The platform has **no "publish/share final dataset" step** — never ask about publishing
  or sharing the result. "What's next" suggests training, not publishing.
- On failure or partial result, lead with what succeeded and what is missing, then one
  concrete next step.

**Before reporting success, verify internally** (never surfaced unless asked): check
artifacts with `show-task` and `show-version`; a task can be `FAILED` while its output
partly exists, or `SUCCEEDED` while a downstream operator rejects the output.

> **Output follows the selected workflow:** read `target_path` and asset/version from
> `pipeline.output.from_stage`, not from a stage named cleaning. Report processing and
> evaluation coverage honestly. 训练就绪数据 is a use-specific conclusion after verifying
> the relevant data requirements; custom processing alone does not establish it.

> **Failed-stage honesty**: Report failed stages with a translated one-line cause plus the
> original error available on request, and verify actual artifacts before claiming success.
> A failed **evaluation** is not a run failure — say
> “evaluation incomplete (informational only; data was produced)”.

See [Pipeline Summary Template](references/pipeline-summary-template.md) for the detailed
template (produce on request only).

> **Mark manual stages before `finish`**: `finish` requires every non-skipped stage to have a terminal status.
> Of the `kind: manual` stages (`plan`/`upload`/`output`), only some are completed automatically;
> `set-result`：
> - `upload`: marked SUCCEEDED automatically by `record-inputs` (no manual step)
> - `plan`: marked SUCCEEDED automatically by `init` (no manual step)
> - `output`: **must be marked manually** — once the proc stage named by `pipeline.output.from_stage`
>   is SUCCEEDED, run `set-result --stage output --expect-task none --result <result.json>`; the result
>   carries the from_stage's target_path/target_asset_id/target_version_id/output_name
>
> Example (write the JSON to a file first — `--result` takes a **file path**, not inline JSON):
> ```bash
> cat > /tmp/result.json <<'JSON'
> {"status":"SUCCEEDED","output_name":"<from_stage output_name>","target_path":"<from_stage target_path>","target_asset_id":"<from_stage target_asset_id>","target_version_id":"<from_stage target_version_id>"}
> JSON
> python scripts/pipeline_state.py --run <run_id> set-result \
>   --stage output --expect-task none --result /tmp/result.json
> ```
> **⚠️ `--result` and `--inputs-file`/`--config` take FILE PATHS.** Passing inline JSON
> (e.g. `--result '{"status":"FAILED"}'`) fails with `[Errno 22] Invalid argument` on
> Windows and is parsed as a path. Always write the JSON to a file and pass its path.
> Call `finish` after marking it.

### Error Handling & Checkpoint Recovery

| Scenario | Strategy |
|----------|---------|
| Stage task `FAILED` | Diagnose with `get-log` (system + job logs); then `retry` (create a **new** task after confirmation) or `skip` (only for informational stages like evaluation — a failed informational stage does not stop the pipeline); required stages stop the pipeline until resolved |
| Stage task `DELETED` | Treat as failed: check logs / resource (e.g. `POD_PENDING` on public pool), adjust after confirmation, create a new task |
| `wait-task` timeout while non-terminal | Re-run `wait-task` and report status and elapsed time; user decides continue / view logs / terminate; do not resubmit |
| Session interrupted | Resume from the checkpoint file (below); continue from the interrupted stage |
| Evaluation FAILED | Informational only — does not block the final training-ready dataset |
| Operator not found | Stop and tell the user; never substitute another operator |

Recovery always creates a new task. See
[Fault Recovery](references/fault-recovery.md) for per-stage causes and the retry/skip
decision.

**Checkpoint**: `~/.cloudrobo/pipeline-runs/<run_id>/state.json`, schema v2. Save the
confirmed plan to plan.json via `pipeline_state.py init`; preserve submission configurations
with `set-task --config`, and record statuses/artifacts via `set-result`. Both Web and Agent
use the same file lock and expected task ID (CAS); never edit state.json directly. Keep all
previous attempts. Old `<run_id>.checkpoint.json` can be imported read-only; see
[Web Monitor](references/web-monitor.md). On resume or each new user turn, read state first,
follow changed task IDs, honor skips/termination, and continue the interrupted stage.

### Long-Running Async Execution Strategy

Data processing tasks may take 10–60 minutes each. Use checkpoint recovery + `wait-task`.

**Wait settings**: use `dataset proc|eval wait-task --timeout 300 --interval 15` in repeated
segments, with heartbeat + state reload after each segment. The CLI defaults remain 1800s
timeout / 10s interval. Terminal states: `SUCCEEDED` / `FAILED` / `DELETED`.
Include full pipeline state (all task IDs) in prompt for Agent to determine current stage
on resume.

**User-facing progress**: report **one line per stage transition** — see
[User-Facing Interaction Rules §5](references/user-facing-interaction.md#5-progress).

```
[2/5] Converting… 3 min elapsed (est. 2–5 min)
```

Do not surface task IDs, JSON, state versions or bookkeeping commands (reserve / resolve /
set-result / show-version). Translate queue states: `POD_PENDING` → `queued for resources
(public pool is busy)`. Render progress in the user's language.

### Local Web Monitoring

A local Web page tracks each pipeline run in real time: current step, task status,
elapsed time, and final result for every run you have started on this machine. It needs
only Python 3.9+ (no extra packages, no cloud login just to view an empty list).

- It observes runs and handles within-step actions; it does **not** submit downstream
  stages or stop/delete cloud tasks on its own.
- Detailed per-task resource usage (CPU/memory/etc.) is viewed in the CloudRobo Console
  using the task ID; the local monitor does not query usage metrics.
- After Web actions, resume at the terminal with "continue" — the Web does not auto-run
  the next stage.

Default opening is the real run list; use an established run ID to open its detail page.
Immediately after plan confirmation and local run initialization, before input
upload/registration or task submission, offer this run's real monitor once unless the
user already accepted/declined or requested opening it. Selecting terminal-only leaves
the run records available for a later explicit opening request. Creation-only drafts do
not trigger this offer or initialize a monitor run.
The run list and detail page offer **删除本地记录** for schema v2 runs that are succeeded,
succeeded with warnings, failed or terminated, with no unresolved submission transaction.
The user confirms in the Web dialog; deletion removes that run's local files/history and
cached views, and never stops/deletes cloud tasks, OBS data or assets. Active/awaiting runs
must terminate orchestration first. Deleted records cannot be resumed; do not re-init the
same run to conceal a missing checkpoint. See the Web guide for deletion/error handling.

**New runs must not inherit stale local state.** `~/.cloudrobo/pipeline-runs/` accumulates
records from every past run on this machine. A new run is identified by a fresh `run_id`;
never resume, re-init or overwrite an existing run directory to "clean up" a previous
attempt. When the user asks for a clean start (`从头开始`, `重跑`, `不要用之前的`), or when
a stale record would otherwise cause a conflict:

- Use a **fresh** `run_id` for the new work. Do not touch old run directories.
- If the user explicitly asks to remove old local records, list them first and confirm the
  scope (this deletes local history only — never cloud tasks, OBS data or assets).
- Stop the local monitor before deleting run directories, then restart it afterwards.
- Local scratch dirs created by a previous attempt (`.workcheck/`, temporary work copies,
  local test outputs) are also stale: clear the ones belonging to the new run's scope before
  reusing them, or use a fresh subdirectory. A "directory already exists" error from an
  earlier attempt is not a code defect — clear it and retry.
- Never delete the user's source data, their operator scripts, or their backup directory.

```bash
# Default: persisted real runs, including an empty list; no run_id required
python3 scripts/pipeline-monitor/server.py --background --open

# An existing real run identified in the conversation
python3 scripts/pipeline-monitor/server.py --run <run_id> --background --open
python3 scripts/pipeline-monitor/server.py --stop

# Only when the user explicitly requests an offline demo (isolated runs-root, background)
python3 scripts/pipeline-monitor/server.py --demo --runs-root /tmp/cloudrobo-demo --background --open
python3 scripts/pipeline-monitor/server.py --runs-root /tmp/cloudrobo-demo --stop
```

1. Preserve terminal monitoring. Web observes and handles within-stage operations; it does
   not submit downstream stages. After Web actions, resume at the terminal with “继续”.
2. Use `pipeline_state.py` for all checkpoint changes: init, set-task, set-result,
   await-decision, heartbeat, finish. Mutating step commands require `--expect-task`;
   use `none` before first submission. Exit 3 means reload and inspect pending_action,
   task/version changes and terminal status; follow the actual cause, not an assumed Web action.
   Before **every** create-task, reserve-task with the expected ID/name/config; only the
   reservation winner may create, then resolve-action with the verified new ID. set-task
   is for recording already-existing tasks, not a substitute for pre-create reservation.
   Each run has one pending submission transaction. For parallel members, reserve A →
   create/verify A → resolve A, then reserve B → create/verify B → resolve B. Do not wait for
   A to finish before submitting B: task execution remains parallel. See the complete
   [parallel submission example](references/web-monitor.md#parallel-submission) and
   [set-result field list](references/web-monitor.md#result-fields).
3. Before any new cloud submission and after every wait segment, reload state. If task_id
   changed follow it; if skipped continue; if TERMINATED stop; if pending_action exists
   wait/reconcile first. Record each confirmed task_config with set-task.
4. Blocking failures: record FAILED then await-decision, enabling the orange Web banner.
   Agent heartbeat older than 12 minutes shows the offline reminder. Web and terminal
   decisions use the same lock; the first valid transaction wins.
5. Web retries query the current preset operator and verify upstream version/path; verified
   DRAFT and RELEASE inputs are supported, while other states require terminal verification.
   They show an editable draft and create a new task only after checkbox confirmation.
   Missing operators/config, stale status and conflicts block submission. Custom OBS or
   workspace operator retries remain terminal operations with fresh discovery.
6. Only advisory steps can be skipped; terminate requires run ID confirmation and leaves
   existing cloud tasks running. The monitor never invokes cloud deletion or in-place restart.
7. After recording every terminal member and the verified output artifact, call finish.
   Advisory failures/skips use SUCCEEDED_WITH_WARNINGS (the summary's PARTIAL).

See [Web Monitor](references/web-monitor.md) for command examples, schema, API, uncertain
submission recovery, legacy read-only import and intranet smoke checks. See
[Web Test Report](references/web-monitor-test-report.md) for local verification and limits.

---

## pipeline.yaml Structure

The pipeline.yaml (snake_case keys) declares:

- `pipeline.name`, `pipeline.workspace_id` (optional)
- `pipeline.inputs[]` — `source_type` (`local` / `asset` / `obs`), `obs_path` /
  `local_path` / `asset_id`+`version_id`, `data_source_type`, `robot_type`; unique `id` for
  multiple sources, optional verified `asset_name`/`obs_path` for asset handoff
- `pipeline.output.asset_name` — sets the selected final proc task's `output_name`
- `pipeline.output.from_stage` — final data source stage; inferred only when there is one
  terminal proc output, otherwise explicitly selected
- `stages[]` — `id`, `operator` (exact Chinese operator name) or `operator_id`,
  `operator_source` (+ OBS fields), `depends_on`, `input_from` (ordered data references), `fail_fast` (stage-level, default `true`;
  evaluation `false`), `parallel_group` (members `{id, operator|operator_id, params}`),
  `kind` (proc/eval for single tasks; optional for groups),
  `params` (only `envs` and `inputs`; config files such as the eval robot description are
  mounted via `params.inputs`). `robot_config` is no longer accepted.

The operator is explicitly specified, not auto-inferred.

**Stage `id` vs `operator`**: `id` = ASCII DAG label for `depends_on` and task naming
(`convert-lerobotv3`, `cleaning`, `quality-eval`, `diversity-eval`) — not a search
keyword. `operator` = exact Chinese marketplace name (e.g. `数据清洗`), resolved with
`list-publication-assets --name` and confirmed unique; `operator_id` = exact asset_id.
One resolution path, no `auto` branch.

**New task/data names (grouped prefix)**: default to
`<pipeline_name>-<stage_id>-<MMDDHHmmss>`, using local month/day/hour/minute/second.
Use the stage ID (parallel evaluation uses the member ID), not a long operator title;
keep the full operator name/ID in metadata. One pipeline's tasks and data assets share
its pipeline prefix for searching. Example: `teleop-convert-1018102430` and
`teleop-clean-1018102430`. Newly registered input assets may use the short label `input`.
After the workflow is chosen, suggest the selected data-producing stages once:

```bash
python scripts/custom_pipeline.py suggest-names --pipeline-name teleop --stage input --stage convert --stage clean
```

The helper is local and read-only. It uses **no random suffix**; duplicate suggestions
within the same process and second get `-2`, `-3`, etc. Separate helper calls/machines
are not a global uniqueness guarantee: before final confirmation, check same-name dataset
assets in the selected workspace catalog, for example
`cloudrobo asset list-assets --catalog-id <catalog_id> --type dataset --exact-name <candidate>`.
If occupied, propose a new timestamp or a short ordinal, recheck it, and persist that name.
The **entire name is limited to 64 characters**, including both separators, timestamp
and any ordinal. Preserve pipeline/stage components; if over the limit, ask for shorter
pipeline or stage short names rather than silently cutting them. For new workflows,
prefer short meaningful IDs (e.g. `convert`, `clean`); do not rename an existing DAG's IDs
just for appearance. Task names must be 3–64 legal characters; proc output names 2–64.

#### Full plan.json example

See [Pipeline Templates §Full plan.json example](references/pipeline-templates.md#full-planjson-example)
— read it when you are about to call `pipeline_state.py init --plan`, not while planning.

The invariants that stay here:

- Every stage declares `depends_on` and `input_from` explicitly.
- `input_from` references an initial input as `input:<id>`; upstream data by stage `id`.
- An eval stage cannot be an `input_from` source, and `pipeline.output.from_stage` must
  point to a proc stage.

Save final output names in `pipeline.output.asset_name` and intermediate names in
`authoring.output_names`, and show the actual values in the plan. Do not reuse template
example literals. `--base <short-base>` remains available only for short ancillary
suggestions such as a new delivery directory (default total ≤32); inside that directory
keep pipeline.yaml / pipeline.draft.json / pipeline-preview.md. The helper creates no files.

Explicit valid user names remain unchanged. A new execution from an old template/config
gets fresh suggestions before confirmation, saved without overwriting the old run.
Resume/state reload/check/export retains confirmed names, including legacy timestamps.
Evaluation and verified processing bypass retain the actual input dataset name and
create no data output name. Web proc retry proposes a new grouped task/output name,
editable before confirmation; eval retry changes only the task name. After retry,
downstream handoff and summary use the new submitted config and verified actual artifact
name, not the old plan literal. Generate from pipeline and stage, never by appending a
suffix to an old output name. Do not invent OBS output paths from any generated name.

**Stage ordering**: Verify the input/output contract of every selected operator. Evaluation
can consume compatible original or processed data without a cleaning ancestor. Known
LeRobot operators require a matching format; custom workspace operators use their own
declared input contract. Reports cannot be used as downstream datasets.

### pipeline.yaml → task_config Mapping

| pipeline.yaml | task_config / CLI |
|---------------|-------------------|
| `pipeline.name` + stage/member `id` | `--name` and `name` |
| `pipeline.workspace_id` | `--workspace-id` (default: current workspace); `catalog_id` from `cloudrobo workspace current` |
| `stages[].operator` / `operator_id` | Resolved operator → `algo_id`, `algo_name`, `algo_entrance`, `image` |
| `stages[].operator_source` | `--algo-type` = `task_config.algo_type` (proc only) |
| `stages[].algo_path` / `job_local_path` / `image` / `algo_entrance` | Same-named fields (`operator_source: obs`) |
| `params.envs` (map) | `envs` JSON-array string `[{"key","value","description"}]`; names must exist in `ext_metadata.environment_variables` |
| `params.inputs[]` (`{name, url_path}`) | `inputs` JSON-array string — full current `ext_metadata.inputs[]` element, only `url_path` replaced |
| `pipeline.output.from_stage` | Proc stage whose verified data is delivered |
| `pipeline.output.asset_name` | Selected final proc stage's `output_name` |
| Selected upstream outputs (`input_from`) | Proc: ordered `dataset_configs`; eval: matching top-level fields + one versioned `dataset_configs` entry |

A `params.envs` key or `params.inputs[].name` that the current operator does not declare is
an error — tell the user. There is no `params.checks` / `params.urdf_path`.

### Robot type mapping

`robot_type` is a pipeline label; the `robot` env enum is operator-specific (e.g.
`数据转换--ros转LeRobotV3`: `manifest | galaxea_r1 | galaxea_a1z | jaka | moz1 | azureloong |
ur5e`, read from `environment_variables[].valid_range`). Map `robot_type` to an enumerated
value (e.g. `r1` → `galaxea_r1`) and confirm it in the plan; if there is no match, ask the
user. If the operator declares no `robot` env, do not set one.

**In user-facing strings, show robot models with a Chinese display name alongside the
enum** (e.g. `星海图 R1 (galaxea_r1)` not bare `galaxea_r1`). See the Chinese display-name
table and rule in
[User-Facing Interaction Rules §Terminology](references/user-facing-interaction.md#terminology);
unknown models — confirm a Chinese name with the user or keep the English.

### Custom Operator Stages

A stage selects its operator via `operator_source` (default `preset`). Processing supports
all three sources below; evaluation references preset/workspace algorithm assets:

- **`preset`** → `PRESET_ASSETS`; discover via `list-publication-assets`.
- **`workspace`** → `WORKSPACE_ASSETS`; discover via `cloudrobo asset list-assets
  --catalog-id <id> --type algorithm --tags "Data Processing"` (or `"Data Evaluation"` for
  evaluation operators) `--name "<name>"`; fields same as preset. **A workspace algorithm
  asset in `DRAFT` status is directly usable** as a task input — the platform runs it
  as-is. Never prompt the user to publish a workspace algorithm asset to `RELEASE`; never
  block the pipeline on algorithm publication. Treat `DRAFT` and `RELEASE` identically for
  algorithm assets. The Agent must not call `publish-version` or `update-version --status
  RELEASE` on a workspace algorithm asset unless the user explicitly asks for publication.
- **`obs`** → `OBS_ASSETS`; task_config adds `algo_path` + `job_local_path`, plus
  `algo_entrance`, `image` (user-provided); `algo_id` is optional (valid UUID if provided).

**Recommended source order** — pick the first that fits, and do not present this as a
menu unless the user asks:

1. `preset` — a platform operator already covers the step.
2. `workspace` — the user has an onboarded custom operator for it.
3. `obs` / onboarding a new operator — only when 1 and 2 do not cover it.

For a brand-new operator, prefer onboarding it as a **workspace algorithm** (via the
dataset skill) rather than raw `obs`: it is reusable, appears in later `list-assets`
queries, and needs no per-task code paths. Choose `obs` only when the user explicitly wants
to mount code without registering an asset.

Custom operators consume their `input_from` sources as ordered `dataset_configs` entries, produce `target_path` /
`target_asset_id` for the next stage, and may declare `ext_metadata.inputs` (same `inputs`
logic). YAML example and source resolution table: "Template C2: Custom Operator Insertion"
in [Pipeline Templates](references/pipeline-templates.md).

**Built-in vs Custom**:
- **Built-in**: 仿真/遥操VLA模型数据处理管线 (`templates/sim-teleop-cleaning.yaml`); user triggers verbally, no YAML
  needed; user can override template fields
- **Custom**: User supplies YAML or the guided flow generates it from their requirements;
  no `type` field. Resource preferences and partial-input handoff remain in the companion
  draft JSON, then feed the confirmed execution plan.

See [Pipeline Templates](references/pipeline-templates.md) for YAML structure, field
definitions, and examples.

---

## CLI Command Format Standard

```bash
cloudrobo <service> <command> [OPTIONS]
cloudrobo dataset proc|eval <command> [OPTIONS]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service / command group | `workspace`, `asset`, `dataset proc` (数据处理任务), `dataset eval` (数据评测任务) | `cloudrobo dataset proc` |
| Subcommand | kebab-case | `list-publication-assets`, `create-task`, `wait-task`, `show-task` |
| Workspace override | `--workspace-id <id>` | `cloudrobo workspace use --workspace-id <id>` |
| JSON parameter | `--task-config '<json>'`, `--ext-metadata '<json>'` | `--ext-metadata '{"annotation_status":true}'` |
| JSON-string fields | `envs`, `inputs`, `dataset_configs` are JSON-array **strings** inside task_config | `"envs": "[{\"key\":\"robot\",\"value\":\"galaxea_r1\"}]"` |
| Boolean flag | `--is-system true` | `--is-system false` |
| Dry-run | `--dry-run` (asset create-asset / create-version / import-asset / update-version, dataset proc/eval create-task; echoes arguments only, no validation) | Preview without executing |
| Output format | JSON to stdout (except `wait-task`, which prints status lines) | — |
| Object storage | `obs://` paths only | `obs://bucket/raw/` |

> **⚠️ Do NOT pipe CLI output into an inline `python -c "json.load(sys.stdin)"` to read a field.**
> Commands such as `cloudrobo asset update-version` / `create-asset` may print a non-JSON
> line (e.g. an `错误:` message) to **stdout** on failure; `json.load` then raises
> `JSONDecodeError` and hides the real error. This produces misleading "shell command
> failed" noise and makes the Agent misdiagnose the cause. Correct pattern:
> 1. Run the command raw (or with `2>&1 | head -40`) and read the actual output first.
> 2. Only parse JSON when the output is known to be JSON — and capture stderr separately.
> 3. On a non-zero exit or an `错误:`/`error` line, treat it as a command failure and show
>    the original text; never swallow it with a parser.

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Use `py -3` (or `python`) instead of `python3` when that is the installed launcher.
> - Windows PowerShell 5.1 can strip nested JSON quotes when calling native programs.
>   The Web "copy CLI" action generates a PowerShell/Python JSON-argv bridge on Windows.
>   Prefer JSON files for the local authoring/state scripts; they accept UTF-8 with or without BOM.
> - Native Windows demo, background/stop and test commands are in [Web Monitor](references/web-monitor.md#windows-powershell).

---

## Core Commands

| Purpose | Command |
|---------|---------|
| Workspace + catalog_id | `cloudrobo workspace current` / `cloudrobo workspace use --workspace-id <id>` |
| Register dataset (local) | `cloudrobo asset import-asset --catalog-id <id> --type dataset --name <n> --local-path <dir> --ext-metadata '{"annotation_status":true}'` |
| Register dataset (obs) | `cloudrobo asset create-asset --catalog-id <id> --type dataset --name <n> --ext-metadata '{"annotation_status":true}'` + `cloudrobo asset create-version --asset-id <id> --url <obs_path>` |
| Find registered dataset | `cloudrobo asset list-assets --catalog-id <id> --type dataset --name <n>` |
| Latest version / version detail | `cloudrobo asset list-versions --asset-id <id> --sort-key created_at --sort-dir desc --limit 1` / `cloudrobo asset show-version --asset-id <id> --version-id <vid>` |
| Discover proc operators | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name <fragment>` |
| Discover eval operators | `cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name <fragment>` |
| Submit proc task (convert/clean) | `cloudrobo dataset proc create-task --name <n> --algo-type <PRESET_ASSETS\|WORKSPACE_ASSETS\|OBS_ASSETS> --task-config '<json>'` |
| Submit eval task (quality/diversity) | `cloudrobo dataset eval create-task --name <n> --task-config '<json>'` |
| Wait to terminal | `cloudrobo dataset proc wait-task --task-id <id> --timeout 300 --interval 15` / `cloudrobo dataset eval wait-task --task-id <id> --timeout 300 --interval 15` |
| Extract output | `cloudrobo dataset proc show-task --task-id <id>` (target_path/target_asset_id), `cloudrobo dataset eval show-task --task-id <id>` (target_report_path) |
| Get report | `cloudrobo dataset eval get-preview --task-id <id> --file-name <target_report_path-without-obs://bucket/-prefix>` |
| Diagnose | `cloudrobo dataset proc\|eval get-log --task-id <id> --is-system true\|false`, then `--file-name <n> --file-path <p>` |
| Retry | `cloudrobo dataset proc\|eval create-task` (new task, after confirmation) |

---

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `workspace_id` | No | Workspace ID (defaults to current CLI workspace) | Set via `cloudrobo workspace use --workspace-id <id>` |
| `source_type` | Yes | Input data source type | `local` / `asset` / `obs` |
| `obs_path` | Conditional | OBS path (when `source_type=obs`) | `obs://bucket/raw/episode-xxx/` |
| `local_path` | Conditional | Local directory (when `source_type=local`) | `/data/sim-raw/` |
| `asset_id` / `version_id` | Conditional | Registered dataset (when `source_type=asset`) | UUIDs |
| `data_source_type` | No | Input data format label (h5/ros2/umi) — not used for auto-selection; use `operator`/`operator_id` explicitly | `h5` / `ros2` / `umi` |
| `operator` / `operator_id` | Yes (per stage/member) | Exact Chinese operator name or exact asset_id | `数据清洗` |
| `robot_type` | No | Robot type; mapped to the operator's `robot` env enum (if declared) or ask | `a2d` / `r1` |
| `params.inputs` (eval) | Optional | Config mounts such as the robot description directory, only when the operator declares the input; `robot_config` is removed | `[{name: ROBOT_CONFIG_PATH, url_path: obs://bucket/config/robot-desc/}]` |
| `pipeline.output.asset_name` | For a data output | Selected final proc task's `output_name` | `processed-data` |
| `pipeline.output.from_stage` | When data source is ambiguous | Final proc output to deliver; unique terminal proc inferred | `custom-filter` |
| `resource_pool_type` | Yes | `PUBLIC_POOL` (default) / `DEDICATED_POOL` (+ `resource_id`, `dedicated_pool_name`) | `PUBLIC_POOL` |
| `worker_spec` | Yes | Flavor per task (templates default 4c8g; 2c4g if `POD_PENDING` on public pool) | `{cpu: 4, memory: 8, gpu: 0, npu: 0}` |
| `fail_fast` | No | Stage-level; whether a failure stops the pipeline (default `true`; evaluation `false`) | `false` |

---

## Configuration Priority

- **envs**: pipeline.yaml stage `params.envs` > operator `ext_metadata.environment_variables[].default`
- **inputs**: user `inputs[].url_path` > operator built-in `url_path` > dataset directory
  config (config.yaml / manifest.yaml) > `robot` env default

This order applies only when supported by the current operator. A valid built-in robot or
default configuration does not require adding a YAML file or external mount.

See [Task Config Reference](references/task-config-catalog.md) for details.

---

## Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md) — CloudRobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege IAM policies for CloudRobo
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagrams for the pipeline
- [Pipeline Templates](references/pipeline-templates.md) — Built-in pipeline template, custom pipeline examples, pipeline state tracking
- [User Guide](references/user-guide.md) — Complete user-facing workflow, features, examples and troubleshooting
- [User-Facing Interaction Rules](references/user-facing-interaction.md) — What the user sees: 8-line plan, one confirmation round, one-line progress, one-page result, terminology translation, authorization boundary
- [Guided Custom Pipeline Authoring](references/custom-pipeline-authoring.md) — Natural-language interview, local YAML generation, revision and execution handoff
- [Task Config Reference](references/task-config-catalog.md) — Operator field mapping + per-stage task_config construction
- [Pipeline Summary Template](references/pipeline-summary-template.md) — Final pipeline summary output template
- [Verification Method](references/verification-method.md) — Verification methods and CLI command reference
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria for pipeline execution
- [Fault Recovery](references/fault-recovery.md) — Fault recovery for conversion, cleaning, and evaluation, plus the cross-cutting Edge Cases table
- [Stage Execution Detail](references/stage-execution.md) — Per-stage task_config construction, submission, wait and report fetching (read on demand)

---

## Verification Method

### Specification Compliance Verification

```bash
bash scripts/test-cli-commands.sh -s . -e cli   # read-only smoke tests
```

### Test Cases

See `templates/test-vars.json` for the test case list.

### Verification Checklist

- Pipeline parsing: declared DAG valid, compatible operator handoffs, no cycles
- Plan confirmed by the user before any mutating operation
- Dynamic operator discovery: exact Chinese names / `operator_id`, no hardcoded IDs, fresh
  query before each submission; missing operator → stopped and reported
- Artifact passing: `target_path` / `target_asset_id` / `target_version_id` feed the next
  proc stage's `dataset_configs` in `input_from` order; eval stages use one source as top-level fields plus a single-item versioned `dataset_configs`
- Stage terminal states reached via `wait-task`; eval reports fetched per member with
  `get-preview --task-id`
- Final data comes from `pipeline.output.from_stage`; eval-only output consists of
  reports and the preserved input. Report actual readiness and coverage without assuming 训练就绪数据

See [Verification Method](references/verification-method.md) and
[Acceptance Criteria](references/acceptance-criteria.md) for detailed checklists.
