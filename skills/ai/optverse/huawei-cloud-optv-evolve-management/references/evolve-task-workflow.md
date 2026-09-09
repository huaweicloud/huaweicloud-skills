# Evolve task management (create / start / stop / delete)

This chapter covers every KooCLI (command-line entry `hcloud`) operation pattern for an Evolve Task.

---

## 1. Full workflow

See the master flow diagram in [SKILL.md §4](../SKILL.md). This chapter focuses on the commands themselves:

| Task stage | hcloud operation | Reference |
|---|---|---|
| Create task | `CreateEvolveTask` | §3 below |
| Start | `StartEvolveTask` | §4 below |
| Status query | `ShowTaskDetails` / `ShowTaskRunningDetails --type=…` | §5 below |
| Fetch results | `ShowTaskResultList` + `ShowTaskResultCommit` | §6 below |
| Fetch logs | `ShowTaskRunningLog` | §7 below |
| Stop | `StopEvolveTask` (dangerous, two-step confirmation) | §8 below |
| Delete | `DeleteEvolveTask` / `BatchDeleteEvolveTask` (dangerous, two-step confirmation) | §8 below |
| Update | `UpdateEvolveTask` (only on DRAFT/PENDING) | §9 below |

---

## 2. Before creating a task: agency + bucket authorization (**only when uploading**)

See commands in [`iam-agency.md`](iam-agency.md) §3-§5 and [`agency-policy.md`](agency-policy.md) §2.

> ⚠️ Only tasks with a **non-empty** `output_path` (e.g. `obs://<bucket>/...`) need authorization. Leaving `output_path=""` (the default, no upload) is always safe and does NOT need an agency. Tasks with a non-empty `output_path` but missing authorization will fail immediately — usually with `OptVerse.1009` / `OBS.0419`.

---

## 3. Create the task (`CreateEvolveTask`)

### 3.1 Python

```bash
hcloud OptVerse CreateEvolveTask \
  --project_id=<project_id> --algorithm_id=<aid> --name="EvolveTask_demo" \
  --description="You are an algorithm design expert specializing in sorting algorithms. ..." \
  --output_path="" \
  --algorithm_file=sort.py --algorithm_func_name=sort_algorithm \
  --evaluator_file=algorithm_evaluator.py --evaluator_func_name=evaluate \
  --evaluator_baseline=algorithm_evaluator.py --evaluator_baseline_func_name=baseline \
  --evaluator_parameter.search_iterations=10 \
  --evaluator_parameter.search_population_size=4 \
  --evaluator_parameter.search_max_workers=1 \
  --evaluator_parameter.evaluator_max_workers=1 \
  --evaluator_parameter.smaller_better=true \
  --evaluator_parameter.llm_models.1=GLM-5 \
  --cli-region=<region> \
  --cli-output=json --cli-query="payload.item.evolve_task_id"
```

### 3.2 C++

```bash
hcloud OptVerse CreateEvolveTask \
  --project_id=<project_id> --algorithm_id=<aid> --name="EvolveTask_cpp_demo" \
  --description="You are an algorithm design expert specializing in sorting algorithms. ..." \
  --output_path="obs://<bucket>/result" \
  --algorithm_file=algorithm.cpp --algorithm_func_name=sort_array \
  --evaluator_file="" --evaluator_func_name="build/evaluate <args>" \
  --evaluator_baseline="" --evaluator_baseline_func_name="build/evaluate <args>" \
  --evaluator_parameter.search_iterations=10 \
  --evaluator_parameter.search_population_size=4 \
  --evaluator_parameter.search_max_workers=2 \
  --evaluator_parameter.evaluator_max_workers=2 \
  --evaluator_parameter.smaller_better=true \
  --evaluator_parameter.llm_models.1=GLM-5 \
  --cli-region=<region> \
  --cli-output=json --cli-query="payload.item.evolve_task_id"
```

> **Field semantics, Python vs C++**:
> - Python: `evaluator_file` is the evaluator source path; `evaluator_func_name` is the function name in that file (default `evaluate`)
> - C++: `evaluator_file` is left blank; `evaluator_func_name` is the post-compile executable command (default `evaluator`, produced by `build_command` compiling `evaluator.cpp`); `algorithm_func_name` is the **function name** to evolve (e.g. `sort_array`), **NOT** the entry command

### 3.3 Important parameters

| Parameter | Recommended value | Notes |
|---|---|---|
| `--output_path` | `""` for no upload / `obs://<bucket>/...` for upload | **No upload is the default**: just leave it blank. The agency + bucket authorization is needed only when the user explicitly wants results in OBS |
| `--evaluator_parameter.smaller_better` | `true` for time / distance metrics; `false` for accuracy / hit metrics | Decides the direction of the baseline |
| `--evaluator_parameter.evaluator_max_workers` | 1 (time-based efficiency functions MUST use 1) / 2 (others) | Concurrent evaluator count |
| `--evaluator_parameter.search_max_workers` | 1 (time-based efficiency functions MUST use 1) / 2 (others) | Concurrent generator count |
| `--evaluator_parameter.search_iterations` | 10 (default, max 100) | Evolution iteration count |
| `--evaluator_parameter.search_population_size` | 4 (default, max 32) | Population size |
| `--evaluator_parameter.llm_models.1` | `GLM-5` etc. (supported models) | Must hit an actually available model name |

> **Time-based efficiency functions MUST use concurrency=1**: functions measuring sort / computation time are extremely concurrency-sensitive; concurrency=1 is a hard requirement.

---

## 4. Start the task

```bash
hcloud OptVerse StartEvolveTask \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --cli-region=<region> \
  --cli-output=json
```

Task state transitions: `DRAFT → PENDING → RUNNING → FINISHED / STOPPED / FAILED`.

---

## 5. Query status

### 5.1 Task details

```bash
hcloud OptVerse ShowTaskDetails \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --cli-region=<region> --cli-output=json
```

### 5.2 Task metadata list (filtered by algorithm)

```bash
hcloud OptVerse ListEvolveTaskMetas \
  --project_id=<project_id> --algorithm_id=<aid> \
  --limit=10 \
  --status_list.1=RUNNING \
  --status_list.2=PENDING \
  --cli-region=<region> --cli-output=json
```

### 5.3 Run details (by `type`)

```bash
hcloud OptVerse ShowTaskRunningDetails \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --type=progress --cli-region=<region> --cli-output=json
```

Allowed `type`: `progress | summary | best_result | generation_stats` (**lowercase underscore**, not uppercase).

### 5.4 Task statistics (per algorithm, all tasks)

```bash
hcloud OptVerse ListEvolveTaskStats \
  --project_id=<project_id> --algorithm_id=<aid> \
  --cli-region=<region> --cli-output=json
```

---

## 6. Task results

### 6.1 Result list

```bash
hcloud OptVerse ShowTaskResultList \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --iteration=-1 --cli-region=<region> --cli-output=json
```

`iteration=-1` means "from the very beginning" (returns all commits, including any pre-iteration-0 entries).

### 6.2 Single commit

```bash
hcloud OptVerse ShowTaskResultCommit \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --commit_id=<commit-id> \
  --iteration=-1 --type=CODE \
  --cli-region=<region> --cli-output=json
```

Allowed `type`: `CODE | INSIGHT | SUMMARY` (**UPPERCASE**, different from `ShowTaskRunningDetails`'s lowercase).

`--iteration` is **required** and acts as a **starting-iteration filter** (NOT a single-round selector): `--iteration=N` returns all commits with `iteration >= N`. Pass `-1` for "from the very beginning" (all commits), or `N >= 0` for "from round N onwards" (includes all subsequent rounds).

> ⚠️ `--commit_id` actually accepts the **fingerprint** (no `sample_X_` prefix), not the `id` field returned by `ShowTaskResultList`:
>
> ```bash
> # ShowTaskResultList returns id like "sample_1_0e76b2e6591df519"
> # --commit_id must take the fingerprint "0e76b2e6591df519"
> COMMIT=$(hcloud OptVerse ShowTaskRunningDetails ... --type=best_result \
>   --cli-output=json --cli-query="payload.item.fingerprint")
> # Use the fingerprint directly in the call
> hcloud OptVerse ShowTaskResultCommit ... --commit_id="$COMMIT" --type=CODE
> ```
>
> Passing the full `sample_X_xxx` causes the API to add another prefix in the path, producing `worktree/sample_1_sample_1_xxx/sort.py does not exist`.

> ⚠️ **`ShowTaskResultCommit --type=CODE` only returns code after the task reaches status=FINISHED**. For STOPPED / FAILED tasks, the worktree archive is cleaned up, and the call returns `eihealth.01000011: object task_results/<project_id>/<aid>/<tid>/<run-stamp>/worktree/<commit_id>/algorithm.py does not exist`.
> In the STOPPED state, `ShowTaskResultList` (metrics list) and `ShowTaskRunningDetails --type=best_result` (best fingerprint + score) still work.
> **The only way to recover the code**: re-run `StartEvolveTask` on the same `task_id` (the platform supports resume), or create a new task.

---

## 7. Run logs

```bash
hcloud OptVerse ShowTaskRunningLog \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --start_byte=0 --cli-region=<region> --cli-output=json
```

`--start_byte` / `--end_byte` are used for incremental fetches.

---

## 8. Stop and delete

```bash
# Actively stop
hcloud OptVerse StopEvolveTask \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --cli-region=<region>

# Delete a single task (dangerous, requires two-step confirmation)
hcloud OptVerse DeleteEvolveTask \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --cli-region=<region>

# Batch delete (max 50 per call)
hcloud OptVerse BatchDeleteEvolveTask \
  --project_id=<project_id> \
  --resources.1=<task-id-1> \
  --resources.2=<task-id-2> \
  --cli-region=<region>
```

> After deletion, result uploads fail immediately and cannot be recovered. If unsure, call `StopEvolveTask` first, then consider `Delete`.

---

## 9. Update the task

```bash
hcloud OptVerse UpdateEvolveTask \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --description="new description prompt" \
  --evaluator_parameter.search_iterations=20 \
  --cli-region=<region>
```

Only allowed in `DRAFT/PENDING`; most fields are rejected in `RUNNING/FINISHED`.

---

## 10. Task state machine

```
       ┌─ StartEvolveTask
DRAFT ─┤
       └─ UpdateEvolveTask
            │
            ▼
PENDING ─── StartEvolveTask triggers
            │
            ▼
RUNNING ─── StopEvolveTask ─▶ STOPPED
            │                  ▲
            ▼                  │
FINISHED ──────────────────────┘
            │
            ▼
FAILED
```

The local cache (`.stats/task_id.csv`) state follows the most recent `ShowTaskDetails` or `ShowTaskRunningDetails` return.