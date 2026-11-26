# DevBox CLI & SDK Installation Guide

Install in this order: **CLI first** (terminal tasks need nothing else), then the JS SDK or Python SDK only if embedding into code.

| Component | Artifact | Import | Runtime | Status |
|-----------|----------|--------|---------|--------|
| CLI | `devbox` binary | `devbox <command>` | none (static binary) | install script (GitHub/GitCode releases) or `make build` (Go >= 1.26) |
| Python SDK | `devbox-sdk` | `import devbox` | Python >= 3.10 | **on PyPI** — `pip install devbox-sdk` (0.1.0); source install is the pin-a-commit fallback |
| JS SDK | `devbox-js-sdk` | `import ... from "devbox-js-sdk"` | Node.js >= 20.18.1 | **on npm** — `npm install devbox-js-sdk` (0.1.0); source build is the pin-a-commit fallback |

Source of truth: `https://github.com/huaweicloud/devspace-devbox`, **`dev` branch** (`cli/`, `python-sdk/`, `js-sdk/` directories).

> **Branch note**: the repository's `main` branch is a placeholder. The GitCode mirror (`gitcode.com/huaweicloud/devspace-devbox`) currently carries only this empty `main` — but the **CLI release channel on GitCode is live** (`gitcode.com/CloudDeveloperDepartment/devbox/releases`, used by `install.sh`). Clone the GitHub `dev` branch for SDK sources. If `git clone` from GitHub fails with TLS/network errors, retry (transient failures are common) or configure a proxy: `export https_proxy=http://<proxy-host>:<proxy-port>`.

> **Moving-target note**: `dev` is the active development branch (v0.1.x, alpha) — the API may change at any time. This skill documents the 0.1.x snapshot. For reproducible installs, pin an exact commit (full clone, no `--depth`, so any SHA resolves):
>
> ```bash
> # DEVBOX_SDK_COMMIT=<commit-sha>  # or a tag, once tags exist
> git clone https://github.com/huaweicloud/devspace-devbox.git /tmp/devspace-devbox
> git -C /tmp/devspace-devbox checkout "$DEVBOX_SDK_COMMIT"
> python3 -m pip install /tmp/devspace-devbox/python-sdk
> ```
>
> The checker script honors the same options via environment variables: `DEVBOX_SDK_REF=<sha>` (pin a commit/tag), `DEVBOX_SDK_REPO_URL=<mirror>` (when GitHub is unreachable), `DEVBOX_SDK_BRANCH=<branch>`. After upgrading to a newer snapshot, re-run `devbox_check.py` to catch API drift against this skill's documented behavior.

## 1. CLI Installation (install this first)

> **Install method**: the CLI installs from **prebuilt release artifacts** via the official install script — no Go toolchain, no source clone. The script picks the right binary for your OS/arch (Linux/Darwin/Windows, amd64/arm64). Official guide: <https://huaweicloud.github.io/devspace-devbox/cli/install>.

### One-click install (any channel)

```bash
# OBS (CN-friendly) — two-step: download then run
curl -fsSL https://tools-artifact.developer.huaweicloud.com/sharedata/devbox/install.sh -o /tmp/devbox_install.sh
bash /tmp/devbox_install.sh

# GitCode
curl -fsSL https://gitcode.com/CloudDeveloperDepartment/devbox/releases/download/latest/install.sh -o /tmp/devbox_install.sh
bash /tmp/devbox_install.sh

# GitHub
curl -fsSL https://github.com/huaweicloud/devspace-devbox/releases/latest/download/install.sh -o /tmp/devbox_install.sh
bash /tmp/devbox_install.sh
```

PowerShell (any channel):

```powershell
irm https://tools-artifact.developer.huaweicloud.com/sharedata/devbox/install.ps1 | iex
irm https://gitcode.com/CloudDeveloperDepartment/devbox/releases/download/latest/install.ps1 | iex
irm https://github.com/huaweicloud/devspace-devbox/releases/latest/download/install.ps1 | iex
```

Options: `-v <version>` pins a version and `-u <url>` points at an alternate artifact mirror; the script verifies SHA256 checksums by default (see `bash install.sh --help` for all flags). `devbox_check.py` runs the same script non-interactively and honors `DEVBOX_CLI_VERSION` / `DEVBOX_CLI_INSTALL_URL` / `DEVBOX_CLI_ARTIFACT_URL`.

| What | Where |
|------|-------|
| binary | `~/.huawei/bin/devbox` |
| config/state | `~/.huawei/devbox/` (config.json fallback; API Key prefers the OS secure credential storage) |

### PATH

```bash
export PATH="$HOME/.huawei/bin:$PATH"       # add to ~/.bashrc / ~/.zshrc to persist
```

### Build from source (fallback only)

Only when no artifact channel is reachable (e.g. the release is not yet published on any channel). Requires Go >= 1.26:

```bash
git clone --depth 1 -b dev https://github.com/huaweicloud/devspace-devbox.git /tmp/devspace-devbox
cd /tmp/devspace-devbox/cli
make build VERSION=v1.0.0        # emits bin/devbox (version injected via ldflags)
mkdir -p ~/.huawei/bin && cp bin/devbox ~/.huawei/bin/
```

### Verify

```bash
export PATH="$HOME/.huawei/bin:$PATH"
devbox --version                 # expected: any 0.1.x version string
devbox auth status               # login state
```

**✅ Correct:** version string prints; `auth status` reports login state (or "not logged in" — expected before configuring a key).

**❌ Common failures:**

```text
devbox: command not found
# → add ~/.huawei/bin to PATH (see above)

curl: (connection) download failed
# → switch channel (-u <other-release-url>) or retry; GitCode channel is usually fastest in CN networks
```

## 2. Python SDK Installation

> **Install method**: `devbox-sdk` is published on **PyPI** (0.1.0) — `pip install devbox-sdk`. Install from source only when you must pin a `dev`-branch commit (see *Install from source* below).

### 1. Install from PyPI (recommended)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install devbox-sdk
```

Or directly with the system interpreter:

```bash
python3 -m pip install devbox-sdk
```

### 2. Verify

```bash
python3 -c "import devbox; print(devbox.__version__)"
# expected: 0.1.x
```

**❌ Common failures:**

```text
ModuleNotFoundError: No module named 'devbox'
# → wrong interpreter: use the same python that installed the package (.venv/bin/python)

ModuleNotFoundError: No module named 'httpx'
# → SDK present but dependency missing: reinstall into this interpreter
```

### Install from source (pin a commit)

Only when the release does not match the snapshot you target — clone the `dev` branch and install the package directory:

```bash
git clone --depth 1 -b dev https://github.com/huaweicloud/devspace-devbox.git /tmp/devspace-devbox
python3 -m pip install /tmp/devspace-devbox/python-sdk
```

### Development install

```bash
cd python-sdk
python -m pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy && pytest
```

## 3. JS SDK Installation

> **Install method**: `devbox-js-sdk` is published on **npm** (0.1.0) — `npm install devbox-js-sdk`. Build from source only when you must pin a `dev`-branch commit (the published tarball already ships `dist/`, which its `exports` map requires).

### 1. Install from npm (recommended)

```bash
cd /path/to/your-project
npm install devbox-js-sdk
```

Your project's `package.json` must support ESM (`"type": "module"`) or use dynamic `import()`.

### 2. Verify

```bash
node -e "import('devbox-js-sdk').then((m) => console.log(m.VERSION))"
# expected: 0.1.x
```

**❌ Common failures:**

```text
ERR_MODULE_NOT_FOUND: Cannot find module 'devbox-js-sdk'
# → not installed in this project: npm install devbox-js-sdk

Cannot use import statement outside a module
# → consuming project is CommonJS: set "type": "module" in package.json or use dynamic import()

engine-strict / unsupported engine errors
# → Node.js < 20.18.1; upgrade Node
```

### Build from source (pin a commit)

`dist/` is required by the package `exports` map, so a source install must be built first:

```bash
git clone --depth 1 -b dev https://github.com/huaweicloud/devspace-devbox.git /tmp/devspace-devbox
cd /tmp/devspace-devbox/js-sdk
npm ci          # installs dev dependencies (needs npm registry access)
npm run build   # emits dist/ (tsc)
cd /path/to/your-project && npm install /tmp/devspace-devbox/js-sdk
```

### Development checks

```bash
cd js-sdk
npm ci
npm run check    # lint + typecheck + unit tests + build
```

## API Key Configuration

The CLI and the SDKs read **different environment variables** — configure both if you use both channels:

```bash
export HW_DEVBOX_API_KEY="devbox_xxx"    # CLI (or: devbox auth login --api-key ...)
export DEVBOX_API_KEY="devbox_xxx"       # JS / Python SDKs
```

Windows CMD:

```bat
set "HW_DEVBOX_API_KEY=devbox_xxx"
set "DEVBOX_API_KEY=devbox_xxx"
```

Details and precedence rules: [iam-policies.md](iam-policies.md).

## Post-installation Smoke Test

```bash
python3 scripts/devbox_check.py            # CLI-first check (installs CLI when missing)
python3 scripts/devbox_check.py --python   # + Python SDK path
python3 scripts/devbox_check.py --js       # JS SDK path
```

With credentials and network access to the Manager, run the CLI end-to-end example:

```bash
bash examples/cli/quickstart.sh
```

## Uninstall

```bash
# CLI (STATE_BASE form keeps the removal scoped to this install)
# the second removal also drops stored credentials/config
STATE_BASE="$HOME"
rm -f "${STATE_BASE}/.huawei/bin/devbox"
rm -rf "${STATE_BASE}/.huawei/devbox"

# Python SDK
python3 -m pip uninstall devbox-sdk

# JS SDK (from the consuming project)
npm uninstall devbox-js-sdk

# remove the cloned source (adjust SRC_BASE if you cloned elsewhere)
SRC_BASE=/tmp
rm -rf "${SRC_BASE}/devspace-devbox"
```

## Troubleshooting Installation

### `git clone` from GitHub fails (TLS / timeout)

1. Retry — transient GnuTLS/EOF errors are common.
2. Configure a proxy: `export https_proxy=http://<proxy-host>:<proxy-port>`.
3. Note: the GitCode mirror carries only an empty `main` branch — it is **not** a usable substitute for the `dev` branch (CLI releases are the exception: `CloudDeveloperDepartment/devbox` on GitCode is the live release channel).

### Wrong branch cloned

`main` contains no SDK/CLI source. Always use `-b dev`.

### `npm install` resolves an old `devbox-js-sdk` (`0.0.0-stage`) or `ERR_MODULE_NOT_FOUND` on `dist/`

A stale registry mirror can lag behind npm. Check what the resolved version is:

```bash
npm view devbox-js-sdk version      # expected 0.1.0; 0.0.0-stage means a stale mirror
```

`0.0.0-stage` is an empty placeholder tarball (no `exports`/`dist`) — install from the official registry instead:

```bash
npm install devbox-js-sdk@0.1.0 --registry=https://registry.npmjs.org
```

### `npm ci` fails

- Check Node version: `node --version` (>= 20.18.1).
- Check npm registry connectivity or configure a mirror.
- Delete `node_modules` and re-run `npm install` only if `npm ci` reports lockfile drift.

### pip install fails

- `python3 -m pip install --upgrade pip` and retry.
- Corporate proxy: `export https_proxy=...` or `pip --proxy`.

### CLI build fails (`make build`)

- Go >= 1.26 required: `go version`.
- `make lint` needs golangci-lint (not required for `build`).

For runtime issues after installation, see [troubleshooting.md](troubleshooting.md).
