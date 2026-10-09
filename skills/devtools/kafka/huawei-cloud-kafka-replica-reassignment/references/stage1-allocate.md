# Stage 1: Allocate New Replicas

## Table of Contents
1. [Input Files](#input-files)
2. [Command Line](#command-line)
3. [Allocation Rules](#allocation-rules)
4. [Placement & Blocking: L0 / NO_OTHER_BROKER / L3](#placement--blocking-l0--nootherbroker--l3)
5. [Disk Threshold & Projection](#disk-threshold--projection)
6. [Balance & Fairness](#balance--fairness)
7. [Outputs](#outputs)

## Input Files

### topic.xlsx (current partition layout)

| Column | Description |
|--------|-------------|
| Topic | Topic name (partitions of the same topic appear contiguously) |
| PartitionCount | Total partition count |
| Partition | Partition ID (0-based) |
| Broker ID | Broker hosting the current replica |
| Path | Mount point of the current replica |
| Size(bytes) | Partition data size in bytes |
| Size(GB) | Partition data size in GB |

### broker.xlsx (current disk usage)

| Column | Description |
|--------|-------------|
| Broker ID | Broker number |
| Host | Host IP |
| Disk (Used \| Total) | Disk usage summary (display only) |
| Partition | Device name |
| Mount Point | Mount path |
| Used (GB) | Used space |
| Total (GB) | Total capacity |
| Usage (%) | Used / total. **May be a string like `'90.00%'`; strip the `%` when parsing.** |

One broker can have multiple rows (multiple mount points); placement is decided at the
**mount-point** granularity, not the broker granularity.

Header names are matched flexibly: the English canonical names are preferred, and legacy
Chinese-language header names from production exports are also accepted.

## Command Line

```bash
python scripts/stage1_allocate.py \
  --topic assets/topic_template.xlsx \
  --broker assets/broker_template.xlsx \
  --output-dir /tmp/out \
  --replica-count 2 \
  --disk-threshold 70
```

- `--replica-count`: target replication factor (default 2). Semantics: "bring every partition up
  to N replicas", not "add N new replicas".
- `--disk-threshold`: disk usage threshold in percent (default 70).

Output contract: **stdout carries exactly one JSON object** (upstream parses the stage result);
the human-readable four-line stage report (stage/inputs/outputs/validation) goes to stderr. Exit
codes are defined in [execution-safety.md](execution-safety.md).

## Allocation Rules

Topics are processed in order (physical input order, deterministic). Within each topic:

1. Take all partitions of the topic and the broker IDs of their existing replicas;
2. `replicas_to_add = replica_count - existing_replica_count` (skip partitions already at or
   above the target);
3. Pick a placement for each partition one slot at a time, updating capacity immediately on the
   chosen (broker, mount point) so later partitions and later slots judge against refreshed
   watermarks.

### Candidates & Exclusion

Each partition tracks `used_pairs = {(broker, mount_point)}`, initialized with the partition's
existing replica placements.

- **Exclude already-used pairs**: the same (broker, mount point) must not host two replicas of the
  same partition — two replicas on one mount point have no failover value and would double-count
  capacity.
- **Candidates sorted by current usage ascending**: lower-watermark disks first, to avoid piling
  hot spots onto the same disk.

## Placement & Blocking: L0 / NO_OTHER_BROKER / L3

Replica resilience is determined by where replicas land; this tool **only admits distinct brokers
(L0)** and blocks whenever it cannot — quantifying the reason. An older version allowed an "L2"
degradation (same broker, different mount point), but that output turned out to be undeliverable:

> **Why L2 was removed**: in standard Kafka reassignment JSON, one partition's `replicas` is a
> list of broker IDs and **must not contain duplicates**; `log_dirs` can only name directories for
> replicas that already exist, so "add a replica on another directory of the same broker" cannot be
> expressed. A plan like the single-broker expansion simply cannot be written into the JSON — the
> old L2 output produced `replicas=[1,1]`, which Kafka rejects on submission. This is not "a
> degradation that looks bad but works"; it is "impossible to express, therefore must block".

| Level | Trigger | Result |
|-------|---------|--------|
| **L0** (only admitted) | A **distinct-broker** mount point exists with projected usage ≤ threshold | Allocate; `degradation` stays empty |
| **NO_OTHER_BROKER** (block) | Only **same-broker** different-mount candidates are within threshold: 0 distinct-broker mount points available | **Stop**: no artifacts written, `status=FAIL`, `reason=NO_OTHER_BROKER`, exit code 2 |
| **L3** (block) | No mount point at all is within threshold (insufficient capacity) | **Stop**: no artifacts written, `status=FAIL`, `reason=L3_BLOCKED`, exit code 2 |

**Why block instead of "place it anyway"**: pushing a replica onto an over-threshold disk, or onto
the same broker, produces a plan that looks complete but either fails on execution (rejected by
Kafka) or blows up a disk. This kind of "half-success" is more dangerous than an explicit failure,
so the blocking semantics are **zero artifacts + explicit failure + quantified gaps**:

- `blockers[]` gives, per item: how many replicas are short and their sizes; how many mount points
  are within threshold (distinct-broker vs same-broker); why same-broker placements are unusable;
  how many distinct-broker mount points to add / how many GB to free / or to raise
  `--disk-threshold`.
- `degradation_events` states explicitly "stage stopped, no artifacts written" so downstream never
  looks for products that do not exist.
- `stats` reports `blocked_replicas` plus the per-reason counts
  `no_other_broker_blocked_replicas` / `l3_blocked_replicas`.

> L1 ("more partitions than brokers, partitions share brokers") is a normal condition and is not
> treated as a degradation, so no `degradation=L1` is produced.

## Disk Threshold & Projection

The decision does not look at the current watermark but at the **projected watermark**:

```
projected used   = mount point used (GB) + replica size being placed (GB)
projected usage  = projected used / disk total (GB) × 100
projected usage ≤ disk_threshold  (placement allowed)
```

**A pre-existing over-threshold disk is WARN, not FAIL**: exported production tables often already
contain disks above the threshold. This was not caused by this run, and failing on it would make
the tool unusable for dirty production data. Handling:

- such mount points are **never picked** as new placements (must not be made worse);
- they are listed in `stats.pre_existing_over_threshold` (e.g. `broker 1 /srv/BigData/data1: 90.00%`);
- check 1.1 emits a WARN "fix this disk first" and the stage still PASSes.

Check 1.1 FAILs only when **this run** pushed a mount point over the threshold.

## Balance & Fairness

Sorting purely by "lowest current watermark" hides a trap: **zero-byte partitions do not raise the
watermark**, so the same lowest broker keeps winning and all new replicas pile onto one or two
brokers (a real measured case: 15 of 22 new replicas landed on one broker).

Therefore the sort key adds **new replicas already accepted by each broker in this run** on top of
current usage, spreading new replicas across brokers; within a broker, mount points then sort by
usage.

Check 1.6 enforces this and reports two views:

- `new-replica distribution max=N/broker, min=M/broker, fair value≈K, hosting brokers X/Y` — are
  new replicas clustered?
- `post-allocation partition count per broker A~B` — overall partition distribution.

Imbalance is WARN, not blocking: it affects long-term load, not whether this plan is executable.

## Outputs

### topic.xlsx

The original replica table (converted from topic.xlsx), columns as in the input table above.
**Read-only passthrough; not modified.**

### topic_new.xlsx

New replica table, **always 8 columns** (independent of replication factor; at factor > 2 the same
partition appears in multiple rows):

| Column | Description |
|--------|-------------|
| Topic | Topic name |
| PartitionCount | Total partition count |
| Partition | Partition ID |
| Broker ID | Broker hosting the new replica |
| Path | Mount point of the new replica |
| Size(bytes) | Partition size (same as original) |
| Size(GB) | Partition size (same as original) |
| degradation | Empty (this version only admits L0; legacy L2 values are no longer produced, the column is kept for compatibility with old artifacts) |

### broker_updated.xlsx

Same structure as the input broker.xlsx, but "Used (GB)" and "Usage (%)" are refreshed by this
allocation. The `Usage (%)` column is written as a string (e.g. `37.84%`); readers must strip the
`%` too.