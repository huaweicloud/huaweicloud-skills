# Validation Rules

Every stage must run its validation; **only a PASS may proceed to the next stage**.

Validation is not a "checklist in a document" but the gate on the execution path:

- the three stage scripts call `validate.py` themselves in `main()`
  (`validate_stage1/2/3`), and the result is written into the stage JSON's `validation` field;
- on validation FAIL the script flips `status` to `FAIL`, sets `reason=VALIDATION_FAIL`, and
  returns according to the exit-code contract;
- if `validate.py` itself is unavailable (import failure, etc.), it **must be treated as FAIL**
  (`reason=VALIDATOR_UNAVAILABLE`) — silently passing is the same as having no gate, which is most
  dangerous in headless execution;
- the Web UI calls the same functions; it does not re-implement validation, so UI and CLI cannot
  disagree.

## Table of Contents
1. [Stage 1 Validation](#stage-1-validation)
2. [Stage 2 Validation](#stage-2-validation)
3. [Stage 3 Validation](#stage-3-validation)
4. [WARN vs FAIL](#warn-vs-fail)
5. [Validation Output Format](#validation-output-format)

## Stage 1 Validation

| # | Check | PASS condition | On failure |
|---|-------|----------------|------------|
| 1.1 | Disk usage threshold | after allocation every mount point usage ≤ disk_threshold | threshold breach **caused by this run** → FAIL listing mount points; **pre-existing** over-threshold → WARN (not FAIL), advise fixing the disk |
| 1.2 | Replica completeness | every partition's replica count = replica_count | FAIL listing missing topic/partition |
| 1.3 | Same-broker conflicts | no two replicas of one partition on the same broker (this version only admits distinct brokers) | FAIL listing conflicting rows |
| 1.4 | Degradation marker | PASS output must contain no non-empty `degradation` (legacy L2/L3 or hand-edited data) | FAIL listing annotated rows |
| 1.5 | Blocking residue | no L3 records | FAIL — L3 means the stage should have blocked; artifacts are untrustworthy |
| 1.6 | Balance & fairness | new replicas spread across brokers; overall partition distribution not extreme | WARN (advisory, non-blocking), with both numeric views |
| 1.7 | Size consistency | `topic_new.xlsx` Size matches the corresponding partition in `topic.xlsx` | FAIL listing mismatches |

**Why 1.1 separates "pre-existing over-threshold"**: exported broker tables often already contain
disks above the threshold. Failing on all of them would make the tool unusable on dirty production
data — and fixing old disks is a separate task. The criterion is "**did this run make a disk
worse**", not "is a disk currently good". Pre-existing issues surface as WARN and are listed in
`stats.pre_existing_over_threshold` so the user knows which disks to fix.

**Why 1.6 looks at new-replica distribution**: which brokers host the new replicas is what this
run can directly control; the overall partition distribution is historical baggage. The primary
criterion is "are new replicas piled onto one or two brokers"; the overall distribution is printed
as reference. Imbalance is only WARN because it is a long-term load issue, not a
plan-executability issue.

## Stage 2 Validation

| # | Check | PASS condition | On failure |
|---|-------|----------------|------------|
| 2.1 | Row count match | `topic_all.xlsx` rows = partition count | FAIL with expected/actual |
| 2.2 | Sort order | topics sorted by total capacity ascending, partitions ascending within topic | WARN (order does not affect correctness) |
| 2.3 | Column structure | required columns present and **no duplicate column names** | FAIL listing missing columns |
| 2.4 | No missing partitions | every (topic, partition) appears | FAIL with missing count |
| 2.5 | No duplicate rows | each (topic, partition) appears exactly once | FAIL with duplicate count |
| 2.6 | Size consistency | merged Size matches source files | judged together with 2.1/2.4 |
| 2.7 | Allocation-column completeness | every partition carries all `replica_count-1` non-empty Allocation columns | FAIL listing topics/partitions missing columns |

**About 2.7**: Stage 1 artifacts are complete in normal operation. Once an intermediate file is
hand-edited or misaligned, empty Allocation rows would silently pass the old Stage 2 and turn into
an obscure log_dirs validation failure at Stage 3. 2.7 stops the "missing new replica" bad row at
the source and names the partition, so a broken table never walks all the way to the JSON.

**Why 2.3 checks duplicate column names**: with many replicas, if every new replica were named
`Path`, the table would have multiple `Path` columns and downstream name-based lookups would read
the wrong one. Column names must be unique (`Allocation Path 1` / `Allocation Path 2` …), and
parsing must be **positional**, not by name.

## Stage 3 Validation

| # | Check | PASS condition | On failure |
|---|-------|----------------|------------|
| 3.1 | JSON syntax valid | every file `json.loads()`-able | FAIL with syntax error location |
| 3.2 | Top-level structure | `partitions` array + `version=1` | FAIL |
| 3.3 | Entry complete | every entry has topic/partition/replicas/log_dirs | FAIL listing missing fields |
| 3.4 | No duplicate replicas | one partition's `replicas` has no duplicate broker (Kafka hard constraint) | FAIL, with an added explanation when the entry carries `degradation=L2` (the old L2-EXCEPTION pass is removed) |
| 3.5 | Replicas length | `len(replicas) = replica_count` | FAIL with entry |
| 3.6 | log_dirs length | `len(log_dirs) = replica_count` | FAIL with entry |
| 3.7 | Partition total | total entries across all files = merged-table row count | FAIL with difference |
| 3.8 | No missing/duplicate | every (topic, partition) appears exactly once | FAIL with list |
| 3.9 | File naming | file names follow the strategy rules **and** pass the security whitelist (topic names only `[A-Za-z0-9._-]`, no `.` / `..`, ≤249) and the realpath containment check | FAIL (`INVALID_TOPIC_NAME`, no file written); case-only topic-file-name collisions are **auto-disambiguated** (later name gets a deterministic suffix `__<hash8>`), recorded in `stats.filename_disambiguations` |
| 3.10 | log_dirs format | first is `"any"`, the rest are mount paths + `/kafka-logs` | FAIL |

**Why 3.4 no longer has an L2 exception**: Kafka reassignment JSON forbids duplicate broker IDs in
one partition's `replicas` — `log_dirs` can only name directories for replicas that already exist,
so "same broker, different mount point" cannot be expressed; `replicas=[1,1]` is rejected by Kafka
on submission. The old version recorded such hits as an exception and let them pass, equivalent to
delivering an unexecutable plan, so this version fails them all:
- duplicate broker → `3.4 FAIL`, message lists the duplicated broker IDs;
- if the entry carries `degradation=L2`, the FAIL detail adds the explanation: the scenario should
  have been blocked at Stage 1 with `NO_OTHER_BROKER`;
- the `l2_exception_count` / `l2_exception_partitions` stats are removed from stage results.

**log_dirs normalization**: table mount points may carry a `/kafka-logs` suffix (or not).
Generation strips any existing suffix then re-concatenates, avoiding `.../kafka-logs/kafka-logs`.

**3.9 case-collision note**: Kafka topic names are case-sensitive; one table can legally contain
both `ITDE_PROD_AD_DIM_LKP` and `ITDE_PROD_ad_dim_lkp`. On case-insensitive file systems
(Windows/macOS) the two names would silently overwrite each other as file names. Stage 3 checks
with `normcase` before writing: on a hit it does **not** block (legal data) but appends a
deterministic suffix to the later file (e.g. `ITDE_PROD_ad_dim_lkp__c038f388.json`) and records the
rename in `stats.filename_disambiguations`; case-sensitive systems (Linux) do not trigger and keep
original names.

**3.9 security-whitelist note**: topic names come from user-uploaded Excel (untrusted input);
`per_topic` / `size_10g` / `custom` use them to build file names; names containing `/`, `..` or
absolute paths would write outside the output directory. Before writing, topic names are checked
against a whitelist (Kafka legal names `[A-Za-z0-9._-]`, no `.` / `..`, ≤249) then a realpath
containment check; either failing → `FAIL(INVALID_TOPIC_NAME)` and no file is written.

## WARN vs FAIL

- **FAIL**: artifacts are untrustworthy or unexecutable; the stage verdict is `FAIL`, exit code
  non-zero; must fix.
- **WARN**: the plan is executable but carries a risk the user should know about (pre-existing
  over-threshold disks, new-replica distribution not spread enough, topic order differing from
  expectation). WARN **never** fails the stage — otherwise every minor deviation would require a
  human and the tool would be unusable.

The criterion is "does this information change the user's decision about the plan", not "is this
information important".

## Validation Output Format

One line per check, `[id] status detail`:

```
1.1 PASS max=37.84%, threshold=70.0%
1.2 PASS all 22 partitions have 2 replicas
1.6 PASS new-replica distribution max=3/broker, min=0/broker
```

WARN example:

```
1.1 WARN pre-existing over-threshold (not caused by this run, fix the disk first): broker 1, mount /srv/BigData/data1: 90.00%
```

FAIL example:

```
1.1 FAIL this run pushed a mount point over threshold: broker 3, mount /srv/BigData/data2: 72.15% > 70%
1.2 FAIL replica count incomplete: topicA/p0; topicA/p3
```

Stage summary (written into the stage JSON's `validation.summary` and the four-line stderr report):

```
=== Stage 1 validation ===
PASS: 6  WARN: 1  FAIL: 0
Conclusion: PASS (proceed to next stage)
```