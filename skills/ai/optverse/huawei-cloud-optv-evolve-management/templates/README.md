# templates/ directory guide

> Templates are split by language: `cpp/` for C++ projects, `python/` for Python projects.
> The agent can copy them directly and modify as needed.

| Sub-directory | Contains file | Purpose |
|---|---|---|
| `python/` | `evaluator.py` | Mode A: after the platform imports the candidate code, this file just calls the function directly and returns the score |
| `python/` | `baseline.py` | No-argument `baseline()` that returns a float |
| `python/` | `algorithm.py` | Algorithm source file, with `# EVOLVE_START` / `# EVOLVE_END` wrapping the whole function |
| `cpp/` | `evaluator.cpp` | Evaluator command source — prints the score to stdout; compiled by `build_command` |
| `cpp/` | `baseline.cpp` | Baseline command source — same protocol as the evaluator |

## Python usage

```bash
# You may rename these files; just keep them consistent with --evaluator_file / --algorithm_file
cp templates/python/algorithm.py  algorithm.py
cp templates/python/evaluator.py evaluator.py
cp templates/python/baseline.py  baseline.py
# For multi-file projects, prefer zip + ImportAlgorithmFile (one-shot upload; see scripts/README.md §zip_helper.py)
python scripts/zip_helper.py --src ./src --out algorithm.zip --force
hcloud OptVerse ImportAlgorithmFile \
  --project_id=<project_id> --algorithm_id=<aid> \
  --file=./algorithm.zip --last_update_time=<ms> \
  --cli-region=<region> --cli-output=json
```

> **`algorithm.py` must contain `# EVOLVE_START` / `# EVOLVE_END`**: these markers wrap the entire function to be evolved (the `def` signature + function body). Without them the platform's auto-injection lands in the wrong place, causing `IndentationError` in every LLM candidate — see [`references/language-python.md` §1](../references/language-python.md).
>
> **Mainstream mode (empirically)**: this skill ships with the minimal "**Mode A direct call**" template — the platform handles importing the candidate code, and the evaluator just calls the function and returns the score. **Users most commonly use Mode A**: write `from sort import sort_algorithm` (or call `sort_algorithm(...)` directly) inside the evaluator, and the platform substitutes `sort.py`. Mode B (read `candidate_code.py` then `exec`) is supported as a fallback — see `references/language-python.md` §2.

## C++ usage

```bash
cp templates/cpp/evaluator.cpp evaluator.cpp
cp templates/cpp/baseline.cpp  baseline.cpp

# The algorithm source file must contain // EVOLVE_START / // EVOLVE_END markers wrapping the function to evolve.
# Example: sort_algorithm.cpp contains:
#   // EVOLVE_START
#   void sort_array(double *arr, int n) { ... }
#   // EVOLVE_END
#
# And provide a complete main(argc, argv[]) for receiving command-line arguments and printing elapsed time.

# When creating the algorithm project, only build_command is needed (no --command)
hcloud OptVerse CreateAlgorithm \
  --project_id=<project_id> --name=Algo_cpp_demo --lang=c++ \
  --build_command="bash ./build.sh" \
  --cli-region=<region>

# For multi-file C++ projects, prefer zip + ImportAlgorithmFile
python scripts/zip_helper.py \
  --src <src_dir> \
  --out <out_zip> --force

hcloud OptVerse ImportAlgorithmFile \
  --project_id=<project_id> --algorithm_id=<aid> \
  --file=./cpp_sort.zip --last_update_time=<ms> \
  --cli-region=<region>

# Create the evolve task (evaluator_file left blank; evaluator_func_name holds the command directly)
hcloud OptVerse CreateEvolveTask \
  --project_id=<project_id> --algorithm_id=<aid> \
  --name="EvolveTask_cpp" --description="..." \
  --output_path="" \
  --algorithm_file=sort_algorithm.cpp --algorithm_func_name=sort_array \
  --evaluator_file="" --evaluator_func_name="build/evaluate <args>" \
  --evaluator_baseline="" --evaluator_baseline_func_name="build/evaluate <args>" \
  --evaluator_parameter.evaluator_max_workers=1 \
  --evaluator_parameter.search_max_workers=1 \
  --evaluator_parameter.search_iterations=10 \
  --evaluator_parameter.search_population_size=4 \
  --evaluator_parameter.smaller_better=true \
  --evaluator_parameter.llm_models.1=GLM-5 \
  --cli-region=<region>
```

### `.gitignore` notes (required reading)

> `.gitignore` **must be preserved inside the zip**.
>
> Why:
> - The platform uses **git** to manage projects (the zip upload triggers `git init`)
> - `.gitignore` typically contains `build` / `build/` to exclude cmake build artefacts
> - Without `.gitignore`, build outputs enter git history
> - On the next cmake rebuild, those residues interfere with the new build (a typical symptom: `build/` already exists and breaks `cmake -B build` behavior)
>
> This skill's `scripts/zip_helper.py` excludes `build` / `__pycache__` / `.git` / `.idea` / `node_modules` and `.o` / `.so` / `.dll` / `.exe` by default; `.gitignore` itself is never excluded.

### `evaluator_func_name` command format

Empirically, three forms are accepted:

```
evaluate                             # executable name only
build/evaluate                       # path + executable name
build/evaluate <args>                 # path + executable name + command-line arguments
```

Total length ≤ 256 characters.

> For Python / C++ semantic differences, see [`references/language-python.md`](../references/language-python.md) and [`references/language-cpp.md`](../references/language-cpp.md).