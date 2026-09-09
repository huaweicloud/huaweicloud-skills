# scripts/ directory guide

> All scripts in this directory **do NOT call `hcloud`** — they only do local helper work. The actual interaction with OptVerse is done by the agent executing `hcloud` commands directly in Bash.

## Script list

| File | Purpose | Calls hcloud? |
|---|---|---|
| `precheck.sh` | One-shot environment check (5 items: hcloud on PATH / version / credentials / region / OptVerse connectivity); bash version | No |
| `precheck.ps1` | Same 5 checks as `precheck.sh`, but for Windows PowerShell 5.1 (this skill has verified it passes 5/5) | No |
| `cache.py` | Local CSV cache for `<algorithm_id>` / `<evolve_task_id>` / `last_update_time`; **does NOT invoke hcloud** (agent orchestrates the flows in shell) | No |
| `zip_helper.py` | Local ZIP packing with explicit exclusion rules; pair with `ImportAlgorithmFile --file=…` | No |

---

## precheck.sh / precheck.ps1

5-item environment check dispatched via `skill action=exec` **before starting any task**.

| Check item | Maps to SKILL.md |
|---|---|
| `hcloud` on PATH | §1.1 KooCLI Installation |
| `hcloud version` (first-run terms accept) | §1.1 |
| `hcloud configure list` (credentials configured) | §1.2 Credentials (AK/SK) |
| region configuration (env / profile) | §1.2 |
| OptVerse connectivity (`ListBuckets` probe) | §1.5 Agency + bucket authorization precondition |

**What precheck does NOT cover** (verify separately):

- §1.3 Python interpreter (precheck does not probe `python`)
- §1.4 IAM permissions (precheck does not validate IAM actions)
- §1.5 Agency creation + bucket authorization (precheck only verifies connectivity, does not actually create agency / authorize bucket)

**Output**: `summary` mode by default; set `CHECK_OUTPUT_MODE=detail` for per-check details.

**Exit code**: `0 = all pass`, `1 = one or more FAIL`.

**Usage** (via `skill action=exec`):

```bash
# Windows PowerShell (preferred — system-installed PS 5.1, verified)
powershell scripts/precheck.ps1

# Git Bash / MSYS2 bash (last resort — WSL bash not verified)
bash scripts/precheck.sh
```

> ⚠️ **Windows shell choice**: prefer `powershell`. Avoid `bash` on Windows: `where bash` may resolve to `C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\bash.exe` (a WSL launcher stub that hangs on "install WSL" when WSL is absent); **WSL bash is NOT verified by this skill**.

---

## cache.py

Local CSV cache for `<algorithm_id>` / `<evolve_task_id>` / `last_update_time`. Use via `$(python scripts/cache.py ...)` to retrieve IDs before running commands:

```bash
AID=$(python scripts/cache.py ensure-algorithm --name "p1test")
TID=$(python scripts/cache.py ensure-task --aid "$AID")

# last_update_time: agent runs hcloud + put-lut explicitly
LUT=$(hcloud OptVerse ShowAlgorithm --algorithm_id="$AID" \
  --cli-region="$REGION" --cli-output=json \
  --cli-query="payload.item.content_update_at")
python scripts/cache.py put-lut --aid "$AID" --lut "$LUT"

# Then later:
LUT=$(python scripts/cache.py get-lut --aid "$AID")
```

Also usable as a Python module:

```python
from scripts.cache import (
    ensure_algorithm, ensure_task, get_lut,
    put_algorithm, put_task, put_lut,
)
```

Subcommands: `ensure-algorithm` / `put-algorithm` / `ensure-task` / `put-task` / `get-lut` / `put-lut`.

> **cache.py does NOT invoke hcloud**: all `last_update_time` flows are orchestrated by the agent in shell; cache.py is a pure-local tool requiring no IAM permission. It only reads / writes the local `.stats/algorithm_id.csv` and `.stats/task_id.csv` files.

See [`scripts/cache.py`](cache.py) header for full details.

---

## zip_helper.py

Local ZIP packing with explicit exclusion rules; pair with `ImportAlgorithmFile --file=…`:

```bash
# Pack the zip (explicit exclusions: build/__pycache__/.git/.idea/node_modules + *.o/*.so/*.dll/*.exe)
python scripts/zip_helper.py \
  --src ./cpp_sort \
  --out ./cpp_sort.zip --force
```

### Collaboration with `hcloud`

After the agent has the zip, in Bash:

```bash
hcloud OptVerse ImportAlgorithmFile \
  --project_id=<project_id> --algorithm_id=<aid> \
  --file=./cpp_sort.zip --last_update_time=<ms> \
  --cli-region=<region>
```

### Why we keep `zip_helper.py`

| Tool | Reads `.gitignore`? | Excludes `*.exe` / `*.so` / `*.o` etc.? |
|---|---|---|
| `scripts/zip_helper.py` | No (uses hard-coded rules) | Yes (suffix-based whitelist) |
| PowerShell `Compress-Archive` | No | No (empirically bundles build artefacts) |
| Linux `zip` | No | No (full default) |

PowerShell `Compress-Archive` worked for multi-file C++ projects only because the `cpp_sort/build/` directory did not yet exist at that point; once cmake actually produces an executable, PowerShell's `zip` will pack it together with everything else.

`.gitignore` **must be preserved** in the zip (see `templates/README.md` for the rationale).

---

## Dependencies

- Python 3.8+
- Standard library only (`zipfile` / `csv` / `pathlib` / `os` / `argparse`); no third-party dependencies
