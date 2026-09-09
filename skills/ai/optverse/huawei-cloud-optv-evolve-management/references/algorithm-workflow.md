# Algorithm project management (create / configure / upload)

This chapter lists every hcloud operation pattern for an Algorithm Project. A single project can host multiple evolve tasks; the **evaluator** and **baseline** (a function in Python, an executable command in C++) must be source files of that project.

---

## 1. Workflow overview

See [SKILL.md §4](../SKILL.md) for the master flow diagram. This chapter concentrates on the commands themselves:

| Stage | hcloud operation | Reference |
|---|---|---|
| ① Create design project | `CreateAlgorithm` | §2 below |
| ② Single-file upload | `SaveAlgorithmFile` | §3 below |
| ③ ZIP batch upload | `ImportAlgorithmFile` | §3 below |
| ④ Verify project files | `ListDirectoryByAlgorithmId` / `ShowAlgorithmFile` | §4 below |
| ⑤ Maintenance | `UpdateAlgorithm` / `DeleteAlgorithm` (dangerous, two-step confirmation) | §4 below |

---

## 2. Create the algorithm project

### 2.1 Python project

```bash
hcloud OptVerse CreateAlgorithm \
  --name="Algorithm_20260101_120000" \
  --lang="python" \
  --description="Evolution project for sort" \
  --cli-region=<region> \
  --cli-output=json \
  --cli-query="payload.item.algorithm_id"
```

The returned `payload.item.algorithm_id` (or `payload.item.id`) IS the `algorithm_id`.

### 2.2 C++ project

C++ requires `--build_command` to compile the uploaded `.cpp` files into executable commands; the resulting `evaluator_func_name` points at the compiled output directly.

```bash
hcloud OptVerse CreateAlgorithm \
  --name="Algorithm_cpp_20260101_120000" \
  --lang="c++" \
  --description="C++ optimization" \
  --build_command="bash ./build.sh" \
  --cli-region=<region> \
  --cli-output=json \
  --cli-query="payload.item.algorithm_id"
```

> **Do NOT pass `--command`**: under C++ projects, `--command` has no effect; what actually drives the evaluator is the `evaluator_func_name` field (see [`language-cpp.md`](language-cpp.md)).

Optional fields:

| Field | Purpose |
|---|---|
| `--build_command` | Build command (required for C++ / Java) |
| `--env` | Pre-install environment script (`pip install -r` / `apt install` etc.) |

---

## 3. Upload files

### 3.0 Timestamp sync (required reading)

Before every `SaveAlgorithmFile` / `ImportAlgorithmFile`, you **MUST** re-run `ShowAlgorithm` to fetch the latest `content_update_at` and pass it as `--last_update_time`. Otherwise `evolve.01050007` fires:

```
File has been modified by another user, please refresh and try again,
content update time = X, last update time = Y.
```

`ShowAlgorithm` → upload → `ShowAlgorithm` → upload → ...

### 3.1 Single-file upload (accepts most text suffixes)

```bash
# 1) Get content_update_at
LUT=$(hcloud OptVerse ShowAlgorithm \
  --project_id=<project_id> --algorithm_id=<aid> \
  --cli-region=<region> \
  --cli-output=json \
  --cli-query="payload.item.content_update_at")

# 2) Upload the file
hcloud OptVerse SaveAlgorithmFile \
  --project_id=<project_id> --algorithm_id=<aid> \
  --file=./evaluator.py \
  --file_path=evaluator.py \
  --last_update_time="$LUT" \
  --cli-region=<region> \
  --cli-output=json
```

> **File type limits**: `SaveAlgorithmFile` accepts common text suffixes such as `.py` / `.cpp` / `.txt` / `.json`, but empirically rejects `.sh` with "unsupported file type". For multi-file C++ projects, switch to `ImportAlgorithmFile` + zip (see §3.2).

### 3.2 ZIP batch upload (init) — **recommended** for multi-file projects

> For multi-file projects, prefer `ImportAlgorithmFile` + zip (≤20 MB): one upload avoids optimistic-lock races and extra network round-trips; the same applies to Python and C++. Single-file upload (§3.1) still works.

```bash
# Pack the zip (works for both C++ and Python multi-file projects)
python scripts/zip_helper.py --src ./src --out algorithm.zip --force

hcloud OptVerse ImportAlgorithmFile \
  --project_id=<project_id> --algorithm_id=<aid> \
  --file=./algorithm.zip \
  --last_update_time="$LUT" \
  --cli-region=<region> \
  --cli-output=json
```

Constraints:

- Single file ≤ 5 MB, zip ≤ 20 MB
- Before a second upload, run `ShowAlgorithm` again to get a fresh `content_update_at`
- The zip must be valid
- `.gitignore` must be preserved in the zip (`zip_helper.py` does not delete it)

---

## 4. Read and maintain

```bash
# List algorithm files in the directory
hcloud OptVerse ListDirectoryByAlgorithmId \
  --project_id=<project_id> --algorithm_id=<aid> \
  --cli-region=<region>

# Read a single file's content (KooCLI does NOT auto-decode base64; handle payload.item.data as needed)
hcloud OptVerse ShowAlgorithmFile \
  --project_id=<project_id> --algorithm_id=<aid> \
  --file_path=evaluator.py \
  --cli-region=<region> \
  --cli-output=json

# Update project metadata (description / build_command etc.)
hcloud OptVerse UpdateAlgorithm \
  --project_id=<project_id> --algorithm_id=<aid> \
  --build_command="g++ -O3 -std=c++17 *.cpp -o main" \
  --cli-region=<region>

# Delete a project (dangerous — requires two-step confirmation)
hcloud OptVerse DeleteAlgorithm \
  --project_id=<project_id> --algorithm_id=<aid> \
  --cli-region=<region>
```

---

## 5. Per-language file checklist

| Language | Algorithm file | Evaluator | Baseline |
|---|---|---|---|
| Python | `algorithm.py` (exports a function) | `evaluator.py` (e.g. `evaluator.py`, containing `def evaluate():`; just keep the file name consistent with `--evaluator_file`) | `baseline.py` (e.g. `baseline.py`, containing `def baseline():`; just keep the file name consistent with `--evaluator_baseline`) |
| C++ | `algorithm.cpp` (compiled into an executable) | `evaluator.cpp` (compiled output usually named `evaluator`) | `baseline.cpp` (compiled output usually named `baseline`) |

For C++ projects, `evaluator_func_name` / `evaluator_baseline_func_name` are reused at the evolve-task stage as the "executable command" — see [`language-cpp.md`](language-cpp.md) and [`evolve-task-workflow.md`](evolve-task-workflow.md).

---

## 6. Filename consistency constraint

> **⚠️ Do NOT rename uploaded files!** The filename passed to the platform (`--file_path`) must exactly match the local `os.path.basename`.
>
> Python: at evolve-task runtime the platform imports the module by the name in `evaluator_file`. C++: `build_command` compiles specific files via `*.cpp` patterns; renaming will break source lookup.

---

## 7. Cache management

**Preferred**: use [`scripts/cache.py`](../scripts/cache.py) to auto-manage the `.stats/` cache files. After `CreateAlgorithm` / uploading files / `CreateEvolveTask`, the agent calls `put-algorithm` / `put-task` / `put-lut` to write; later reads via `ensure-algorithm` / `ensure-task` / `get-lut`. See [SKILL.md §8.4](../SKILL.md) / [`scripts/cache.py`](../scripts/cache.py) header comments.

**Underlying CSV format** (what `cache.py` reads and writes):

`algorithm_id.csv`:

```
algorithm_name,algorithm_id,content_update_at
<name>,<aid>,<ms>
```

`task_id.csv`:

```
algorithm_id,evolve_task_id,task_name,create_time
<aid>,<tid>,<task_name>,<create_time>
```

Whenever you create / query / delete algorithm projects and tasks, sync the corresponding cache:

- `ensure_algorithm`: look up `aid` by `name`; reuse on cache hit, otherwise create and write
- `ensure_task`: look up `tid` by `aid` (and optional `name`); error on miss
- Cache validation: if `hcloud OptVerse ShowAlgorithm` errors out in the shell, treat the cached `aid` as stale