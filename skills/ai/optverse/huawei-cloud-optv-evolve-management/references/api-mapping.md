# OptVerse API to KooCLI (command-line entry `hcloud`) mapping

This document maps every OptVerse / IAM operation touched by this skill to its KooCLI (command-line entry `hcloud`) invocation form.

> **⚠️ Mandatory rule**: all calls must go through `hcloud OptVerse <Operation>` or `hcloud IAM <Operation>`. Manually constructing HTTP requests or calling the OpenAPI directly via `requests` is forbidden.
>
> This skill only handles **code-evolution** operations (`CreateEvolveTask` / `ShowTask*` / … / `ListEvolveTaskMetas`). Operations outside this scope (math programming, cutting, etc., with a `service_type` parameter) are not covered by this document.

---

## 1. General conventions

### 1.1 Region and project

OptVerse endpoints are region-scoped services; you must pass both the region and the project ID:

| Parameter | Source | Notes |
|---|---|---|
| `--cli-region` | User-specified or read from env var | Region; KooCLI defaults to profile-based resolution, but the `HUAWEI_CLOUD_REGION` env var is recommended |
| `--project_id` | IAM query or env var | Project-level ID; KooCLI can also infer from the profile's `cli-project-id` |

Global services like `IAM CreateAgency` ignore the region, but you can still pass it.

### 1.2 Output and filtering

- Recommended: use `--cli-output=json` for structured return values
- Optional: `--cli-output=table` for human-friendly tabular output
- Optional: `--cli-query="<jmespath>"` for field filtering, e.g. `--cli-query="payload.item.id"`
- Any operation can use `hcloud --debug ...` (**global flag**, not a subcommand parameter) to print request / response details for troubleshooting; some subcommands (e.g. `CreateEvolveTask`) do not accept the subcommand-level `--cli-debug=true`

---

## 2. Algorithm design projects

| Purpose | hcloud operation | Method |
|---|---|---|
| List algorithm projects | `hcloud OptVerse ListAlgorithms` | GET |
| Create design project | `hcloud OptVerse CreateAlgorithm` | POST |
| Get algorithm details | `hcloud OptVerse ShowAlgorithm` | GET |
| Update algorithm project | `hcloud OptVerse UpdateAlgorithm` | PATCH |
| Delete algorithm project | `hcloud OptVerse DeleteAlgorithm` | DELETE |
| List algorithm files | `hcloud OptVerse ListDirectoryByAlgorithmId` | GET |
| Get algorithm file content | `hcloud OptVerse ShowAlgorithmFile` | GET |
| Save / upload algorithm file | `hcloud OptVerse SaveAlgorithmFile` | PUT |
| Initialize via ZIP | `hcloud OptVerse ImportAlgorithmFile` | PUT |

### 2.1 Key parameters

`CreateAlgorithm` / `UpdateAlgorithm`:
- Required `name`, `lang` (`python` | `c++` | `java`)
- Optional `description`, `build_command`, `env`, `command`, `picture`
- `build_command` is used in C++ projects to compile uploaded `.cpp` files into executable commands

`SaveAlgorithmFile` uploads via formData:
- `--file` — local file path
- `--file_path` — server-side storage path (must be consistent with other places)
- `--last_update_time` — must match the algorithm's current `content_update_at` (call `ShowAlgorithm` to fetch first)

`ImportAlgorithmFile`: upload a zip (≤ 20 MB); only `--file` and `--last_update_time` required.

---

## 3. Evolve tasks

| Purpose | hcloud operation | Method |
|---|---|---|
| Create evolve task | `hcloud OptVerse CreateEvolveTask` | POST |
| Update evolve task | `hcloud OptVerse UpdateEvolveTask` | PATCH |
| Get task details | `hcloud OptVerse ShowTaskDetails` | GET |
| Start task | `hcloud OptVerse StartEvolveTask` | POST |
| Stop task | `hcloud OptVerse StopEvolveTask` | POST |
| Delete single task | `hcloud OptVerse DeleteEvolveTask` | DELETE |
| Batch delete tasks | `hcloud OptVerse BatchDeleteEvolveTask` | POST |
| Task list (by algorithm) | `hcloud OptVerse ListEvolveTaskMetas` | GET |
| Task statistics (across algorithms) | `hcloud OptVerse ListEvolveTaskStats` | GET |
| Run details (progress / summary / best_result / generation_stats) | `hcloud OptVerse ShowTaskRunningDetails` | GET |
| Result list | `hcloud OptVerse ShowTaskResultList` | GET |
| Single commit result | `hcloud OptVerse ShowTaskResultCommit` | GET |
| Run log | `hcloud OptVerse ShowTaskRunningLog` | GET |

### 3.1 `ShowTaskRunningDetails` type enum

| type | Meaning |
|---|---|
| `progress` | Current iteration / running status |
| `summary` | baseline / final_best / total / duration etc. summary |
| `best_result` | Best result's `commit_id` and score |
| `generation_stats` | Per-generation statistics |

> ⚠️ Values use **lowercase underscore** (different from `ShowTaskResultCommit --type=CODE/SUMMARY/INSIGHT` which uses uppercase).

> ⚠️ `--type=summary` only has complete content after `status=FINISHED`; during RUNNING / PENDING, `payload.item` fills up gradually, and on **STOPPED / FAILED, `payload.item` is empty `{}`**.
> For "current best individual" info, switch to `--type=best_result` (works in any state; returns `{fingerprint, iteration, value, metric_name, population_index}`).
> `--type=progress` and `--type=generation_stats` work normally under RUNNING / FINISHED; on STOPPED they may also be empty.

### 3.2 `CreateEvolveTask` key body

| Field | Required | Range | Notes |
|---|---|---|---|
| `algorithm_id` | Yes | [1,128] | Algorithm project ID |
| `name` | Yes | [0,64] | Task name |
| `description` | Yes | [1,65536] | Task prompt (LLM input) |
| `evaluator_file` | Python yes / C++ no | [0,65536] | Python: evaluator file path; C++: leave blank |
| `evaluator_func_name` | Yes | [1,256] | Python: evaluator function name; C++: evaluator command |
| `evaluator_baseline` | Python yes / C++ no | [0,65536] | Python: baseline file path; C++: leave blank |
| `evaluator_baseline_func_name` | Yes | [1,256] | Python: baseline function name; C++: baseline command |
| `output_path` | Yes (can be blank) | [0,256] | Result OBS path; **leave blank when not uploading** |
| `evaluator_parameter.evaluator_max_workers` | Yes | [1,32] | Max evaluator count |
| `evaluator_parameter.llm_models.1,llm_models.2…` | Yes | string array | LLM models in use |
| `evaluator_parameter.search_iterations` | Yes | [1,100] | Max evolution iterations |
| `evaluator_parameter.search_population_size` | Yes | [1,32] | Population size |
| `evaluator_parameter.smaller_better` | No | bool | Whether smaller is better (default `true`) |
| `algorithm_file` | No | [0,256] | Algorithm source file path |
| `algorithm_func_name` | **Yes (can be `""`)** | [0,256] | Algorithm function name (C++ may use as entry command); empirically, `CreateEvolveTask` requires the flag to be explicitly present (empty string acceptable) even when `# EVOLVE_START` markers exist, otherwise backend 500 `functionName is null` |

### 3.3 hcloud array syntax (KooCLI notation)

`evaluator_parameter.llm_models` is an array; KooCLI represents it as:

```
--evaluator_parameter.llm_models.1=GLM-5
--evaluator_parameter.llm_models.2=GPT-X
```

`BatchDeleteEvolveTask`'s `--resources.[N]` follows the same pattern.

---

## 4. Bucket authorization (OBS)

| Purpose | hcloud operation | Method |
|---|---|---|
| List buckets | `hcloud OptVerse ListBuckets` | GET |
| List objects in a bucket | `hcloud OptVerse ListObject` | GET |
| Grant OptVerse service permission on a bucket | `hcloud OptVerse AuthorizePermission` | PUT |
| Revoke authorization | `hcloud OptVerse RevokePermission` | PUT |
| List current authorization relations | `hcloud OptVerse ListPermission` | GET |

> **Agency must exist before authorization**: without an IAM Agency, `AuthorizePermission` will fail. See [`iam-agency.md`](iam-agency.md) for agency creation.

---

## 5. IAM Agency

| Purpose | hcloud operation | Method |
|---|---|---|
| Create custom policy | `hcloud IAM CreateAgencyCustomPolicy` | POST |
| Create agency | `hcloud IAM CreateAgency` | POST |
| List agencies | `hcloud IAM ListAgencies` | GET |
| Get agency details | `hcloud IAM ShowAgency` | GET |
| List attached policies | `hcloud IAM ListAttachedAgencyPoliciesV5` | GET |
| Attach policy to agency | `hcloud IAM AttachAgencyPolicyV5` | POST |
| Detach policy | `hcloud IAM DetachAgencyPolicyV5` | POST |
| Update agency | `hcloud IAM UpdateAgency` | PUT |
| Delete agency | `hcloud IAM DeleteAgency` | DELETE |

Parameter details: see [`iam-agency.md`](iam-agency.md).

---

## 6. Command conventions

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=<region>

# Verify
hcloud configure list
hcloud OptVerse ListBuckets --cli-region=<region> --cli-output=json
hcloud IAM ListAgencies --domain_id=<domain-id> --cli-region=<region> --cli-output=json
```

> Never paste AK/SK in plaintext in conversations or scripts. Use `hcloud configure list` only to check that credentials exist.