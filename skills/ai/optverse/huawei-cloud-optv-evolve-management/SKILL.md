---
name: huawei-cloud-optv-evolve-management
description: |
  Huawei Cloud algorithm auto-design (LLM4AD) skill.
  Performs the full lifecycle through KooCLI (command-line entry `hcloud`): algorithm project management, file upload, evolve task CRUD, status polling, result retrieval, and log inspection;
  also uses KooCLI's `hcloud IAM` subcommand to create the trust agency and grant algorithm design module bucket permissions.
  Trigger words: code evolution, evolve task, LLM4AD, algorithm optimization,
  upload algorithm file, create evolve task, start evolve task, fetch evolve result, evolve log,
   代码演化, 演化任务, LLM4AD, code evolution, 算法优化,
  上传算法文件, 创建演化任务, 启动演化任务, 拉取演化结果, 演化日志
tags: [huawei-cloud, optverse, llm4ad, code-evolution, python, cpp]
---

> **⚠️ Execution Method (Must Read)**: All scripts must be executed via `skill action=exec`; do not run them directly in the shell.
> - All OptVerse calls in this skill MUST go through KooCLI (command-line entry `hcloud`). Direct calls to the OptVerse OpenAPI via `requests` or any other HTTP library are forbidden.
> - Files in `scripts/` are **skill-shipped helper tools** (`zip_helper.py` / `cache.py`); all of them are pure-local tools that **do not invoke KooCLI subprocesses**.
> - **The Agent itself MUST NOT** create one-off temporary `.py` script files; for Python JSON processing, prefer `python -c "..."` inline execution.
> **Do NOT create temporary script files** (`.py` / `.zip` / `.json` / `.toml` etc.); temporary artefacts (zip packages, JSON caches, scan results) go under `.stats/` or `OPTV_CACHE_DIR` in a fixed location, and **must be cleaned up after use**.
> **⚠️ Security Rule (Must Read)**: Never expose AK / SK in conversation, scripts, or output. Only verify credential presence via `hcloud configure list`.

# Algorithm Auto-Design Skill (English)

## Overview

End-to-end code evolution on the Huawei Cloud **Scientific Computing Zone — Algorithm Design Module**:

- Upload algorithm code, evaluator and baseline into an algorithm design project
- Create and start an evolve task, monitor progress, fetch results and logs

**When result upload to OBS bucket is required** (optional path, skip for default scenario):

- Create / maintain an IAM Agency as the cross-service trust anchor
- Grant bucket (OBS) permissions to the algorithm design module

Supported languages:

| Language | Algorithm | evaluator | baseline |
|---|---|---|---|
| Python | source file + function name | source file (e.g. `evaluator.py`) with `def evaluate():` | source file (e.g. `baseline.py`) with `def baseline():` |
| C++    | source file + function name (evolved function) | compiled executable command (e.g. `build/evaluate <args>`) | compiled executable command (may equal evaluator) |

C++ projects use `CreateAlgorithm --build_command` to compile the uploaded `.cpp` files into executables. The `evaluator_file` / `evaluator_baseline` fields are left blank for C++; only the command name is provided.

## Directory Layout

```
skills/ai/optverse/huawei-cloud-optv-evolve-management/
├── SKILL.md                # This file (English)
├── references/              # Topic-split documentation
│   ├── readme.md
│   ├── api-mapping.md
│   ├── prerequisites.md
│   ├── parameter-format.md
│   ├── iam-policies.md
│   ├── iam-agency.md
│   ├── agency-policy.md
│   ├── language-python.md
│   ├── language-cpp.md
│   ├── algorithm-workflow.md
│   ├── evolve-task-workflow.md
│   ├── result-logs-status.md
│   ├── troubleshooting.md
│   ├── verification-method.md
│   ├── cli-installation-guide.md
│   └── plan-maintenance.md
├── scripts/                 # Local tools (no hcloud calls)
│   ├── readme.md
│   ├── precheck.sh
│   ├── precheck.ps1
│   ├── cache.py
│   ├── build_task_url.py
│   └── zip_helper.py
├── templates/               # evaluator / baseline / algorithm source code skeletons
│   ├── readme.md
│   ├── python/
│   │   ├── evaluator.py
│   │   ├── baseline.py
│   │   └── algorithm.py
│   └── cpp/
│       ├── evaluator.cpp
│       └── baseline.cpp
└── .stats/                  # Locally maintained caches (algorithm_id, task_id)
    ├── algorithm_id.csv
    └── task_id.csv
```

`references`, `scripts`, `templates` (three sub-dirs by role): references describe; scripts execute local-only helpers; templates supply uploadable source.

---

## 1. Prerequisites

> **Required first step**: before any `hcloud OptVerse ...` or `hcloud IAM ...` call, dispatch `scripts/precheck.sh` (Linux / Git Bash / WSL) or `scripts/precheck.ps1` (Windows PowerShell) via `skill action=exec`. The precheck covers: ① KooCLI install ② AK/SK configure ③ region config ④ OptVerse API connectivity.

### 1.0 One-shot environment check (required first step)

> ⚠️ **Windows shell choice**: use **`powershell`** (system-installed Windows PowerShell 5.1; this skill has verified PS 5.1 + precheck.ps1 passing 5/5 checks).
> Avoid `bash` on Windows by default: `where bash` may resolve to `C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\bash.exe` (a WSL launcher stub that hangs on "install WSL" when WSL is absent); **WSL bash is NOT verified by this skill**.

Before starting a task, **must** dispatch the precheck script via `skill action=exec` once (covers 5 checks in one go):

```bash
# Windows PowerShell (via skill action=exec; preferred)
powershell scripts/precheck.ps1

# Git Bash / MSYS2 bash (via skill action=exec; last resort — WSL bash not verified)
bash scripts/precheck.sh
```

**Output**: ✅ / ⚠️ summary (default `summary` mode; set `CHECK_OUTPUT_MODE=detail` for per-check details)

**Exit code**: `0 = all pass`, `1 = one or more FAIL`

**What it covers (mapping to §1 sub-sections)**:

| precheck item | Maps to |
|---|---|
| `hcloud` command (in PATH) | §1.1 KooCLI Installation |
| `hcloud version` (first-run terms accept) | §1.1 KooCLI Installation |
| `hcloud configure list` (credentials configured) | §1.2 Credentials (AK/SK) |
| `region` configuration (env / profile) | §1.2 Credentials, `A. Project ID` etc. |
| `OptVerse connectivity` (`ListBuckets` probe) | §1.5 Agency + bucket authorization (precondition: connectivity OK) |

**What it does NOT cover** (verify separately):

- §1.3 Python interpreter (precheck does not probe `python`)
- §1.4 IAM permissions (precheck does not validate IAM actions)
- §1.5 Agency creation + bucket authorization (precheck only verifies connectivity, does not actually create agency / authorize bucket)

#### 1.0.1 Fallback shell table

> If `powershell` is unavailable, the only documented fallback is `bash` (Git Bash / MSYS2 / Linux). **WSL bash is NOT verified by this skill — avoid it**.

| Probe | Meaning | Recommended precheck |
|---|---|---|
| `powershell` on PATH | Windows PowerShell 5.1 (system-installed, widespread) | `powershell scripts/precheck.ps1` |
| `bash` on PATH | Git Bash / MSYS2 / Linux | `bash scripts/precheck.sh` |

#### 1.0.2 Manual fallback 5-line probe

If `precheck.sh` / `precheck.ps1` cannot run, see [`references/prerequisites.md`](references/prerequisites.md) §2.1 "5-line manual probe" for the 5 manual verification commands.

### 1.1 KooCLI Installation (the `hcloud` CLI)

> Full install / credentials / network verification, see [`references/cli-installation-guide.md`](references/cli-installation-guide.md). Quick verify: `hcloud version` (expected output `当前KooCLI版本:7.2.12.1` or later); on first run, the terms prompt may need a `y` (pipe `y` in non-interactive scripts).

### 1.2 Credentials (AK/SK)

If AK/SK is not configured yet, run `hcloud configure init` interactively (enter AK / SK / region / project ID, etc.).

Once configured, verify connectivity:

```bash
hcloud configure list
hcloud OptVerse ListBuckets --cli-region=<region> --cli-output=json
hcloud IAM ListAgencies --domain_id=<my-account-id> \
  --cli-region=<region> --cli-output=json
```

> Security rule: never expose AK/SK in conversation, scripts, or output.

### 1.3 Python interpreter

- Default: system `python`
- Third-party packages needed by the evaluator are installed via the algorithm's `--env` field: pass a **complete `pip install <pkgs>` command** (passed to `CreateAlgorithm`); the platform runs it before evaluation.

> ⚠️ **Windows PowerShell + hcloud fatal combo**: `powershell_exec hcloud ... --project_id=$AID`
> passes the literal string `$AID` to KooCLI (**PowerShell variables do NOT expand across processes**),
> producing confusing "invalid parameter value" errors. **Correct**: always use §6.8 `skill action=exec`
> argv-array form; pass variables through the argv array explicitly.
>
> ```text
> ❌  powershell_exec hcloud OptVerse ShowTaskDetails --project_id=$AID --evolve_task_id=$TID
> ✅  skill action=exec --name huawei-cloud-optv-evolve-management \
>        --command ["hcloud","OptVerse","ShowTaskDetails",
>                   "--project_id="+AID,"--evolve_task_id="+TID,"--cli-region="+REGION]
> ```

- **Windows PowerShell users**: see the **Execution Method** rule at the top of this document and §6.8 below. `hcloud` MUST be invoked through `skill action=exec` argv-array form; never through `powershell_exec hcloud ...`. PowerShell variable expansion (`$AID` / `$TID`) inside the KooCLI subprocess can silently corrupt argument values and produce confusing "invalid parameter value" errors.

### 1.4 IAM permissions

Required actions are listed in [`references/iam-policies.md`](references/iam-policies.md). System policies `OptVerse FullAccess` + `Security Administrator` work for sanity checks; production environments should use the custom policy JSON in that file.

### 1.5 Agency + bucket authorization (OPTIONAL)

If the evolve task needs to upload its results to your own OBS bucket, you MUST create the IAM agency first, then authorize the bucket. **If no result upload is needed** (just inspect progress and results from the OptVerse console / `hcloud`), both steps can be skipped — in that case `CreateEvolveTask --output_path` is left blank.

The visualized flow and concrete commands appear in §4.2 §A "One-time preparation". Detailed operations live in [`references/iam-agency.md`](references/iam-agency.md) and [`references/agency-policy.md`](references/agency-policy.md).

> **How to decide**: if you only want to view evolve results in OptVerse's console or via `hcloud`, and do not need artefacts in OBS, you can skip §A and use §B.2 with `--output_path=""`.

---

## 2. Triggers

Activate this skill when any of the following user intents appears:

- "create an evolve task" / "start evolve task" / "stop/delete evolve task"
- "upload algorithm code" / "add evaluator to algorithm project"

---

## 3. Safety & Risk Constraints

- **Two-step confirmation for every destructive call**: print the command and a risk warning; only execute after explicit user confirmation. Applies to `IAM DeleteAgency`, `OptVerse DeleteAlgorithm`, `OptVerse DeleteEvolveTask`, `OptVerse BatchDeleteEvolveTask`, `OptVerse RevokePermission`.
- **Never rename uploaded files**; the file path passed to `--file_path` must equal `os.path.basename(local_file)`.
- **Time-based efficiency functions must use concurrency = 1**: `--evaluator_max_workers=1` and `--search_max_workers=1`.
- **Credential safety**: only check presence via `hcloud configure list`; never echo values.
- **C++ projects must supply `build_command`**; otherwise `evaluator.cpp` / `baseline.cpp` / `algorithm.cpp` cannot be compiled into executable commands.

---

## 4. Standard Workflow

### 4.1 Default scenario (no OBS upload)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [1] Environment & connectivity                                       │
│     hcloud version / hcloud configure list                            │
│     hcloud OptVerse ListBuckets --cli-region=<region>                 │
├──────────────────────────────────────────────────────────────────────┤
│ [2] Create algorithm project                                          │
│     hcloud OptVerse CreateAlgorithm                                    │
│       --name=… --lang=python|c++                                       │
│       [--build_command="…"]  # required for C++                       │
├──────────────────────────────────────────────────────────────────────┤
│ [3] Upload algorithm + evaluator + baseline                           │
│     hcloud OptVerse SaveAlgorithmFile --file_path=<…> (multiple times) │
│     or hcloud OptVerse ImportAlgorithmFile --file=<zip>                │
├──────────────────────────────────────────────────────────────────────┤
│ [4] Create evolve task (output_path blank)                            │
│     hcloud OptVerse CreateEvolveTask --output_path="" --description=… │
├──────────────────────────────────────────────────────────────────────┤
│ [5] Start the task                                                    │
│     hcloud OptVerse StartEvolveTask --evolve_task_id=…                │
├──────────────────────────────────────────────────────────────────────┤
│ [6] Poll status / fetch results                                       │
│     hcloud OptVerse ShowTaskRunningDetails --type=…                   │
│     hcloud OptVerse ShowTaskResultCommit --type=CODE …                │
├──────────────────────────────────────────────────────────────────────┤
│ [7] (optional) Stop / delete the task (delete needs two-step confirm)  │
│     hcloud OptVerse StopEvolveTask / DeleteEvolveTask                │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Optional path: upload results to OBS

For the upload scenario (i.e. `CreateEvolveTask --output_path="obs://<bucket>/<prefix>"`), the one-time agency + bucket-authorization setup lives in:

- [`references/agency-policy.md`](references/agency-policy.md) — bucket authorization via `OptVerse AuthorizePermission`
- [`references/iam-agency.md`](references/iam-agency.md) — agency create / attach / query

> **Agency is OPTIONAL**: if you only inspect evolve results in the OptVerse console or via `hcloud`, skip the agency setup entirely and use `--output_path=""` (see §4.1 default scenario).

### 4.3 Reference: official sample algorithms + algorithm_id format

The platform ships three **official sample algorithms** for reference and ad-hoc debugging:

| algorithm_id | Algorithm |
|---|---|
| `0` | Sort |
| `1` | CVRP |
| `2` | CirclePacking |

> **Two algorithm_id formats coexist**:
> - **Official samples**: short numeric strings `id=0` / `id=1` / `id=2` (no hyphens)
> - **Self-built projects**: hyphenated `uuid`, e.g. `44d5914f-e3cc-406f-aefc-c04913493bec`
>
> **Always preserve the original format** — stripping hyphens from a self-built uuid and passing it as a short id will fail with `evolve.01050004 Algorithm id does not exist`.

---

## 5. Command Quick Reference

> **⚠️ Hard requirement (all `hcloud` commands)**: all `hcloud` parameters MUST use the `--key=value` form; the space-separated form is forbidden.
>
> **WHY**: `--key=value` is a literal string passed to the hcloud subprocess; the space form (e.g. `--project_id xxx`) relies on shell token splitting, which silently breaks across platforms / PowerShell argv arrays / Git Bash escaping — triggering "missing required option" or "invalid parameter value" errors.
>
> **Failure anti-patterns** (never write these):
>
> | ❌ Wrong form | Failure |
> |---|---|
> | `--project_id xxx` (space + positional) | KooCLI rejects → "missing required option" |
> | `--project_id= $VAR` (bash, unquoted) | bash splits into `--project_id=` (empty value) + `$VAR` (positional) |
> | `--project_id=$VAR` (Windows PowerShell child execution) | `$VAR` is NOT expanded by PowerShell inside the subprocess — literal `$VAR` sent |
> | `-r cn-east-3` (short option + value space-separated) | Some commands reject; use `-r=cn-east-3` |

### 5.1 IAM Agency

> Full reference: see [`references/iam-agency.md`](references/iam-agency.md). The agency name is **mandatory**: `optverse_service_trust`. For the policy Action list given to the backend service account, see the same reference document.

### 5.2 Algorithm

```bash
# List
hcloud OptVerse ListAlgorithms --limit=10 --cli-region=<region>

# Python project
hcloud OptVerse CreateAlgorithm \
  --name="Algorithm_20260101_120000" --lang="python" --description="…" \
  --cli-region=<region>

# C++ project (with build_command)
hcloud OptVerse CreateAlgorithm \
  --name="Algorithm_cpp_20260101_120000" --lang="c++" --description="…" \
  --build_command="bash ./build.sh" \
  --cli-region=<region>

# Details
hcloud OptVerse ShowAlgorithm --project_id=<project_id> --algorithm_id=<aid> --cli-region=<region>

# Directory
hcloud OptVerse ListDirectoryByAlgorithmId --project_id=<project_id> --algorithm_id=<aid> --cli-region=<region>

# Upload single file (must fetch last_update_time first via ShowAlgorithm)
hcloud OptVerse SaveAlgorithmFile --project_id=<project_id> --algorithm_id=<aid> \
  --file=./evaluator.py --file_path=evaluator.py --last_update_time=<ms> \
  --cli-region=<region>

# Delete (dangerous, requires two-step confirmation)
hcloud OptVerse DeleteAlgorithm --project_id=<project_id> --algorithm_id=<aid> --cli-region=<region>
```

### 5.3 Evolve task

```bash
# Python
hcloud OptVerse CreateEvolveTask \
  --project_id=<project_id> --algorithm_id=<aid> --name=… --description=… --output_path=… \
  --evaluator_file=evaluator.py --evaluator_func_name=evaluate \
  --evaluator_baseline=baseline.py --evaluator_baseline_func_name=baseline \
  --evaluator_parameter.search_iterations=10 \
  --evaluator_parameter.search_population_size=4 \
  --evaluator_parameter.search_max_workers=2 \
  --evaluator_parameter.evaluator_max_workers=2 \
  --evaluator_parameter.smaller_better=true \
  --evaluator_parameter.llm_models.1=GLM-5 \
  --cli-region=<region>

# C++
hcloud OptVerse CreateEvolveTask \
  --project_id=<project_id> --algorithm_id=<aid> --name=… --description=… --output_path=… \
  --algorithm_file=sort_algorithm.cpp --algorithm_func_name=sort_array \
  --evaluator_file="" --evaluator_func_name="build/evaluate <args>" \
  --evaluator_baseline="" --evaluator_baseline_func_name="build/evaluate <args>" \
  --evaluator_parameter.smaller_better=true \
  --evaluator_parameter.llm_models.1=GLM-5 \
  --cli-region=<region>

# Start
hcloud OptVerse StartEvolveTask --project_id=<project_id> --evolve_task_id=<tid> --cli-region=<region>

# Status
hcloud OptVerse ShowTaskDetails --project_id=<project_id> --evolve_task_id=<tid> --cli-region=<region>

# Progress / summary / best result / generation stats
# ⚠️ --type uses lowercase underscore (4 values: progress / summary / best_result / generation_stats)
hcloud OptVerse ShowTaskRunningDetails --project_id=<project_id> --evolve_task_id=<tid> \
  --type=progress --cli-region=<region>

# Results
hcloud OptVerse ShowTaskResultList   --project_id=<project_id> --evolve_task_id=<tid> --cli-region=<region>
# ⚠️ --type uses UPPERCASE (3 values: CODE / SUMMARY / INSIGHT)
# ⚠️ `--type=CODE` returns a **base64-encoded string** (NOT plaintext); SUMMARY / INSIGHT are plaintext
hcloud OptVerse ShowTaskResultCommit --project_id=<project_id> --evolve_task_id=<tid> \
  --commit_id=<cid> --iteration=<n> --type=CODE --cli-region=<region>
# --iteration=<n> is REQUIRED; <n> is the iteration segment in "sample_<n>_<fp>"
# Or auto-derive via: python scripts/cache.py get-iteration --commit-id "$COMMIT"

# Stop / delete (delete requires two-step confirmation)
hcloud OptVerse StopEvolveTask  --project_id=<project_id> --evolve_task_id=<tid> --cli-region=<region>
hcloud OptVerse DeleteEvolveTask --project_id=<project_id> --evolve_task_id=<tid> --cli-region=<region>
```

> **⚠️ `--type=` casing rules differ**:
> - `ShowTaskRunningDetails --type=` uses **lowercase underscore** (`progress` / `summary` / `best_result` / `generation_stats`)
> - `ShowTaskResultCommit --type=` uses **uppercase** (`CODE` / `SUMMARY` / `INSIGHT`)

### 5.4 Buckets / authorization

```bash
hcloud OptVerse ListBuckets --project_id=<project_id> --cli-region=<region>
hcloud OptVerse AuthorizePermission --project_id=<project_id> --bucket=<bucket> --cli-region=<region>
hcloud OptVerse RevokePermission  --project_id=<project_id> --bucket=<bucket> --cli-region=<region>
hcloud OptVerse ListPermission   --project_id=<project_id> --cli-region=<region>
```

### 5.5 Direct task / algorithm URL

> **💡 URL capability**: before or after running a task, call `python scripts/build_task_url.py -r <region> --task-id <tid>` to build a direct console URL; add `--open` to launch it in the default browser.

```bash
# Just print the URL
python scripts/build_task_url.py -r <region> --task-id <tid>

# Print + launch in default browser (Windows / Linux / macOS)
python scripts/build_task_url.py -r <region> --task-id <tid> --open
```

> Parameters:
> - `-r / --region` is required (e.g. `cn-east-3`); other regions (test envs) require `export TEST_ENV_REGION=<region> TEST_ENV_DOMAIN=<domain>` first
> - `--task-id` or `--algorithm-id` — one of them is required; builds the evolve-task detail page or the algorithm-project page respectively
> - `--open` opens the browser only when a graphical desktop is detected; in headless / SSH-no-X11 / Windows-service-session contexts, it prints "please open the URL manually" and exits with code 1
> - `--quiet` silences the URL print (use with `--open` to just launch the browser)

See [`scripts/build_task_url.py`](scripts/build_task_url.py) header for details.

---

## 6. Key Constraints (Operational)

### 6.1 Evaluator / baseline semantics per language

| Field | Python | C++ |
|---|---|---|
| `--algorithm_file` | Python source file under evolution | C++ source file with `// EVOLVE_START/END` markers |
| `--algorithm_func_name` | function name (e.g. `sort_algorithm`); can be omitted if the algorithm file contains `# EVOLVE_START` / `# EVOLVE_END` (platform auto-extracts from the `def` inside the markers) | function name (e.g. `sort_array`), **NOT** a launch command |
| `--evaluator_file` | evaluator source path (**can be the same file as baseline**) | leave blank |
| `--evaluator_func_name` | function name `evaluate` (default) | compiled executable command, e.g. `build/evaluate <args>` |
| `--evaluator_baseline` | baseline source path (may equal `evaluator_file`) | leave blank |
| `--evaluator_baseline_func_name` | function name `baseline` (default) | compiled executable command (may equal evaluator) |

The C++ `evaluator` / `baseline` executables **must** print a single floating point number followed by a newline to stdout.

> Empirically verified: `evaluator_file` and `evaluator_baseline` can be the same file (function names must differ).

#### Required-field 3-layer breakdown (Agent self-check before `CreateEvolveTask`)

See [`references/parameter-format.md`](references/parameter-format.md) §7 "CreateEvolveTask required-field 3-layer breakdown" for the full 6-field table; the same 3 buckets (`Agent must ask user` / `hcloud param must be passed` / `hcloud value must be non-empty`) are listed there.

### 6.2 C++ requires `// EVOLVE_START` / `// EVOLVE_END`

The function under evolution must be wrapped by these markers; the platform only replaces code between the markers. Code outside the markers (including `main`) is preserved. See [`references/language-cpp.md`](references/language-cpp.md) for the full template + caveats.

### 6.3 Refresh `content_update_at` before every upload

`--last_update_time` of `SaveAlgorithmFile` / `ImportAlgorithmFile` must equal the algorithm's `content_update_at` exactly, otherwise `evolve.01050007` fires. **Re-run `ShowAlgorithm` before every upload**.

### 6.4 `description` is the LLM prompt

Write it like a prompt:

1. Role (e.g. "You are an expert at …")
2. Background (what problem to solve)
3. Objective (faster / more accurate / shorter / larger)
4. Key constraints
5. Output format (optional)

Example fragments:

- Sort: "You are an expert at designing fast and efficient sorting algorithms. Create sorting algorithms that are correct and fast."
- CVRP: "You are a route planning expert. Given a set of customers and a fleet of vehicles with limited capacity, the task is to design a novel algorithm to select the next node in each step, with the objective of minimizing the total cost."

### 6.5 Time-based efficiency = concurrency 1

When the evaluator measures time:

```
--evaluator_parameter.evaluator_max_workers=1 --evaluator_parameter.search_max_workers=1
```

### 6.6 `smaller_better`

| Metric direction | `smaller_better` | Baseline target |
|---|---|---|
| Bigger = better (accuracy) | `false` | baseline should be smaller |
| Smaller = better (time) | `true` | baseline should be larger |

### 6.7 Two-step confirmation for destructive calls

```
About to execute:
  hcloud OptVerse DeleteEvolveTask --project_id=<project_id> --evolve_task_id=<tid> --cli-region=<region>
Impact: results lost, future callbacks will fail immediately.
Continue? [y/N]
```

### 6.8 Cross-platform call principles

> **Core principles**: cross-platform stability doesn't come from one "standard call form", but from 3 iron rules:
> 1. **All OptVerse / IAM calls go through `hcloud <Service> <Op>` (KooCLI subprocess)**, never direct HTTP OpenAPI
> 2. **argv-array form** for parameters (avoids shell escaping / cross-shell unreliability)
> 3. **`--key=value` form**, never `--key value` space-separated

Different agents / Skill Runtimes use different "call form" syntax; the table below orders them by priority:

| Style combo (call style + path scheme) | Example invocation | Notes |
|---|---|---|
| **Skill Runtime wrapper + Skill URI** (**preferred**) | `skill action=exec --name <skill> --command ["powershell","-File","skill://scripts/precheck.ps1"]` | Skill Runtime auto-resolves `skill://` to the skill package root; cross-shell stable |
| Skill Runtime wrapper + absolute path (fallback) | `skill action=exec --name <skill> --command ["powershell","-File","/abs/path/scripts/precheck.ps1"]` | When Skill Runtime doesn't support `skill://` |
| Direct shell + relative path (cwd must be at skill root) | `powershell scripts/precheck.ps1` | bash / PowerShell tool calls directly; requires cwd already at workspace |
| Direct Python fork (**not recommended**) | `python -c "import subprocess; subprocess.run(['hcloud',...])"` | Bypasses agent-framework isolation / cache semantics |

> ⚠️ Which style is available depends on your agent framework (see its docs). **Regardless of style, the 3 iron rules must hold**.

#### Anti-patterns (forbidden in any style)

| ❌ Anti-pattern | Why it's bad |
|---|---|
| `requests.post('https://optverse...', json=...)` direct to OpenAPI | Bypasses KooCLI auth / error handling / retry / `--debug` logging; crosses the "direct OpenAPI" red line |
| `--key value` space-separated | bash splits it as `--key=` (empty value) + `value` (independent token); PowerShell `$VAR` doesn't expand |
| `python -c "import subprocess; ..."` self-forking hcloud | Bypasses agent-framework isolation / cache semantics; inconsistent with Skill Runtime's script-call mechanism |

#### Polling strategy

Before **`CreateEvolveTask` (inclusive)** the agent MUST ask the user to pick one of two polling modes; do NOT defer this to after `CreateEvolveTask` / `StartEvolveTask` — that breaks the flow and the agent gets stuck in a polling loop right after `StartEvolveTask`.
- **(a) Agent polls actively**: loop `ShowTaskDetails` until `FINISHED` / `FAILED` / `STOPPED`
- **(b) User self-queries (recommended)**: hand `evolve_task_id` + a direct link (`python skill://scripts/build_task_url.py -r <region> --task-id <tid> --open`) to the user; query `ShowTaskDetails` on demand afterwards.

**Not recommended** to start polling right away (avoids long agent-session occupation)

---

## 7. Filesystem Conventions

### 7.1 Temporary files

- Never write temp files inside the skill directory or user home.
- Auto-generated temp scripts must go under `OPTV_CACHE_DIR` (default the skill's `.stats/` folder) and be cleaned up afterwards.

### 7.2 Cache files

`.stats/` is maintained manually:

- `.stats/algorithm_id.csv` — currently active algorithm ID
- `.stats/task_id.csv` — every evolve task created in this session

### 7.3 Filename consistency

> **⚠️ Do not rename uploaded files.** Python evaluator / baseline file names are **not strictly required** — only the file passed to `--evaluator_file` / `--evaluator_baseline` in `CreateEvolveTask` matters (the platform imports by file name). For C++ projects the `build_command` must compile to executables whose names match `--evaluator_func_name` / `--evaluator_baseline_func_name`.

---

## 8. Parameter Categories Quick Reference

> **Parameter syntax reference**: detailed `--key=value` / nested / array / enum / size-limit / JMESPath syntax lives in [`references/parameter-format.md`](references/parameter-format.md). This section is a quick **A/B/C classification** for the agent only.

When starting a task, the agent decides where each parameter comes from by following the three categories below — **first fill from A, then collect from B, finally cover with C defaults**.

### 8.1 A. Pre-configured (Agent retrieves automatically, do NOT ask user)

| Parameter | Source |
|---|---|
| `--project_id` | `hcloud configure show` output, or env var `HUAWEI_CLOUD_PROJECT_ID` |
| `--cli-region` | `hcloud configure show` output, or env var `HUAWEI_CLOUD_REGION` |
| `--algorithm_id` (existing project) | local cache `.stats/algorithm_id.csv`, indexed by `algorithm_name`; prefer [`scripts/cache.py`](scripts/cache.py) `ensure-algorithm` |
| `--evolve_task_id` (existing task) | local cache `.stats/task_id.csv`, indexed by `algorithm_id`; prefer `scripts/cache.py` `ensure-task` |
| `--last_update_time` | agent runs `hcloud OptVerse ShowAlgorithm` to fetch `content_update_at`, then `scripts/cache.py put-lut --lut <ms>` to write; use `get-lut` to read on subsequent calls |

### 8.2 B. Must Ask User (Agent must NOT guess)

Collect **all at once** before starting, do NOT ask step-by-step:

1. **Language**: `python` / `c++`
2. **Algorithm goal / prompt**: what to evolve and constraints (goes into `--description`); see §6.4 for the prompt template
3. **Algorithm source file local path** + **`--algorithm_file`** + **`--algorithm_func_name`**
4. **Evaluator local path + function name** (Python) / **evaluator_func_name command** (C++)
5. **Baseline local path + function name** (Python) / **baseline_func_name command** (C++)
6. **`--build_command`** (**C++ only, required**)
7. **`--bucket`** + **`--output_path="obs://..."`** (**only when result upload to OBS is required**; skip for default scenario**)
8. **`--evaluator_parameter.search_iterations`** (**required**): number of evolution rounds; see [`parameter-format.md`](references/parameter-format.md) for the full `--evaluator_parameter.*` syntax
9. **Post-start polling mode** (**required**): pick one — see [§6.8 Polling strategy](#68-cross-platform-call-principles); for long tasks prefer user self-query
10. **Two-step confirmation for destructive operations** — see §3

### 8.3 C. Agent Auto-Generated (user may override; do NOT proactively ask)

| Parameter | Default rule |
|---|---|
| `--name` (project / task) | `Algorithm_YYYYMMDD_HHMMSS` / `EvolveTask_<algo-name>_<timestamp>` |
| `--description` | Generic template: role (domain expert) + background (what problem to solve) + objective (user-specified: speed / accuracy / distance / other) + key constraints + output format (optional); see §6.4 |
| `--output_path` | Default `""` (**no upload**) |
| `--evaluator_parameter.search_iterations` | Default 10 (suggest 3-5 for first run) |
| `--evaluator_parameter.search_population_size` | Default 4 (suggest 3) |
| `--evaluator_parameter.smaller_better` | Time/distance → `true`; accuracy/hit-rate → `false` (inferred from evaluator semantics) |
| `--evaluator_parameter.{evaluator,search}_max_workers` | Time class → `1`; otherwise → `2` |
| `--evaluator_parameter.llm_models.1` | Default `GLM-5` |
| **Agency / policy names** (upload scenario) | `optverse_service_trust` / `policy_ai4s_llma4ad` / `op_svc_oroas_container0` |

### 8.4 Cache Helper

`scripts/cache.py` encapsulates cache file I/O. Before running commands, the agent uses `$(python scripts/cache.py ...)` to retrieve `<aid>` / `<tid>`:

```bash
AID=$(python scripts/cache.py ensure-algorithm --name "p1test")
TID=$(python scripts/cache.py ensure-task --aid "$AID")

# last_update_time: agent runs hcloud + put-lut explicitly
LUT=$(hcloud OptVerse ShowAlgorithm --algorithm_id="$AID" \
  --cli-region="$REGION" --cli-output=json \
  --cli-query="payload.item.content_update_at")
python scripts/cache.py put-lut --aid "$AID" --lut "$LUT"

# Then later:
LUT=$(python scripts/cache.py get-lut --aid "$AID")
```

Also usable as a Python module:

```python
from scripts.cache import (
    ensure_algorithm, ensure_task, get_lut,
    put_algorithm, put_task, put_lut,
)
```

Cache tool subcommands: `ensure-algorithm` / `put-algorithm` / `ensure-task` / `put-task` / `get-lut` / `put-lut`. See [`scripts/cache.py`](scripts/cache.py) header for details.

> **cache.py does NOT invoke hcloud**: all `last_update_time` flows are orchestrated by the agent in shell; cache.py is a pure-local tool requiring no IAM permission.

---

## 9. Scripts/ Integration

`scripts/` ships only **local-only helpers** (none call `hcloud`). Full usage for each script lives in [`scripts/readme.md`](scripts/readme.md):

- `precheck.sh` / `precheck.ps1`: 5-item one-shot environment check
- `cache.py`: local CSV cache for `<algorithm_id>` / `<evolve_task_id>` / `last_update_time`
- `build_task_url.py`: print (or open) a direct console URL for a task / algorithm
- `zip_helper.py`: local ZIP packaging; pairs with `ImportAlgorithmFile --file=…`

After that, every business API call and local script invocation is dispatched via `skill action=exec` (see §6.8).

---

## 10. Lessons learned

After running end-to-end with `hcloud`, the following rules emerged:

1. `evaluator_file` and `evaluator_baseline` can point to the **same** file, as long as the function names differ.
2. `algorithm_file` and `evaluator_file` may also be the same module (or different modules), provided names don't collide.
3. C++ algorithm sources **must** include `// EVOLVE_START` and `// EVOLVE_END` around the function under evolution. The platform only replaces the code between the markers; everything else (including `main`) is preserved.
4. C++ `algorithm_func_name` is the **function name** (`sort_array`), **not** a launch command. `evaluator_func_name` is the compiled executable command (e.g. `build/evaluate <args>`), which may include a path and command-line arguments.
5. The same executable command can be used as both `evaluator_func_name` and `evaluator_baseline_func_name`. The platform distinguishes them by replacing the evolved algorithm source.
6. **Re-run `ShowAlgorithm` before every** `SaveAlgorithmFile` / `ImportAlgorithmFile` to fetch the latest `content_update_at`. Reusing an old value triggers `evolve.01050007`.
7. `SaveAlgorithmFile` fails on `.sh` scripts ("不支持的文件类型"). For multi-file C++ projects, always go through `ImportAlgorithmFile` + ZIP.
8. `.gitignore` must be preserved inside the zip: the platform manages projects with **git** (zip uploads trigger `git init`). `.gitignore` typically lists `build` / `build/` to exclude cmake build artefacts. Without `.gitignore`, build outputs would enter git history and **break subsequent cmake runs** (e.g. `build/` already exists, cmake refuses to overwrite cleanly).
9. **baseline comparison locations**:
   - baseline value: `Metric[metric_value] = X` line inside the `Baseline Population` table from `ShowTaskRunningLog`
   - best value: `payload.item.value` from `ShowTaskRunningDetails --type=best_result`
   - any individual's score: `list[].fitness_value` from `ShowTaskResultList`
   - improvement = `(baseline - best) / baseline`

Full error catalogue: [`references/troubleshooting.md`](references/troubleshooting.md) §4-§5.

---

## 11. End-to-End Examples

End-to-end examples for Python and C++ (with full CLI command sequences) live in `references/`:

- **Python (default, no upload)**: see [`references/language-python.md`](references/language-python.md) §7 for the typical `CreateEvolveTask` command + [`references/algorithm-workflow.md`](references/algorithm-workflow.md) for algorithm project create + upload + [`references/evolve-task-workflow.md`](references/evolve-task-workflow.md) §3-§8 for the full lifecycle (start / poll / fetch / stop).
- **Python (upload to OBS)**: same as above + [`references/agency-policy.md`](references/agency-policy.md) for one-time agency / bucket authorization + `--output_path=obs://...`.
- **C++ (default, no upload)**: see [`references/language-cpp.md`](references/language-cpp.md) §5 for the typical C++ `CreateEvolveTask` command + the same `evolve-task-workflow.md` references.

---

## 12. Related Documents

| Document | Purpose |
|---|---|
| [references/api-mapping.md](references/api-mapping.md) | OptVerse / IAM to hcloud CLI mapping |
| [references/prerequisites.md](references/prerequisites.md) | Credentials, environment, project ID |
| [references/parameter-format.md](references/parameter-format.md) | Parameter forms, nesting, arrays, JMESPath |
| [references/iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [references/iam-agency.md](references/iam-agency.md) | IAM agency create / update / delete |
| [references/agency-policy.md](references/agency-policy.md) | OBS bucket authorization (post-agency) |
| [references/language-python.md](references/language-python.md) | Python project conventions (evaluator/baseline same file, two running modes) |
| [references/language-cpp.md](references/language-cpp.md) | C++ project conventions (EVOLVE markers, build_command, command-style evaluator) |
| [references/algorithm-workflow.md](references/algorithm-workflow.md) | Algorithm project workflow |
| [references/evolve-task-workflow.md](references/evolve-task-workflow.md) | Evolve task workflow |
| [references/result-logs-status.md](references/result-logs-status.md) | Results, logs, status |
| [references/troubleshooting.md](references/troubleshooting.md) | Troubleshooting |
| [references/verification-method.md](references/verification-method.md) | Verification |
| [references/plan-maintenance.md](references/plan-maintenance.md) | **(agent-side, optional)** `plan` / `scratchpad` tool maintenance (multi-step task state-machine; skip if your agent does not have these tools) |