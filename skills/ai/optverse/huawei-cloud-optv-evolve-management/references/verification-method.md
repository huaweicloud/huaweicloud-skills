# Verification methods

After each group of operations, use the tables below to quickly confirm that the results match expectations.

---

## 1. IAM agency

| Operation | Verification command | Expected |
|---|---|---|
| List agencies | `hcloud IAM ListAgencies --domain_id=<id> --cli-region=<region>` | Returns a JSON array containing the target agency |
| Details | `hcloud IAM ShowAgency --agency_id=<id> --domain_id=<id>` | `agency.name`, `agency.trust_domain_name`, etc. match expectations |

---

## 2. Algorithm project

| Operation | Verification command | Expected |
|---|---|---|
| Create design project | `hcloud OptVerse ShowAlgorithm --project_id=<project_id> --algorithm_id=<aid> --cli-region=<region>` | `payload.item.id` matches the passed-in `<aid>`; `content_update_at` returns a millisecond timestamp |
| Python single-file / multi-file upload | `hcloud OptVerse ListDirectoryByAlgorithmId --project_id=<project_id> --algorithm_id=<aid>` | List contains uploaded `.py` files (evaluator / baseline may be the same file or different files) |
| C++ multi-file / ZIP upload | Same as above | List contains `evaluator.cpp` / `baseline.cpp` / `algorithm.cpp` / `CMakeLists.txt` / `build.sh` / `.gitignore` etc. |
| ZIP upload | Same as above | List contains every file path inside the ZIP |
| Read file content | `hcloud OptVerse ShowAlgorithmFile --project_id=<project_id> --algorithm_id=<aid> --file_path=<path>` | `payload.item.data`, after decoding from base64, matches the local file |
| Modify metadata | `hcloud OptVerse ShowAlgorithm ...` | `payload.item.description` / `build_command` updated |

---

## 3. Evolve task

| Operation | Verification command | Expected |
|---|---|---|
| Create task | `hcloud OptVerse ShowTaskDetails --project_id=<project_id> --evolve_task_id=<tid>` | `payload.item.status == "DRAFT"` |
| Start task | `ShowTaskDetails` | Status changes to `PENDING` → `RUNNING` within 60 s |
| Progress query | `hcloud OptVerse ShowTaskRunningDetails --type=progress --evolve_task_id=<tid>` | `payload.item.iteration` increases monotonically |
| Summary stats | `--type=summary` | `payload.item` includes `baseline_value`, `final_best_value`, `total_individuals` |
| Best result | `--type=best_result` | `payload.item.fingerprint` is non-empty (after the task has run) |
| Result list | `hcloud OptVerse ShowTaskResultList --evolve_task_id=<tid>` | Elements of `payload.list[]` include `commit_id`, `iteration` |
| Single commit | `hcloud OptVerse ShowTaskResultCommit --commit_id=<cid> --iteration=-1 --type=CODE ...` | `payload.item` contains the actual code (**note**: `--iteration` is required; `--commit_id` takes the fingerprint, without the `sample_X_` prefix) |
| Actively stop | `StopEvolveTask` + `ShowTaskDetails` | Status `STOPPED` |
| Delete | `DeleteEvolveTask` + `ShowTaskDetails` | 404 / task no longer present under the project |

---

## 4. Bucket authorization

| Operation | Verification command | Expected |
|---|---|---|
| Authorize | `hcloud OptVerse ListPermission --cli-region=<region>` | Returned list contains the target bucket |
| List buckets | `hcloud OptVerse ListBuckets --cli-region=<region>` | Bucket list under the current account |
| List objects | `hcloud OptVerse ListObject --bucket=<bucket> --cli-region=<region>` | Object prefixes inside the bucket |
| Revoke | Run `ListPermission` again | Bucket is gone from the list |

---

## 5. End-to-end verification checklist

To start an end-to-end evolve task, go through this checklist item by item:

> Items marked "upload scenario" only apply when `output_path=obs://<bucket>/...`; skip them all for the default scenario.

- [ ] `hcloud configure list` shows credentials are present and not leaked
- [ ] (upload scenario) `hcloud IAM ListAgencies` shows the `optverse_service_trust` agency exists
- [ ] (upload scenario) Custom policy `policy_ai4s_llma4ad` is attached to the agency (`ListAttachedAgencyPoliciesV5`)
- [ ] `ListAlgorithms` can list the account's existing algorithm projects
- [ ] `CreateAlgorithm` returns a valid `algorithm_id`
- [ ] Python: `SaveAlgorithmFile` uploads evaluator / baseline / algorithm Python files successfully (file name is governed by `--file_path`, just needs to match `--evaluator_file` / `--algorithm_file` in `CreateEvolveTask`)
- [ ] C++: `CreateAlgorithm --build_command="..."` set correctly; `SaveAlgorithmFile` or `ImportAlgorithmFile` uploads evaluator.cpp / baseline.cpp / .gitignore etc.
- [ ] `ListDirectoryByAlgorithmId` lists all uploaded files (algorithm + evaluator + baseline, possibly in the same file)
- [ ] (upload scenario) `AuthorizePermission` completes bucket authorization
- [ ] `CreateEvolveTask` returns an `evolve_task_id`
- [ ] Python: `--evaluator_file=<file> --evaluator_func_name=evaluate --evaluator_baseline=<file> --evaluator_baseline_func_name=baseline` correct
- [ ] C++: `--algorithm_func_name=<func>` and `--evaluator_func_name=<cmd>` correct (empirically: function name + post-compile command)
- [ ] After `StartEvolveTask`, status moves to PENDING → RUNNING
- [ ] `ShowTaskRunningDetails --type=progress` returns progress
- [ ] `ShowTaskResultCommit --commit_id=<fingerprint> --iteration=-1 --type=CODE` retrieves concrete code
- [ ] Task ends with status FINISHED
- [ ] `StopEvolveTask` / `DeleteEvolveTask` succeed after two-step confirmation
- [ ] Local caches `.stats/algorithm_id.csv` and `.stats/task_id.csv` match the actual operations