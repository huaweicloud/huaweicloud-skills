# Agent Instructions
## OpenViking Long-Term Memory
You have OpenViking long-term memory integrated. Follow these protocols:
### Auto-Recall (at conversation start)
Before responding to the user's first message, check the session for an already-injected
`<openviking-context>` block; if it answers the question, use it and skip extra tool calls.
Otherwise call `search` with `mode="context"` for "what do I know about X" (the server
assembles a token-budgeted digest across memory types), or `find` for a fast ranked list.
Use retrieved context to inform responses; do not mention the retrieval process.
### Proactive Search (during tasks)
1. `search` with `mode="context"` — first choice for relevant past knowledge, error solutions, decisions.
2. `find` — fast ranked list when you want raw hits to triage yourself.
3. `read` — expand promising hits (viking:// URIs) before relying on them; an abstract may be stale.
4. `grep` / `glob` — exact text or filename matching when you know the literal string or file name.
### Auto-Capture (after meaningful exchanges)
After completing a task or learning important information:
1. `remember` — call this whenever the user shares preferences, important facts, decisions,
   or explicitly asks to remember/keep/save something (e.g. "记住", "记住这个", "请记住",
   "remember this", "帮我记一下"). This is the ONLY way to persist to long-term memory —
   there is no automatic session capture, so if you don't call `remember`, nothing is saved.
   Do not mirror routine back-and-forth chatter, but DO capture durable knowledge.
2. `add_resource` — import files, directories, URLs, or repos as durable knowledge.
   Processing is asynchronous; report that ingestion started rather than blocking.
3. Never echo credentials or surface private memories unrelated to the task.
### Repo Context
When starting work in a repository:
1. Call `add_resource` with the repo path to index it for context-aware assistance.
2. Use `search` to find prior work on the same codebase.
Do not wait to be asked — proactively use these tools for context-aware responses across sessions and projects.
