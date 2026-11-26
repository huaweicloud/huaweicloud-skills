# DevBox CLI Command Reference

`devbox` — DevBox sandbox management CLI (Go/cobra, command style modeled after E2B CLI). Version family: **0.1.x** (`dev` branch; release and internal test builds such as `test1106.002` share the same command surface). Chinese/English messages switch via `DEVBOX_LANG=zh` (default English).

## Global

| Option | Behavior |
|--------|----------|
| `-v, --verbose` | debug logs incl. API request/response bodies (API Key auto-masked) |
| `--version` | prints the version string only (any build) |
| `-f, --format pretty\|json` | output format where supported (`sbx ls`, `sbx in`, `tpl ls`) |
| `DEVBOX_LANG=zh` | Chinese messages |

Credential resolution order (all commands): command-line flag > `HW_DEVBOX_API_KEY` env > OS secure credential storage > `~/.huawei/devbox/config.json`.

> The Manager address is **injected at build time** (`internal/config.DefaultServer` = `https://devbox.developer.myhuaweicloud.com`, the production Manager) and is **not configurable at runtime**.

## Command groups

| Group | Alias | Purpose |
|-------|-------|---------|
| `devbox auth` | — | login, status, logout |
| `devbox sandbox` | `sbx` | full sandbox lifecycle + terminal + exec |
| `devbox template` | `tpl` | list templates |

## auth

```bash
devbox auth status                       # login state (+ user name when logged in)
devbox auth login                        # browser login (opens browser, local callback port)
devbox auth login --api-key <key>        # validate & save API Key (secure credential storage preferred)
devbox auth logout                       # clear stored API Key and user info
```

- `auth login` without `--api-key` reuses the local key (env > secure-credential-storage/config); only opens the browser when none is stored.
- API Key validation endpoint: `{AuthCheckDomain}/v1/api-keys/check` (build-time injected).

## sandbox (sbx)

### create (`cr <templateID>`)

```bash
devbox sbx create <templateID>                        # create AND enter interactive terminal
devbox sbx create <templateID> -d                     # detached: print sandbox ID only
devbox sbx create <tpl> -d -t 600                     # detached, 600 s lifetime
devbox sbx create <tpl> -c /root -e FOO=bar -t 600 \
    --lifecycle.ontimeout pause --lifecycle.autoresume
devbox sbx create <tpl> -b <build-id>                 # pin a template build
```

| Flag | Default | Notes |
|------|---------|-------|
| `-t, --timeout` | 300 | seconds, 10–86400; explicit 0 → error |
| `-m, --metadata key=value` | — | repeatable; business tags |
| `-e, --env KEY=VAL` | — | repeatable; **terminal-session-only** env vars (not persisted into the sandbox; gone after `exit`) |
| `-b, --build-id` | latest | pin template build |
| `--lifecycle.ontimeout` | kill | `kill` or `pause` |
| `--lifecycle.autoresume` | false | requires `ontimeout=pause` |
| `-d, --detach` | false | do not enter the terminal; print the sandbox ID |
| `-c, --cwd` | sandbox default | initial working directory (terminal session) |

Without `-d`, the local terminal becomes the sandbox shell; type `exit` to leave. The printed sandbox ID is a **36-char lowercase UUID** (letters/digits/hyphens) — required format for all `<sandboxID>` arguments.

### list (`ls`)

```bash
devbox sbx ls
devbox sbx ls -l 50 -s running,paused -m "user=abc"
devbox sbx ls -t <templateID-or-alias> --started-after <RFC3339> -o <order>
devbox sbx ls -f json                                 # raw API data
```

| Flag | Default | Notes |
|------|---------|-------|
| `-m, --metadata` | — | filter string |
| `-t, --template` | — | template ID or alias |
| `--started-after` | — | RFC3339 timestamp |
| `-o, --order` | — | server-defined ordering |
| `-s, --state` | — | comma list: `running,paused,stopped` |
| `-l, --limit` | 100 | page size |
| `-f, --format` | pretty | `pretty\|json` |

### info (`in <sandboxID>`)

```bash
devbox sbx in <sandboxID>            # sandbox details (pretty)
devbox sbx in <sandboxID> -f json    # raw API data
```

### kill (`kl [sandboxID...]`)

```bash
devbox sbx kl <id1> <id2>            # multiple IDs
devbox sbx kl --all                  # delete ALL matching running sandboxes
devbox sbx kill --all -s paused -m "user=abc"    # bulk with filters
```

`--all` is **destructive** — it deletes every sandbox matching the (optional) state/metadata filters. Verify with `sbx ls` first.

### pause / resume (`ps` / `rs`)

```bash
devbox sbx ps <sandboxID>            # pause: memory+disk snapshot, 24 h retention
devbox sbx rs <sandboxID> -t 600     # resume with new remaining lifetime
```

### connect (`cn <sandboxID>`)

```bash
devbox sbx cn <sandboxID>                          # enter interactive terminal
devbox sbx cn <sandboxID> -c /tmp -e MYTEST=123    # cwd + session env vars
devbox sbx cn <sandboxID> -t 600                   # also extends the sandbox TTL
```

Same interactive semantics as `create` without `-d`. Running/paused sandboxes only; paused sandboxes are resumed implicitly.

### timeout (`to <sandboxID>`)

```bash
devbox sbx to <sandboxID> -t 600     # reset remaining lifetime (may shorten)
```

### refresh (`rf <sandboxID>`)

```bash
devbox sbx rf <sandboxID> -d 300     # extend to AT LEAST now+300 s (never shortens)
```

### exec (`ex <sandboxID> <command...>`)

```bash
devbox sbx ex <sandboxID> -- uname -a
devbox sbx ex <sandboxID> -c /tmp -- ls -la
devbox sbx ex <sandboxID> -e GO_ENV=dev -- go version
devbox sbx ex -b <sandboxID> -- long-job     # background: prints the PID to stderr
devbox sbx ex <sandboxID> -- ./build.sh -b   # `-b` here belongs to ./build.sh, not to devbox
```

- Requires ≥ 2 args (sandboxID + at least one command word).
- **DevBox options must come before the sandbox ID**: everything after the ID is passed through to the remote command (`SetInterspersed(false)`), so `-b/-c/-e/-u` written after the ID reach the remote command instead of being parsed by `devbox`. Put `--` before the command when it starts with a flag-looking word.
- `-b/--background` runs the command in background and prints the PID to **stderr**; the remote process keeps running after the local command returns.
- `-c/--cwd`, `-e/--env` set the execution environment; `-u/--user` selects the sandbox user.

## template (tpl)

```bash
devbox tpl list
devbox tpl ls -f json
```

Prints template ID, name, aliases, and build info. `sbx create` accepts a template **ID or alias**.

> **`-f json` field names**: the CLI emits Go-style tags — `templateID`, `buildID`, `cpuCount`, `memoryMB`, `diskSizeMB` (capital `ID`). When scripting, match `templateID`/`buildID`; `template_id`/`build_id` (snake_case) are **Python SDK** field names — do not mix them.

```json
[
  {
    "templateID": "tpl-devbox-base-4g",
    "name": "devbox-base-4g",
    "aliases": ["base-4g"],
    "buildID": "devbox-base-4g-aarch64-20261106021421",
    "cpuCount": 2, "memoryMB": 4096, "diskSizeMB": 10240
  }
]
```

## Typical flows

```bash
# Quick one-off task
devbox auth status
SBX=$(devbox sbx create tpl-devbox-base-4g -d -t 600)
devbox sbx ex "$SBX" -- bash -lc 'cd /tmp && git clone https://example.com/repo.git'
devbox sbx kl "$SBX"

# Interactive development session
devbox sbx create tpl-devbox-base-4g -c /root -t 3600
# ... work inside the sandbox shell ...
exit

# Overnight pause instead of delete
devbox sbx ps <id>            # today
devbox sbx rs <id> -t 600     # tomorrow (within 24 h)
```

## Exit codes and errors

- Non-zero exit code on failure, localized message on stderr (no duplicated usage dump).
- `auth` failures point at the API Key (re-issue, then `devbox auth login --api-key "$HW_DEVBOX_API_KEY"`).
- `-v` prints masked request/response traces for support.
