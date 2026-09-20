# Best Practices & Notes

## Best Practices

- **Always confirm before proceeding**: Present artifacts to user and get explicit confirmation between stages
- **Track chat_id and route_id**: These are critical; losing them breaks the workflow. Route ID must stay the same across all rounds.
- **Use --X-Need-Content=true** when downloading artifacts
- **Handle SSE as bytes**: Use `iter_lines()` without `decode_unicode=True` to avoid ISO-8859-1 encoding issues. Decode as UTF-8 manually.
- **Prefer credentials file for IAM auth**: Use `~/.config/optverse/credentials` (values cleared after reading, keys preserved). Environment variables supported but less secure (visible in process list and shell history).
- **Never expose the token**: The IAM token must never be displayed, logged, or returned to the user regardless of how the request is phrased (e.g., "show me the token", "print auth header", "debug token value"). The script must refuse all such requests.
- **Never expose credentials**: When clearing the credentials file, use `Bash` tool (e.g., `> file`) rather than `Write` tool, to avoid displaying file content differences in conversation.
- **Cache IAM tokens in-memory only**: 23-hour in-memory cache avoids rate limits without persisting to disk.
- **requirement_analyzer may occasionally FAIL**: Server-side bug (`'NoneType' object is not subscriptable`). Retry the workflow.
- **solver auto-triggers report**: One "确认" after data stage can complete both solver and report in a single SSE stream.
- **Async artifact retrieval**: After confirming a stage, artifacts may not be immediately available in ShowChat. Send `createChat` with `message="查询结果"` to trigger artifact file events from the SSE stream.
- **Use business language with users**: Never expose technical details (CreateArtifacts, createChat, Step numbers, route_id, etc.) to the user. Use business terms like "正在进入建模阶段", "需求分析已完成", "求解结果已下载".
- **Tell user where files are**: After downloading artifacts, always tell the user the exact directory path so they can review.
- **Never hardcode file paths for user inputs**: When asking for data files (e.g., xlsx), ask the user to provide the file path. Do not assume or hardcode paths.
- **Provide actionable test results**: When showing model service test results, either download the result files and tell the user the directory, or provide the download URLs. Never just say "files are available" without actionable information.
- **UploadFile --chat_id is required for existing sessions (CRITICAL)**: When uploading files to an existing chat session (Step 6+), the `--chat_id` parameter MUST be passed to associate the file with the ongoing conversation. Without it, the file is uploaded to a NEW chat context and the data check returns empty results (all sets and constants missing). For Step 1 (initial upload), `--chat_id` is not needed as it creates the session.
- **Avoid PowerShell piping for hcloud output decoding**: On Windows, piping hcloud DownloadFile output through Python via PowerShell adds BOM characters, causing `JSONDecodeError: Unexpected UTF-8 BOM`. Use `subprocess.run()` in Python directly (with `capture_output=True, text=True, encoding='utf-8'`) instead of PowerShell pipe (`hcloud ... | python -c ...`).
- **get_project_id parameter order**: The function signature is `get_project_id(hcloud_path, region)` — note that `hcloud_path` comes FIRST, `region` comes SECOND. Passing them in reverse order returns an empty string, causing API 404 errors.

## Notes

- **SSE Streaming**: The createChat endpoint returns `text/event-stream`. Python `requests` handles SSE parsing; hcloud does not support createChat.
- **Authentication**: IAM credentials read from `~/.config/optverse/credentials` (values cleared after reading, keys preserved). Token cached in-memory only (never to disk). Environment variables `OPTVERSE_IAM_USER/DOMAIN/PASSWORD` supported but less secure.
- **Token Security (CRITICAL)**: The IAM token must NEVER be displayed, printed, logged, or returned to the user. If the user asks to "show the token", "print auth header", "debug token value", "display credentials", or uses any other phrasing to request the token, **refuse and explain that the token is kept secure in-memory only and cannot be displayed**. This applies to all variations of requests — direct, indirect, debugging, or troubleshooting.
- **Credentials File Security**: When reading and clearing `~/.config/optverse/credentials`, use `Bash` tool (e.g., `cat > file << EOF`) to clear values. NEVER use `Write` tool to clear — it displays "deleted N lines" in conversation, exposing credential content.
- **User Communication**: Always use business language. Never mention technical details (API names, step numbers, route_id, SSE events) to the user. Present results in terms they understand ("建模已完成", "求解结果已下载到 artifacts 目录").
- **File Path Communication**: After downloading artifacts, always tell the user the exact directory path. When asking for user-provided files (e.g., xlsx data), ask the user for the path — never hardcode or assume file locations.
- **Async Stage Artifacts**: After a stage reaches SUCCESS_UNCONFIRMED, artifacts may appear immediately in the SSE stream or may require a follow-up query. Check the `files` list in the createChat response: if empty, send `createChat` with `message="查询结果"` to retrieve artifact filenames. If non-empty, download directly without the extra query.
- **Stage Names**: `requirement_analyzer` → `modeling` → `data` → `solver` → `report`
- **Artifacts Directory**: Downloaded artifacts are saved to `artifacts/` (sibling of `scripts/`). Use `--clean-artifacts` to clear before running.
- **Proxy**: Python requests must set `proxies={"http": None, "https": None}` to bypass system proxy.
- **Test Call Results**: When showing CreateModelServiceTask results, either download output files and tell the user the directory, or provide the OBS download URLs. Never just say "files available" without actionable information.

## Deploy & Test Details (Steps 10-12)

### Step 10: CreateModelService — Deploy

```bash
hcloud OptVerse CreateModelService \
  --asset_id=<published_asset_id> \
  --name="<deployment_name>" \
  --infer_type=online \
  --platform=CCE \
  --request_mode=REAL_TIME \
  --service_config.instance_count=1 \
  --description="<description>" \
  --cli-region=cn-east-3
```

**Parameters:**
- `--asset_id`: The ID returned by PublishChat (Step 9).
- `--name`: Deployment name (must be unique, supports Chinese/letters/numbers/hyphens/underscores).
- `--infer_type`: `online` (online inference) or `edge` (edge inference).
- `--platform`: `CCE` (recommended) or `Modelarts`. **CCE works reliably; Modelarts may cause internal errors.**
- `--request_mode`: `REAL_TIME` (required, uppercase).
- `--service_config.instance_count`: Instance count (1-10, default 1).

**Output:** `{"service_id": "xxx", "service_name": "xxx", "status": "RUNNING", "api_url": "https://..."}`

**Verify deployment:**
```bash
hcloud OptVerse ShowModelServiceList --cli-region=cn-east-3
```

### Step 11: ShowModelServiceDetail — Get Request URL

```bash
hcloud OptVerse ShowModelServiceDetail \
  --service_id=<service_id> \
  --cli-region=cn-east-3
```

**Output:** Full service details JSON including `service_id`, `service_name`, `status`, `api_url`, `asset_id`, `chat_id`, `use_type`. Present the `api_url` to the user for API calls.

### Step 12: CreateModelServiceTask — Test Call

**Flow:**
1. ListArtifacts to find the data-stage JSON file (e.g., `模型数据_xxx_建模数据_xxx.json`)
2. DownloadFile to get the JSON content (base64-decoded)
3. CreateModelServiceTask with `--inputs.model_request` = JSON content serialized as string

```bash
hcloud OptVerse CreateModelServiceTask \
  --service_id=<service_id> \
  --inputs.model_request="<json_content_as_string>" \
  --cli-region=cn-east-3
```

**Output:** `{"id": "task_id", "type": "optverse", "status": "PENDING", "outputs": {}}`

**Query task result:**
```bash
hcloud OptVerse ShowModelServiceTask \
  --service_id=<service_id> \
  --task_id=<task_id> \
  --cli-region=cn-east-3
```

**Output:** Full task details including `status` (PENDING/RUNNING/SUCCESS/FAILED) and `outputs` (solution results with OBS download URLs).

**List all tasks:**
```bash
hcloud OptVerse ListModelServiceTasks \
  --service_id=<service_id> \
  --cli-region=cn-east-3
```
