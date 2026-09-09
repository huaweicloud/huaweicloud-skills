# Troubleshooting

Grouped by error type: parameter errors, auth errors, agency / bucket authorization errors, upload errors, runtime errors.

---

## 1. Parameter / command errors

| Error keywords | Cause | Resolution |
|---|---|---|
| `Missing required option '--xxx'` | Required parameter not passed | Re-run `hcloud OptVerse <Op> --help` to verify parameters |
| `value should be one of [...]` | Illegal enum value | Only pass legal values like `python|c++|java`, `true|false` |
| `length should be at most N` | Length limit exceeded | Trim `name` / `description` etc. |
| `array item count should be at most N` | Array too long (e.g. `llm_models` ≤ 30) | Limit the LLM model count; batch-delete N ≤ 50 |
| `output_path should not be empty when bucket permission required` | Left `output_path` blank but no agency was set up | **Leave blank if no upload needed**; for upload, set up agency + authorization first |

Diagnostic flow:

1. `hcloud OptVerse <Op> --help` to verify parameters (**official authority**)
2. Check dot-nesting: `--evaluator_parameter.search_iterations`
3. Array index starts from 1: `--evaluator_parameter.llm_models.1=...`
4. Check whether required / optional fields are missing or duplicated

---

## 2. Auth / credential errors

| Error | Cause | Resolution |
|---|---|---|
| `APIGW.0301` / 401 / `The token is invalid` | Token expired / AK/SK wrong | Re-inject credentials; verify with `hcloud configure list` |
| `APIGW.0311` / 404 / `project id is invalid` | Project ID does not exist | Confirm in the IAM console; hcloud can also infer from profile |
| `APIGW.0303` / 403 / `Required action xxx` | IAM missing an action | See [`iam-policies.md`](iam-policies.md) §3 to add the action |

Diagnostic commands:

```bash
hcloud configure list
hcloud OptVerse ListBuckets --cli-region=<region> --cli-output=json
```

---

## 3. Agency / bucket authorization errors

| Error | Cause | Resolution |
|---|---|---|
| `IAM.0025` / `AgencyNotFound` | The IAM agency `optverse_service_trust` was not created | `hcloud IAM CreateAgency --agency.name=optverse_service_trust` |
| `IAM.0050` / `PolicyNotAttached` | `policy_ai4s_llma4ad` was not attached to the agency | `hcloud IAM AttachAgencyPolicyV5 --agency_id=... --policy_id=...` |
| `IAM.0043` / `CannotDeleteAgencyInUse` | Deleting an agency that is still referenced | First `OptVerse RevokePermission`, then delete the Agency |
| `OptVerse.1009` / `User has no authority to operate the bucket` | No bucket authorization | `hcloud OptVerse AuthorizePermission --bucket=<bucket>` |
| `OBS.0419` / `Insufficient bucket policy permissions` | Bucket policy was manually cleaned | Same as above — re-authorize |
| `OBS.0404` / `BucketNotFound` | Wrong bucket name or cross-account | Confirm in the OBS console that the bucket exists |
| `IAM.0009` / `DomainNotMatch` | `trust_domain_name` is wrong | Use the official OptVerse account |
| `IAM.0008` / `PermissionDenied` | The creator's account lacks `iam:agencies:create` | Ask the account admin to grant the permission or switch accounts |

Diagnostic sequence:

```bash
# 1. Check whether the agency exists
hcloud IAM ListAgencies --domain_id=<my-account-id> \
  --cli-region=<region> --cli-output=json

# 2. Check the policies attached to the agency
hcloud IAM ListAttachedAgencyPoliciesV5 \
  --agency_id=<agency-id> \
  --cli-region=<region>

# 3. Check bucket authorization
hcloud OptVerse ListPermission \
  --project_id=<project_id> --cli-region=<region> --cli-output=json
```

---

## 4. File upload errors

| Error | Cause | Resolution |
|---|---|---|
| `last_update_time is invalid` | Did not call `ShowAlgorithm` to fetch `content_update_at` before uploading | Follow the strict flow in [`algorithm-workflow.md`](algorithm-workflow.md) §3 |
| `evolve.01050007` / `File has been modified by another user` | After the previous upload, `content_update_at` was refreshed and the old value is now invalid | **Before every `SaveAlgorithmFile` / `ImportAlgorithmFile`, you MUST re-run `ShowAlgorithm` to get the latest `content_update_at`** |
| `Failed to read file parameter: unsupported file type` | The file extension in `SaveAlgorithmFile --file=...` is not allowed (e.g. `.sh`) | Multi-file C++ projects: switch to `ImportAlgorithmFile` + zip; see [`language-cpp.md`](language-cpp.md) §3 |
| `file size exceeds 5MB` | Single file exceeds the limit in `SaveAlgorithmFile` | Switch to `ImportAlgorithmFile` with a ZIP (≤ 20 MB) |
| `invalid zip file` | `ImportAlgorithmFile` failed | Verify zip validity with `7z t` |
| `file not allowed` | Zip contains forbidden extensions | Remove `*.exe` / `*.so`, repack the zip |

---

## 5. Evolve runtime errors

### 5.1 Python project

| Error | Cause | Resolution |
|---|---|---|
| `Evaluator module not found` | Evaluator filename inconsistent | The uploaded file name must match `--evaluator_file` |
| `Evaluator function not found` | Wrong function name | Keep `--evaluator_func_name` consistent with `def evaluate():` |
| `Baseline function not found` | Wrong baseline function name | Keep `--evaluator_baseline_func_name` consistent with `def baseline():` |
| `output_path is invalid` | Output path is not a valid OBS URL | Use `obs://<bucket>/<dir>`; the bucket must be authorized first |
| `name 'sort_algorithm' is not defined` | Evaluator in Mode A without `from sort import sort_algorithm` | Use `from <module> import <func>` instead |

### 5.2 C++ project

| Error | Cause | Resolution |
|---|---|---|
| `build failed: command not found` | Compiler path in `build_command` is invalid | Use absolute paths or verify with `which` |
| `bash ./build.sh: line 1: rm: build/*: No such file or directory` | `build` directory does not exist on first build | Change `build.sh` to `rm -rf build` or add `&& mkdir -p build` |
| `evaluator: command not found` | The build artefact is not exposed in `command` / `evaluator_func_name` | Fix `build_command` to emit an executable; ensure `evaluator_func_name` matches the `add_executable(...)` name |
| `evaluator returned non-zero` | The executable returns a non-zero exit code | Check stderr; usually path errors |
| `evaluator output not a number` | stdout did not print a float line per protocol | Only print `%.6f\n`; route logs to stderr |
| `algorithm_main not found` | `--algorithm_func_name` does not match the artefact in `build_command` | Fix `command` / `algorithm_func_name`, or add a `cp` step |
| `EVOLVE_START / EVOLVE_END_END not found` | Algorithm source file missing markers | Add `// EVOLVE_START` and `// EVOLVE_END` around the function to evolve |

General:

| Error | Cause | Resolution |
|---|---|---|
| `model xxx is not available` | Wrong LLM model name | Confirm available models via platform docs |
| `Evolve task status is FAILED` | Task failed | First read the full `ShowTaskRunningLog`; common causes: bucket unauthorized or unauthorized, or description too long |

---

## 6. Empty progress / statistics fields

| Field | When value is empty | Resolution |
|---|---|---|
| `payload.item.iteration` | `RUNNING` but `iteration=0` | Wait 30–60 s and retry, or confirm the task was not rejected by `START` |
| `payload.item.fingerprint` | `ShowTaskRunningDetails --type=best_result` returns nothing | The task has not produced any commits yet; keep waiting for RUNNING |

---

## 7. hcloud tool limitations

| Limitation | Scenario | Resolution |
|---|---|---|
| Keys with `.` are interpreted by hcloud as nesting points | Some custom annotation fields | Avoid keys with `.` in scripts; if necessary, use inline `python -c` to bypass |
| `--cli-jsonInput` UTF-8 BOM parsing fails | JSON input with special encoding | Convert to ASCII or strip the BOM |
| `--dryrun` inconsistent with actual request behavior | hcloud bug | Always use `hcloud --debug ...` for debugging (see the real request). Note: **`--debug` is an `hcloud` global flag**, not a subcommand parameter; some subcommands (e.g. `CreateEvolveTask`) do not accept subcommand-level `--cli-debug=true` |

---

## 8. Debug template

> ⚠️ KooCLI's `--debug` is an **`hcloud` global parameter**, used as `hcloud --debug OptVerse <Op> ...`.
> Some subcommands (e.g. `CreateEvolveTask` empirically) do not accept subcommand-level `--cli-debug=true`, and report "incorrect parameter: cli-debug".

```bash
# Enable hcloud debug
hcloud --debug OptVerse <Op> --cli-region=<region> \
  --cli-output=json --project_id=<project_id> ...

# Extract only payload
... --cli-query="payload"

# Only view HTTP status
hcloud --debug OptVerse <Op> ... 2>&1 | grep -i "http/1\.1"
```

---

## 8. 5xx Internal Error

`eihealth.01000004 "Internal error"`: a generic error wrapper by the KooCLI client; **the original error lives in the backend logs**. Recommend adding `--debug` to record the request timestamp (with millisecond precision) + full payload + `X-Request-Id`, and provide that to ops for backend log lookup. **Wrapping automatic retries is discouraged** — a 500 is a data / state error; retrying does not solve it and only pollutes the backend logs.

---

## 9. Diagnostic sequence summary

1. `hcloud OptVerse <Op> --help` — check parameters
2. `hcloud configure list` — check credentials
3. `hcloud IAM ListAgencies` — check whether the agency exists
4. `hcloud OptVerse ListBuckets` — check account connectivity
5. `hcloud OptVerse ListPermission` — check bucket authorization
6. `hcloud OptVerse ShowTaskRunningLog` — view runtime logs