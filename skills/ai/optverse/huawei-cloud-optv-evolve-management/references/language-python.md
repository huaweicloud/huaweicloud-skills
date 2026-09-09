# Evaluator / baseline / algorithm for Python

OptVerse evolve-task requirements for **Python** projects:

| Role | Form | Key conventions |
|---|---|---|
| Algorithm | Standard Python source file exporting the function to evolve | Specify via `--algorithm_file` + `--algorithm_func_name` |
| Evaluator | Module-level no-arg `def evaluate():` function | `--evaluator_file=<file.py>` + `--evaluator_func_name=evaluate` |
| Baseline | Module-level no-arg `def baseline():` function | `--evaluator_baseline=<file.py>` + `--evaluator_baseline_func_name=baseline` |
| Output | Floating-point number | Direction determined by `--evaluator_parameter.smaller_better` |

> **Empirically relaxed**: `evaluator_file` and `evaluator_baseline` may point to **the same file**, as long as the function names do not collide. A common shape is `algorithm_evaluator.py` containing both `evaluate` and `baseline`.

---

## 1. `EVOLVE_START` / `EVOLVE_END` markers (required reading; empirical notes)

Python algorithm files also support wrapping **the entire function to evolve** (the `def` signature + docstring + function body) with `# EVOLVE_START` / `# EVOLVE_END`. Once the platform recognizes these markers, it replaces the code between them wholesale with the candidate implementation.

Minimal example:

```python
from typing import List

# EVOLVE_START
def sort_algorithm(arr: List[int]) -> List[int]:
    """
    Sort a 1D list in ascending order.
    """
    return sorted(arr)
# EVOLVE_END
```

Conventions:

- `# EVOLVE_START` and `# EVOLVE_END` must appear as a pair, and **only one pair is allowed**
- Wrap the entire function `def <func_name>(...)` (signature + docstring + function body) — let the LLM rewrite the body while keeping the signature
- Outside the markers, keep normal imports, helper functions, and unrelated code
- **Must use `#` (Python single-line comment)**; `//` is not allowed
- **Strongly recommend writing the markers explicitly**: empirically, omitting the markers triggers platform auto-injection that often lands in the wrong place (before the `def` signature); when the LLM replaces the block, it replaces the signature too, producing `IndentationError` and invalidating every candidate
- Between `# EVOLVE_START` and `# EVOLVE_END`, **place only one function** (multiple functions confuse the LLM about which to rewrite)
- **When the markers are present, `--algorithm_func_name` is required but may be empty**: empirically, `CreateEvolveTask` requires the flag to be explicitly present (empty string `""` acceptable) even when markers exist, otherwise backend 500 `functionName is null`
- **`--algorithm_file` must be passed explicitly** (KooCLI `--help` marks it optional, but the backend DB schema is `NOT NULL`; omitting it → MySQL `Column 'algorithm_file' cannot be null` → 500 `eihealth.01000004`)

> See [`templates/python/algorithm.py`](../templates/python/algorithm.py) for a complete template.

---

## 2. File and function naming

- Evaluator / baseline function names **may** be `evaluate` / `baseline` (recommended), but are **not required** — any names work, as long as they match `--evaluator_func_name` / `--evaluator_baseline_func_name`
- `algorithm_file` is usually a different source file from the evaluator; but all functions can live in the same file as long as the names do not collide
- When uploading to OptVerse, `--file_path` must equal `os.path.basename(local_file)`

> **⚠️ Do NOT rename uploaded files!** The platform runs the evaluator by `import`-ing the module using `file_path` as the module name; renaming causes `ModuleNotFoundError`.

---

## 3. Evaluator style (direct call — recommended)

The platform auto-imports the candidate algorithm file (e.g. `sort.py`) into the global namespace; the evaluator just prepares test data, calls the function, and returns the score.

```python
# algorithm_evaluator.py
import time
import random

def evaluate():
    test_data = [random.randint(1, 10_000_000) for _ in range(100_000)]
    start = time.time()
    sort_algorithm(test_data)              # direct call — platform has already imported it
    return time.time() - start             # return the score

def baseline():
    test_data = [random.randint(1, 10_000_000) for _ in range(100_000)]
    start = time.time()
    some_baseline_implementation(test_data)
    return time.time() - start
```

**How it works**: write `from sort import sort_algorithm` (or call `sort_algorithm(...)` directly) in the evaluator; the platform substitutes `sort.py` at evaluation time. This is the most common and simplest pattern.

---

## 4. Baseline style (typical)

```python
def baseline():
    """Baseline function: returns the evaluation score of the original / baseline code.
    Return value semantics must match `evaluate`."""
    score = 0.0  # TODO: fill in the baseline evaluation
    return score
```

---

## 5. Time-based efficiency functions: force concurrency=1

Evaluator functions measuring time (sort, computation duration, etc.) must set concurrency to 1:

```
--evaluator_parameter.evaluator_max_workers=1
--evaluator_parameter.search_max_workers=1
```

Otherwise concurrent execution can race and distort scores.

---

## 6. `output_path`: default blank (no upload)

`CreateEvolveTask --output_path` defaults to "no OBS upload":

```bash
hcloud OptVerse CreateEvolveTask \
  --project_id=<project_id> --algorithm_id=$AID \
  --name="EvolveTask_demo" \
  --description="..." \
  --output_path="" \
  ...
```

Only when the user explicitly wants results in OBS:

1. Follow [`iam-agency.md`](iam-agency.md) to create `policy_ai4s_llma4ad` + `optverse_service_trust`;
2. Follow [`agency-policy.md`](agency-policy.md) for `OptVerse AuthorizePermission`;
3. Then set `--output_path="obs://<bucket>/<prefix>"`.

---

## 7. Create the evolve task

The most common `CreateEvolveTask` shape for Python projects:

```bash
hcloud OptVerse CreateEvolveTask \
  --project_id=<project_id> --algorithm_id=$AID \
  --name="EvolveTask_demo" \
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
  --cli-region=<region>
```

> **Simplified version**: when the algorithm file contains `# EVOLVE_START` / `# EVOLVE_END`, **`--algorithm_func_name` is still required but can be passed as an empty string** (`--algorithm_func_name=""`); the platform extracts the function name from the `def <func_name>(...)` between the markers.

```bash
hcloud OptVerse CreateEvolveTask \
  --project_id=<project_id> --algorithm_id=$AID \
  --name="EvolveTask_demo" \
  --description="You are an algorithm design expert specializing in sorting algorithms. ..." \
  --output_path="" \
  --algorithm_file=sort.py --algorithm_func_name="" \
  --evaluator_file=algorithm_evaluator.py --evaluator_func_name=evaluate \
  --evaluator_baseline=algorithm_evaluator.py --evaluator_baseline_func_name=baseline \
  --evaluator_parameter.search_iterations=10 \
  --evaluator_parameter.search_population_size=4 \
  --evaluator_parameter.search_max_workers=1 \
  --evaluator_parameter.evaluator_max_workers=1 \
  --evaluator_parameter.smaller_better=true \
  --evaluator_parameter.llm_models.1=GLM-5 \
  --cli-region=<region>
```

> For the full flow (including `StartEvolveTask`, status polling, fetching the best code), see [SKILL.md §11](../SKILL.md).