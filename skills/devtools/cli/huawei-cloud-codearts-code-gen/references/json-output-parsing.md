

**Parse JSON output:**

`codearts run --format json` emits **JSONL** — one JSON object per line. Parse it line by line.

| Event type | Action |
|----------|------|
| `step_start` | Record `sessionId` |
| `text` | The model's answer. **The generated code lives here**, inside markdown fenced code blocks in `.content`; extract the code from the fence (the fence language tag tells you the language). |
| `tool_use` | Records a tool invocation only. It does **not** carry generated file paths — do **not** read `.output.path`; that field is not produced. |
| `step_finish` | Check `.status` to decide whether the run completed successfully |
| `error` | Display the error message and stop |

**The CLI does NOT create or write any files.** The task description's `Output: <path>` line only
conveys where output is expected — it is a **hint**, and the CLI will neither create that directory
nor write that file. After parsing, the agent MUST write each extracted code block to disk itself
(creating parent directories as needed) and then report the paths it actually wrote. Never report a
path that was not really written.

---

## Task Description Tips

Clear descriptions improve generation quality:

```
Write a chat server in Python:
- Features: WebSocket real-time communication, user auth, message storage
- Tech stack: FastAPI + Redis + SQLite
- Output: /workspace/chat_server/
```

**`Output:` is a hint, not a CLI feature.** The CLI never creates directories or files, so the
`Output:` path in a task description only tells the model where the code is *intended* to live.
The agent is responsible for writing the generated code to disk afterwards. Prefer a path inside the
current workspace, state the intended file names in the task description, and attach existing files
you want the model to modify with `-f`:

```bash
bash scripts/codearts_run.sh run --format json -m "huaweicloud-maas/GLM-5.1" \
  -f ./src/server.py "add request validation and unit tests"
```
