# CLI Installation Guide

| CLI Tool | Purpose | Installation |
|----------|---------|-------------|
| `skill-quality-cli` | Quality telemetry for Huawei Cloud skills | Linux/macOS/Git Bash: `bash <SKILL_DIR>/scripts/ensure_cli.sh`; Windows PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File <SKILL_DIR>\scripts\ensure_cli.ps1` (ensured idempotently if absent) |
| `hcloud` | Huawei Cloud KooCLI | See [KooCLI installation](https://support.huaweicloud.com/cli/index.html). Scope commands with the global parameter `--cli-region`: `hcloud <Service> <Operation> --cli-region=<region>` |

## Windows / cross-platform installation (issue #929)

**Why this exists.** The official installer (`scripts/install_cli.sh`) maps only
`linux-x86_64` / `linux-arm64`, and the official manifest currently publishes only a
`linux-arm64` package — so **Windows x86_64 has no supported `skill-quality-cli`
installation entry**. On Chinese Windows the official `cli_entry.py` additionally
decodes child output with the locale codec (GBK), which raises `UnicodeDecodeError`
and loses Chinese output (issue #929).

### Entry points

| Shell / platform | Command |
|------------------|---------|
| Windows PowerShell | `powershell -NoProfile -ExecutionPolicy Bypass -File <SKILL_DIR>\scripts\ensure_cli.ps1` (optional `-InstallDir <dir>`, default `%USERPROFILE%\.local\bin`) |
| Windows Git Bash / MSYS2 / Cygwin | `bash <SKILL_DIR>/scripts/ensure_cli.sh` (detects `MINGW*`/`MSYS*`/`CYGWIN*` and delegates to `install_cli.py`) |
| Linux / macOS | `bash <SKILL_DIR>/scripts/ensure_cli.sh` (unchanged: reuses `install_cli.sh`) |
| Direct / any platform | `python <SKILL_DIR>/scripts/install_cli.py [--install-dir DIR] [--manifest-file FILE\|--manifest-url URL] [--package-dir DIR] [--platform TAG] [--no-python-fallback] [--force] [--dry-run] [--json]` |

`ensure_cli.sh` / `ensure_cli.ps1` are idempotent and warn-only: when installation
fails (network, manifest, checksum) they print a warning and exit 0, so the skill
keeps running in degraded mode. `install_cli.py` itself is fail-closed and exits
non-zero on any installation error.

- Default install directory: `~/.local/bin` (POSIX) / `%USERPROFILE%\.local\bin`
  (Windows), overridable with `--install-dir` or `SQC_INSTALL_DIR`.
- Default manifest: the official CLI API URL; override with `--manifest-url` /
  `SQC_MANIFEST_URL`, or use `--manifest-file <json>` for offline installs.

### Native package vs pure-Python fallback

- Platform has a native package → **native** mode (the packaged
  `skill-quality-cli.bin` plus the launchers is installed).
- No native package (e.g. Windows x86_64) → **`python-fallback`** mode: the
  installer extracts the pure-Python fallback (`cli_entry.py` + `cli_reporting.py`,
  placed under `skill-quality-cli.d/`) from the official `tar.gz` after its SHA256
  has been verified, and generates UTF-8-forcing launchers: `skill-quality-cli`
  (POSIX `sh`) and `skill-quality-cli.cmd` (Windows).
- Which launcher uses the native `.bin`: the `.bin` branch is only generated for the
  launcher of the platform the installation actually ran on. A native install writes
  `skill-quality-cli.bin`, and only that platform's launcher prefers it (falling back
  to `cli_entry.py`); the other launcher runs `cli_entry.py` directly. In
  `python-fallback` mode no `.bin` is installed at all, so both launchers run
  `cli_entry.py`:

  | Install | `skill-quality-cli` (sh) | `skill-quality-cli.cmd` |
  |---------|--------------------------|--------------------------|
  | native, Windows (`win32-*`) | runs `cli_entry.py` | `skill-quality-cli.bin`, else `cli_entry.py` |
  | native, POSIX (`linux-*` / `darwin-*`) | `skill-quality-cli.bin`, else `cli_entry.py` | runs `cli_entry.py` |
  | `python-fallback` | runs `cli_entry.py` (no `.bin` installed) | runs `cli_entry.py` (no `.bin` installed) |
- Verification is **fail-closed**: a manifest entry without `sha256`, or a checksum
  mismatch, refuses the installation.
- Extra flags: `--no-python-fallback` refuses to fall back (native-only); `--force`
  clears previous artifacts and reinstalls; `--dry-run` prints the install-plan JSON
  without downloading or writing anything; `--json` prints the result as JSON
  (otherwise a short human-readable summary); `--package-dir` reuses
  already-downloaded packages; `--platform` overrides the detected platform tag
  (e.g. `linux-x86_64`, `linux-arm64`, `darwin-arm64`, `win32-x86_64`).

### Why `PYTHONUTF8=1` is required

The official `cli_entry.py::cmd_run` runs the wrapped command as:

```python
proc = subprocess.run(command, env=env, capture_output=True, text=True)
```

`text=True` **without** `encoding` decodes the child's output with the locale
encoding — on Chinese Windows that is GBK/cp936. The wrapped scripts emit UTF-8
(Chinese output), so the decode raises `UnicodeDecodeError` and the Chinese text is
lost. `PYTHONUTF8=1` enables Python's UTF-8 mode (PEP 540), which makes the default
text encoding UTF-8; `PYTHONIOENCODING=utf-8` covers the standard streams.

`ensure_cli.sh`, `ensure_cli.ps1` and `hcloud-run.sh` export both variables before
invoking Python / `skill-quality-cli`, so running any of them is enough.

### Self-check

```bash
skill-quality-cli version
```

A working install prints the CLI version. If the command is missing, re-run the
entry point for your shell and make sure the install directory is on `PATH`
(`%USERPROFILE%\.local\bin` on Windows, `~/.local/bin` on POSIX).

### Provenance (read before upstreaming)

`scripts/install_cli.sh` and `scripts/ensure_cli.sh` were originally generated by
**`huawei-cloud-skill-quality-cli-inject`** (v3.0.0) and carry a "do not edit
manually" marker. `scripts/install_cli.py`, `scripts/ensure_cli.ps1`, the Windows
branch in `ensure_cli.sh` and the UTF-8 exports in `hcloud-run.sh` are **local
additions made by this skill to fix issue #929** — they are *not* an official
`inject` capability, and re-running the inject may overwrite the generated scripts.

## Manual upgrade

CLI no longer auto-upgrades（合规 v1.7+）。To upgrade to the latest version, run manually:

```bash
skill-quality-cli upgrade
```

## Disable telemetry (optional)

Telemetry is automatic (opt-out). To disable reporting entirely (rare), set:

```bash
export SKILL_QUALITY_REPORT=0
```

## Manual cold-start (fallback)

If `ensure_cli.sh` is unavailable, install manually:

```bash
bash <SKILL_DIR>/scripts/install_cli.sh
```

`install_cli.sh` is POSIX-only (it maps `linux-x86_64` / `linux-arm64` only). On
Windows use the cross-platform entry instead:

```bash
python <SKILL_DIR>/scripts/install_cli.py --install-dir "%USERPROFILE%\.local\bin"
```

The install script downloads the platform package, verifies it, and installs
`skill-quality-cli` into `~/.local/bin/` (POSIX) or `%USERPROFILE%\.local\bin`
(Windows). Upgrade afterwards with `skill-quality-cli upgrade`.

## KooCLI command format

KooCLI commands follow `hcloud <Service> <Operation> [--param=value ...]` and
should carry the global region parameter:

```bash
hcloud ECS ListServers --cli-region=cn-north-4
```

In this skill every `hcloud` call goes through `scripts/hcloud-run.sh`, which
injects `--cli-region` automatically from the `HW_CLI_REGION` environment
variable when set (and the command does not already pass it).
