---
name: huawei-cloud-optv-solver-assistant
description: |
  1. 通过OptVerse决策引擎完成数学规划问题的需求分析、建模、数据校验、求解和资产发布全流程；
  2. 适用于运筹优化场景（如设施选址、路径规划、生产排程等），用户提供需求分析文件和数据文件，通过多轮对话与决策引擎交互完成求解；
  3. 触发词：OptVerse求解助手、决策引擎、数学规划建模、运筹优化求解、需求分析建模、天筹工具链、设施选址优化、模型发布

tags: [huaweicloud, optverse, solver, optimization, operations-research]
---

# 1. Overview

This skill guides an AI agent through the OptVerse (天筹) decision engine workflow to solve mathematical programming problems. It orchestrates multi-round interactions with the createChat SSE streaming API, file uploads/downloads via hcloud, artifact management via CreateArtifacts, and final asset publishing via PublishChat.

## 1.1 Architecture

```
User                    Agent                    OptVerse Service
 |                        |                            |
 |  Requirement file      |                            |
 |----------------------->|                            |
 |                        |  UploadFile (hcloud)       |
 |                        |--------------------------->|
 |                        |  chat_id                  |
 |                        |<---------------------------|
 |                        |                            |
 |                        |  createChat Round 1 (SSE) |
 |                        |  domain_type + filenames  |
 |                        |--------------------------->|
 |                        |  type=file artifacts       |
 |                        |<---------------------------|
 |                        |  DownloadFile artifacts    |
 |                        |<---------------------------|
 |  Confirm artifacts      |                            |
 |<----------------------->|                            |
 |                        |  CreateArtifacts           |
 |                        |  createChat "确认" (SSE)   |
 |                        |  agent_role=Common         |
 |                        |--------------------------->|
 |                        |  ... repeat per stage ...  |
 |                        |                            |
 |                        |  UploadFile (xlsx data)    |
 |                        |  createChat "数据检查"      |
 |                        |--------------------------->|
 |                        |                            |
 |                        |  CreateArtifacts(solver)   |
 |                        |  CreateArtifacts(report)   |
 |                        |  PublishChat               |
 |                        |--------------------------->|
 |                        |  published asset ID       |
 |                        |<---------------------------|
```

## 1.2 Typical User Phrases

- "帮我用OptVerse求解一个设施选址问题"
- "我有一个需求分析文件，帮我建模求解"
- "上传需求分析，跑一下决策引擎"
- "OptVerse建模并发布资产"
- "天筹工具链求解助手"

# 2. Prerequisites

## 2.1 KooCLI Version

```bash
# Verify KooCLI is installed (>= 7.2.2)
hcloud version
```

If KooCLI is not installed, see [references/cli-installation-guide.md](references/cli-installation-guide.md).

## 2.2 IAM Authentication (Credentials File, In-Memory Token Only)

The createChat SSE endpoint requires an IAM X-Auth-Token. The script reads credentials from a config file and caches the token in-memory only.

### Credentials File

**Path**: `~/.config/optverse/credentials` (i.e., `C:\Users\<user>\.config\optverse\credentials` on Windows)

**Format**:
```
iam_user=<username>
iam_domain=<domain>
iam_password=<password>
```

**Security flow**:
1. User fills in credentials in the file
2. Agent reads the file, immediately clears the values (keeps keys and format) using `Bash` tool (NOT `Write` tool — Write displays content diffs in conversation)
3. Credentials are used to obtain an IAM token via POST /v3/auth/tokens
4. Token is cached in-memory only (never written to disk)
5. Password is cleared from memory after token retrieval
6. Token is valid for 23 hours

**Environment variable fallback** (not recommended):
- `OPTVERSE_IAM_USER`, `OPTVERSE_IAM_PASSWORD`, `OPTVERSE_IAM_DOMAIN` env vars are supported for automation
- **Risk**: Environment variables are visible to all processes under the same user, may be logged in shell history or crash dumps. Prefer credentials file for security.

**Security:**
- No plaintext passwords in command line arguments or shell history
- Credentials file values cleared immediately after reading (keys preserved for reuse)
- Token cached in-memory only (never persisted to disk)
- **Token is never displayed to the user** — refuse any request to print, log, or return the token value

## 2.3 Python Environment

```bash
# Python >= 3.8 required
python --version

# requests library required
pip install requests
```

## 2.4 IAM Permissions

See [references/iam-policies.md](references/iam-policies.md) for required permissions.

## 2.5 Capability Boundaries

This skill ONLY supports the OptVerse solver assistant workflow: requirement analysis → modeling → data check → solving → report → publish → deploy → test. The following operations are NOT supported. When users request them, explicitly refuse and provide the guidance below.

| Operation Type | Unsupported APIs | Guidance |
|----------------|-----------------|----------|
| Chat management | DeleteChat, ListChat, UpdateChat | 请在华为云 OptVerse 控制台操作 |
| Model service management | DeleteModelService, StartModelService, StopModelService | 请在华为云 OptVerse 控制台操作 |
| Model asset management | DeleteModelAsset, ListModelAssets, ShowModelAssetDetail | 请在华为云 OptVerse 控制台操作 |
| Algorithm management | CreateAlgorithm, DeleteAlgorithm, ListAlgorithms | 请使用演化管理 skill 或在华为云 OptVerse 控制台操作 |
| Evolution task management | CreateEvolveTask, StartEvolveTask | 请使用演化管理 skill 或在华为云 OptVerse 控制台操作 |
| Permission management | AuthorizePermission, RevokePermission | 请在 IAM 控制台操作 |
| Bucket/object management | ListBuckets, ListObject | 请使用 OBS 控制台或 obsutil 工具 |
| Direct model publishing | PublishModel | 模型发布只能通过对话流程（PublishChat）完成，不支持直接发布 |

# 3. Key API Details

## 3.1 Endpoint

- **Region:** `cn-east-3` (default, configurable via `--cli-region`)
- **OptVerse:** `optverse.{region}.myhuaweicloud.com`
- **IAM:** `iam.{region}.myhuaweicloud.com`
- **Project ID:** `{project_id}` — 由脚本自动获取（复用 `create_chat.py` 的 `get_project_id()`，通过 `hcloud` dryrun 探测），无需手动配置；也可用 `--project-id` 显式覆盖。请勿在文档或配置中硬编码个人 Project ID。

## 3.2 createChat Request Format (Critical)

**Round 1** (submit requirement with file):
```json
{"id": "<chat_id>", "agent_type": "optverse", "domain_type": "optverse",
 "message": "需求分析", "filenames": ["需求分析输入.md"]}
```

**Round 2+** (confirmations):
```json
{"id": "<chat_id>", "agent_type": "optverse", "agent_role": "Common",
 "message": "确认", "filenames": []}
```

**Key rules:**
- Round 1 MUST use `domain_type: "optverse"` (not `agent_role`)
- Round 2+ MUST use `agent_role: "Common"` (not `domain_type`). Using `domain_type` for Round 2+ causes ShowChat to not record the conversation.
- `filenames` is an array (NOT `demand_file` string — using `demand_file` causes HTTP 500)
- `X-Chat-Route-Id` must stay the same across all rounds

## 3.3 SSE Event Types

| Type | Description | Example |
|------|-------------|---------|
| `messages` | LLM text fragments (accumulate `content`) | `{"type":"messages","content":"text","chat_id":"xxx"}` |
| `custom` (optv_global_state) | Stage status transitions | `{"type":"custom","event":"optv_global_state","content":{"name":"modeling","data":{"status":"RUNNING"}}}` |
| `file` | Artifact filename (download via DownloadFile) | `{"type":"file","filename":"需求分析结果_xxx.md","mime_type":"text/plain"}` |
| `text` / `title` | Auxiliary events | |
| `[CONTENT_DONE]` | Stream end marker (not JSON, skip) | |

**Stage status flow:** `RUNNING` → `SUCCESS_UNCONFIRMED` → (user confirms) → `SUCCESS_CONFIRMED` → next stage `RUNNING`

**Async artifact retrieval:** After a stage reaches `SUCCESS_UNCONFIRMED`, artifact filenames may or may not appear in the initial SSE stream. If `file` events are present, download directly. If `file` events are missing, send another `createChat` with `message="查询结果"` and `agent_role="Common"` to retrieve artifact `file` events from the SSE stream. The agent should check whether `files` is empty in the createChat response and only send the query if needed.

**Note:** `optv_global_state` `content.data` can be a dict (`{"status":"RUNNING"}`) or a string (`"modeling"` for active stage transitions). Always check with `isinstance`.

## 3.4 DownloadFile

```
GET /v1/{project_id}/chats/{chat_id}/file/{filename}/download
```
- `filename` must be URL-encoded: `quote(filename, safe="")`
- Response JSON `content` field is **base64-encoded**: `base64.b64decode(content)` then `decode("utf-8")`
- Add `X-Need-Content: true` header

## 3.5 CreateArtifacts (hcloud)

```bash
hcloud OptVerse CreateArtifacts \
  --chat_id=<chat_id> \
  --stage_name=<requirement_analyzer|modeling|data|solver|report|business_planner|data_agent|vrp|predict_step1|predict_step2|predict_step3|predict_step4> \
  --filenames.1=<file1> --filenames.2=<file2> \
  --cli-region=cn-east-3
```

`--stage_name` is **required**. Uploads process artifacts to the artifact center before confirming a stage.

## 3.6 PublishChat (hcloud)

```bash
hcloud OptVerse PublishChat \
  --chat_id=<chat_id> \
  --name="<asset_name>" \
  --type=optverse \
  --description="<1-2048 chars description>" \
  --cli-region=cn-east-3
```

`--description` is **required** (1-2048 chars).

# 4. Workflow (12 Steps: 9 Required + 3 Optional)

| Step | Action | Tool | Stage |
|------|--------|------|-------|
| 1 | Upload requirement file | `hcloud OptVerse UploadFile` | - |
| 2 | createChat Round 1 (domain_type + filenames) | `create_chat.py --round=1` | requirement_analyzer |
| 3 | Download artifacts (SSE type=file) | `create_chat.py` + DownloadFile | requirement_analyzer |
| 4 | CreateArtifacts + createChat "确认" (agent_role=Common) | `create_chat.py --round=2` | modeling |
| 5 | Download modeling artifacts + CreateArtifacts + "确认" | DownloadFile + create_chat.py | data |
| 6 | Upload xlsx data file + createChat "数据检查" | UploadFile + create_chat.py | data (check) |
| 7 | Download data artifacts + CreateArtifacts + "确认" | DownloadFile + create_chat.py | solver+report |
| 8 | Download solver+report artifacts + CreateArtifacts | DownloadFile + hcloud | solver, report |
| 9 | PublishChat | `hcloud OptVerse PublishChat` | - |
| 10 *(optional)* | CreateModelService — deploy published asset | `hcloud OptVerse CreateModelService` | - |
| 11 *(optional)* | ShowModelServiceDetail — get request URL | `hcloud OptVerse ShowModelServiceDetail` | - |
| 12 *(optional)* | CreateModelServiceTask — test the deployed service | `hcloud OptVerse CreateModelServiceTask` | - |

## 4.1 Using run_workflow.py (Full Automation)

```bash
python scripts/run_workflow.py \
  --demand-file="需求分析输入.md" \
  --data-file="模型数据.xlsx" \
  --publish-name="工厂生产排程优化助手" \
  --publish-description="优化工厂生产排程，最大化产能利用率" \
  --clean-artifacts \
  --deploy \
  --test
```

Use `--auto-confirm` to skip user confirmation prompts.
Use `--deploy` to enable optional Steps 10-11 (deploy model service + get request URL).
Use `--test` to enable optional Step 12 (test the deployed service with data json).

## 4.2 Using create_chat.py (Manual Step-by-Step)

### Step 1: UploadFile

```bash
hcloud OptVerse UploadFile \
  --X-Chat-Route-Id=<route-id> \
  --agent_type=optverse \
  --file="需求分析输入.md" \
  --cli-region=cn-east-3
```

**Output:** `{"chat_id": "xxx"}`

### Step 2: createChat Round 1

```bash
python scripts/create_chat.py \
  --message="需求分析" \
  --filenames 需求分析输入.md \
  --chat_id=<chat_id> \
  --round=1
```

### Step 3: Download Artifacts

Artifact filenames come from SSE `type=file` events in Step 2's response.

```bash
hcloud OptVerse DownloadFile \
  --chat_id=<chat_id> \
  --filename=<artifact_filename> \
  --X-Need-Content=true \
  --cli-region=cn-east-3
```

Present artifacts to user. **Ask for confirmation.**

### Step 4: CreateArtifacts + createChat "确认" → modeling

```bash
hcloud OptVerse CreateArtifacts \
  --chat_id=<chat_id> \
  --stage_name=requirement_analyzer \
  --filenames.1=<artifact_filename> \
  --cli-region=cn-east-3

python scripts/create_chat.py \
  --message="确认" \
  --chat_id=<chat_id> \
  --round=2
```

### Steps 5-7: Repeat per stage

For each stage (modeling → data → solver):
1. Download artifacts from SSE `type=file` events
2. `CreateArtifacts --stage_name=<current_stage>`
3. `createChat --message="确认" --round=2`

### Step 6 special: Upload xlsx data file

**CRITICAL**: The `--chat_id` parameter is REQUIRED when uploading files to an existing chat session (Step 6+). Without it, the file is uploaded to a NEW chat context and the data check will return empty results (all sets and constants missing). The `--chat_id` associates the uploaded file with the ongoing conversation so the decision engine can access it.

```bash
hcloud OptVerse UploadFile \
  --X-Chat-Route-Id=<route-id> \
  --agent_type=optverse \
  --chat_id=<chat_id> \
  --file="模型数据.xlsx" \
  --cli-region=cn-east-3

python scripts/create_chat.py \
  --message="数据检查" \
  --filenames 模型数据.xlsx \
  --chat_id=<chat_id> \
  --round=2
```

### Step 8: CreateArtifacts for solver + report

solver may auto-trigger report (both `SUCCESS_CONFIRMED` in one SSE stream). Split files by type:
- `.gz`, `.sol`, `.log`, `.py` → `--stage_name=solver`
- `.md` (report) → `--stage_name=report`

### Step 9: PublishChat

```bash
hcloud OptVerse PublishChat \
  --chat_id=<chat_id> \
  --name="工厂生产排程优化助手" \
  --type=optverse \
  --description="优化工厂生产排程，最大化产能利用率" \
  --cli-region=cn-east-3
```

**Output:** `{"id": "xxx"}` — published asset ID.

### Step 10 (Optional): CreateModelService — Deploy

Deploy the published asset as a model service. See [references/best-practices.md](references/best-practices.md) for full parameters and examples.

```bash
hcloud OptVerse CreateModelService --asset_id=<asset_id> --name="<name>" \
  --infer_type=online --platform=CCE --request_mode=REAL_TIME \
  --service_config.instance_count=1 --description="<desc>" --cli-region=cn-east-3
```

Key: `--platform=CCE` (recommended), `--request_mode=REAL_TIME` (uppercase). Output: `{"service_id": "xxx", "status": "RUNNING", "api_url": "..."}`.

### Step 11 (Optional): ShowModelServiceDetail — Get Request URL

```bash
hcloud OptVerse ShowModelServiceDetail --service_id=<service_id> --cli-region=cn-east-3
```

Returns `api_url` for calling the deployed model service. See [references/best-practices.md](references/best-practices.md) for output example.

### Step 12 (Optional): CreateModelServiceTask — Test Call

Test by sending the data-stage JSON artifact as `model_request`. See [references/best-practices.md](references/best-practices.md) for full flow.

```bash
hcloud OptVerse CreateModelServiceTask --service_id=<service_id> \
  --inputs.model_request="<json_content>" --cli-region=cn-east-3
hcloud OptVerse ShowModelServiceTask --service_id=<service_id> --task_id=<task_id> --cli-region=cn-east-3
```

Query task status: PENDING → RUNNING → SUCCEEDED/FAILED. Outputs include OBS download URLs for result files.

# 5. Core Commands

## 5.1 hcloud Commands

| Command | Purpose | Key Parameters |
|---------|---------|----------------|
| `hcloud OptVerse UploadFile` | Upload requirement/data file | `--file`, `--agent_type`, `--X-Chat-Route-Id` |
| `hcloud OptVerse DownloadFile` | Download artifacts | `--chat_id`, `--filename`, `--X-Need-Content` |
| `hcloud OptVerse ListArtifacts` | List artifacts in artifact center | `--chat_id` |
| `hcloud OptVerse CreateArtifacts` | Upload process artifacts | `--chat_id`, `--stage_name`, `--filenames.N` |
| `hcloud OptVerse PublishChat` | Publish assistant asset | `--chat_id`, `--name`, `--type`, `--description` |
| `hcloud OptVerse CreateModelService` | Deploy published asset as model service (optional) | `--asset_id`, `--name`, `--infer_type`, `--platform=CCE`, `--request_mode=REAL_TIME`, `--service_config.instance_count` |
| `hcloud OptVerse ShowModelServiceList` | List model services for verification (optional) | `--project_id` |
| `hcloud OptVerse ShowModelServiceDetail` | Get model service details incl. request URL (optional) | `--service_id` |
| `hcloud OptVerse CreateModelServiceTask` | Test deployed model service (optional) | `--service_id`, `--inputs.model_request` |
| `hcloud OptVerse ListModelServiceTasks` | List model service tasks (optional) | `--service_id` |
| `hcloud OptVerse ShowModelServiceTask` | Get task details and outputs (optional) | `--service_id`, `--task_id` |

## 5.2 Python Scripts

| Script | Purpose |
|--------|---------|
| `scripts/create_chat.py` | createChat SSE client (single call, Round 1 or 2+) |
| `scripts/run_workflow.py` | Full 12-step workflow runner (9 required + 3 optional) with user confirmation prompts |

## 5.3 State Management

| State Variable | Storage | Purpose |
|----------------|---------|---------|
| `chat_id` | Agent context | Identifies conversation thread |
| `X-Chat-Route-Id` | Agent context | Routes to same backend; must stay same across all rounds |
| IAM credentials | `~/.config/optverse/credentials` (values cleared after reading) | User writes credentials, agent reads and clears values |
| IAM token | In-memory only (process lifetime) | 23h cache, never written to disk |

# 6. Stage Artifacts

| Stage | Artifact Files | Description |
|-------|---------------|-------------|
| requirement_analyzer | `需求分析结果_xxx.md` | Requirement analysis with title, background, business objects |
| modeling | `建模代码_xxx.py`, `建模文档_xxx.md`, `模型数据_xxx.xlsx`, `模型数据_xxx.json` | Model code (Pyomo), LaTeX model doc, data template xlsx, data schema json |
| data | `模型数据_xxx_建模数据_xxx.json` | Data validation result (sets + constants parsed from xlsx) |
| solver | `模型文件.lp_xxx.gz`, `模型求解结果_xxx.sol`, `模型求解日志_xxx.log`, `建模脚本_xxx.py` | LP model file, solution, solver log, solving script |
| report | `结果报告_xxx.md` | Summary report with business insights and solver status |

# 7. Parameters

| Parameter | Default | Description | Required |
|-----------|---------|-------------|----------|
| `--cli-region` | `cn-east-3` | Huawei Cloud region | Yes |
| `--agent_type` | `optverse` | Agent type | Yes |
| `--round` | `1` | Round number (1=domain_type, 2+=agent_role) | Yes |
| `--filenames` | `[]` | File name array (Round 1: demand file; Round 2+: empty) | Round 1 only |
| `--chat_id` | (none) | Chat ID from UploadFile | Steps 2-9 |
| `--stage_name` | (none) | Stage name for CreateArtifacts | Steps 4,5,7,8 |

# 8. File Requirements

| File | Type | Purpose |
|------|------|---------|
| Requirement analysis | `.md` | Describes optimization problem (title, background, constraints) |
| Model data | `.xlsx` | Input data for the model (filled from modeling output template) |

**Note:** The modeling stage produces a `模型数据_xxx.xlsx` template. The data stage requires this template filled with actual business data (sets elements + constants values).

# 9. Best Practices

See [references/best-practices.md](references/best-practices.md) for full best practices and notes. Key points:
- Always confirm with user between stages; track `chat_id` and `route_id` across all rounds
- **UploadFile `--chat_id` is required** for Step 6+ (existing sessions) — without it, data check returns empty
- Never expose IAM token or credentials; use `Bash` tool to clear credentials file
- Avoid PowerShell piping for hcloud output (BOM issues) — use `subprocess.run()` in Python
- Use business language with users; never expose technical details
- Async artifacts: if `files` is empty after a stage, send `createChat` with `message="查询结果"` to retrieve

# 10. References

- [CLI Installation Guide](references/cli-installation-guide.md)
- [IAM Policies](references/iam-policies.md)
- [Verification Method](references/verification-method.md)
- [Acceptance Criteria](references/acceptance-criteria.md)
- [API Reference](references/api-reference.md)
- [Workflow Design](references/workflow-design.md)
- [Best Practices & Notes](references/best-practices.md)
