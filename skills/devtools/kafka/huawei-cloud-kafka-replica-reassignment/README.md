# Kafka Replica Expansion & Partition Reassignment

Expand Kafka cluster partitions from the current replication factor to a target factor
(1→2, 1→3, 2→N), pick placements by disk watermarks, and produce partition reassignment JSON
that can be passed directly to `kafka-reassign-partitions.sh --execute`.

Applies to: replica expansion, partition reassignment, cross-mount-point balancing, capacity
feasibility assessment before expansion.
Not for: cluster installation/deployment, Kafka parameter tuning, or merely querying current
partition layout.

---

## 1. Quick Start

### 1.1 Prepare Inputs

Two Excel tables; templates in `assets/` (or regenerate with the UI's "template download", or
`python scripts/generate_templates.py`):

| File | Required columns | Description |
|------|------------------|-------------|
| `topic.xlsx` | Topic / PartitionCount / Partition / Broker ID / Path / Size(GB) | current placement and capacity of every partition replica |
| `broker.xlsx` | Broker ID / Path / Total(GB) / Used(GB) / Usage(%) | capacity and watermark of every broker mount point |

`Size(bytes)` is optional; the scripts back-calculate from `Size(GB)`. Rows missing both are
treated as 0.

### 1.2 Command Line in Three Steps

```bash
# Stage 1: allocate new replicas
python scripts/stage1_allocate.py --topic topic.xlsx --broker broker.xlsx \
    --output-dir out --replica-count 2 --disk-threshold 70

# Stage 2: merge master table
python scripts/stage2_merge.py --main out/topic.xlsx --new out/topic_new.xlsx \
    --output-dir out --replica-count 2

# Stage 3: emit JSON (artifacts land in out/json/)
python scripts/stage3_json.py --input out/topic_all.xlsx --output-dir out \
    --replica-count 2 --strategy size_10g --strategy-param 10
```

Confirm the previous step's exit code is `0` before chaining. Stage 2's inputs are Stage 1's
artifacts; do not hand-edit intermediate tables.

### 1.3 Web UI

```bash
pip install -r scripts/requirements.txt   # Flask needed only for the UI
python scripts/app.py                     # default http://127.0.0.1:5000
```

The UI provides upload, template download, parameter panel, one-click three-stage run, and review
report. Uploads and artifacts land under the system temp directory
`kafka-replica-reassignment-work/`, overridable with `KAFKA_REASSIGN_WORK_DIR`; the skill package
itself is never written to.

The parameter panel's JSON split strategy is a dropdown: **split by topic partition size**
(`size_10g`, fill the GB threshold; topics above it get one file each), **split by topic count**
(`topic_count`, fill topics per file), merge all (`single_file`), one file per topic
(`per_topic`), or custom combination (`custom`, fill size threshold and pack count). Pick and run;
artifacts are downloadable from the result area.

---

## 2. Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--replica-count` | 2 | target replication factor, may be 3, N; adds `target - current` new replicas per partition |
| `--disk-threshold` | 70 | projected usage of any mount point must not exceed this value (%) after allocation |
| `--strategy` | `size_10g` | JSON split strategy, see below |
| `--strategy-param` | 10 | varies by strategy, see below |

### JSON Split Strategies

| Strategy | Meaning | `--strategy-param` |
|----------|---------|--------------------|
| `size_10g` | topics with single partition > threshold get one file each; the rest merge into `1common.json` | capacity threshold GB, default 10 |
| `topic_count` | every N topics one `batch_<n>.json` | topic count |
| `single_file` | all into `all_partitions.json` | ignored |
| `per_topic` | one `<topic>.json` per topic | ignored |
| `custom` | combined: topics larger than `big_size` get one file each; the rest packed `small_batch` per file | JSON string, e.g. `{"big_size": 10, "small_batch": 10}` |

---

## 3. Output Contract

The three scripts behave identically for headless calls and automation:

- `stdout`: **exactly one JSON object** (stage result + `stats` + `validation`), parse with
  `json.loads` directly;
- `stderr`: the human-readable four-line stage report (stage / inputs / outputs / validation);
- exit code: `0` = PASS, `1` = stage validation has FAIL, `2` = blocked
  (`NO_OTHER_BROKER` no distinct broker / `L3_BLOCKED` insufficient capacity, **no artifacts
  written in either case**).

Artifact names are fixed and contain no cluster name:

Stage 1 artifacts: `topic.xlsx` (original replicas), `topic_new.xlsx` (new replicas, 8 columns
including `degradation`), `broker_updated.xlsx` (refreshed watermarks).
Stage 2 artifact: `topic_all.xlsx` (merged master table, 10 columns; 12 columns at factor 3, no
duplicate column names).
Stage 3 artifacts: JSON file set under `json/`, each entry shaped like
`{"topic": "...", "partition": 0, "replicas": [16, 11], "log_dirs": ["any", "..."]}`.

Because Stage 1's input table and its artifact share the name (`topic.xlsx`), `--output-dir` must
not point at the input directory; pointing there is blocked with `OUTPUT_OVERWRITES_INPUT`
(rc=1, no artifacts written) to avoid overwriting the user's current-state table. Legacy
`dolce_main.csv` / `dolce_main_new.csv` / `dolce_main_all.csv` files can still be read, no need to
re-run Stage 1.

**Stage 3 security boundary**: topic names come from user-uploaded Excel files and are untrusted
input; the `per_topic` / `size_10g` / `custom` strategies embed topic names into JSON file names.
Before writing, the scripts validate topic names against a whitelist (Kafka legal names
`[A-Za-z0-9._-]`, no `.` / `..`, max 249 characters) and run a realpath containment check to
confirm the final path stays inside the output directory; an invalid topic name fails the stage
with `INVALID_TOPIC_NAME` and no file is written, and file names are never silently rewritten.

---

## 4. Placement Rules & Blocking

Every partition is brought up to the target factor in topic order. Placement is judged on
**projected usage** (current value + the capacity being placed), and broker watermarks are
refreshed immediately after every placement, so multiple partitions never pile onto one disk.

Priority:

1. **L0 normal**: distinct broker, projected usage within threshold — first choice, and **the only
   admitted level**.
2. **NO_OTHER_BROKER block**: when only same-broker different-mount candidates are within
   threshold, **do not allocate**. Kafka reassignment JSON forbids duplicate broker IDs in one
   partition's `replicas` (`log_dirs` can only name directories for existing replicas), so the
   "same broker, different mount point" plan cannot be expressed and would be rejected on
   submission — the legacy `L2` degraded output is removed and replaced by blocking.
   `status=FAIL`, exit code `2`, no artifacts written; `blockers` gives the gap (0 distinct-broker
   mount points within threshold; add/expand a distinct-broker placement).
3. **L3 block**: when no mount point at all is within threshold (insufficient capacity),
   **do not allocate**; `status=FAIL`, exit code `2`, no artifacts written; `blockers` gives the
   quantified gap (how many replicas short, how many usable mount points, how many distinct-broker
   mount points need to enter the threshold, or how high to raise the threshold).

New replicas are spread across brokers (`asset_partition_balance_max/min`), never piled onto one
or two brokers.

**Pre-existing problems do not block this run**: if a mount point was already over threshold before
this run, it only warns and is listed in `pre_existing_over_threshold` (check 1.1 WARN); it does
not stop this run — hard-blocking would make "fix that disk first" a hidden prerequisite.

---

## 5. Validation & Regression

- Every script runs its own stage validation (`scripts/validate.py`) before exiting and only
  returns 0 on PASS; the Web UI and the CLI share the same checks, and **an unavailable validation
  module is treated as FAIL**, never a silent pass. There is no "bypass the validation" path even
  in headless execution.
- After changing scripts, run the regression:

```bash
python evals/run_evals.py     # exit code = number of failing assertions, 0 = all pass
```

Covers the golden path, NO_OTHER_BROKER block, L3 block, read-only (two runs identical + input
shas unchanged), pre-existing over-threshold disks, factor 3 + `topic_count`, the Stage-3
duplicate-broker hard check, and topic-name path-traversal interception — eight cases. Fixtures
are fixed under `evals/fixtures/`, regeneratable with `evals/build_fixtures.py`.

---

## 6. FAQ

**Q: The script reports `VALIDATOR_UNAVAILABLE` / exit code 1, but the artifacts look fine?**
Treating an unloadable validation module as FAIL is intentional — artifacts without validation
have no basis. Check that `scripts/validate.py` exists under `scripts/` and Python can import it.

**Q: Why am I blocked (NO_OTHER_BROKER / L3_BLOCKED) even though there is usable disk?**
Read the quantified gaps in `blockers`. Two cases:
- `NO_OTHER_BROKER`: within threshold there is **only same-broker different-mount capacity**.
  Kafka reassignment JSON forbids duplicate broker IDs in one partition's `replicas`; the plan
  cannot be expressed and would be rejected on submission, so add a broker or free capacity on
  another broker so a distinct-broker placement enters the threshold.
- `L3_BLOCKED`: no mount point at all is within threshold. Either the target replication factor
  exceeds the usable broker count, or the threshold is set so low that all projections cross it.
  Fix the pre-existing disks or raise `--disk-threshold`.

**Q: Can intermediate CSVs be hand-edited?**
No. Stage 2 parses a fixed column order positionally; hand-added/removed columns will directly
misalign. Adjust via parameters or input tables, then re-run.

**Q: Is `degradation_count > 0` in the report serious?**
Yes. This version only admits L0 (distinct broker) at Stage 1, so `degradation_count > 0` can only
come from legacy artifacts or hand-corrupted intermediate tables — such partitions cannot be
expressed as Kafka reassignment JSON and Stage 3 will reject them as duplicate brokers. Re-run
Stage 1, or add brokers and recompute.

**Q: Can it run read-only ("just compute, don't touch my tables")?**
Yes. Run the same inputs twice: Stage 1 `stats` and `topic_new.xlsx` are byte-identical, and input
file shas are unchanged (regression case 4 enforces this).