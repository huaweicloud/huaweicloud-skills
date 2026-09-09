# Results, logs, status queries and best practices

## 1. Result-query actions overview

| Action | hcloud operation |
|---|---|
| Progress (current iteration, running status) | `ShowTaskRunningDetails --type=progress` |
| Summary statistics (baseline / final_best / total_individuals…) | `ShowTaskRunningDetails --type=summary` |
| Best result (commit_id + value) | `ShowTaskRunningDetails --type=best_result` |
| Per-generation stats | `ShowTaskRunningDetails --type=generation_stats` |
| Global task statistics | `ListEvolveTaskStats --algorithm_id=<aid>` |
| Result list (all commits) | `ShowTaskResultList` |
| Single commit's code | `ShowTaskResultCommit --type=CODE` |
| Single commit's summary | `ShowTaskResultCommit --type=SUMMARY` |
| LLM reflection (Insight) | `ShowTaskResultCommit --type=INSIGHT` |

> **Note**: the two command groups use different casing for `--type`:
> - `ShowTaskRunningDetails --type=` uses **lowercase underscore** (`progress` / `summary` / `best_result` / `generation_stats`)
> - `ShowTaskResultCommit --type=` uses **UPPERCASE** (`CODE` / `SUMMARY` / `INSIGHT`)

---

## 2. Typical query flow

```bash
# 1. List all running tasks under the current algorithm
hcloud OptVerse ListEvolveTaskMetas \
  --project_id="$PROJECT_ID" --algorithm_id="$AID" \
  --status_list.1=RUNNING --status_list.2=PENDING \
  --cli-region=<region> --cli-output=json

# 2. Fetch the best commit
hcloud OptVerse ShowTaskRunningDetails \
  --project_id="$PROJECT_ID" --evolve_task_id="$TID" --type=best_result \
  --cli-region=<region> --cli-output=json \
  --cli-query="payload.item"
```

Common fields in `payload.item`:

| Field | Meaning |
|---|---|
| `fingerprint` | Best result commit identifier |
| `iteration` | Corresponding iteration round |
| `value` | Evaluation score (interpreted per `smaller_better`) |

```bash
COMMIT=$(hcloud OptVerse ShowTaskRunningDetails \
  --project_id="$PROJECT_ID" --evolve_task_id="$TID" --type=best_result \
  --cli-region=<region> --cli-output=json \
  --cli-query="payload.item.fingerprint")
ITER=$(hcloud OptVerse ShowTaskRunningDetails \
  --project_id="$PROJECT_ID" --evolve_task_id="$TID" --type=best_result \
  --cli-region=<region> --cli-output=json \
  --cli-query="payload.item.iteration")

# 3. Fetch the best commit's code
ITER=$(python scripts/cache.py get-iteration --commit-id "$COMMIT")
hcloud OptVerse ShowTaskResultCommit \
  --project_id="$PROJECT_ID" --evolve_task_id="$TID" --commit_id="$COMMIT" \
  --iteration="$ITER" --type=CODE --cli-region=<region> --cli-output=json

# 4. View LLM reflection (Insight) if needed
hcloud OptVerse ShowTaskResultCommit \
  --project_id="$PROJECT_ID" --evolve_task_id="$TID" --commit_id="$COMMIT" \
  --iteration="$ITER" --type=INSIGHT --cli-region=<region> --cli-output=json
```

---

## 3. Log retrieval

```bash
# Fetch logs
hcloud OptVerse ShowTaskRunningLog \
  --project_id="$PROJECT_ID" --evolve_task_id="$TID" \
  --start_byte=0 --cli-region=<region> --cli-output=json
```

You can paginate via `payload.item.next_byte` and `payload.item.log_content`.

---

## 4. Status field reference

```text
DRAFT     — task created but not started
PENDING   — waiting for scheduling / resource preparation
RUNNING   — evolution in progress
FINISHED  — evolution complete (success or configured limit reached)
STOPPED   — user actively stopped
FAILED    — failed
```

---

## 5. Best practices

1. **Force concurrency=1 for time-based evaluators**: for evaluator functions that measure sort/computation time (in either Python or C++), set `--evaluator_parameter.evaluator_max_workers=1` and `--evaluator_parameter.search_max_workers=1` — otherwise you get spurious "the more concurrency, the faster" pseudo-optimizations.
2. **Append a timestamp to task names**: use `EvolveTask_YYYYMMDD_HHMMSS` to differentiate entries in the list.
4. **The `description` IS the LLM prompt**: it is fed directly to the LLM, so it must contain role, background, objective, constraints, and output format.
3. **Agency before bucket authorization**: run `IAM CreateAgency` first, then `OptVerse AuthorizePermission`.
4. **C++ projects must specify `build_command`**: ensure evaluator.cpp / baseline.cpp / algorithm.cpp all compile into runnable binaries; the binary name (CMakeLists `add_executable`) must match `evaluator_func_name` / `evaluator_baseline_func_name`.
5. **File names must be consistent end-to-end**: the uploaded filename (`--file_path`) must equal the local `os.path.basename` and be identical to `--evaluator_file` and other parameters.
6. **Stop before delete**: call `StopEvolveTask` before deletion to prevent result-upload interruptions.
7. **Cache must stay in sync with reality**: refresh `.stats/task_id.csv` after every create / query / delete on tasks.