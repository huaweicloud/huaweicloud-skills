# Acceptance Criteria

This document defines the pass/fail criteria for testing the DevBox sandbox skill (Python SDK `devbox-sdk` 0.1.x and JS SDK `devbox-js-sdk` 0.1.x, source `devspace-devbox` `dev` branch).

## Criteria Overview

| # | Category | Criteria | Verification Method |
|---|----------|----------|---------------------|
| AC-0a | Installation (CLI) | `devbox` binary installed and version prints | `devbox --version` |
| AC-0b | CLI auth | CLI login state OK | `devbox auth status` |
| AC-0c | CLI templates | templates listable | `devbox tpl list` |
| AC-0d | CLI end-to-end | create → exec → kill via CLI | `examples/cli/quickstart.sh` |
| AC-1 | Installation (Python) | `devbox` importable, version 0.1.x | `python3 -c "import devbox; print(devbox.__version__)"` |
| AC-2 | Installation (JS) | `devbox-js-sdk` importable, VERSION 0.1.x | `node -e "import('devbox-js-sdk').then(m=>console.log(m.VERSION))"` |
| AC-3 | Authentication | API Key accepted by Manager | `client.templates.list()` succeeds |
| AC-4 | Sandbox creation | Create returns a running sandbox | `Sandbox.create("default")` → `sandbox_id`, state running |
| AC-5 | Commands | Foreground command output correct | `commands.run("printf hi")` → stdout `hi`, exit 0 |
| AC-6 | Command options | envs/cwd/check work | `run("pwd", cwd="/tmp")`, `check=False` on failing cmd |
| AC-7 | Background processes | background + stdin + wait | echoed stdin in `wait().stdout` |
| AC-8 | Process management | list / signal / reconnect | `commands.list()`, `send_signal`, `commands.connect(pid)` |
| AC-9 | Files (text) | write/read round-trip | `files.write` + `files.read` equal |
| AC-10 | Files (structure) | list/stat/make_dir/move/remove | operations succeed |
| AC-11 | Files (transfer) | upload + download | downloaded file matches local source |
| AC-12 | File watch | events received and stream closes | `files.watch` yields ≥ 1 event |
| AC-13 | PTY | interactive session output | `pty.start` + `pwd` → path in stdout |
| AC-14 | Git | clone + status + config + add + commit | exit 0 each |
| AC-15 | Lifecycle | set_timeout / refresh | `end_at` extends; no error |
| AC-16 | Pause / resume | same sandbox resumes | `pause()` → `connect()`/`resume()` → same `sandbox_id` |
| AC-17 | Multi-sandbox | DevBox client list/create | created sandbox appears in `list()` |
| AC-18 | Async (Python) | AsyncSandbox full flow | async create/run/kill succeeds |
| AC-19 | Error handling | DevBoxError fields present | catch and inspect `code`/`status_code` |
| AC-20 | Security | no credentials in output/logs | review all output |
| AC-21 | Cleanup | test sandboxes deleted | `list()` shows no test sandboxes |

## Detailed Criteria

### AC-0a: CLI Installation

**Preconditions:** none.

**Steps:**

1. `export PATH="$HOME/.huawei/bin:$PATH"; devbox --version`.

**✅ Pass:** prints a version string (any build, e.g. `0.1.0-release` or internal test builds like `test1106.002`).

**❌ Fail:** command not found — install via script or source build ([sdk-installation-guide.md](sdk-installation-guide.md)).

### AC-0b: CLI Authentication

**Steps:**

1. `export HW_DEVBOX_API_KEY=...` then `devbox auth login --api-key "$HW_DEVBOX_API_KEY"` (or `devbox auth login` with a stored key).
2. `devbox auth status`.

**✅ Pass:** reports logged-in state.

**❌ Fail:** verify failed / not logged in — re-issue the API Key ([iam-policies.md](iam-policies.md)).

### AC-0c: CLI Templates

**Steps:** `devbox tpl list`.

**✅ Pass:** at least one template printed.

### AC-0d: CLI End-to-End

**Steps:** `bash examples/cli/quickstart.sh` — creates a detached sandbox, runs `printf cli-ok`, asserts output, kills the sandbox.

**✅ Pass:** script exits 0 with `CLI QUICKSTART PASSED`.

**❌ Fail:** any step errors — check auth (AC-0b), template availability (AC-0c), network.

### AC-1: Python SDK Installation

**Preconditions:** Python >= 3.10.

**Steps:**

1. `python3 -c "import devbox; print(devbox.__version__)"`.

**✅ Pass:** prints `0.1.x`.

**❌ Fail:** `ModuleNotFoundError` — install from the `devspace-devbox` `dev` branch per [sdk-installation-guide.md](sdk-installation-guide.md).

### AC-2: JS SDK Installation

**Preconditions:** Node.js >= 20.18.1.

**Steps:**

1. `node -e "import('devbox-js-sdk').then(m=>console.log(m.VERSION))"` inside the consuming project.

**✅ Pass:** prints `0.1.x`.

**❌ Fail:** module not found — `npm install devbox-js-sdk` in the consuming project (source fallback: `npm ci && npm run build`, then `npm install ./js-sdk`).

### AC-3: Authentication

**Steps:**

1. `export DEVBOX_API_KEY=...`
2. `with DevBox() as c: c.templates.list()`.

**✅ Pass:** non-empty template list (or a documented empty-template environment).

**❌ Fail:** `AuthenticationError` (401) / `PermissionDeniedError` (403) — see [iam-policies.md](iam-policies.md).

### AC-4: Sandbox Creation

**Steps:**

1. `sandbox = Sandbox.create("default", timeout=120)`
2. `sandbox.sandbox_id`, `sandbox.get_info().state`.

**✅ Pass:** non-empty ID; state `running`.

**❌ Fail:** `DevBoxError` on create (quota/network/template).

### AC-5: Commands

**Steps:**

1. `result = sandbox.commands.run("printf 'skill-ac5'")`.

**✅ Pass:** `result.exit_code == 0` and `result.stdout == "skill-ac5"`.

**❌ Fail:** non-zero exit, empty stdout, or exception.

### AC-6: Command Options

**Steps:**

1. `sandbox.commands.run("pwd", cwd="/tmp")` → stdout starts with `/tmp`.
2. `sandbox.commands.run("exit 3", check=False)` → `exit_code == 3`, no exception.
3. `sandbox.commands.run("exit 3")` → raises `CommandExitError` with `.result`.

**✅ Pass:** all three behave as described.

### AC-7: Background Processes

**Steps:**

1. `proc = sandbox.commands.run("cat", background=True, stdin=True)`
2. `proc.send_stdin("ac7\n"); proc.close_stdin(); result = proc.wait()`.

**✅ Pass:** `"ac7" in result.stdout`.

### AC-8: Process Management

**Steps:**

1. `procs = sandbox.commands.list()` — lists EnvD processes.
2. `sandbox.commands.send_signal(proc.pid, "SIGTERM")` on a sleeping background process.
3. `handle = sandbox.commands.connect(proc.pid)` — reconnects; only new output is received.

**✅ Pass:** all calls succeed; `send_signal` with an invalid signal name raises `ValueError`.

### AC-9: Files (Text)

**Steps:**

1. `sandbox.files.write("/tmp/ac9.txt", "roundtrip")`
2. `sandbox.files.read("/tmp/ac9.txt")`.

**✅ Pass:** read == written. Also verify `read_bytes` returns `b"roundtrip"`.

### AC-10: Files (Structure)

**Steps:**

1. `sandbox.files.make_dir("/tmp/ac10")`
2. `sandbox.files.move("/tmp/ac9.txt", "/tmp/ac10/ac9.txt")`
3. `sandbox.files.stat("/tmp/ac10/ac9.txt")`
4. `sandbox.files.list("/tmp/ac10")`
5. `sandbox.files.remove("/tmp/ac10/ac9.txt")`.

**✅ Pass:** each step succeeds; `exists("/tmp/ac10/ac9.txt")` is False after remove.

### AC-11: Files (Transfer)

**Steps:**

1. Create a local temp file with known bytes.
2. `sandbox.files.upload(local, "/tmp/ac11.bin")`
3. `sandbox.files.download("/tmp/ac11.bin", local2)`.

**✅ Pass:** `local2` bytes == original.

### AC-12: File Watch

**Steps:**

1. Start `watch("/tmp/ac12", { include_entry: false })` as the consumer.
2. From a background command, create a file after a short delay: `commands.run("sleep 1; printf x > /tmp/ac12/proof.txt", background=True)` — the watcher must be subscribed before the change.
3. Receive the event; close the generator/iterator.

**✅ Pass:** at least one event observed; no leaked connection errors after close.

**❌ Fail pattern to avoid:** writing the file BEFORE starting the watch — the event is not replayed and the loop may hang forever.

### AC-13: PTY

**Steps:**

1. `session = sandbox.pty.start(size=PtySize(rows=30, cols=100))`
2. `session.send_stdin("echo ac13\n")`, then `exit\n`
3. `out = session.wait(check=False).stdout`.

**✅ Pass:** `ac13` appears in output.

### AC-14: Git

**Steps:**

1. `sandbox.git.clone("https://github.com/octocat/Hello-World.git", "/tmp/ac14", depth=1)`
2. `sandbox.git.set_config("/tmp/ac14", "user.name", "ac")`
3. `sandbox.git.set_config("/tmp/ac14", "user.email", "ac@example.com")`
4. `sandbox.git.add("/tmp/ac14", ".")` and `sandbox.git.commit("/tmp/ac14", "ac14")` (after touching a file)
5. `sandbox.git.status("/tmp/ac14")`.

**✅ Pass:** every command exits 0. Push/pull with credentials are optional (need a throwaway remote).

### AC-15: Lifecycle

**Steps:**

1. Create with `timeout=120`.
2. `sandbox.set_timeout(300)` — `get_info().end_at` moves later.
3. `sandbox.refresh(600)` — end_at at least now+600.
4. `sandbox.set_timeout(10)` — shortens (sandbox auto-destroys shortly after).

**✅ Pass:** no errors; times change as described.

### AC-16: Pause / Resume

**Steps:**

1. `sandbox.pause()` → state `paused`; data-plane calls raise `ConflictError` until resume.
2. `sandbox.close()` (keep) → `resumed = Sandbox.connect(sid, timeout=300)`.
3. Verify same `sandbox_id` and that files written before pause are still readable.

**✅ Pass:** resumed sandbox works; original file content intact.

**Note:** pause/resume requires a deployed Gateway↔Manager resume path; in environments without it, this AC may be N/A.

### AC-17: Multi-Sandbox

**Steps:**

1. `with DevBox() as client:`
2. `client.sandboxes.create("default", timeout=120, metadata={"ac": "17"})`
3. `page = client.sandboxes.list(limit=100)` — find the sandbox by ID and `metadata`
4. `client.sandboxes.get(sid)`; kill.

**✅ Pass:** sandbox appears in the list with the given metadata; `get` returns info.

### AC-18: Async (Python)

**Steps:**

1. Run the async basic example (`examples/python/async_basic.py`).

**✅ Pass:** completes with expected output.

### AC-19: Error Handling

**Steps:**

1. Trigger an error (e.g., `Sandbox.connect("nonexistent-id")`).
2. Catch `DevBoxError`; inspect `code`, `status_code`, `message`, `request_id`.

**✅ Pass:** structured fields present (e.g. 404 `NotFoundError`).

### AC-20: Security

**Steps:**

1. Review all output produced during AC-1..AC-19.

**✅ Pass:** no API Key values, connect tokens, or Git credentials appear anywhere.

### AC-21: Cleanup

**Steps:**

1. After tests, `client.sandboxes.list()`; delete any leftover test sandboxes.

**✅ Pass:** no test sandboxes remain running/paused.

## Test Execution

Run the AC table top-down; each detailed section above defines the pass/fail criteria. Command sequences and the complete runnable script live in [verification-method.md](verification-method.md).
