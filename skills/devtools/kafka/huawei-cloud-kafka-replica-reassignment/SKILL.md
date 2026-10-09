---
name: huawei-cloud-kafka-replica-reassignment
description: >
  Kafka 集群副本扩容与分区重分配工具：支持可变副本数（1→2、1→3、2→N）、可调磁盘使用率阈值（默认
  70%）、Web UI 界面（上传 topic/broker 表格、下载模板、调整参数）、三阶段流水线（分配→合并→转
  JSON）每阶段带检查门控、策略化 JSON 文件生成（大 topic 单独出文件、按 N 个 topic 打包，或在 Web UI 上按 topic 个数 / topic 分区大小自定义拆分）、格式
  校验、复核报告生成。触发词：Kafka 副本扩容、加副本、副本数调整、partition reassignment、分区重
  分配、reassignment json、单副本改双副本/多副本、磁盘使用率分配、dolce_main、broker-main、
  topic.xls、broker.xls、kafka reassignment tool。不适用于：仅查询分区现状、非 Kafka 场景的 CSV
  转换、集群装机与部署、Kafka 参数调优。
---

# Kafka Replica Expansion & Partition Reassignment

Expand Kafka cluster partitions from their current replication factor to a target factor and
produce partition reassignment JSON that can be passed directly to
`kafka-reassign-partitions.sh --execute`.

## Configurable Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `replica_count` | 2 | Target replication factor. Accepts 2, 3, N. The scripts add `replica_count - current_replicas` new replicas per partition. |
| `disk_threshold` | 70 | Disk usage ceiling (%). After allocation, no mount point's projected usage may exceed this value. |
| `json_strategy` | `size_10g` | Strategy for splitting the output JSON, described below. |
| `json_strategy_param` | 10 | Strategy parameter (topic-count threshold or size threshold, depending on strategy). |

### JSON Split Strategies

| Strategy | Meaning | Parameter Usage |
|----------|---------|-----------------|
| `size_10g` | Topics with any single partition > 10 GB get their own JSON file; the rest are merged into a common file. | `json_strategy_param` = size threshold (GB), default 10 |
| `topic_count` | Merge N topics into one JSON file. | `json_strategy_param` = topic count, default 10 |
| `single_file` | Merge all partitions into one JSON file. | none |
| `per_topic` | One JSON file per topic. | none |
| `custom` | Combined strategy. | `json_strategy_param` = JSON string, e.g. `{"big_size": 10, "small_batch": 10}`: topics larger than `big_size` get one file each, the remaining topics are packed `small_batch` per file |

Users can also define combined strategies in the UI, e.g. "one file per topic larger than 10 GB,
then 10 topics per file for the rest" — this combination maps to the `custom` strategy.

## The Three Stages (sequential, each gated by checks)

```
Stage 1: Allocate new replicas -> check -> PASS? -> Stage 2
Stage 2: Merge master table  -> check -> PASS? -> Stage 3
Stage 3: Emit JSON           -> check -> PASS? -> Deliver
```

**Gate rule**: after each stage its corresponding validation runs (see
`references/validation-rules.md`). Only a PASS moves to the next stage; a FAIL reports the exact
assertion and offending rows, so fix the data and re-run that stage. The gate lives inside the
scripts themselves (`validate.py`); the Web UI and the CLI share the same checks. **If the
validation module is unavailable, the stage is treated as FAIL** — never silently pass. Later
stages depend on the previous stage's output files.

### Stage 1: Allocate new replicas -> read `references/stage1-allocate.md`

- Input: `topic.xlsx` (current partitions), `broker.xlsx` (disk usage)
- Outputs: `topic.xlsx` (original replica table), `topic_new.xlsx` (new replicas),
  `broker_updated.xlsx` (refreshed disk table)
- Naming: output names are fixed (`topic.xlsx` / `topic_new.xlsx` / `topic_all.xlsx` /
  `broker_updated.xlsx`) and contain no cluster name. Because the input table is *also called*
  `topic.xlsx`, `--output-dir` must differ from the input directory; otherwise the script blocks
  with `OUTPUT_OVERWRITES_INPUT` (rc=1, no artifacts written). Legacy `dolce_main*.csv`
  intermediate files from older versions can still be read.
- Core: process topics in order and bring every partition up to the target replication factor.
  Placement is decided by **projected usage** (current value + the capacity being placed now).
  **Only distinct brokers (L0) are allowed**; new replicas are spread across brokers to avoid
  piling onto one or two, and broker watermarks are refreshed after every allocation.
- Checks: no threshold breach caused by this run (pre-existing over-threshold disks only warn and
  are listed in `pre_existing_over_threshold`), replica count complete, no same-broker conflicts,
  new-replica distribution balanced.
- **When allocation is impossible, block**: `status=FAIL`, exit code 2, **no artifacts written**,
  `blockers` provides quantified gaps — never "place it anyway" to fake a complete plan:
  - `NO_OTHER_BROKER`: only *same-broker different-mount* candidates are within threshold. Kafka
    reassignment JSON forbids duplicate broker IDs in one partition's `replicas` (`log_dirs` can
    only name directories for existing replicas), so such a plan cannot be expressed and would be
    rejected on submission — block instead of degrading.
  - `L3_BLOCKED`: no mount point is within threshold at all (insufficient capacity).

### Stage 2: Merge master table -> read `references/stage2-merge.md`

- Inputs: `topic.xlsx` (original replicas), `topic_new.xlsx` (new replicas)
- Output: `topic_all.xlsx` (merged master table)
- Core: sort by topic total capacity ascending; same topic grouped together, partitions ascending.
- Checks: row count matches, sort order correct, column structure complete.

### Stage 3: Emit JSON -> read `references/stage3-json.md`

- Input: `topic_all.xlsx`
- Outputs: the reassignment JSON file set under `/json/`
- Core: split files by strategy, then validate the generated JSON. The Web UI parameter panel can
  select "split by topic count" or "split by topic partition size" and fill in the parameter; the
  CLI expresses the same choice with `--strategy` + `--strategy-param`.
- Checks: JSON schema valid, file split matches the strategy, `replicas`/`log_dirs` fields
  complete, no duplicate broker IDs per partition (the old L2 exception has been removed — such
  JSON would be rejected by Kafka).
- **Security boundary**: topic names come from user-uploaded Excel files (untrusted input), and
  `per_topic` / `size_10g` / `custom` embed topic names into file names. Before writing, topic
  names are validated against a whitelist (`[A-Za-z0-9._-]`, no `.` / `..`, max length 249) plus a
  realpath containment check; invalid names fail the stage with `INVALID_TOPIC_NAME` and no file
  is written.

## Command Line Usage (headless / CI / agent)

The three stages are standalone CLI scripts that run without the Web UI; chain them in headless
environments as follows:

```bash
# Stage 1: allocate new replicas (--replica-count target factor, --disk-threshold usage %)
python scripts/stage1_allocate.py --topic topic.xlsx --broker broker.xlsx \
    --output-dir out --replica-count 2 --disk-threshold 70

# Stage 2: merge master table
python scripts/stage2_merge.py --main out/topic.xlsx --new out/topic_new.xlsx \
    --output-dir out --replica-count 2

# Stage 3: emit JSON (artifacts land in out/json/)
python scripts/stage3_json.py --input out/topic_all.xlsx --output-dir out \
    --replica-count 2 --strategy size_10g --strategy-param 10
```

`--strategy` values and their parameters: `size_10g` (`--strategy-param` = per-partition capacity
threshold in GB, default 10), `topic_count` (= topics per file), `single_file`, `per_topic`,
`custom` (`--strategy-param` is a JSON string such as
`'{"big_size": 10, "small_batch": 10}'`: topics larger than `big_size` get one file each, the rest
are packed `small_batch` per file).

**Output contract** (identical across the three scripts):

- `stdout` carries exactly one JSON object (stage result + `stats` + `validation`); callers do
  `json.loads(stdout)` directly.
- `stderr` carries a human-readable four-line stage report (stage / inputs / outputs / validation).
- Exit codes: `0` = PASS, `1` = stage validation has FAIL, `2` = blocked
  (`NO_OTHER_BROKER` no distinct broker / `L3_BLOCKED` insufficient capacity; no artifacts written
  in either case).

**Gating**: every script runs its own stage validation (`validate.py`) before exiting and only
returns 0 on PASS — there is no "bypass the validation" path even in headless execution. If
validation fails, do not feed that stage's artifacts downstream; fix the data and re-run the stage.

**Working directory**: Web UI uploads and artifacts land by default under the system temp
directory `kafka-replica-reassignment-work/`, overridable with the `KAFKA_REASSIGN_WORK_DIR`
environment variable; the skill package itself is never written to (the package may be read-only).

## Regression Self-Check (run after any script change)

```bash
python evals/run_evals.py     # exit code = number of failing assertions, 0 = all pass
```

Fixtures are fixed (`evals/fixtures/`, regeneratable with `evals/build_fixtures.py`), artifacts go
to temp directories, and every case verifies that input file shas are unchanged — reruns always
produce the same numbers. Cases cover the golden path, NO_OTHER_BROKER blocking, L3 blocking,
read-only behavior, pre-existing over-threshold disks, replication factor 3, the Stage-3 duplicate-
broker hard check, and topic-name path-traversal interception (eight cases).

## Web UI

Start the UI: `python scripts/app.py` (default port 5000)

UI features:
- **Upload area**: drag-and-drop `topic.xlsx` and `broker.xlsx`
- **Template download**: download blank templates (`topic_template.xlsx`, `broker_template.xlsx`)
- **Parameter panel**: adjust replication factor, disk threshold, JSON strategy and parameters
- **Run button**: run the three-stage pipeline in one click, showing each stage's status live
- **Report view**: show the review report after the pipeline finishes

## Output Format

Every stage reports a fixed four-line format (stage / inputs / outputs / validation) in
the runtime language. This version keeps Chinese runtime labels for those four lines.

The review report (`report.html`) contains: parameter summary, per-stage validation results,
degradation/block list, disk usage distribution, JSON file inventory.

## When to Stop and Ask

Read `references/execution-safety.md`. At minimum, stop when:
- a change to the user's **original input files** is needed
- projected disk usage approaches or exceeds the threshold after allocation
- allocation is blocked (`NO_OTHER_BROKER` / `L3_BLOCKED`), or the merged table / JSON fails validation
- validation fails and the cause is unclear

## File Structure

```
huawei-cloud-kafka-replica-reassignment/
├── SKILL.md
├── README.md                    # quick start, parameters, FAQ
├── evals/
│   ├── evals.json               # regression cases (golden path / NO_OTHER_BROKER / L3 block / read-only / over-threshold / RF 3 / duplicate-broker hard check / topic-name sanitization)
│   ├── run_evals.py             # regression entry: python evals/run_evals.py (exit code = failure count)
│   ├── build_fixtures.py        # regenerate fixtures (deterministic)
│   └── fixtures/                # input tables for NO_OTHER_BROKER / L3 block / over-threshold
├── references/
│   ├── stage1-allocate.md       # Stage 1 detailed rules
│   ├── stage2-merge.md          # Stage 2 merge rules
│   ├── stage3-json.md           # Stage 3 JSON conversion + strategies
│   ├── validation-rules.md      # per-stage validation checklist
│   └── execution-safety.md      # safety rules
├── scripts/
│   ├── app.py                   # Flask Web UI
│   ├── stage1_allocate.py       # Stage 1 script
│   ├── stage2_merge.py          # Stage 2 script
│   ├── stage3_json.py           # Stage 3 script
│   ├── tabio.py                 # intermediate artifact I/O (xlsx/TSV compatible, new names preferred, legacy fallback)
│   ├── validate.py              # validation module
│   ├── report.py                # report generation
│   ├── generate_templates.py    # template generation
│   └── requirements.txt         # dependencies
├── assets/
│   ├── topic_template.xlsx      # topic template
│   └── broker_template.xlsx     # broker template
└── templates/
    └── index.html               # UI page
```