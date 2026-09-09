# Prerequisites

This section covers everything needed before running `hcloud` calls: hcloud installation, credential injection, required environment variables, and basic checks.

> **Quick start**: before initializing a task, you can run [`scripts/precheck.sh`](../scripts/precheck.sh) (bash) or [`scripts/precheck.ps1`](../scripts/precheck.ps1) (PowerShell) for a one-shot environment check (covers KooCLI install, version, credentials, region, connectivity). See [SKILL.md §1.0](../SKILL.md) for details. **The sections below describe what `precheck` does NOT cover** (Python interpreter, IAM permissions, agency / bucket authorization).

> **⚠️ Execution method (required reading)**: all commands (including but not limited to: business API `hcloud …` calls, local helper tool calls like `scripts/cache.py` / `scripts/zip_helper.py`, pre-task checks, directory / file reads) MUST go through `skill action=exec`, unless the current agent does not support `skill action=exec` — in that case fall back to direct shell execution.

## 0. Pre-configured values (agent retrieves automatically, **does NOT ask user**)

When the agent starts a task, the following parameters should be **fetched directly** rather than asked from the user:

| Parameter | Source |
|---|---|
| `--project_id` | `project_id` from `hcloud configure show` output; or env var `HUAWEI_CLOUD_PROJECT_ID` |
| `--cli-region` | `region` from `hcloud configure show` output; or env var `HUAWEI_CLOUD_REGION` |
| `--algorithm_id` (existing project) | Local cache `.stats/algorithm_id.csv`, indexed by `algorithm_name`; preferably [`scripts/cache.py`](../scripts/cache.py) `ensure-algorithm` |
| `--evolve_task_id` (existing task) | Local cache `.stats/task_id.csv`, indexed by `algorithm_id`; preferably `scripts/cache.py` `ensure-task` |
| `--last_update_time` | Agent runs `hcloud OptVerse ShowAlgorithm` to fetch `content_update_at`, then `scripts/cache.py put-lut --lut <ms>` writes; later read with `get-lut` |

> These parameters are fetched by the agent directly — **do not proactively ask the user**. See [SKILL.md §8.1](../SKILL.md) for details.

---

## 1. hcloud CLI

```bash
hcloud version
```

Output looks like `当前KooCLI版本:7.2.12.1`. On first run:

```bash
printf "y\n" | hcloud version
```

> Detailed installation steps, cross-platform notes, and troubleshooting are in `skills/devtools/cli/huawei-cloud-cli-guidance/`. On first run, accept terms interactively (or pipe `y` in non-interactive scripts):

```bash
printf "y\n" | hcloud version
```

---

## 2. Credentials (AK/SK) and 5-line manual probe

Verify connectivity:

```bash
hcloud configure list
hcloud OptVerse ListBuckets --cli-region=<region> --cli-output=json
hcloud IAM ListAgencies --domain_id=<my-account-id> \
  --cli-region=<region> --cli-output=json
```

> Security rule: never paste AK/SK in plaintext into conversations or scripts.

### 2.1 5-line manual probe (when precheck fails)

When `precheck.sh` / `precheck.ps1` cannot run (env anomalies / path issues / encoding garbage), use these 5 commands to manually verify:

```bash
# 1. hcloud on PATH
command -v hcloud  # Windows PowerShell: Get-Command hcloud

# 2. hcloud version
hcloud version  # first run needs interactive accept: `printf "y\n" | hcloud version`

# 3. credentials configured
hcloud configure list

# 4. region config
hcloud configure show  # look for region field; or $env:HUAWEI_CLOUD_REGION

# 5. OptVerse connectivity
hcloud OptVerse ListBuckets --cli-region=<region> --cli-output=json
# expect: meta_info + payload.list non-empty
```

Any step failing means the corresponding precheck item will FAIL; fix the environment before proceeding.

---

## 3. Python interpreter (why the skill needs Python) (dependency check + self-check)

### 3.1 Self-check (required before the agent's first command)

```bash
python --version  # Expect Python 3.8+; if missing, see §3.4 path-discovery hints
```

**Mandatory action on self-check failure**: if `python --version` returns non-zero or the `python` command is missing, the agent **MUST explicitly inform the user** that the following items will be impacted (see §3.2), so the user can decide whether to install Python or confirm the virtual-env path before continuing:

- Multi-file Python / C++ projects **cannot be packaged and uploaded** (`zip_helper.py` unavailable)
- Algorithm / task ID caching **cannot be managed automatically** (`cache.py` unavailable; all commands need manual `$AID=$(hcloud ...)` chains)
- `--cli-output=json` output **cannot be parsed programmatically** (inline `python -c` unavailable; the agent can only read JSON by eye)

If `python` is unavailable, ask the user to install Python 3.8+ or activate a virtual environment.

### 3.2 Steps that depend on Python

The following skill-shipped tools need Python on the user's local machine:

| Tool | Purpose | Impact when Python is missing |
|---|---|---|
| `scripts/zip_helper.py` | Multi-file project zip packing (input for `ImportAlgorithmFile`) | Multi-file Python / C++ projects **cannot be uploaded**; only `SaveAlgorithmFile` one-file-at-a-time, and C++ multi-file (with `.sh` / `CMakeLists.txt`) **cannot be handled at all** |
| `scripts/cache.py` | Caching `<aid>` / `<tid>` / `last_update_time` | Every command needs a manual `$AID=$(hcloud ...)` chain; the agent cannot auto-fetch historical IDs from `.stats/` |
| Inline `python -c "..."` | One-shot JSON extraction, field parsing | The agent cannot parse `--cli-output=json` results — eyes only |

### 3.3 The evaluator itself (OptVerse platform-side, no local Python needed)

- When `--lang=python`, the evaluator runs on the **OptVerse platform**, which **does NOT depend on the user's local Python interpreter** (the platform has its own)
- If the evaluator needs third-party packages, put a `pip install` command into `--env` (passed to `CreateAlgorithm`); the platform will run it

### 3.4 Path-discovery hints

When `python` cannot be found on Windows, common fallback paths:

```powershell
# WindowsApps stub (the most common failure cause)
py --version

# Installed but not on PATH (search common locations)
where.exe python 2>$null; Get-Command python -ErrorAction SilentlyContinue

# Existing virtual environment (recommended; explore the standard venv paths)
```

Once a usable Python is found, set an environment variable for reuse:

```bash
export PYTHON="\PYTHON-PATH\python.exe"  # bash
$env:PYTHON = "C:\PYTHON-PATH\python.exe"  # PowerShell
```

Skill commands can use `"$PYTHON" scripts/cache.py ...` to call scripts.

---

## 4. Network and proxy

- When accessing OptVerse OpenAPI from an internal network, use the Apig address — make sure `HUAWEI_CLOUD_REGION` resolves consistently with the Apig domain
- If you hit 403/404, first run `hcloud OptVerse <Op> --help` to verify version and parameters

---

## 5. Security rules

- **Never** put AK/SK in plaintext in conversations / scripts / logs
- Verify credential presence only via `hcloud configure list`
- Prefer environment variables and profile mode
- For sequential multi-task execution, do NOT reuse the Secret Key — use STS temporary credentials instead

---

## 6. PowerShell terminal pitfalls (empirically observed)

On Windows, two common pitfalls degrade hcloud output under PowerShell.

### 6.1 GBK terminal garbles Chinese characters

Under the **default PowerShell GBK terminal**, fields containing Chinese characters in hcloud output get garbled (e.g. `prepare_content` from `ShowTaskRunningLog`, various `error_msg`); however, JSON keys and English-only logs are unaffected and remain hard to read by eye.

Two workarounds:

1. **Switch to a UTF-8 terminal before running** (recommended):

   ```powershell
   chcp 65001
   hcloud OptVerse ShowTaskRunningLog ...  # Chinese displayed correctly
   ```

2. **Parse `--cli-output=json` fields directly**: Chinese garbling only affects the human eye; it does not affect JSON data. Write a script to read fields like `payload.item.log_content` (English / numbers / timestamps render fine).

### 6.2 PowerShell variable expansion into hcloud subprocess

When PowerShell subprocesses pass variables like `$TID` / `$PROJECT_ID` to hcloud, you may get "invalid parameter value" errors — **recommend using hard-coded values first** to confirm the command shape, then switch back to variables.

---