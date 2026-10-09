# Stage 2: Merge Master Table

## Table of Contents
1. [Input Files](#input-files)
2. [Command Line](#command-line)
3. [Merge Rules](#merge-rules)
4. [Sort Rules](#sort-rules)
5. [Column Layout](#column-layout)
6. [Output File](#output-file)

## Input Files

- `topic.xlsx`: original replica information (Stage 1's topic.xlsx conversion)
- `topic_new.xlsx`: new replica information (Stage 1 artifact)

Both are Excel workbooks (`.xlsx`) with headers; legacy pre-upgrade TSV intermediate files can
still be read.

## Command Line

```bash
python scripts/stage2_merge.py \
  --main /tmp/out/topic.xlsx \
  --new /tmp/out/topic_new.xlsx \
  --output-dir /tmp/out \
  --replica-count 2
```

`--replica-count` must match Stage 1: it determines the merged table column count (original
replica + N-1 new replicas).

## Merge Rules

Join the two files on `(Topic, Partition)` to produce one master table: one row per partition,
carrying both the original replica and the new replica information.

- Join by `(Topic, Partition)`, not by row number — Stage 1 skips partitions already at the target
  factor, so row numbers do not align.
- If the merge yields 0 rows, or missing/duplicate partitions appear, they must be reported
  (`missing_partitions` / `duplicate_rows`), never silently emitted as a half table.

**The `degradation` column must be carried through as-is**: this version only admits L0, so the
column is empty; the column exists for compatibility with old artifacts. If a legacy L2 annotation
is read, Stage 3's duplicate-broker hard check rejects it (that scenario should have been blocked
by `NO_OTHER_BROKER` at Stage 1), so this stage never drops or loses the column and lets the
problem surface at final validation.

> With more than two replicas, one partition has multiple new-replica rows; merge must concatenate
> them into `Allocation Broker ID 1/N` slots, not overwrite or drop rows.

## Sort Rules

1. Sort by topic total capacity (sum of `Size(GB)` over all partitions × all replicas) **ascending**;
2. Rows of the same topic stay together;
3. Within a topic, sort by `Partition` **ascending**.

### Capacity Example

Topic A has 6 partitions, RF 2, each partition 0.1 GB: `6 × 2 × 0.1 = 1.2 GB`
Topic B has 10 partitions, RF 2, each partition 0.5 GB: `10 × 2 × 0.5 = 10.0 GB`

Result: Topic A first, Topic B second. Ascending order means **small topics run first as a
trial**, big topics later (larger execution window).

## Column Layout

### Replication factor 2 — fixed 10 columns

| # | Column | Source | Description |
|---|--------|--------|-------------|
| 1 | Topic | both | topic name |
| 2 | PartitionCount | both | total partition count |
| 3 | Partition | both | partition ID |
| 4 | Original Broker ID | topic.xlsx | original replica broker |
| 5 | Original Path | topic.xlsx | original replica mount point |
| 6 | Allocation Broker ID | topic_new.xlsx | new replica broker |
| 7 | Allocation Path | topic_new.xlsx | new replica mount point |
| 8 | Size(bytes) | topic.xlsx | partition size in bytes |
| 9 | Size(GB) | topic.xlsx | partition size in GB |
| 10 | degradation | topic_new.xlsx | degradation marker (empty in this version; legacy L2 passes through) |

### Replication factor > 2 — 12 columns

Columns 6/7 expand to numbered pairs so **column names stay unique**:

| Column |
|--------|
| Topic |
| PartitionCount |
| Partition |
| Original Broker ID |
| Original Path |
| Allocation Broker ID 1 |
| Allocation Path 1 |
| Allocation Broker ID 2 |
| Allocation Path 2 |
| Size(bytes) |
| Size(GB) |
| degradation |

**Why the new replica columns are numbered**: if every new replica were named `Path`, the table
would contain duplicate `Path` columns and downstream name-based lookups would read the wrong
value (this was a real defect in an early version: the merged table had two `Path` columns and
Stage 3 read the original path). Column names must therefore be unique — originals get an
`Original` prefix, new ones an `Allocation` prefix plus a slot number.

**Parsing must be positional, not by name**: column names vary with the replication factor; only
positions are stable (first 5 columns fixed, the two `Size` columns fixed just before
`degradation`). Downstream scripts slice by position.

## Output File

`topic_all.xlsx`: the merged master table (`.xlsx`, with headers), written to `--output-dir`.

stdout returns the stage JSON, whose `stats` contains at least:

```json
{
  "main_rows": 22, "new_rows": 22, "merged_rows": 22, "expected_rows": 22,
  "missing_partitions": 0, "duplicate_rows": 0,
  "topic_count": 3, "degradation_count": 0,
  "topic_sizes": {"ITDE_DEV_rfr_channel_ifrs_lkp": 4.2, "...": 1.5}
}
```

If `degradation_count` disagrees with Stage 1's count, degradation information was lost during the
merge.