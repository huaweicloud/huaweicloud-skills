---
name: huawei-cloud-cloudrobo-data-pipeline
description: >
  Guide users to create or revise custom CloudRobo pipelines from natural-language
  requirements, generating validated pipeline.yaml drafts without requiring hand-written
  YAML. Compose workflows from selected preset and workspace algorithm assets, with
  optional OBS processing operators. Offer sim/teleop conversion → cleaning → evaluation
  as an explicitly selected template, with dynamic operator discovery, CLI-only
  Agent task submission, artifact handoff and local Web monitoring via a Python SDK backend.
  Triggers include: 创建自定义管线, 引导配置管线, 帮我设计管线, 生成pipeline.yaml,
  修改管线步骤, custom pipeline builder, 仿真数据处理, 遥操数据清洗, 数据管线,
  数据转换, 数据清洗, 数据评测, TrainingReady, sim-teleop-cleaning, data pipeline,
  打开管线监控, 打开监控网站, pipeline monitor, web monitor.
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
[User Guide 用户指南](references/user-guide.md).

> Compose and run the user's selected operator workflow. The sim/teleop processing chain
> is an optional template. **Agent orchestration uses CLI commands. The optional Web backend uses the
> Python SDK for platform queries and confirmed within-step task creation; the browser calls local HTTP APIs.**

For “把本地数据提交数据管线” and other execution requests, keep input preparation inside
this run: confirm the full plan → `init` using the **original** local/OBS/asset source →
offer/open this run's monitor → prepare inputs with Asset Center → `record-inputs` → submit
ready tasks. Reading the asset skill early does not authorize importing before these steps.
Uploading creates an input asset; it does not turn this run's original `source_type: local`
into `asset`, or make its upload step skipped. Only assets already supplied for reuse at
the start of this run qualify for that not-applicable state.

---

## Overview 概述

### Pipeline Stages

Clarify input and goal → select operators and dependencies → validate compatible data
handoffs → review/export → confirm execution → prepare input as needed → run the declared
workflow → verify the selected data output and reports.

Only the built-in sim/teleop template uses Stage 0→5 below: parse → upload/register →
convert → clean → evaluate → output. Custom workflows may consist entirely of preset
operators, workspace algorithms, or a mixture; conversion, cleaning and evaluation are
chosen according to the user's goal and the actual operator contracts.

### Execution Modes

| Mode | User Intent Example | Stages |
|------|-------------------|--------|
| **Built-in pipeline** | "用遥操/仿真数据处理模板" (sim/teleop data processing template) | Stage 0→5 (load `sim-teleop-cleaning.yaml` template) |
| **Guided custom creation / revision** | "引导我创建自定义管线" / "清洗后加一步，不执行" | Collect choices → validate → export YAML + editable draft + preview; execute only if requested |
| **Custom pipeline** | User provides `pipeline.yaml` | Parse and execute its declared operator DAG |
| **Reuse existing data** | "我已有处理后的数据，接两个空间算法" | Verify the input, then execute only the selected steps |
| **Open monitoring** | "打开监控网站" / "查看当前管线监控" | Open the existing real run or persisted run list directly; no pipeline creation or demo-mode interview |

### Data Upload Routing 数据上传先用资产中心

For local data upload/import within a pipeline, locate and read
`huawei-cloud-cloudrobo-asset` (Asset Center), especially **Scenario 1: Import Local Asset**
and **Import asset**. Resolve the installed skill by name; in this repository its sibling
entrypoint is `../huawei-cloud-cloudrobo-asset/SKILL.md`. Follow its workflow using
**`cloudrobo asset` CLI commands**, preserving this pipeline's confirmed workspace/catalog,
input directory, dataset metadata and naming choices. A request only to upload/import an
asset belongs to that skill and does not require creating a pipeline.

- Local directory: `cloudrobo asset import-asset --local-path ...` performs asset/version
  creation and OBS upload together. Do not first search for generic OBS skills, obsutil,
  `aws s3`, raw storage APIs or custom upload scripts, then register the same data again.
- Existing `obs://` source: use the asset registration flow; do not upload again or pass
  an OBS URL as `--local-path`. Existing asset/version: verify and reuse it.
- Read-only metadata checks may precede confirmation, but import/upload starts only after
  the execution plan is confirmed and the monitor-opening offer has been made.
  Reuse that authorization for unchanged import scope; do not ask for the same approval
  again merely because the asset skill was loaded.
- After import, record actual asset/version IDs, use `show-version` to verify its URL and
  readiness, then use `record-inputs` on the **same run initialized before import**.
  Keep its original `source_type` and `local_path`/`obs_path`; add registration metadata,
  rather than rebuilding the plan as an existing-asset run. A returned ID alone
  does not prove the files finished uploading. On partial failure, use the asset skill's
  supported recovery with the verified IDs and original confirmed input; do not blindly
  create another asset/version, delete an incomplete version or publish RELEASE.

The asset skill's README frontmatter may override CLI metadata; inspect applicable
metadata before confirmation and resolve conflicts with the plan, rather than silently
changing the target or modifying the user's source files. If the companion skill is not
installed in a standalone environment, keep using the same asset CLI workflow documented
below and report that limitation; a separate OBS tool is not a prerequisite.

> **Ordering comes from operator contracts:** validate each upstream format and output
> against its consumer. LeRobot evaluation requires compatible data, not a mandatory
> cleaning ancestor. Do not insert conversion or cleaning merely to match the template.

### Skip-Stage Input Requirements

The following table describes resuming the built-in template. For an arbitrary workflow,
verify the first selected operator's input requirements instead. Existing processed data
can be supplied as an asset, OBS directory or local directory; only perform the upload or
registration required by that source, without adding template processing stages.

| Start Stage | User Must Provide | Prompt |
|-------------|-------------------|--------|
| Stage 3 (cleaning) | Conversion output: `target_path`, `target_asset_id`, `target_version_id`, asset name | "Please provide the converted LeRobotV3 dataset's OBS path, asset_id and version_id" |
| Stage 4 (evaluation) | Cleaning output: `target_path`, `target_asset_id`, `target_version_id`, asset name; optional config mount (e.g. robot description) if the operator declares it and the selected metrics need it | "Please provide the cleaned dataset's OBS path, asset_id and version_id; provide a config OBS directory only when the selected metrics need it" |

If a required handoff value is missing, ask the user. A missing version or asset name can be resolved with
`cloudrobo asset list-versions --asset-id <id> --sort-key created_at --sort-dir desc --limit 1`
and `cloudrobo asset show-asset --asset-id <id>`; confirm the result with the user.

### Data Flow Contract

These numbered handoffs describe the built-in template. For custom workflows, pass each
declared proc input as an ordered `dataset_configs` entry, each eval input as matching top-level dataset fields plus one `dataset_configs` entry, and
take final data from `pipeline.output.from_stage`, rather than a fixed cleaning stage.
Recommend a single dataset per branch for ease of use; this is not a proc restriction.
A merge-capable proc operator may consume A and B's datasets and produce one dataset.
Use ordered `input_from` for data sources and `depends_on` for waiting gates. Evaluation
still accepts one dataset; merge first if evaluation needs the combined result. Verify
multi-input count, order, formats and single-dataset output against the actual operator.

| From → To | Handoff Values |
|-----------|----------------|
| Stage 0 → 1 | `source_type`, `obs_path` / `local_path` / `asset_id`+`version_id`, `data_source_type`, `robot_type` |
| Stage 1 → 2 | `dataset_asset_id`, `dataset_version_id`, dataset name, dataset OBS path (from `show-version`) |
| Stage 2 → 3 | Conversion `target_path`, `target_asset_id`, `target_version_id`, `<conversion output_name>` → cleaning `dataset_configs` |
| Stage 3 → 4 | Cleaning `target_path`, `target_asset_id`, `target_version_id`, `<cleaning output_name>` → eval top-level fields + single-item `dataset_configs` with `version_id`; optional `inputs` config mounts |
| Stage 4 → 5 | Per-member eval `task_id` / `status` / `target_report_path` and report links; TrainingReady path = cleaning `target_path` |

---

## Prerequisites 前置条件

Local authoring requires only Python 3.9+; no cloud authentication or available operator
is needed to save a clearly marked draft. The following prerequisites apply when resolving
real platform metadata or executing the pipeline, not when merely creating local files.

1. **cloudrobo CLI** installed + authenticated via `cloudrobo config set ak <ak> sk <sk>` or
   `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` — see
   [CLI Installation Guide](references/cli-installation-guide.md)
2. **workspace_id** set via `cloudrobo workspace use --workspace-id <id>` (or pass
   `--workspace-id` to `create-task`)
3. Raw data available: local directory, registered asset, or OBS path
4. Resource pool with available quota for data processing tasks (see Resource spec in
   Step 2.3)
5. The required operators are published in the current region/marketplace (checked at
   discovery time; see Step 2.1)
6. IAM permissions for asset, dataset proc/eval and OBS operations — see
   [IAM Policies](references/iam-policies.md)

### Execution Environment Preflight 执行环境预检

Before the first local script, identify the actual shell (Git Bash, PowerShell, or other),
select an available Python interpreter and verify it really runs Python 3.9+. Accept
Miniconda's `python`; do not assume `python3` or `py -3` exists. Reuse the verified
interpreter for subsequent scripts. Examples below use `python3` as notation; adapt the
launcher and shell syntax before executing. Git Bash paths use quoted forward slashes,
e.g. `cd 'C:/Users/name/My Project/skill'`. Detailed shell examples and checks are in the
[CLI Installation Guide](references/cli-installation-guide.md#environment-preflight).

Before resolving a real execution plan, run `cloudrobo config get region`; this reads
local configuration, not live regional proof. Cross-check the intended region against
available workspace/endpoint information, including explicit intranet endpoint overrides.
If the command is unavailable, the value is missing, or sources conflict, ask the user
before real execution; never infer the task region from an SWR image URL or silently
change configuration. Note the region source in the plan explanation. A local draft may
leave the region unresolved; opening existing monitoring does not require this cloud preflight.

---

## Workflow 工作流

### Open Monitoring Only 仅打开监控

For “打开监控网站”, “打开管线监控” or equivalent requests, go directly to
[Local Web Monitoring](#local-web-monitoring-本地-web-监控) and the default-opening rules
in [Web Monitor](references/web-monitor.md). This request authorizes starting/reusing the
local service and opening the browser; do not first ask whether to use demo or real mode.

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

### Requested Processing Skip 保留原输入跳过

The Web offers “跳过…” for an unsubmitted single-input proc stage. It records an
`awaiting_decision.kind: skip` request; it does not immediately mark the stage skipped
or submit downstream tasks. Existing advisory evaluation skip remains a direct action.

**Agent responsibility boundary**: on a skip request the Agent only performs **technical compatibility verification** — check that the stage's original input (asset/version/path) is compatible with the current CLI input contract of every direct downstream operator. The Agent **must not** reject a skip for business reasons such as "user goal", "TrainingReady requires it" or "business need"; the user's explicit skip in the Web UI takes precedence over the Agent's business inference. Verification is limited to "can downstream consume this input" and excludes judgments such as "is this data suitable for training".

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

#### Guided Custom Pipeline Creation 引导创建自定义管线

When the user wants to create/design/configure a pipeline without YAML, or revise an
existing pipeline, read [Guided Custom Pipeline Authoring](references/custom-pipeline-authoring.md).
Reuse information already given; guide missing choices from data stage/source and desired
output through steps/operators, optional params, resources and failure policy. Do not ask
the user to write YAML or silently choose the full built-in template.

If the user only says “创建管线” or “引导我”, start with “希望处理什么数据、得到什么结果？
如果已有想用的算子，请告诉我名称和顺序。” Do not prefill stages, data formats, robot type,
quality/diversity evaluation, or output names. Discover candidate preset/workspace
operators for the stated goal; a custom workflow does not require custom operator code.

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

Only an explicit request to use the built-in sim/teleop template loads
`templates/sim-teleop-cleaning.yaml`. A general request about sim/teleop data is handled
by guided creation unless the user selects this template.
Confirm with user: display parsed stages; ask input data source (local/asset/obs),
`robot_type` if not specified, the resource pool, and the TrainingReady output name; allow
field overrides. `data_source_type` (h5/ros2/umi) is an input format label — the operator
is explicitly specified in pipeline.yaml.

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

Use one task graph and one ready queue for every workflow. The local adapter expands old
`parallel_group` members into task nodes, inherits group defaults and expands group waiting
edges to all members; saved YAML and Web grouping remain compatible. Neither the Agent nor
the user selects a separate scheduler for grouped versus ungrouped tasks.
After registration, task submission or result update, call `pipeline_state.py --run <run_id>
ready-tasks`. `action=submit` means submit the returned ready nodes before polling any active
task; after each submission resolve and re-query, since the queue is a snapshot, not a reservation.
`action=reconcile` requires resolving the existing transaction first. `action=poll` means no
ready task remains and active tasks need short CLI status rounds. `decide`/`blocked` require
the relevant decision, input or manual check; `readonly`/`stopped` do not authorize submission.
Readiness is a local dependency check, not operator/input validation or execution approval.
For each create, finish `reserve A → create A (without --wait) → verify returned task ID
with show-task → resolve A`, then immediately do the same for ready B. Resolve records
the task ID while it is pending/running; do not wait for execution success to release
the submission transaction. An uncertain create still requires reconciliation first.
This is non-blocking sequential dispatch: the single pending-action protocol prevents
concurrent create transactions but never holds the slot for the cloud task's runtime.

**Full CLI chain: reserve-task → create-task → verify → resolve-action**:

```bash
# 1. Prepare the task_config JSON file (all required fields; dataset_configs/envs/inputs are JSON strings)
#    See the full example in Step 2.3

# 2. reserve-task: reserve the submit transaction (--expect-task none = first submit, no existing task_id)
python scripts/pipeline_state.py --run <run_id> reserve-task \
  --stage convert --expect-task none \
  --name "<pipeline>-convert-<MMDDHHmmss>" \
  --config "<task_config.json>"
# Returns pending_action.id and the new state version

# 3. create-task: submit the real task (without --wait)
cloudrobo dataset proc create-task \
  --name "<pipeline>-convert-<MMDDHHmmss>" \
  --algo-type PRESET_ASSETS \
  --task-config "$(cat <task_config.json>)"
# Returns task_id and status=PENDING
# Note: on 400 "name already in use", verify with list-tasks --name <name> whether the task was created

# 4. verify: confirm the returned task_id with show-task
cloudrobo dataset proc show-task --task-id <task_id>

# 5. resolve-action: record the task_id and release the submit transaction
python scripts/pipeline_state.py --run <run_id> resolve-action \
  --action-id <pending_action.id> --task-id <verified_task_id>
# Returns stage.status=PENDING, stage.task_id=<task_id>

# 6. wait-task: poll to a terminal state
cloudrobo dataset proc wait-task --task-id <task_id> --timeout 300 --interval 15

# 7. set-result: record the result (JSON file with status/output_name/target_path/target_asset_id/target_version_id)
python scripts/pipeline_state.py --run <run_id> set-result \
  --stage convert --expect-task <task_id> \
  --result "<result.json>"
```

When the user requests parallel A/B from the same registered dataset, bind both with
`input_from: ["input:default"]` (or the chosen initial ID); do not omit B's binding and
accidentally inherit A as its dependency. Distinct branches may instead select distinct
initial datasets. A downstream merge explicitly waits for both A/B outputs.

Only wait when no currently ready task remains unsubmitted. With independent branches
in flight, query all active task IDs in a short CLI show-task round (about every 15 s),
record changed results/heartbeats and re-evaluate ready steps each round. Avoid a
300-second single-task wait that delays another newly ready branch. The concrete
Stage 2/3 wait examples below describe the sequential template path; apply this frontier
rule to custom DAGs. Cloud resource shortages may still queue an already submitted B;
report its task ID/status separately from an Agent-delayed submission.

#### Execution Plan Confirmation (Mandatory)

Before **any** mutating operation (`create-asset` / `create-version` / `import-asset` /
`update-version` / `create-task`), resolve the operators (Steps 2.1, 3.1, 4.1) and show the
user the full plan:

- Input source and the assets/versions that will be created or published
- Per stage: resolved operator (name / asset_id / image), `--algo-type`, `envs` values
  (including defaults that will be used), `inputs` mounts (config files such as the eval
  robot description are passed only this way)
- Resource pool type (and `resource_id` / `dedicated_pool_name` for `DEDICATED_POOL`),
  `worker_spec` / `head_spec` / `worker_num`
- Task names, output names (each proc step and the selected `pipeline.output.from_stage`) and
  output paths

Proceed only after explicit user confirmation. Re-confirm if any value changes later
(e.g. a smaller flavor after `POD_PENDING`, or a new task after `FAILED`).

After confirmation, save the instantiated plan as JSON and initialize schema v2 with
`python3 scripts/pipeline_state.py --run <run_id> init --plan <resolved-plan.json>`.
Use the input source supplied for this run, even when registration IDs become available
later. For a local directory, preserve `source_type: local` and `local_path`; IDs need not
exist at init. Do not import first to fill those IDs, reclassify the result as an existing
asset, or create a second run when moving from input preparation to conversion.
Immediately offer once to open this run's monitor, **before starting Stage 1 input
upload/registration, version publication or any task submission**. Do not wait for asset
registration or format conversion. This applies equally to local, OBS and existing-asset
inputs, including evaluation-only workflows. See [Web Monitor](references/web-monitor.md).
Say “执行计划已确认，运行记录已创建，准备执行。是否打开本次运行监控？终端会继续跟踪。”
Local init does not establish successful cloud submission; the page can already show the
confirmed plan and pending/not-applicable input preparation without a task ID.
If the user already requested monitoring, open it now without asking again. Otherwise
offer “打开本次运行监控 / 仅终端跟踪”; do not ask demo vs real mode. When opening is
accepted, start/reuse the service and open this run before proceeding to Stage 1. Keep terminal
orchestration moving while awaiting this optional preference; do not set await-decision
or pause the pipeline for it. No response means no browser launch, not execution failure.
Do not repeat the offer on retries, wait segments or checkpoint recovery.

### Stage 1: Data Upload & Registration

Use [Data Upload Routing](#data-upload-routing-数据上传先用资产中心): read the Asset Center
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
its completed upload/registration is **SUCCEEDED / 已登记**, never skipped.
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
cloudrobo asset import-asset --catalog-id <catalog_id> --type dataset --name "<dataset_name>" --local-path "<local_dir_path>" --ext-metadata '{"annotation_status":true}'
cloudrobo asset show-version --asset-id <asset_id> --version-id <version_id>
```

**Version handoff — do not publish by default**: read the exact version with `show-version`
and verify its path and status. A verified `DRAFT` input can be consumed by supported
platform/operator combinations; do not ask to publish merely because it is not `RELEASE`.
If the platform/operator explicitly requires `RELEASE`, or a downstream failure is verified
to be caused by that release requirement, ask for confirmation before publishing. Other
failures (path, permission, format, unfinished upload) are not reasons to publish.
Versions such as `CREATING` or unknown states still need readiness checks.

Only for an established release requirement and confirmed publication:

```bash
cloudrobo asset update-version --asset-id <asset_id> --version-id <version_id> --status RELEASE
```

The dataset OBS path passed to Stage 2 is the version `url` from `show-version` — do not
concatenate paths manually.
Persist every verified initial dataset (asset ID, exact version, actual name and version
URL) with `pipeline_state.py --run <run_id> record-inputs --inputs-file <resolved-inputs.json>
--expect-version <current_state_version>` before downstream submission; see
[input registration](references/web-monitor.md#record-inputs). It completes the upload
bookmark only after all inputs have registration metadata. Do not write only
`{"status":"SUCCEEDED"}` for upload, leave verified IDs only in conversation/task configs,
or flatten multiple datasets into upload's single target fields.

### Stage 2: Format Conversion (Built-in Template Reference)

Stages 2–4 below document the optional sim/teleop template's concrete operators and CLI
examples. Custom workflows use their declared operators and dependencies; these numbered
steps are not mandatory stages and must not be inserted automatically.

Convert raw data to LeRobotV3 format. The conversion operator is specified explicitly
via `operator` (exact Chinese name) or `operator_id` (asset_id) in pipeline.yaml —
`data_source_type` (h5/ros2/umi) is the input data format label, not an auto-selection
mechanism.

#### Step 2.1: Discover Conversion Operator

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
> region/marketplace, stop and tell the user. Never silently substitute another operator;
> continue only if the user explicitly changes the stage `operator` / `operator_id`.

> **Dynamic discovery — query fresh every time**: never hardcode asset IDs and **never
> reuse operator info (image/algo_id/command/inputs) from a previous run** — the platform
> updates assets (new image versions, fixed commands) and a stale image can silently fail.
> Re-run `list-publication-assets` before every submission and use the **current** result;
> confirm unique match, else ask user.

#### Step 2.2: Extract Operator Metadata

From the `list-publication-assets` result, extract fields per the mapping in
[Task Config Reference](references/task-config-catalog.md):

| Operator Asset Field | task_config Field |
|---------------------|-------------------|
| `asset_id` | `algo_id` |
| `name` | `algo_name` |
| `ext_metadata.command` | `algo_entrance` |
| `ext_metadata.engine.image_url` | `image` |
| `ext_metadata.environment_variables` | `envs` (if present) |
| `ext_metadata.inputs` | `inputs` (optional mounts, see below) |

There is no `ext_metadata.hyperparams` and no task_config `params` field — operator
behaviour is tuned only through `envs` and `inputs`. Read env names, valid values and
defaults from `ext_metadata.environment_variables`, show them to the user, and build the
`envs` JSON-array string (`[{"key":...,"value":...,"description":...}]`).

#### Step 2.2b: Resolve Operator Input Mounts

Read `ext_metadata.inputs` from the discovered operator (it may be absent or `null` — then
omit `inputs`) and decide which (if any) to mount: `required: true` must be provided
(built-in `url_path` needs no action); `required: false` is optional — **do not prompt by
default**, ask only for custom config or when the operator would otherwise fail.

> **`inputs` format**: `inputs` is a JSON-array **string** field (like `dataset_configs` /
> `envs`). Each element is the operator's `ext_metadata.inputs[]` element **copied as
> returned by the current query** (do not add or strip fields), with only `url_path` set to
> the user-selected `obs://` path. Never use `obs_path` as an inputs key. Input names
> (`DATA_CONFIG_PATH`, `CURATION_CONFIG_PATH`, `ROBOT_CONFIG_PATH`, etc.) are **dynamic** —
> read them from `ext_metadata.inputs` at discovery time, never hardcode. Example:

```text
"inputs": "[{\"name\":\"<input-name-from-ext_metadata>\",\"label\":\"<as returned>\",\"required\":false,\"url_path\":\"obs://bucket/config/\",\"input_type\":\"<as returned>\",\"description\":\"<as returned>\",\"access_method\":\"env\"}]"
```

Known operator inputs (reference — always re-read the current `ext_metadata.inputs`; see
[Task Config Reference](references/task-config-catalog.md)): conversion/cleaning may have
optional config mounts; evaluation may have an optional robot description mount;
desensitization has a required built-in model mount.

Input datasets do not universally require YAML files. Use the selected operator's built-in
`robot` environment/default configuration, existing dataset config, or optional external
config mount as appropriate. Only when a YAML config file is actually needed, apply the
[manifest candidate rules](references/task-config-catalog.md#manifest-config-names);
manifest mode alone does not require an external file or an evaluation config mount.

#### Step 2.3: Construct task_config and Submit

```bash
cloudrobo dataset proc create-task --name "<pipeline_name>-<stage_id>-<MMDDHHmmss>" --algo-type <PRESET_ASSETS|WORKSPACE_ASSETS|OBS_ASSETS> --task-config '<json>'
```

`--algo-type` comes from the stage `operator_source` (`preset` → `PRESET_ASSETS`,
`workspace` → `WORKSPACE_ASSETS`, `obs` → `OBS_ASSETS`) and overrides
`task_config.algo_type`, so keep both identical. Submit **without** `--wait`, record the
`task_id`, then wait in Step 2.4.

**Resource spec** (follows the dataset skill's task-config guidance): `resource_pool_type`
is `PUBLIC_POOL` (default) or `DEDICATED_POOL` — ask the user in Stage 0; for
`DEDICATED_POOL` also set `resource_id` and `dedicated_pool_name`. The templates use
**4c8g** (`worker_spec: {cpu: 4, memory: 8, gpu: 0, npu: 0}`) as the default `worker_spec`;
for CCE/K8S `head_spec` is `{cpu: 0, memory: 0, gpu: 0, npu: 0}` and `worker_num` is `1`.

**Public pool note**: on the public pool, a 4c8g pod can stay in `POD_PENDING` under
resource contention. If that happens, choose a smaller flavor such as 2c4g
(`{cpu: 2, memory: 4, gpu: 0, npu: 0}`) or use a dedicated pool, then create a new task
after user confirmation.

**RAY tasks (cluster_type=CCE_RAY / task_framework_type=RAY)**: `head_spec` must be
non-zero; example head **2c4g** (`{cpu: 2, memory: 4, gpu: 0, npu: 0}`), workers **4c8g × 2**
(`worker_spec: {cpu: 4, memory: 8, gpu: 0, npu: 0}`, `worker_num: 2`).

See [Task Config Reference](references/task-config-catalog.md) for the full task_config
template and the CLI-validated required fields.

> **Required proc task_config fields**: CLI validation rejects a task_config with missing fields. Besides
> the example above, a proc task_config must also include the following (a missing or empty value fails
> with a "required field missing or empty" error):
> - `catalog_id` — the workspace's catalog_id (from `cloudrobo workspace current`, **not** the operator's catalog_id)
> - `cluster_type` — `CCE` (standard); `CCE_RAY` for RAY tasks
> - `task_framework_type` — `K8S` (standard); `RAY` for RAY tasks
> - `output_type` — `BUILD_IN_ASSET` (default, platform-managed output) or `UDF_OBS_ASSET` (user-specified OBS output directory)
> - `evs_spec` — `0` (default; only public-pool tasks may set a non-zero EVS)
>
> Full proc task_config example (all required fields):
>
> ```json
> {
>   "name": "<pipeline_name>-convert-<MMDDHHmmss>",
>   "algo_type": "PRESET_ASSETS",
>   "algo_id": "<operator asset_id>",
>   "algo_name": "<operator name>",
>   "algo_entrance": "<operator ext_metadata.command>",
>   "image": "<operator ext_metadata.engine.image_url>",
>   "catalog_id": "<workspace catalog_id>",
>   "resource_pool_type": "PUBLIC_POOL",
>   "cluster_type": "CCE",
>   "task_framework_type": "K8S",
>   "envs": "[{\"key\":\"robot\",\"value\":\"galaxea_r1\"}]",
>   "dataset_configs": "[{\"obs_path\":\"obs://...\",\"dataset_type\":\"BUILD_IN_ASSET\",\"asset_id\":\"<id>\",\"asset_name\":\"<name>\",\"version_id\":\"<vid>\"}]",
>   "output_type": "BUILD_IN_ASSET",
>   "output_name": "<output asset name>",
>   "head_spec": {"cpu": 0, "memory": 0, "gpu": 0, "npu": 0},
>   "worker_spec": {"cpu": 4, "memory": 8, "gpu": 0, "npu": 0},
>   "worker_num": 1,
>   "evs_spec": 0
> }
> ```
>
> **Note**: `envs`, `dataset_configs` and `inputs` are JSON array **strings** (wrapped in double quotes),
> not native JSON objects. When building the task_config JSON file, these fields must be string values.

**Operator inputs**: operators with `ext_metadata.inputs` — add the `inputs` string only
for mounts the user selected (Step 2.2b). Optional inputs are omitted by default.
(`OBS_ASSETS` operators use `algo_path` + `job_local_path` instead — see
[Custom Operator Stages](#custom-operator-stages).)

**Input dataset**: Use the registered asset from Stage 1 — construct `dataset_configs`
with `obs_path` = version `url` from `show-version`, `dataset_type: BUILD_IN_ASSET`,
`asset_id`, `asset_name`, `version_id`.

**Output**: `output_name` = `<conversion output_name>` (confirmed in the plan).

#### Step 2.4: Wait and Extract Output

```bash
cloudrobo dataset proc wait-task --task-id <id> --timeout 300 --interval 15
cloudrobo dataset proc show-task --task-id <id>   # Extract status / target_path / target_asset_id
cloudrobo asset list-versions --asset-id <target_asset_id> --sort-key created_at --sort-dir desc
cloudrobo asset show-version --asset-id <target_asset_id> --version-id <target_version_id>
```

Use the task's returned version when available. Otherwise inspect version candidates
(including further pages as needed) and verify which belongs to this task and output path.
Do not select the newest version by position; ask if the exact version remains ambiguous.

> **`wait-task` output and FAILED prompt**: `wait-task` prints text status lines
> (`START → <status>`, `最终状态: <status>`), not JSON. On `FAILED` it asks interactively
> whether to show logs (`任务失败，是否查看日志？`); with no stdin it prints `Aborted!` and
> exits 1 after `最终状态: FAILED` — that is the task result, not a CLI error. In
> non-interactive runs pipe an answer: `printf 'n\n' | cloudrobo dataset proc|eval wait-task
> ...`. Always read the result with `show-task`, then diagnose with `get-log`.

- `SUCCEEDED` → extract `target_path`, `target_asset_id` and the exact `target_version_id` matching this task output;
  verify the version/path with `show-version`; a verified `DRAFT` may proceed without
  publication. Only an established downstream RELEASE requirement needs publication
  confirmation; pass the verified data to Stage 3
- `wait-task` timed out while the status is still non-terminal → re-run `wait-task` and
  report progress; do **not** resubmit
- `FAILED` / `DELETED` → diagnose with `cloudrobo dataset proc get-log --task-id <id>
  --is-system true|false`, then `--file-name <name> --file-path <path>`; after user
  confirmation create a **new** task. See [Fault Recovery](references/fault-recovery.md)

### Stage 3: Data Cleaning

Run the single `数据清洗` (data cleaning) operator. Its sub-checks (outlier detection,
anomaly detection, state-action consistency, FK correction, base-frame alignment, blur
frame detection) are descriptive only — they are not pipeline.yaml keys. A custom cleaning
config is supplied via the operator's `CURATION_CONFIG_PATH` input when the operator
exposes it.

#### Step 3.1: Discover Cleaning Operator

```bash
cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --name "数据清洗"
```

> **Operator name**: match the exact `数据清洗` name (or `operator_id`) and confirm a unique
> match. If it is not found, apply the "Operator not found → stop" rule from Step 2.1.

#### Step 3.2: Construct task_config and Submit

Same flow as Steps 2.2–2.3, with:
- **Input**: `dataset_configs` built from Stage 2's `target_path` / `target_asset_id` /
  `target_version_id` / `<conversion output_name>`
- **envs**: read `environment_variables` from the operator `ext_metadata` and construct
  `envs` accordingly — variable names, valid values, and defaults are all dynamic (do not
  hardcode), e.g. `mode` (cleaning strategy) and `robot` (robot type) when declared. Map
  `robot_type` to an enumerated `robot` value (see [Robot type mapping](#robot-type-mapping))
- **inputs**: optional `CURATION_CONFIG_PATH` (custom cleaning config) from stage
  `params.inputs`, expanded per Step 2.2b
- **Output**: `output_name` = `pipeline.output.asset_name` (TrainingReady dataset name)
- **Resource**: as in Step 2.3

```bash
cloudrobo dataset proc create-task --name "<pipeline_name>-cleaning-<MMDDHHmmss>" --algo-type <PRESET_ASSETS|WORKSPACE_ASSETS|OBS_ASSETS> --task-config '<json>'
```

#### Step 3.3: Wait and Extract Output

```bash
cloudrobo dataset proc wait-task --task-id <id> --timeout 300 --interval 15
cloudrobo dataset proc show-task --task-id <id>   # Extract status / target_path / target_asset_id
cloudrobo asset list-versions --asset-id <target_asset_id> --sort-key created_at --sort-dir desc
cloudrobo asset show-version --asset-id <target_asset_id> --version-id <target_version_id>
```

- `SUCCEEDED` → extract `target_path`, `target_asset_id`, exact `target_version_id` using the Step 2.4 verification rules, pass to Stage 4
- Timeout / `FAILED` / `DELETED` → same handling as Step 2.4 (see the `wait-task` output and
  FAILED prompt note there)

### Stage 4: Data Evaluation

Run quality evaluation + diversity evaluation in parallel (both depend on cleaning output).

#### Step 4.1: Discover Evaluation Operators

```bash
cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "质量评测"
cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --name "多样性评测"
```

Match the exact names `数据集质量评测-LeRobot` / `数据集多样性评测-LeRobot` (or `operator_id`).
If `--tags` returns nothing, retry with `--sub-type data_evaluating --name "<fragment>"`;
if still not found, apply the "Operator not found → stop" rule.

#### Step 4.2: Construct eval task_config and Submit (Parallel)

Evaluation tasks use `dataset eval create-task` (not `proc create-task`, and there is no
`--algo-type` option). Common eval fields: `name`, `algo_id`, `algo_name`,
`algo_entrance`, `image`, `dataset_type`, `dataset_name`, `dataset_path`,
`resource_pool_type`, `worker_spec`, `dataset_configs` (+ `dataset_id` when `dataset_type=BUILD_IN_ASSET`).
See [Task Config Reference](references/task-config-catalog.md) for the eval template.

**Input**: top-level `dataset_type: BUILD_IN_ASSET`, `dataset_id` = cleaning
`target_asset_id`, `dataset_name` = `<cleaning output_name>`, `dataset_path` = cleaning
`target_path`. Also include a single-item `dataset_configs` JSON-array string containing
that same asset/name/path and its exact `version_id` = cleaning `target_version_id`. Both
eval tasks share the same cleaned input/version. Use the
[version handoff rules](references/task-config-catalog.md#dataset-version-handoff);
read the created task back before relying on Console cloning.

**Config files are mounted from OBS (`inputs`)**: the task_config field `robot_config` has
been removed — never send it. Any configuration directory, including the robot description
(robots.yaml / URDF), is passed only through the operator's declared `ext_metadata.inputs`
(e.g. `ROBOT_CONFIG_PATH`; the name is dynamic) with `url_path` set to the user's `obs://`
directory, written in the pipeline as each eval member's `params.inputs`. Members resolve
their mounts independently; there is no group-level default. When no mount is selected,
omit `inputs` and run with the operator's built-in/default configuration. Manifest mode
does not make a mount mandatory. Explain any robot-dependent metrics that are unavailable
in the report; default-config evaluation must not be described as full robot-dependent
coverage. Show each member's mounts or “未挂载（使用算子内置/默认配置）” in the execution plan.
Do not invent a path or use the dataset path as a substitute.
If the CLI/SDK rejects an eval task because `robot_config` is missing, the installed client
is outdated: upgrade it rather than adding the field. A pipeline YAML that still contains
`robot_config` fails validation; move the directory into that member's `params.inputs`.

**envs**: if the evaluation operator declares `environment_variables` (e.g. a `robot` env),
read valid values and defaults at discovery time (do not hardcode) and map `robot_type` to
an enumerated value. If none are declared, omit `envs`.

**Robot description mount**: if the task fails with
`ValueError: ROBOT_CONFIG environment variable is not set`, check whether the chosen
metrics require robot geometry or whether this operator version fails to run without it.
If the operator declares a matching input (e.g. `ROBOT_CONFIG_PATH`), offer the actual
robots.yaml/URDF OBS directory as that member's mount and confirm the scope change before
a new task. Otherwise report the operator limitation (evaluation is advisory).

> **Do not work around via `algo_entrance`**: copy `ext_metadata.command` unchanged; an
> `export ROBOT_CONFIG=/` prefix in task_config is not the way to change operator
> behaviour — use `envs` / `inputs`. Changes to the command belong in the operator asset
> version's `ext_metadata.command`.

Evaluation remains advisory (`fail_fast: false`) — a failed eval does not block TrainingReady
output.

**Parallel submission**: submit both tasks **without** `--wait`, record both `task_id`s,
then wait for each in Step 4.3. Stage 5 only proceeds when all members reach a terminal
state.
Complete reserve/create/verify-ID/resolve for the first member, then submit the second
immediately; never run wait-task or wait for the first report between these transactions.

```bash
cloudrobo dataset eval create-task --name "<pipeline_name>-quality-eval-<MMDDHHmmss>" --task-config '<json>'
cloudrobo dataset eval create-task --name "<pipeline_name>-diversity-eval-<MMDDHHmmss>" --task-config '<json>'
```

**Resource**: as in Step 2.3 per eval task. Parallel group total = 2 × the selected eval
`worker_spec`.

#### Step 4.3: Wait for Both Tasks to Terminal

```bash
cloudrobo dataset eval wait-task --task-id <quality_task_id> --timeout 300 --interval 15
cloudrobo dataset eval wait-task --task-id <diversity_task_id> --timeout 300 --interval 15
```

`wait-task` prints status lines (not JSON) and prompts on `FAILED` — in non-interactive runs
pipe `printf 'n\n' |` into it (see the note in Step 2.4), then read each result with
`cloudrobo dataset eval show-task --task-id <id>`.

- All `SUCCEEDED` → proceed to Step 4.4
- `wait-task` timed out while non-terminal → re-run `wait-task`, report progress; do not
  resubmit
- Any `FAILED` / `DELETED` → diagnose with `cloudrobo dataset eval get-log --task-id <id>
  --is-system true|false`; evaluation is advisory and does not block TrainingReady output
  (stage `fail_fast: false`). A new eval task is created only after user confirmation

#### Step 4.4: Get Evaluation Reports

Run for **each** eval member (quality and diversity):

```bash
cloudrobo dataset eval show-task --task-id <eval_task_id>   # Extract target_report_path
cloudrobo dataset eval get-preview --task-id <eval_task_id> --file-name <target_report_path-without-obs://bucket/-prefix>
```

`--file-name` is `target_report_path` with the `obs://<bucket>/` prefix removed (e.g.
`obs://bucket-0/cloudrobo/test.pdf` → `cloudrobo/test.pdf`). Add `--is-download` for a
download link instead of a preview link.

For a platform `get-preview` error 500/502/503/504, wait briefly and repeat the same read
once. If it fails again, retain the task ID, report path and error for diagnosis. A preview
read failure does not change the evaluation task result or justify resubmitting the task.
The Web shows a manual retry hint and does not automatically repeat preview requests.

### Stage 5: Output

After the pipeline reaches the end (or stops at a terminal state), output a **full pipeline
summary** to the user. The summary must cover:

1. **Pipeline run overview** — pipeline name, mode (built-in/custom), workspace_id, run
   window (start/end time), and a per-stage status table (✅ SUCCEEDED / ⚠️ PARTIAL / ❌ FAILED)
2. **Data situation** — input source (type, format, robot type, path), intermediate
   artifacts (each stage's `target_path` / `target_asset_id` / asset name), and the final
   selected final data path (or the preserved input and reports for eval-only workflows)
3. **Resource usage** — per-stage `worker_spec` and resource pool type
4. **Issues & recommendations** — failed stages, error messages, root-cause analysis,
   and actionable next steps for the user
5. **Evaluation reports** — per member status, `target_report_path` and `get-preview`
   link (temporary; save promptly)
6. **Reproducibility** — all task IDs (for tracing/retry) and the instantiated
   pipeline.yaml, plus the verified region and its source (CLI configuration / user confirmation)
7. **Version publication** — query the recorded asset/version IDs for intermediate and final
   data outputs with `show-version`, list each status, and give one consolidated publication
   reminder at completion. Ask once whether any listed versions should be published if not
   already decided; honor prior choices. Declining publication does not block `finish` or
   turn a successful run into a warning. Never put the asset's `DRAFT` status into the task
   `status` field; version status belongs in the Agent summary, not a new set-result field.

> **Output follows the selected workflow:** read `target_path` and asset/version from
> `pipeline.output.from_stage`, not from a stage named cleaning. Report processing and
> evaluation coverage honestly. TrainingReady is a use-specific conclusion after verifying
> the relevant data requirements; custom processing alone does not establish it.

> **Failed-stage honesty**: Report FAILED stages with the error message from the `show-task`
> detail and the system/job logs (e.g. `ROBOT_CONFIG environment variable is not set`) and verify actual artifacts on OBS before
> claiming success — a task may be FAILED while its report/output partially exists, or
> SUCCEEDED while downstream operators reject the output.

See [Pipeline Summary Template](references/pipeline-summary-template.md) for the full
summary output template.

> **Mark manual stages before `finish`**: `finish` requires every non-skipped stage to have a terminal status.
> Of the `kind: manual` stages (`plan`/`upload`/`output`), only some are completed automatically;
> `set-result`：
> - `upload`: marked SUCCEEDED automatically by `record-inputs` (no manual step)
> - `plan`: marked SUCCEEDED automatically by `init` (no manual step)
> - `output`: **must be marked manually** — once the proc stage named by `pipeline.output.from_stage`
>   is SUCCEEDED, run `set-result --stage output --expect-task none --result <result.json>`; the result
>   carries the from_stage's target_path/target_asset_id/target_version_id/output_name
>
> Example:
> ```bash
> python scripts/pipeline_state.py --run <run_id> set-result \
>   --stage output --expect-task none \
>   --result '{"status":"SUCCEEDED","output_name":"<from_stage output_name>","target_path":"<from_stage target_path>","target_asset_id":"<from_stage target_asset_id>","target_version_id":"<from_stage target_version_id>"}'
> ```
> Call `finish` after marking it.

### Error Handling & Checkpoint Recovery

| Scenario | Strategy |
|----------|---------|
| Stage task `FAILED` | Diagnose with `get-log` (system + job logs); then `retry` (create a **new** task after confirmation) or `skip` (only when the stage has `fail_fast: false`); `fail_fast: true` stages stop the pipeline until resolved |
| Stage task `DELETED` | Treat as failed: check logs / resource (e.g. `POD_PENDING` on public pool), adjust after confirmation, create a new task |
| `wait-task` timeout while non-terminal | Re-run `wait-task` and report status and elapsed time; user decides continue / view logs / terminate; do not resubmit |
| Session interrupted | Resume from the checkpoint file (below); continue from the interrupted stage |
| Evaluation FAILED | Advisory, does not block output (`fail_fast: false`) |
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

### Local Web Monitoring 本地 Web 监控

The complete local monitor ships in `scripts/pipeline-monitor/`; it needs Python 3.9+ on
Windows/macOS/Linux and no additional packages or internet assets. Windows uses the
standard-library `msvcrt` byte-range lock; Unix uses `flock`. Keep the complete scripts
directory, including `platform_utils.py`, when copying the skill.

Detailed task resource usage is inspected in CloudRobo Console using the task ID; the
local Web monitor does not query usage metrics. Keep resource pool/specification fields
in task configuration because they are required for submission and retry.

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
Run from the skill directory:

```bash
# Default: persisted real runs, including an empty list; no run_id required
python3 scripts/pipeline-monitor/server.py --background --open

# An existing real run identified in the conversation
python3 scripts/pipeline-monitor/server.py --run <run_id> --background --open
python3 scripts/pipeline-monitor/server.py --stop

# Only when the user explicitly requests an offline demo
python3 scripts/pipeline-monitor/server.py --demo --open
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

## pipeline.yaml Structure pipeline.yaml 结构

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

`pipeline_state.py init --plan` requires plan.json to declare DAG dependencies explicitly (`depends_on`/`input_from`), and an eval stage cannot be a data source. A complete schema-valid example:

```json
{
  "pipeline_name": "teleop",
  "workspace_id": "<workspace_id>",
  "inputs": [
    {
      "id": "default",
      "source_type": "local",
      "local_path": "/data/raw/",
      "data_source_type": "ros2",
      "robot_type": "galaxea_r1"
    }
  ],
  "stages": [
    {
      "id": "convert",
      "kind": "proc",
      "operator": "数据转换--ros转LeRobotV3",
      "operator_source": "preset",
      "depends_on": [],
      "input_from": ["input:default"],
      "output_name": "teleop-convert"
    },
    {
      "id": "clean",
      "kind": "proc",
      "operator": "数据清洗",
      "operator_source": "preset",
      "depends_on": ["convert"],
      "input_from": ["convert"],
      "output_name": "teleop-clean"
    },
    {
      "id": "quality-eval",
      "kind": "eval",
      "operator": "数据集质量评测-LeRobot",
      "operator_source": "preset",
      "depends_on": ["clean"],
      "input_from": ["clean"],
      "fail_fast": false
    }
  ],
  "output": {
    "from_stage": "clean",
    "asset_name": "teleop-clean"
  }
}
```

Key points:
- `inputs[].id` must be unique with multiple inputs; it may be omitted for a single input (defaults to `default`)
- Every stage must declare `depends_on` (wait dependencies) and `input_from` (data source) explicitly
- `input_from` references an initial input as `input:<id>` and an upstream output by stage `id`
- **An eval stage cannot be an `input_from` source** (evaluation only produces reports)
- `pipeline.output.from_stage` must point to a proc stage, not an eval stage

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
`数据转换--ros转LeRobotV3`: `auto | galaxea_r1 | galaxea_a1z | jaka | moz1 | azureloong |
ur5e`, read from `environment_variables[].description`). Map `robot_type` to an enumerated
value (e.g. `r1` → `galaxea_r1`) and confirm it in the plan; if there is no match, ask the
user. If the operator declares no `robot` env, do not set one.

### Custom Operator Stages

A stage selects its operator via `operator_source` (default `preset`). Processing supports
all three sources below; evaluation references preset/workspace algorithm assets:

- **`preset`** → `PRESET_ASSETS`; discover via `list-publication-assets`.
- **`workspace`** → `WORKSPACE_ASSETS`; discover via `cloudrobo asset list-assets
  --catalog-id <id> --type algorithm --tags "Data Processing"` (or `"Data Evaluation"` for
  evaluation operators) `--name "<name>"`; fields same as preset.
- **`obs`** → `OBS_ASSETS`; task_config adds `algo_path` + `job_local_path`, plus
  `algo_entrance`, `image` (user-provided); `algo_id` is optional (valid UUID if provided).

Custom operators consume their `input_from` sources as ordered `dataset_configs` entries, produce `target_path` /
`target_asset_id` for the next stage, and may declare `ext_metadata.inputs` (same `inputs`
logic). YAML example and source resolution table: "Template C2: Custom Operator Insertion"
in [Pipeline Templates](references/pipeline-templates.md).

**Built-in vs Custom**:
- **Built-in**: `templates/sim-teleop-cleaning.yaml`; user triggers verbally, no YAML
  needed; user can override template fields
- **Custom**: User supplies YAML or the guided flow generates it from their requirements;
  no `type` field. Resource preferences and partial-input handoff remain in the companion
  draft JSON, then feed the confirmed execution plan.

See [Pipeline Templates](references/pipeline-templates.md) for YAML structure, field
definitions, and examples.

---

## CLI Command Format Standard CLI命令格式标准

```bash
cloudrobo <service> <command> [OPTIONS]
cloudrobo dataset proc|eval <command> [OPTIONS]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service / command group | `workspace`, `asset`, `dataset proc` (proc-tasks), `dataset eval` (eval-tasks) | `cloudrobo dataset proc` |
| Subcommand | kebab-case | `list-publication-assets`, `create-task`, `wait-task`, `show-task` |
| Workspace override | `--workspace-id <id>` | `cloudrobo workspace use --workspace-id <id>` |
| JSON parameter | `--task-config '<json>'`, `--ext-metadata '<json>'` | `--ext-metadata '{"annotation_status":true}'` |
| JSON-string fields | `envs`, `inputs`, `dataset_configs` are JSON-array **strings** inside task_config | `"envs": "[{\"key\":\"robot\",\"value\":\"galaxea_r1\"}]"` |
| Boolean flag | `--is-system true` | `--is-system false` |
| Dry-run | `--dry-run` (asset create-asset / create-version / import-asset / update-version, dataset proc/eval create-task; echoes arguments only, no validation) | Preview without executing |
| Output format | JSON to stdout (except `wait-task`, which prints status lines) | — |
| Object storage | `obs://` paths only | `obs://bucket/raw/` |

> **Windows / PowerShell:** Examples use bash syntax. To run on Windows PowerShell:
> - Flatten `\` line continuations to a single line, or end lines with a backtick.
> - Set env vars with `$env:NAME="value"` instead of `export NAME="value"`.
> - Use `py -3` (or `python`) instead of `python3` when that is the installed launcher.
> - Windows PowerShell 5.1 can strip nested JSON quotes when calling native programs.
>   The Web "copy CLI" action generates a PowerShell/Python JSON-argv bridge on Windows.
>   Prefer JSON files for the local authoring/state scripts; they accept UTF-8 with or without BOM.
> - Native Windows demo, background/stop and test commands are in [Web Monitor](references/web-monitor.md#windows-powershell).

---

## Core Commands 核心命令

| Purpose | Command |
|---------|---------|
| Workspace + catalog_id | `cloudrobo workspace current` / `cloudrobo workspace use --workspace-id <id>` |
| Register dataset (local) | `cloudrobo asset import-asset --catalog-id <id> --type dataset --name <n> --local-path <dir> --ext-metadata '{"annotation_status":true}'` |
| Register dataset (obs) | `cloudrobo asset create-asset --catalog-id <id> --type dataset --name <n> --ext-metadata '{"annotation_status":true}'` + `cloudrobo asset create-version --asset-id <id> --url <obs_path>` |
| Find registered dataset | `cloudrobo asset list-assets --catalog-id <id> --type dataset --name <n>` |
| Latest version / version detail | `cloudrobo asset list-versions --asset-id <id> --sort-key created_at --sort-dir desc --limit 1` / `cloudrobo asset show-version --asset-id <id> --version-id <vid>` |
| Publish version | `cloudrobo asset update-version --asset-id <id> --version-id <vid> --status RELEASE` |
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

## Parameter Confirmation 参数确认

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

## Configuration Priority 配置优先级

- **envs**: pipeline.yaml stage `params.envs` > operator `ext_metadata.environment_variables[].default`
- **inputs**: user `inputs[].url_path` > operator built-in `url_path` > dataset directory
  config (config.yaml / manifest.yaml) > `robot` env default

This order applies only when supported by the current operator. A valid built-in robot or
default configuration does not require adding a YAML file or external mount.

See [Task Config Reference](references/task-config-catalog.md) for details.

---

## Reference Documents 参考文档

- [CLI Installation Guide](references/cli-installation-guide.md) — CloudRobo CLI installation and configuration
- [IAM Policies](references/iam-policies.md) — Least-privilege IAM policies for CloudRobo
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagrams for the pipeline
- [Pipeline Templates](references/pipeline-templates.md) — Built-in pipeline template, custom pipeline examples, pipeline state tracking
- [User Guide 用户指南](references/user-guide.md) — Complete user-facing workflow, features, examples and troubleshooting
- [Guided Custom Pipeline Authoring](references/custom-pipeline-authoring.md) — Natural-language interview, local YAML generation, revision and execution handoff
- [Task Config Reference](references/task-config-catalog.md) — Operator field mapping + per-stage task_config construction
- [Pipeline Summary Template](references/pipeline-summary-template.md) — Final pipeline summary output template
- [Verification Method](references/verification-method.md) — Verification methods and CLI command reference
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria for pipeline execution
- [Fault Recovery](references/fault-recovery.md) — Fault recovery for conversion, cleaning, and evaluation

---

## Edge Cases 边界情况

| Scenario | Handling |
|----------|----------|
| Missing `workspace_id` | Run `cloudrobo workspace use --workspace-id <id>` or pass `--workspace-id` |
| AK/SK not set | Configure via `cloudrobo config set ak <ak> sk <sk>` or `HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK` (see [CLI Installation Guide](references/cli-installation-guide.md)) |
| Input source not specified | Must ask the user (local / asset / obs) |
| Required operator not found in region | Stop and tell the user; never substitute another operator |
| Multiple operator matches | Show matches and ask the user, or use `operator_id` |
| `--tags` filter returns nothing | Retry with `--sub-type data_processing` / `data_evaluating` + `--name`; still nothing → stop |
| `robot_type` not in the operator's `robot` enum | Map to an enumerated value or ask the user |
| Operator declares no `inputs` / `environment_variables` | Omit `inputs` / `envs` |
| Undeclared `params.envs` key or `params.inputs` name | Error — tell the user |
| Missing/empty required task_config field | CLI validation error before submission; check required fields in the task config reference |
| `--algo-type` vs `task_config.algo_type` | Keep identical (`--algo-type` overrides); `dataset eval create-task` has no `--algo-type` |
| Dataset version `DRAFT` | Verify version/path and continue when supported; only an established RELEASE requirement triggers publication confirmation |
| `wait-task` timeout, task non-terminal | Re-run `wait-task`, report progress; do not resubmit |
| Task `FAILED` / `DELETED` | Diagnose with `get-log`; create a new task after confirmation |
| `POD_PENDING` on public pool | Smaller flavor (e.g. 2c4g) or dedicated pool; new task after confirmation |
| `ROBOT_CONFIG environment variable is not set` | Mount the robot description directory via `inputs` (e.g. `ROBOT_CONFIG_PATH`) if the operator declares it |
| CLI/SDK requires `robot_config` | Outdated client; upgrade the CloudRobo SDK/CLI — do not add the removed field |
| Evaluation failed | Advisory (`fail_fast: false`); report, TrainingReady output still produced |
| Circular `depends_on` | Error, ask the user to fix the YAML |
| Session interrupted | Resume from `~/.cloudrobo/pipeline-runs/<run_id>/state.json` via `pipeline_state.py show` |
| Evaluation report link | OBS temporary URL; save/download promptly |
| Object storage | Must use `obs://` paths |
| Mutating ops | Plan confirmation before create/import/update/create-task |
| Cross-skill | Single-task proc/eval CRUD, logs, preview and diagnosis → `huawei-cloud-cloudrobo-dataset`; this skill composes selected preset/workspace operator workflows and offers the sim/teleop template |

---

## Verification Method 验证方法

### Specification Compliance Verification 规范合规验证

```bash
bash scripts/test-cli-commands.sh -s . -e cli   # read-only smoke tests
```

### Test Cases 测试用例

See `templates/test-vars.json` for the test case list.

### Verification Checklist 验证清单

- Pipeline parsing: declared DAG valid, compatible operator handoffs, no cycles
- Plan confirmed by the user before any mutating operation
- Dynamic operator discovery: exact Chinese names / `operator_id`, no hardcoded IDs, fresh
  query before each submission; missing operator → stopped and reported
- Artifact passing: `target_path` / `target_asset_id` / `target_version_id` feed the next
  proc stage's `dataset_configs` in `input_from` order; eval stages use one source as top-level fields plus a single-item versioned `dataset_configs`
- Stage terminal states reached via `wait-task`; eval reports fetched per member with
  `get-preview --task-id`
- Final data comes from `pipeline.output.from_stage`; eval-only output consists of
  reports and the preserved input. Report actual readiness and coverage without assuming TrainingReady

See [Verification Method](references/verification-method.md) and
[Acceptance Criteria](references/acceptance-criteria.md) for detailed checklists.
