# Verification Method

This document provides step-by-step verification procedures for the DevBox skill, **CLI first**, then the JS and Python SDK paths: environment, authentication, sandbox lifecycle, commands, files, PTY, Git, multi-sandbox management, and cleanup.

The quickest path is the bundled check script (CLI-first by default):

```bash
python3 scripts/devbox_check.py             # CLI: install + version + auth
python3 scripts/devbox_check.py --python    # Python SDK path (+ --smoke for e2e)
python3 scripts/devbox_check.py --js        # JS SDK path
bash examples/cli/quickstart.sh             # CLI end-to-end (needs auth + network)
```

## Verification Checklist

| # | Verification Item | Method | Expected Result |
|---|------------------|--------|-----------------|
| 0a | CLI installed | `devbox --version` | any version string (release or internal test build) |
| 0b | CLI auth | `devbox auth status` | logged-in state (after `auth login --api-key "$HW_DEVBOX_API_KEY"`) |
| 0c | CLI templates | `devbox tpl list` | >= 1 template |
| 0d | CLI sandbox e2e | `sbx create <tpl> -d` → `sbx ex <id> -- printf cli-ok` → `sbx kl <id>` | stdout `cli-ok`, clean kill |
| 1 | Python runtime >= 3.10 | `python3 --version` | 3.10+ |
| 2 | Python SDK installed | `python3 -c "import devbox; print(devbox.__version__)"` | 0.1.x |
| 3 | Node runtime >= 20.18.1 (JS path) | `node --version` | v20.18.1+ |
| 4 | JS SDK installed | `node -e "import('devbox-js-sdk').then(m=>console.log(m.VERSION))"` | 0.1.x |
| 5 | API Key configured | `echo ${DEVBOX_API_KEY:+set}` / `echo ${HW_DEVBOX_API_KEY:+set}` | `set` |
| 6 | Manager reachable / templates | `client.templates.list()` | >= 1 template |
| 7 | Sandbox creation | `Sandbox.create("default", timeout=120)` | `sandbox_id` non-empty |
| 8 | Command execution | `sandbox.commands.run("printf hi")` | `stdout == "hi"`, `exit_code == 0` |
| 9 | File write/read | `files.write` + `files.read` | round-trip equal |
| 10 | File upload/download | `files.upload` + `files.download` | local file matches |
| 11 | Background process + stdin | `run("cat", background=True, stdin=True)` | `wait().stdout` echoes stdin |
| 12 | Process reconnect | `commands.connect(pid)` | new output received |
| 13 | PTY session | `pty.start()` + `send_stdin("pwd\n")` | output contains a path |
| 14 | Git workflow | `git.clone` + `status` | exit 0 |
| 15 | Lifecycle: set_timeout/refresh | `set_timeout(60)` / `refresh(300)` | no error; `end_at` updated |
| 16 | Pause/resume | `pause()` + `resume()` | same `sandbox_id`, state running |
| 17 | Multi-sandbox list | `client.sandboxes.list()` | created sandbox present |
| 18 | Cleanup | `kill()` + `list()` | sandbox gone |

## Step 0: Verify the CLI (do this first)

```bash
export PATH="$HOME/.huawei/bin:$PATH"
devbox --version                   # 0.1.x version string
export HW_DEVBOX_API_KEY="devbox_xxx"
devbox auth status                 # logged-in state
devbox tpl list                    # >= 1 template
```

**If `devbox` is not installed:** run the install script (see [sdk-installation-guide.md](sdk-installation-guide.md)) or let `devbox_check.py` install it.

## Step 0b: CLI End-to-End (needs auth + network)

```bash
SBX=$(devbox sbx create <templateID> -d -t 300)
devbox sbx ex "$SBX" -- printf cli-ok     # expected stdout: cli-ok
devbox sbx kl "$SBX"                      # clean kill
```

Or run the bundled example: `bash examples/cli/quickstart.sh`.

## Step 1–2: Runtime and SDK Installation

```bash
python3 --version                                      # >= 3.10
python3 -c "import devbox; print(devbox.__version__)"  # 0.1.x; if missing -> sdk-installation-guide.md
node --version 2>/dev/null                             # >= 20.18.1 (JS path only)
```

## Step 3: Verify Authentication

```python
from devbox import DevBox, DevBoxError

try:
    with DevBox() as client:
        print("templates:", [t.name for t in client.templates.list()])
except DevBoxError as e:
    print("AUTH/NETWORK ERROR:", e.code, e.status_code, e.message)
    raise SystemExit(1)
```

Expected: a non-empty template list. 401/403 → re-issue the API Key ([iam-policies.md](iam-policies.md)).

## Step 4: Sandbox + Commands

```python
with Sandbox.create("default", timeout=120) as s:
    r = s.commands.run("printf 'hello from DevBox'")
    assert r.exit_code == 0 and r.stdout == "hello from DevBox"
    p = s.commands.run("cat", background=True, stdin=True)
    p.send_stdin("rt\n"); p.close_stdin()
    assert "rt" in p.wait().stdout
```

## Step 5: Files

```python
with Sandbox.create("default", timeout=120) as s:
    s.files.write("/tmp/v.txt", "data")
    assert s.files.read("/tmp/v.txt") == "data"
    s.files.make_dir("/tmp/w")
    assert any(e.name == "v.txt" for e in s.files.list("/tmp"))
    s.files.upload("/etc/hostname", "/tmp/up.txt")
    s.files.download("/tmp/up.txt", "/tmp/dl.txt")   # downloaded bytes must match
```

## Step 6: PTY

```python
with Sandbox.create("default", timeout=120) as s:
    session = s.pty.start()
    session.send_stdin("echo pty-ok\n"); session.send_stdin("exit\n")
    assert "pty-ok" in session.wait(check=False).stdout
```

(Directory watch: start the watcher BEFORE the change — see the Files section of SKILL.md.)

## Step 7: Git

```python
with Sandbox.create("default", timeout=300) as s:
    s.git.clone("https://github.com/octocat/Hello-World.git", "/tmp/hello", depth=1)
    assert s.git.status("/tmp/hello").exit_code == 0   # exit 127 -> template lacks git
```

## Step 8: Lifecycle

```python
s = Sandbox.create("default", timeout=120)      # no `with`: we keep it
s.set_timeout(600); s.refresh(900); s.pause(); s.close()
r = Sandbox.connect(s.sandbox_id, timeout=300)  # resume via connect
assert r.sandbox_id == s.sandbox_id
assert r.commands.run("echo alive").stdout.strip() == "alive"
r.kill()
```

## Step 9: Multi-Sandbox

```python
with DevBox() as client:
    s = client.sandboxes.create("default", timeout=120, metadata={"purpose": "verify"})
    page = client.sandboxes.list(limit=100)
    assert any(i.sandbox_id == s.sandbox_id and i.metadata.get("purpose") == "verify"
               for i in page.items)
    s.kill()
```

## Step 10: Cleanup Verification

```python
with DevBox() as client:
    for info in client.sandboxes.list().items:
        print(info.sandbox_id, info.state, info.metadata)
# no leftover verify/test sandboxes should remain running
```

## Complete Verification Script (Python)

```bash
#!/bin/bash
set -e
export DEVBOX_API_KEY="${DEVBOX_API_KEY:?DEVBOX_API_KEY must be set}"

python3 - <<'EOF'
from devbox import DevBox, Sandbox

# 1. templates
with DevBox() as client:
    templates = client.templates.list()
    assert templates, "no templates visible"

# 2. sandbox + commands + files
with Sandbox.create("default", timeout=120) as s:
    r = s.commands.run("printf verify-ok")
    assert r.stdout == "verify-ok", r
    s.files.write("/tmp/v.txt", "data")
    assert s.files.read("/tmp/v.txt") == "data"
    p = s.commands.run("cat", background=True, stdin=True)
    p.send_stdin("roundtrip\n"); p.close_stdin()
    assert "roundtrip" in p.wait().stdout

print("ALL CHECKS PASSED")
EOF
```

**Expected final output:**

```text
ALL CHECKS PASSED
```

Any assertion failure or `DevBoxError` means the corresponding capability is broken — consult [troubleshooting.md](troubleshooting.md).
