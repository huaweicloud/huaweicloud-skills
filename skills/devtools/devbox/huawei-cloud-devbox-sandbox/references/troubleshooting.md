# Troubleshooting Guide

Common issues and solutions when using the DevBox Python/JS SDKs (`devspace-devbox` `dev` branch, SDK 0.1.x).

## Table of Contents

1. [CLI Issues](#cli-issues)
2. [Installation Issues](#installation-issues)
3. [Authentication Issues](#authentication-issues)
4. [Sandbox Creation Issues](#sandbox-creation-issues)
5. [Command / Process Issues](#command--process-issues)
6. [File Issues](#file-issues)
7. [PTY Issues](#pty-issues)
8. [Git Issues](#git-issues)
8. [Lifecycle Issues (pause/resume/timeout)](#lifecycle-issues-pausetimeout)
10. [Network / TLS Issues](#network--tls-issues)
11. [Rate Limits and Quota](#rate-limits-and-quota)

---

## CLI Issues

### Problem: `command not found: devbox`

**Cause:** the binary is not in PATH or not installed.

**✅ Correct fix:**

```bash
ls -la ~/.huawei/bin/devbox || echo "not installed"
export PATH="$HOME/.huawei/bin:$PATH"
# or reinstall (two-step: download then run):
#   curl -fsSL https://gitcode.com/CloudDeveloperDepartment/devbox/releases/download/latest/install.sh -o /tmp/devbox_install.sh
#   bash /tmp/devbox_install.sh
```

### Problem: `auth status` shows not logged in / verify failed

**Cause:** no stored key and no `HW_DEVBOX_API_KEY` in the environment.

**Solution:** `devbox auth login --api-key "$HW_DEVBOX_API_KEY"` (env-injected) or interactive `devbox auth login` (browser). The key is stored in the OS secure credential storage when available, else `~/.huawei/devbox/config.json`.

### Problem: CLI works but SDK (or vice versa) reports auth failure

**Cause:** the CLI and the SDKs read **different env vars** (`HW_DEVBOX_API_KEY` vs `DEVBOX_API_KEY`). Both target the same production Manager (`devbox.developer.myhuaweicloud.com`), so the fix is usually the credential, not the address.

**Solution:** set both `HW_DEVBOX_API_KEY` (CLI) and `DEVBOX_API_KEY` (SDKs); see [iam-policies.md](iam-policies.md) for the full precedence rules.

### Problem: install script returns 404/403 on every channel

**Cause:** the prebuilt artifacts are not published to that channel (yet), or the channel is blocked by your network.

**Solution:** try another channel first — OBS is CN-friendly (`https://tools-artifact.developer.huaweicloud.com/sharedata/devbox/install.sh`); pin a version with `DEVBOX_CLI_VERSION=<version>`; point `DEVBOX_CLI_INSTALL_URL` at a reachable mirror of install.sh. If no channel works, build from source (Go >= 1.26): `git clone -b dev ... && cd cli && make build && cp bin/devbox ~/.huawei/bin/`. `devbox_check.py` tries all channels then falls back automatically.

### Problem: `sbx create` "hangs" the terminal

**Cause:** without `-d`, `sbx create` enters the **interactive terminal** — your terminal becomes the sandbox shell. This is expected behavior.

**Solution:** type `exit` to leave; use `sbx create <tpl> -d` in scripts to print the sandbox ID instead.

### Problem: `sbx ex` passes my flags to the remote command (or vice versa)

**Cause:** `exec` has interspersed flags disabled — parsing stops at the first non-flag word (the sandbox ID), so everything after the ID goes to the remote command.

**Solution:** put DevBox options **before the sandbox ID**, then `--` (optional but explicit) and the remote command:

```bash
devbox sbx ex -c /tmp <id> -- ./build.sh -b   # -c is devbox's; -b belongs to build.sh
devbox sbx ex -b <id> -- long-job             # -b here is devbox's background flag (prints PID to stderr)
```

---

## Installation Issues

### Problem: `ModuleNotFoundError: No module named 'devbox'`

**Cause:** The Python SDK is not installed for the interpreter being used.

**✅ Correct fix:**

```bash
python3 -m pip install devbox-sdk          # published on PyPI
python3 -c "import devbox; print(devbox.__version__)"
```

Source fallback (pin a `dev`-branch commit; `main` is an empty placeholder): `git clone --depth 1 -b dev https://github.com/huaweicloud/devspace-devbox.git` then `python3 -m pip install ./devspace-devbox/python-sdk`.

If using a venv, run the script with the same interpreter that installed the package (`.venv/bin/python`).

**❌ Incorrect fix:** installing with `python3 -m pip` but running the script with a different interpreter (system vs venv).

### Problem: `ERR_MODULE_NOT_FOUND` / `Cannot find module 'devbox-js-sdk'` (JS)

**Cause:** The JS SDK was not installed into the consuming project.

**Solution:**

```bash
cd /path/to/your-project && npm install devbox-js-sdk   # published on npm
```

Source-build fallback (pin a `dev`-branch commit): `cd devspace-devbox/js-sdk && npm ci && npm run build` (a source install needs `dist/`), then `npm install /path/to/devspace-devbox/js-sdk`.

The consuming project must be ESM (`"type": "module"`) or use dynamic `import()`.

### Problem: Engine errors on `npm ci` / unsupported Node

**Cause:** Node.js < 20.18.1.

**Solution:** upgrade Node (`nvm install 20` or distribution package).

### Problem: `git clone` from GitHub fails (GnuTLS / TLS / timeout)

**Cause:** network filtering or transient GitHub connectivity.

**Solution:**

1. Retry — transient failures are common.
2. Configure a proxy: `export https_proxy=http://<proxy-host>:<proxy-port>`.
3. Note: the GitCode mirror carries only an empty `main` branch — it is **not** a usable substitute for the `dev` branch.

---

## Authentication Issues

### Problem: `AuthenticationError` (401)

**Cause:** `DEVBOX_API_KEY` missing or invalid.

**Solution:**

1. `echo ${DEVBOX_API_KEY:+set}` — confirm it is set in the running process.
2. Re-issue the API Key at the DevBox management page and re-inject.
3. Never attempt to fix 401 by disabling TLS verification.

### Problem: `PermissionDeniedError` (403)

**Cause:** Key revoked or outside the allowed scope.

**Solution:** re-issue an API Key for the DevBox scenario; pause execution until the user confirms the new key is injected, then retry.

### Problem: `ConfigurationError: api_key is required`

**Cause:** neither parameter nor env var provided.

**Solution:**

```bash
export DEVBOX_API_KEY="devbox_xxx"
# or: Sandbox.create("default", api_key="devbox_xxx")
```

---

## Sandbox Creation Issues

### Problem: create fails with quota / 429

**Cause:** too many running or paused sandboxes for the account.

**Solution:**

1. `client.sandboxes.list(states=["running"])` — inspect usage (`Page.total`).
2. Delete unneeded sandboxes (`kill()`).
3. Quota may be shared across the account even if the sandboxes are not visible to this client.
4. If nothing is cleanable and the limit persists, collect `request_id` and contact support.

### Problem: create times out or returns a network error — did it succeed?

**Cause:** the request may have reached the server before failing.

**✅ Correct approach:**

```python
try:
    sandbox = Sandbox.create("default", timeout=120)
except DevBoxError:
    with DevBox() as client:      # check before re-creating
        recent = [i for i in client.sandboxes.list().items if i.state == "running"]
    # ... decide, avoid duplicate sandboxes
```

**❌ Incorrect approach:** blindly retrying `create()` — may double resource usage.

### Problem: `NotFoundError` connecting to an existing sandbox

**Cause:** the sandbox expired or was deleted. Deleted sandboxes cannot be recovered; paused sandboxes can be resumed within 24 h.

**Solution:** verify with `client.sandboxes.get(id)`; create a new sandbox if gone.

---

## Command / Process Issues

### Problem: command has no output

**Checks:**

1. Does the command actually write to stdout/stderr?
2. Is the program buffering output? (Python: use `python -u` or `flush=True`.)
3. Is it waiting for stdin? Use `stdin=True` and `close_stdin()`.
4. Background commands: output is collected via `wait()`, not at `run()`.
5. `disconnect()` does not stop the remote process — the process may still be running.

### Problem: reconnected process misses earlier output

**Cause:** by design — `commands.connect(pid)` receives only output produced after re-subscribing; there is no replay.

**Solution:** write important output to files (`files.write`) and read them back.

### Problem: `CommandExitError` on every failing command

**Cause:** `check=True` is the default.

**Solution:** pass `check=False` (Python) / `{ check: false }` (JS) to inspect `exit_code`/`stderr` directly.

### Problem: `ConfigurationError: user switching is not supported`

**Cause:** the `user` parameter was passed; current EnvD does not support it.

**Solution:** remove the `user` parameter — commands run as the sandbox's default system user.

### Problem: `ValueError` on commands

**Checks:** blank command string, invalid signal name (only `SIGTERM`/`SIGKILL`), `pid < 1`.

---

## File Issues

### Problem: `ValueError: sandbox paths must be absolute`

**Cause:** a relative path was passed.

**Solution:** always use `/`-rooted paths inside the sandbox.

### Problem: `NotFoundError` on read/stat

**Cause:** the file does not exist (or was removed after pause/resume on a node that lost disk state — should not normally happen).

**Solution:** check with `files.exists(path)` first.

### Problem: watch leaks connections

**Cause:** the watch generator/iterator was not closed.

**Solution (Python):**

```python
from contextlib import closing
with closing(sandbox.files.watch("/tmp")) as events:
    for event in events:
        ...
```

**Solution (JS):** `break`/`return` out of the `for await` loop.

### Problem: uploaded binary file is corrupted

**Cause:** text encoding was used for binary data.

**Solution:** use `read_bytes` / write `bytes` (Python) or `Uint8Array` + `readBytes` (JS).

---

## PTY Issues

### Problem: PTY output contains control characters

**Cause:** terminal escape sequences are part of PTY streams — expected.

**Solution:** filter for display only; the SDK returns the raw stream.

### Problem: PTY handle no longer accepts input

**Cause:** `wait()` already returned the exit result.

**Solution:** start a new session; `exit` ends the remote shell by design.

### Problem: locale/garbled characters

**Solution:** pass `envs` to `pty.start()` (e.g. `LANG=en_US.UTF-8`) — the SDK does not force a locale the image may not have installed.

---

## Git Issues

### Problem: exit code 127 on git commands

**Cause:** `git` is not installed in the sandbox template image.

**Solution:** pick a template that includes git, or install it first (`commands.run("apt-get install -y git")` if the image permits).

### Problem: cannot access GitHub/GitLab from inside the sandbox

**Cause:** DNS, network reachability, and repository permissions depend on the sandbox runtime — local machine connectivity does not imply sandbox connectivity.

**Solution:** test inside the sandbox (`commands.run("curl -sI https://github.com")`); for private repos pass `GitCredentials` (token) — they are injected as env vars, never persisted.

### Problem: push/pull fail with auth errors

**Solution:** use a token: `GitCredentials(username=..., password=os.environ["GIT_TOKEN"])`; `GIT_TERMINAL_PROMPT=0` is set by the SDK so git never hangs on prompts.

---

## Lifecycle Issues (pause/timeout)

### Problem: pause or resume is slow

**Cause:** pause saves memory+disk state; duration scales with memory, disk and load; auto-pause also has scheduling delay.

**Solution:** check state via `get_info()` instead of assuming failure from a slow call. Do not conclude "not executed" from a client timeout alone.

### Problem: `ConflictError: sandbox is paused`

**Cause:** data-plane calls on a paused sandbox.

**Solution:** call `resume()` or `Sandbox.connect(id)` first. With `lifecycle.auto_resume=True`, a compatible Gateway wakes the sandbox on the first data-plane request.

### Problem: sandbox disappeared before job finished

**Cause:** lifetime expired (default 300 s); background cleanup is asynchronous.

**Solution:** schedule `refresh()` for long jobs (e.g. a timer/loop), or create with a larger `timeout` (max 86400 s). `is_running()` may briefly lag during cleanup.

### Problem: `set_timeout(10)` didn't kill instantly

**Cause:** cleanup runs asynchronously.

**Solution:** poll `is_running()`/`get_info()`; expect eventual `stopped`/`NotFoundError`.

### Problem: old handles broken after resume

**Cause:** by design — old network streams are not guaranteed valid after pause/resume.

**Solution:** reconnect processes by PID, re-establish file watches; the SDK does not replay commands.

---

## Network / TLS Issues

### Problem: `ServiceUnavailableError` / unable to reach the service

**Checks:**

1. Manager URL correct (`DEVBOX_API_URL`, default `https://devbox.developer.myhuaweicloud.com`).
2. DNS resolution and HTTPS (443) egress allowed.
3. Proxy needed? `export https_proxy=...`.
4. For local gateway testing: `DEVBOX_GATEWAY_URL` template must contain `{tunnel_id}`.

### Problem: TLS certificate verification failed against the Gateway

**Cause:** temporary debug environment without a proper certificate on the data plane.

**Solution (debug only):**

```bash
export DEVBOX_GATEWAY_SKIP_TLS_VERIFY=true   # skips Gateway certificate verification; remove after debugging
```

This does not affect Manager verification, cannot fix DNS or auth problems, and exposes the connect token and sandbox data to interception. Never use in production.

---

## Rate Limits and Quota

### Problem: 429 / rate limited

**Solution:** honor `RateLimitError.retry_after`, reduce request frequency, check running-sandbox quota. Do not blindly re-submit commands or file writes whose outcome is unknown.

### Problem: quota exhausted on create

**Solution:** list running sandboxes (`client.sandboxes.list(states=["running"])`) and delete unused ones (`kill()`); quota may be shared across the account. If nothing is cleanable and the limit persists, collect `request_id` and contact support.

---

## Getting Help

1. Enable more diagnostics: catch `DevBoxError` and record `code`, `status_code`, `request_id`, `message` (and for commands, `exit_code` + sanitized stdout/stderr).
2. Reproduce with the smallest example (`examples/python/basic.py`).
3. Collect versions: SDK (`devbox.__version__` / `VERSION`), Python/Node version, timestamps, method names.
4. **Never include** API Keys, connect tokens, Git credentials, or sensitive file contents in issue reports.
5. Report issues to the DevBox team via the `devspace-devbox` repository issue tracker.
