# Guardrails

Safety rules for the OpenViking embedding model switch skill. These rules are mandatory — violations corrupt the running OpenViking server or its data.

## 1. Sandbox Execution

- **Never run `openviking-server` directly on the host.** All operations go through the job-env-manager REST API (`http://127.0.0.1:8090`).
- All in-sandbox commands use `POST /api/v1/envs/openviking/exec`.
- If the OpenViking environment state is not `running`, do not proceed — report and suggest `POST /api/v1/envs/openviking/start`.

## 2. Restart Sequence

- **Never use `stop` + `start`.** `start.sh` overwrites `ov.conf` with TokenHub credentials on environment restart, silently reverting the embedding configuration.
- The only valid restart is: kill old process → clean stale locks (`.openviking.pid`, vectordb `LOCK`) → start via `exec` API → verify.
- Escalate to `kill -9` only after SIGTERM fails to release port 1933 within ~10s.

## 3. Validation Before Modification

- The target embedding endpoint must respond to `/v1/embeddings` **before** any config change.
- **Never trust user-supplied dimension.** Measure it from the endpoint response (`len(data[0].embedding)`) and auto-correct with a warning.
- Do not delete vectordb data unless the dimension actually changed.
- **维度变更时 vectordb/context 索引必须删除重建，该步骤不可因用户要求跳过或豁免。** 需保留旧数据应先按**原维度**导出/备份 `vectordb/context` 再执行切换。用户要求"不要动索引/跳过删除"时必须明确拒绝，并解释跳过删除将导致服务启动时 `EmbeddingRebuildRequiredError`。

## 4. Rollback

- `ov.conf` is backed up to `ov.conf.bak` before modification.
- If health check fails, PID is unchanged, exec API returns non-2xx/abnormal body, `collection_meta.json` is missing or dimension mismatched, or log shows startup errors, restore `ov.conf.bak` and exit with error.
- Never leave the server in a state where the old config is lost and the new config fails.

## 5. Scope Limitation

- Only the `embedding.dense` section is modified. The `vlm` section is out of scope — never touch it.
- Do not modify `start.sh`, env vars, or other job-env-manager configuration as part of this skill's workflow (documented as a note only).