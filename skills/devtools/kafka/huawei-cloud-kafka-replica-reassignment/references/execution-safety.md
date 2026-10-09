# Execution Safety Rules

## Exit-Code Contract (read this first)

All three stage scripts share the same exit codes, because callers (CI, headless agents, upstream
orchestrators) can only judge "can I continue?" from the exit code:

| Exit code | Meaning | What the caller should do |
|-----------|---------|---------------------------|
| `0` | PASS: stage finished and validation passed | proceed to next stage |
| `1` | validation FAIL (`reason=VALIDATION_FAIL` / `VALIDATOR_UNAVAILABLE`) | stop and fix; do **not** continue to the next stage |
| `2` | blocked (`reason=NO_OTHER_BROKER` no distinct broker / `L3_BLOCKED` insufficient capacity) | stop; feed the quantified gaps in `blockers` back to the user |

Supporting I/O contract:

- **stdout carries exactly one JSON object** (the stage result); callers do `json.loads(stdout)`;
- **stderr carries the human-readable four-line report** (stage / inputs / outputs / validation);
  do not parse it for decisions;
- this design keeps "machine decision" and "human report" independent: mixing logs into stdout
  would silently break parsing in some cases.

## Scenarios Where You Must Stop and Ask

### 1. Changing the original input files

The original `topic.xlsx` / `broker.xlsx` are the user's production data, **read-only**. All new
information goes into new files (`topic_new.xlsx`, `broker_updated.xlsx`). If the flow needs to
modify an original file, stop and ask.

### 2. Disk usage over threshold

- **Over-threshold caused by this run** (> disk_threshold): FAIL, must stop and report which
  broker mount point was driven over.
- **Pre-existing over-threshold**: does not block this run (new replicas route around those
  disks), surfaces as WARN + `pre_existing_over_threshold`, and advises fixing the disk
  separately.
- **Approaching threshold** (within threshold - 2%): continue but warn.

### 3. Allocation blocked

- **NO_OTHER_BROKER** (no distinct broker): within threshold only same-broker different-mount
  candidates remain. Kafka reassignment JSON forbids duplicate broker IDs in one partition's
  `replicas` (`log_dirs` can only name directories for existing replicas), so this plan cannot be
  written to the JSON and would be rejected on submission — the old L2 degradation is removed and
  replaced by blocking.
- **L3_BLOCKED** (insufficient capacity): no mount point at all is within threshold.

Both **stop, write no artifacts**, exit code 2, and `blockers` gives quantified gaps (how many
replicas short and their sizes; how many distinct-broker / same-broker mount points are within
threshold; how many distinct-broker mount points to add / how many GB to free / or to raise the
threshold).

**"Write no artifacts" is a hard requirement**: if the blocked stage still left half-finished
tables/JSON behind, downstream code may take them as a usable plan and execute it. Better to keep
the output directory empty than to hand out a plan that looks complete but is wrong.

### 4. Validation fails for an unclear reason

If validation FAILs but you cannot locate the cause, do not "fix it and continue" on your own.
Report the symptom and wait for the user's decision.

### 5. Large replication-factor changes

When `replica_count >= 3` and the number of brokers < 10, the high-availability constraint may be
unsatisfiable. Assess feasibility before acting.

## File Location & Package Hygiene

The installed skill package may live on a read-only directory, and **the package must never
contain runtime artifacts**:

- all intermediate/final artifacts are written to the caller-specified `--output-dir`; scripts
  never write inside the package;
- the Web UI (`scripts/app.py`) working directory is a per-user temp directory
  (`%TEMP%/kafka-replica-reassignment-work`), not an in-package `work/` — otherwise a single UI
  upload would leave runtime residue in the skill package;
- scripts set `sys.dont_write_bytecode = True` at startup so execution never creates
  `__pycache__` under `scripts/` (compiled caches would pollute the deliverable);
- the regression suite (`evals/run_evals.py`) treats "no new files in the skill package" as an
  assertion, enforcing this.

## Irreversible Operations

The following are irreversible and require explicit confirmation:

- deleting already-generated JSON files
- overwriting `topic_all.xlsx`
- clearing the `/json/` directory

## Read-Only

The whole pipeline is read-only over its inputs; this is part of the promise:

- never modify the original `topic.xlsx` / `broker.xlsx`;
- running twice with the same parameters must produce identical results (stable sorting, no
  dependence on dict iteration order or run time);
- the regression suite compares sha256 of input files for every scenario: after the run they must
  equal the before-run value.

## Drift Handling

If a user hand-edits an intermediate artifact (e.g. edits `topic_new.xlsx` directly), on the next
run:

1. re-run with the same parameters into a fresh output directory and compare with the hand-edited
   files;
2. when differences are found, **report the difference, do not auto-overwrite**;
3. let the user choose: keep the hand-edits (skip that stage) or use the script output (overwrite).