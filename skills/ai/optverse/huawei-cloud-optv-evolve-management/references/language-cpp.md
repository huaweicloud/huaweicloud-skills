# Evaluator / baseline / algorithm for C++

Key differences between C++ and Python projects on OptVerse:

| Role | Python | C++ |
|---|---|---|
| Algorithm source | `algorithm.py`, exports the function to evolve | `sort_algorithm.cpp` (containing `// EVOLVE_START/END`) |
| Evaluator | `evaluate()` in a source file | **Executable command** (with path and command-line arguments) |
| Baseline | `baseline()` in a source file | **Executable command** (may be the same as the evaluator) |
| Output | Function returns a float | Command prints one float line to stdout |
| Build | Not required | `--build_command` compiles `*.cpp`; the artefacts determine the evaluator command |

> **Key points (empirical notes)**:
> - C++ algorithm source files **must** use `// EVOLVE_START` / `// EVOLVE_END` markers to delimit the function under evolution; the platform only replaces code between these two lines.
> - `evaluator_func_name` / `evaluator_baseline_func_name` in C++ are the **post-compile executable command**, which may be "path + executable name + command-line arguments", e.g. `build/evaluate <args>`.
> - `algorithm_func_name` in C++ is the **name of the function being evolved** (e.g. `sort_array`).
> - `evaluator_file` / `evaluator_baseline` in C++ are **left blank**; the command is everything.
> - Creating a C++ project via `CreateAlgorithm` does **NOT** need a `--command` field; `build_command` decides the artefacts, and `evaluator_func_name` decides how to invoke them.

---

## 1. `EVOLVE_START` / `EVOLVE_END` markers (required reading)

C++ algorithm files **must** wrap the function body to evolve with `// EVOLVE_START` and `// EVOLVE_END`. The platform replaces the code between the markers with the candidate implementation; everything outside the markers (including `main`, helper functions, comments) is preserved verbatim.

```cpp
#include <iostream>
#include <cstdlib>
#include <ctime>
#include <chrono>
#include <climits>

// Sort function (example: quicksort)
// EVOLVE_START
void sort_array(double *arr, int n) {
    // Naive bubble sort (for demonstration; low efficiency)
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                double temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}
// EVOLVE_END

// Validate that the result is sorted (non-decreasing)
bool is_sorted(double *arr, int n) { ... }

int main(int argc, char *argv[]) {
    // Parse command-line argument n, generate test data
    // Call sort_array(arr, n) and print elapsed time (ms) to stdout
}
```

Conventions:

- `// EVOLVE_START` and `// EVOLVE_END` must appear as a pair, and **only one pair is allowed**
- The function body in between is what evolves (suggest placing only the function definition)
- Outside the function body (`main` etc.) you can organize freely, but `main` is required so `build_command` produces an executable

---

## 2. Algorithm project (`CreateAlgorithm`)

```bash
hcloud OptVerse CreateAlgorithm \
  --project_id=<project_id> \
  --name="Algorithm_cpp_sort_demo" --lang=c++ \
  --description="Demo C++ evolution" \
  --build_command="bash ./build.sh" \
  --cli-region=<region>
```

Key fields for C++ projects:

| Field | Required | Purpose |
|---|---|---|
| `--lang` | Yes | `c++` |
| `--build_command` | Yes | **Compile command** run by the platform after file upload; determines the artefact path |

> Empirically: what actually drives the evaluator in C++ is the `evaluator_func_name` field (see §4); other C++-unrelated fields can be omitted.

---

## 3. File upload

### 3.1 File-type limits

`SaveAlgorithmFile` accepts most common text suffixes, but empirically rejects script files like `.sh` with "unsupported file type". **For multi-file C++ projects, prefer ZIP (`ImportAlgorithmFile`) directly.**

### 3.2 ZIP packaging requirements

- Archive ≤ 20 MB, must be a valid zip
- Top-level structure directly holds the source files (`.cpp` / `.h` / `CMakeLists.txt` / `build.sh` / `.gitignore` etc.); do not nest extra directories
- **`.gitignore` must be preserved**: the platform uses git to manage the project; `.gitignore` excludes build artefacts (typically `build` / `build/`). If `.gitignore` is missing, build outputs enter git history and disrupt subsequent cmake rebuilds
- `scripts/zip_helper.py` (shipped with this skill) excludes `build` / `__pycache__` / `.git` / `.idea` / `node_modules` and `.o` / `.so` / `.dll` / `.exe` by default; `.gitignore` itself is never excluded

```bash
# Use PowerShell's built-in Compress-Archive
Compress-Archive -Path "D:\path\cpp_sort\*" \
  -DestinationPath "D:\path\cpp_sort.zip" -Force
```

Or use this skill's helper script:

```bash
python scripts/zip_helper.py \
  --src <src_dir> \
  --out <out_zip> --force
```

### 3.3 Upload command

```bash
# 1) Get content_update_at
LUT=$(hcloud OptVerse ShowAlgorithm \
  --project_id=<project_id> --algorithm_id=$AID \
  --cli-region=<region> --cli-output=json \
  --cli-query="payload.item.content_update_at")

# 2) Upload the zip via ImportAlgorithmFile
hcloud OptVerse ImportAlgorithmFile \
  --project_id=<project_id> --algorithm_id=$AID \
  --file=./cpp_sort.zip --last_update_time=$LUT \
  --cli-region=<region>
```

### 3.4 Verification

```bash
hcloud OptVerse ListDirectoryByAlgorithmId \
  --project_id=<project_id> --algorithm_id=$AID \
  --cli-region=<region>

# Expected: .gitignore / CMakeLists.txt / build.sh / sort_algorithm.cpp
```

---

## 4. `evaluator_func_name` / `baseline_func_name` (empirically observed forms)

In C++, `evaluator_func_name` is the post-compile executable command, which can be:

- Command name only: `evaluate`
- Path prefix: `build/evaluate`
- With command-line arguments: `build/evaluate <args>`
- Spaces and argument arrays are allowed; total length ≤ 256

`evaluator_baseline_func_name` may be **the same command** as `evaluator_func_name`.

> **Real-world scenario**: when baseline and evaluator share the same compiled binary, pass the same command for both; the evolve platform distinguishes them by substituting the algorithm file.

---

## 5. Create the evolve task

The most common `CreateEvolveTask` shape for C++ projects:

```bash
hcloud OptVerse CreateEvolveTask \
  --project_id=<project_id> --algorithm_id=$AID \
  --name="EvolveTask_cpp_sort_demo" \
  --description="You are an algorithm design expert specializing in sorting algorithms. ..." \
  --output_path="" \
  --algorithm_file=sort_algorithm.cpp --algorithm_func_name=sort_array \
  --evaluator_file="" --evaluator_func_name="build/evaluate <args>" \
  --evaluator_baseline="" --evaluator_baseline_func_name="build/evaluate <args>" \
  --evaluator_parameter.search_iterations=10 \
  --evaluator_parameter.search_population_size=4 \
  --evaluator_parameter.search_max_workers=1 \
  --evaluator_parameter.evaluator_max_workers=1 \
  --evaluator_parameter.smaller_better=true \
  --evaluator_parameter.llm_models.1=GLM-5 \
  --cli-region=<region>
```

Field semantics: see [SKILL.md §6.1](../SKILL.md).

> For the full flow (including `StartEvolveTask`, status polling, fetching the best code), see [SKILL.md §11](../SKILL.md).

---

## 6. evaluator / baseline command: stdout protocol

`evaluator` / `baseline` commands must print the final score (a floating-point number) as a line to stdout:

```
$ ./build/evaluate <args>
17.43821
```

The platform reads the float from that line and populates `best_result.value`.

> **No extra output**: the evaluation logic reads only the first line; route other logs to stderr.

---

## 7. Debugging and build failures

Check `ShowTaskRunningLog` for build errors:

```bash
hcloud OptVerse ShowTaskRunningLog \
  --project_id=<project_id> --evolve_task_id=<tid> \
  --start_byte=0 --cli-region=<region>
```

Common symptoms and handling:

| Symptom | Handling |
|---|---|
| `error: undefined reference to xxx` | Check that all `*.cpp` files are uploaded to the same algorithm project; or that `CMakeLists.txt` lists them |
| `bash ./build.sh` fails with `rm build/* -rf` (build/ doesn't exist on first run) | Change `build.sh` to use `rm -rf build` instead of `rm build/* -rf` |
| `evaluator: command not found` | The artefact name (in `CMakeLists.txt`'s `add_executable`) doesn't match `evaluator_func_name` |
| `output not a number` | The evaluator command outputs a non-number; only allow `%.6f\n` |
| CMake fails during build and `build/` already exists | Usually historical build residue (`.gitignore` not uploaded or not effective); run `rm -rf build` and retry |