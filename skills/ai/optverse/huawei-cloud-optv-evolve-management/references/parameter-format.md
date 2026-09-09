# Parameter forms and hcloud CLI usage

## 1. General parameter form

```bash
hcloud OptVerse <Operation> \
  --cli-region=<region> \
  --project_id=<project-id> \
  --<body-param>=<value> ... \
  --cli-output=json \
  [--cli-query="<jmespath>"]
```

Key points:

- Region and project ID are required; fallback to profile / environment variables if not passed
- `body`-type parameters are passed directly as `--key=value`
- `query`-type parameters are also passed as `--key=value`
- `path`-type parameters become URL path segments (hcloud builds the URL based on the command — no need to write it manually)
- `formData`-type parameters (file uploads) are passed as `--file=<path>` referring to a local file

---

## 2. Nested objects and arrays

### 2.1 Nested objects

Use dot-notation for nesting:

```bash
--metadata.name=demo \
--evaluator_parameter.search_iterations=10 \
--evaluator_parameter.search_population_size=4
```

### 2.2 Arrays

Use `.<N>` indices, starting from 1:

```bash
# LLM model list
--evaluator_parameter.llm_models.1=GLM-5 \
--evaluator_parameter.llm_models.2=GPT-X

# Batch delete tasks
--resources.1=<task-id-1> \
--resources.2=<task-id-2>
```

### 2.3 Keys with dots in comments

The evolve algorithm side does not currently use keys with dots like `network.alpha.kubernetes.io/default-security-group`, but if introduced in the future, you can:

1. Use `--cli-jsonInput` to pass JSON directly (ASCII, remove BOM)
2. Or replace dots with hyphens (hcloud will fill back in, but only for some endpoints)

If hcloud limits apply (see [`troubleshooting.md`](troubleshooting.md)), you can use a Python helper script in `scripts/` to work around it.

---

## 3. Enums and value ranges

`hcloud --help` gives explicit value ranges (e.g. `lang` only allows `python|c++|java`). They must be strictly observed. Common key constraints:

| Parameter | Values |
|---|---|
| `--lang` | python \| c++ \| java |
| `--evaluator_parameter.smaller_better` | true \| false |
| `--cli-output` | json \| table \| yaml etc. |
| `--type` (ShowTaskRunningDetails) | progress \| summary \| best_result \| generation_stats |
| `--type` (ShowTaskResultCommit) | CODE \| INSIGHT \| SUMMARY |

---

## 4. Array / object size limits

| Parameter | Limit |
|---|---|
| `evaluator_parameter.llm_models` | ≤ 30 |
| `resources` (BatchDeleteEvolveTask) | ≤ 50 task IDs |
| `name` (algorithm) | ≤ 128 |
| `name` (evolve_task) | ≤ 64 |
| `description` (evolve_task) | ≤ 65536 |
| `description` (algorithm) | ≤ 32768 |
| `command`, `build_command`, `env` | ≤ 256 |
| `output_path` | ≤ 256 |
| `evaluator_file`, `evaluator_baseline` | ≤ 65536 |
| `algorithm_file` | ≤ 256 |

---

## 5. JMESPath filtering (`--cli-query`)

hcloud's `--cli-query` supports JMESPath. It reduces returned fields and eases downstream processing:

```bash
# Only show ID and name
hcloud OptVerse ListAlgorithms \
  --limit=10 \
  --cli-region=<region> \
  --cli-output=json \
  --cli-query="payload.list[*].{id:id,name:name,lang:lang}"

# Directly extract the best iteration value
hcloud OptVerse ShowTaskRunningDetails \
  --project_id=<project_id> \
  --evolve_task_id=<tid> \
  --type=best_result \
  --cli-region=<region> \
  --cli-output=json \
  --cli-query="payload.item.value"
```

---

## 6. File upload (`formData`)

`SaveAlgorithmFile` / `ImportAlgorithmFile` need `--file`:

```bash
hcloud OptVerse SaveAlgorithmFile \
  --project_id=<project_id> \
  --algorithm_id=<aid> \
  --file=./build.py \
  --file_path=build.py \
  --last_update_time=<millis> \
  --cli-region=<region> \
  --cli-output=json
```

Constraints:

- Single file ≤ 5 MB (SaveAlgorithmFile)
- Zip ≤ 20 MB (ImportAlgorithmFile), must be a valid zip
- File names must be consistent with other files in the target project to avoid import failure during evaluation

---

## 7. CreateEvolveTask required-field 3-layer breakdown

Before running `CreateEvolveTask`, the agent runs a self-check on the 6 required fields. The "3-layer breakdown" asks: (1) does the agent need to ask the user for this? (2) must the hcloud parameter be passed? (3) must the value be non-empty?

| Field | Agent must ask user | hcloud param must be passed | hcloud value must be non-empty |
|---|---|---|---|
| `--algorithm_file` | ✅ | ✅ | ✅ (Python / C++ both required; missing it → backend 500) |
| `--algorithm_func_name` | ✅ | ✅ **MUST be passed.** Python: pass function name (e.g. `sort_algorithm`) OR empty string `""` (when `algorithm.py` has `# EVOLVE_START` / `# EVOLVE_END` markers — platform auto-extracts from the `def` inside). C++: pass function name (e.g. `sort_array`). **Empirically verified**: `CreateEvolveTask` requires the flag to be explicitly present (empty string `""` acceptable) even when markers exist, otherwise backend 500 `functionName is null`. | ⚠️ Python auto-extract mode allows empty `""`; otherwise must be non-empty |
| `--evaluator_file` | ✅ | ✅ | Python required / **C++ empty `""`** |
| `--evaluator_func_name` | ✅ | ✅ | ✅ |
| `--evaluator_baseline` | ✅ | ✅ | Python required / **C++ empty `""`** |
| `--evaluator_baseline_func_name` | ✅ | ✅ | ✅ |

**Key distinctions**:

- **Agent must ask user**: collected from user before starting the task (so commands later won't fail on missing args)
- **hcloud param must be passed**: the parameter name must appear on the command line (empty-string value is allowed)
- **hcloud value must be non-empty**: the value cannot be empty (except C++'s intentional empty `""` for `evaluator_file` / `evaluator_baseline`)

Example: C++ `--evaluator_file=""` is "param passed + value empty"; Python `--evaluator_func_name=evaluate` is "param passed + value non-empty".