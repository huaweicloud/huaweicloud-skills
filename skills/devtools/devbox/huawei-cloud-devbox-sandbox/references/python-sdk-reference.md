# DevBox Python SDK Reference

Package `devbox-sdk` (import name `devbox`), version 0.1.x. Requires Python 3.10+, depends on `httpx>=0.27,<1`.

## Public API (`from devbox import ...`)

| Export | Kind | Purpose |
|--------|------|---------|
| `Sandbox` | class | Main sync entry point for one sandbox |
| `Envd` / `AsyncEnvd` | class | EnvD runtime metrics/envs/health (sync/async) |
| `EnvdHealth` | dataclass | `envd_version` |
| `EnvdMetrics` | dataclass | `timestamp`, `cpu_count`, `cpu_used_pct`, `mem_total`, `mem_used`, `mem_cache`, `disk_total`, `disk_used`, `oom_kills` (all required) plus optional `cpu_possible`, `cpu_target`, `cpu_target_attempts`, `cpu_write_pending_ms` |
| `OomKill` | dataclass | `seq`, `process` |
| `AsyncSandbox` | class | Async counterpart |
| `DevBox` | class | Reusable client managing multiple sandboxes |
| `AsyncDevBox` | class | Async counterpart |
| `CommandHandle` / `AsyncCommandHandle` | class | Running background process / PTY session |
| `CommandResult` | dataclass | `exit_code`, `stdout`, `stderr`, `pid` |
| `SandboxInfo` | dataclass | `sandbox_id`, `template_id`, `state`, `started_at`, `end_at`, `cpu_count`, `memory_mb`, `disk_size_mb`, `metadata`, `lifecycle` |
| `TemplateInfo` | dataclass | `template_id`, `name`, `aliases`, `build_id`, `cpu_count`, `memory_mb`, `disk_size_mb` |
| `SandboxLifecycle` | dataclass | `on_timeout` (`"kill"`/`"pause"`), `auto_resume` (bool) |
| `SandboxState` | enum | `RUNNING/PAUSED/STOPPED` (transient states trimmed in 0.1.x dev) |
| `FileInfo` | dataclass | `name`, `path`, `type`, `size`, `mode`, `permissions`, `owner`, `group`, `modified_at`, `symlink_target` |
| `FileType` | enum | `FILE/DIRECTORY/SYMLINK` |
| `FileWatchEvent` | dataclass | `name`, `type`, `path`, `entry` |
| `ProcessInfo` | dataclass | `pid`, `command`, `running`, `started_at` |
| `PtySize` | dataclass | `rows=24`, `cols=80` (must be >= 1) |
| `Page[T]` | dataclass | `items`, `next_token`, `total` |
| `GitCredentials` | dataclass | `username`, `password` (repr-hidden) |
| `DevBoxError` + subclasses | exceptions | see [Errors](#errors) |

## Configuration

| Setting | Env var | Default | Notes |
|---------|---------|---------|-------|
| API Key | `DEVBOX_API_KEY` or `E2B_API_KEY` | required | also `api_key=` parameter |
| Manager URL | `DEVBOX_API_URL` or `E2B_API_URL` | `https://devbox.developer.myhuaweicloud.com` | https only (http for localhost only) |
| Gateway URL override | `DEVBOX_GATEWAY_URL` | Manager-returned address | template may contain `{tunnel_id}` and `{port}` |
| Request timeout | `request_timeout=` param | Manager 150 s, data plane 30 s | one value overrides both |
| Gateway TLS skip | `DEVBOX_GATEWAY_SKIP_TLS_VERIFY` | off | **debug only** |

Constructor/`create()` parameters take precedence over environment variables.

## Sandbox (sync)

### Creation & Connection

```python
Sandbox.create(
    template="default",          # template ID, name, or alias
    *,
    timeout=300,                # seconds, 10..86400
    envs=None,                  # Mapping[str, str]
    metadata=None,              # Mapping[str, str]
    build_id=None,              # pin a template build
    lifecycle=None,             # SandboxLifecycle(on_timeout="pause", auto_resume=True)
    api_key=None, api_url=None, gateway_url=None,
    request_timeout=None, headers=None,
) -> Sandbox

Sandbox.connect(sandbox_id, *, timeout=300, ...) -> Sandbox
# Fetches Gateway credentials from the Manager (resumes a paused sandbox);
# does NOT itself open a data-plane connection. Deleted sandboxes cannot be reconnected.
```

`with Sandbox.create(...) as s:` deletes (`kill()`) the sandbox on exit. Sandboxes obtained from `Sandbox.create()` / `Sandbox.connect()` own their control transport and close it in `close()`; sandboxes obtained from a `DevBox` client do not (the client owns it).

### Lifecycle

| Method | Behavior |
|--------|----------|
| `sandbox_id` | property — sandbox ID |
| `info` | property — cached `SandboxInfo` |
| `get_info() -> SandboxInfo` | refresh state from Manager |
| `is_running() -> bool` | Manager-reported state is RUNNING (not a data-plane probe); `NotFoundError` → False |
| `set_timeout(timeout)` | **reset** remaining lifetime (can shorten); 10–86400 s |
| `refresh(duration=300)` | extend to **at least** `duration` remaining; never shortens |
| `pause()` | memory+disk snapshot, closes data-plane connections; retained 24 h; context exit still kills — call `close()` to keep |
| `resume(*, timeout=300) -> Sandbox` | resume on the same object; replaces the connect token |
| `kill() -> bool` | delete sandbox; `False` if already deleted/expired (idempotent cleanup) |
| `close()` | close local connections only |

### Runtime facets

`sandbox.commands` → `Commands`; `sandbox.files` → `Filesystem`; `sandbox.pty` → `Pty`; `sandbox.git` → `Git`; `sandbox.envd` → `Envd`.

## Envd (runtime diagnostics)

```python
metrics = sandbox.envd.get_metrics()   # EnvdMetrics: cpu_count, cpu_used_pct,
                                       # mem_total/mem_used/mem_cache, disk_total/disk_used,
                                       # oom_kills (tuple[OomKill(seq, process)]) and optional
                                       # cpu_possible/cpu_target/cpu_target_attempts/
                                       # cpu_write_pending_ms (None when envd omits them)
envs = sandbox.envd.get_envs()         # EnvD's current environment variables
health = sandbox.envd.health()         # EnvdHealth(envd_version="...") via X-Envd-Version
```

Direct probes of EnvD's own REST endpoints (`/metrics`, `/envs`, `/health`) — useful for monitoring and diagnostics. Wire keys are snake_case; `AsyncEnvd` mirrors all methods with `await`.

## Commands

```python
Commands.run(
    command, *,
    background=False,           # True -> CommandHandle
    envs=None, cwd=None, user=None,   # user unsupported -> ConfigurationError
    stdin=False,                # allocate stdin for the process
    timeout=60,                 # seconds; also enforced server-side
    on_stdout=None, on_stderr=None,   # callables str -> None (foreground only)
    check=True,                 # raise CommandExitError on non-zero exit
) -> CommandResult | CommandHandle

Commands.connect(pid, *, timeout=60) -> CommandHandle   # re-attach by PID
Commands.list() -> tuple[ProcessInfo, ...]              # EnvD-managed processes
Commands.send_stdin(pid, data)                          # str or bytes
Commands.close_stdin(pid)
Commands.send_signal(pid, "SIGTERM" | "SIGKILL")
```

`CommandHandle`:

| Method | Behavior |
|--------|----------|
| `.pid` | process ID |
| `wait(*, on_stdout, on_stderr, check=True) -> CommandResult` | collect output until exit |
| `send_stdin(data)` / `close_stdin()` | feed the process |
| `send_signal("SIGTERM"\|"SIGKILL")` / `kill()` | signal the process |
| `disconnect()` | detach local stream only — remote process keeps running |

Reconnect notes: `commands.connect(pid)` receives only output produced **after** re-subscribing — no replay. Commands execute as `/bin/bash -l -c <command>` under the sandbox's default user.

## Filesystem

| Method | Notes |
|--------|-------|
| `read(path, *, encoding="utf-8") -> str` | text read |
| `read_bytes(path) -> bytes` | binary read |
| `write(path, data, *, encoding="utf-8") -> FileInfo` | create/replace (str or bytes) |
| `write_batch(files: Mapping[str, str\|bytes]) -> tuple[FileInfo, ...]` | sequential writes |
| `list(path, *, depth=1) -> tuple[FileInfo, ...]` | depth >= 1 |
| `stat(path) -> FileInfo` | metadata |
| `exists(path) -> bool` | via stat; `NotFoundError` → False |
| `make_dir(path)` | create directory |
| `move(source, destination)` | move/rename |
| `remove(path)` | delete file or directory |
| `upload(local_path, remote_path) -> FileInfo` | local → sandbox |
| `download(remote_path, local_path) -> Path` | sandbox → local |
| `watch(path, *, recursive=False, include_entry=True) -> Generator[FileWatchEvent]` | must be closed (e.g. `contextlib.closing`) to release the data-plane connection |

> **Watch timing**: start the watcher BEFORE the change happens — events produced before the subscription exists are not replayed. Official pattern: start a background command `sleep 1; printf done > /dir/done.txt`, then iterate the watch generator; the 1 s buffer lets the subscription establish first.

All sandbox paths must be **absolute** (`/...`) or `ValueError` is raised.

## PTY

```python
sandbox.pty.start(
    command="/bin/bash", *,
    size=None,                  # PtySize(rows, cols); default PtySize(24, 80)
    envs=None, cwd=None, user=None,
) -> CommandHandle              # input goes to the pty stream

sandbox.pty.connect(pid, *, timeout=None) -> CommandHandle
sandbox.pty.resize(pid, PtySize(rows=40, cols=120))
```

- `TERM=xterm-256color` is set by default; pass `envs` to override locale.
- Send `exit\n` to end the remote shell; `disconnect()` only detaches the output stream.
- After `wait()` returned, the handle no longer accepts input.

## Git

```python
Git.clone(url, path, *, branch=None, depth=None, credentials=None, timeout=300)
Git.status(repository)                       # --short --branch
Git.checkout(repository, reference, *, create=False)
Git.add(repository, paths="." )              # str or sequence
Git.commit(repository, message)
Git.pull(repository, *, remote="origin", branch=None, credentials=None, timeout=300)
Git.push(repository, *, remote="origin", branch=None, credentials=None, timeout=300)
Git.set_config(repository, key, value)
```

`GitCredentials(username=..., password=...)` — injected as `DEVBOX_GIT_USERNAME` / `DEVBOX_GIT_PASSWORD` env vars with `GIT_TERMINAL_PROMPT=0`; a temporary credential helper reads them. Nothing is persisted in the sandbox's `.git/config`.

## DevBox client (multi-sandbox)

```python
with DevBox(api_key=None, api_url=None, gateway_url=None,
            request_timeout=None, headers=None, http_transport=None) as client:
    client.templates.list() -> list[TemplateInfo]
    client.sandboxes.create(template="default", *, timeout=300, envs=None,
                            metadata=None, build_id=None, lifecycle=None) -> Sandbox
    client.sandboxes.connect(sandbox_id, *, timeout=300) -> Sandbox
    client.sandboxes.get(sandbox_id) -> SandboxInfo
    client.sandboxes.list(*, template=None, metadata=None, states=(), limit=None,
                          next_token=None, started_after=None, order=None) -> Page[SandboxInfo]
```

- `DevBox.close()` closes only the control connection — each `Sandbox` must be closed separately.
- `list()` filters: `template`, `metadata`, `states`, `started_after` (RFC3339), `order` (`asc`/`desc`); `limit` 0–1000 (0 = no limit); pagination via `Page.next_token` (header `X-Next-Token`); `Page.total` from `X-Total-Running`.
- `states` accepts `SandboxState` members or raw strings.

## Async API

`AsyncSandbox`, `AsyncDevBox`, `AsyncCommandHandle` mirror the sync API exactly:

```python
async with await AsyncSandbox.create("default") as sandbox:
    result = await sandbox.commands.run("uname -a")
    process = await sandbox.commands.run("cat", background=True, stdin=True)
    await process.send_stdin("hi\n")
    await process.close_stdin()
    print((await process.wait()).stdout)

async for event in sandbox.files.watch("/tmp"):
    ...   # async generator; aclose() releases the stream
```

## Errors

`DevBoxError(message, *, code, status_code, target, details, request_id, retry_after)`; `str(e)` appends `[code]`.

| Exception | HTTP | When |
|-----------|------|------|
| `ConfigurationError` | — | missing API key, bad URL, unsupported `user` |
| `ValidationError` | 400/422 | invalid parameters |
| `AuthenticationError` | 401 | missing/invalid API Key |
| `PermissionDeniedError` | 403 | no permission |
| `NotFoundError` | 404 | sandbox/path/process not found |
| `ConflictError` | 409 | state conflicts (`already_killed`, paused sandbox, etc.) |
| `RateLimitError` | 429 | quota/rate limit; check `retry_after` |
| `RequestTimeoutError` | 408 | request timeout |
| `ServiceUnavailableError` | 5xx | server/network unavailable |
| `ProtocolError` | — | malformed server response |
| `CommandExitError` | — | non-zero exit (check=True); carries `.result` |

```python
from devbox import DevBoxError, CommandExitError, RateLimitError, Sandbox

try:
    result = Sandbox.create("default").commands.run("false")
except CommandExitError as e:
    print(e.result.exit_code, e.result.stderr)
except DevBoxError as e:
    print(e.code, e.status_code, e.request_id, e.message)
```

## Timeout & Retry Semantics (summary)

- Manager requests: 150 s default; data-plane HTTP: 30 s default; both become `request_timeout` when set.
- Command `timeout` (default 60 s) is a **connect-protocol** timeout enforced server-side too; it is per network phase, not a wall-clock cap for the whole operation.
- `timeout`/`duration` values are seconds; lifecycle timeout bounds: 10–86400.
- Request timeouts never change sandbox lifetime.
- Transport retries: connection-establishment failures only (`httpx.ConnectError`/`ConnectTimeout`), two retries with 0.1 s / 0.2 s delays. Rate limits, server errors, and possibly-delivered writes are never retried.

## Install & Verify

```bash
python3 -m venv .venv && .venv/bin/python -m pip install devbox-sdk   # published on PyPI
.venv/bin/python -c "import devbox; print(devbox.__version__)"
```

Source fallback (pin a `dev`-branch commit): `git clone -b dev https://github.com/huaweicloud/devspace-devbox.git`, then `pip install ./devspace-devbox/python-sdk`.

See [sdk-installation-guide.md](sdk-installation-guide.md) for details and the JS equivalent.
