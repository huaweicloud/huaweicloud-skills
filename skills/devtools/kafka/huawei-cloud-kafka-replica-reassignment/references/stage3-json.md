# Stage 3: Emit Reassignment JSON

## Table of Contents
1. [Input File](#input-file)
2. [Command Line](#command-line)
3. [JSON Format](#json-format)
4. [Split Strategies](#split-strategies)
5. [Filename Security Boundary](#filename-security-boundary)
6. [Format Validation](#format-validation)
7. [Output](#output)

## Input File

`topic_all.xlsx`: the Stage 2 merged master table (`.xlsx` workbook, with headers).

**Read by column position, not by column name**: the number of new-replica columns varies with
`--replica-count`; only positions are stable — the first 5 columns are
`Topic / PartitionCount / Partition / Original Broker ID / Original Path`, followed by pairs of
`Allocation Broker ID [n] / Allocation Path [n]`, the last two columns `Size(bytes) / Size(GB)`,
and `degradation` at the end.

## Command Line

```bash
python scripts/stage3_json.py \
  --input /tmp/out/topic_all.xlsx \
  --output-dir /tmp/out \
  --replica-count 2 \
  --strategy size_10g \
  --strategy-param 10
```

- `--strategy`: `size_10g` (default) / `topic_count` / `single_file` / `per_topic` / `custom`
- `--strategy-param`: capacity threshold (GB) or topic count; for `custom`, a strategy config JSON

JSON files are written to `<output-dir>/json/`.

## JSON Format

```json
{
  "partitions": [
    {
      "topic": "ITDE_PROD_StoIndihome_lkp",
      "partition": 0,
      "replicas": [3, 16],
      "log_dirs": ["any", "/srv/BigData/data4/kafka-logs"]
    }
  ],
  "version": 1
}
```

### Field Mapping

| JSON field | Merged-table source | Description |
|------------|---------------------|-------------|
| `topic` | Topic | topic name |
| `partition` | Partition | partition ID (integer) |
| `replicas` | `[Original Broker ID] + [Allocation Broker ID n...]` | broker list of all replicas; **first is the original, the rest appended by column order** |
| `log_dirs` | `["any"] + [Allocation Path n...]` | first fixed to `"any"`, the rest are new-replica mount points + `/kafka-logs` |

- **Multiple replicas**: `replicas` / `log_dirs` lengths both equal `replica_count`.
- **log_dirs normalization**: mount points may or may not carry a `/kafka-logs` suffix. Strip any
  existing suffix before concatenating to avoid `.../kafka-logs/kafka-logs`.
- **Numeric tolerance**: broker/partition/size cells may be strings (common in Excel exports);
  convert to int/float with fallback values, and never let an unparseable value crash the stage.

## Split Strategies

Grouping follows "execution risk": big topics' replica moves occupy bandwidth for a long time, so
they must be one file each — executed and observed separately; small topics can be batched.

The UI parameter panel exposes the two most common choices as dropdowns: **split by topic
partition size** (= `size_10g`) and **split by topic count** (= `topic_count`), with the threshold
as the filled parameter; `single_file` / `per_topic` / `custom` are chosen on the command line or
combined.

### Strategy 1: `size_10g` (default)

- Topic with max single-partition `Size(GB)` **> threshold** → one file per topic, named
  `{seq}{topic}.json`, seq starting at 2;
- Remaining topics → merged into `1common.json`;
- Threshold = `--strategy-param` (default 10 GB).

### Strategy 2: `topic_count`

- Every N topics packed into one file, named `batch_{seq}.json`, seq starting at 1;
- N = `--strategy-param` (default 10).

### Strategy 3: `single_file`

- All partitions merged into one `all_partitions.json`.

### Strategy 4: `per_topic`

- One file per topic, named `{topic}.json`.

### Strategy 5: `custom`

`--strategy-param` is a JSON config combining the two ideas:

```bash
--strategy custom --strategy-param '{"big_size": 10, "small_batch": 10}'
```

Semantics: topics with max single-partition Size > `big_size` get one file each; the remaining
small topics are packed `small_batch` per file. The UI strategy config panel ultimately builds
this same JSON.

## Filename Security Boundary

The `per_topic` / `size_10g` / `custom` strategies embed **topic names directly into file names**
(e.g. `ITDE_PROD_ad_dim_lkp.json`, `2dolce_main.json`). Topic names come from user-uploaded Excel
files — exported from production and passed around externally, hence **untrusted input**; if a name
contains `/`, `..` or an absolute path, concatenation would write outside the output directory,
allowing arbitrary file write/overwrite. Two gates run before writing:

1. **Topic-name whitelist validation** (`INVALID_TOPIC_NAME`): consistent with Kafka's default
   legal names — only `[A-Za-z0-9._-]`, no `.` / `..` as a complete topic name, max length 249.
2. **realpath containment check**: validate each final file name with a `basename` consistency
   check and the regex `^[A-Za-z0-9._-]+\.json$`, then use `realpath` to confirm the joined path
   still lies inside `<output-dir>/json/` (defense in depth — even if a future strategy builds an
   unexpected name, it cannot be written outside).

Either check failing → stage `FAIL` (`reason=INVALID_TOPIC_NAME`, exit code 1) and **no file is
written**; the scripts never silently rewrite file names (rewriting would break the
topic→file mapping and hide data problems). The whitelist matches what Kafka itself allows — Kafka
rejects these characters in topic names by default, so rejecting them cannot hurt a legal cluster.

## Format Validation

After generation, validate item by item (rule details in [validation-rules.md](validation-rules.md)):

1. **Syntax valid**: every file `json.loads()`-able;
2. **Top-level structure**: `partitions` array + `version=1`;
3. **Entry complete**: every entry has `topic` / `partition` / `replicas` / `log_dirs`;
4. **Replica constraint**: `replicas` has no duplicate broker, length = `replica_count`;
   `log_dirs` length = `replica_count`, first value `"any"`;
5. **Completeness**: total entries across all files = merged-table row count, no missing, no
   duplicates;
6. **Naming compliance**: file names match the chosen strategy (including the security whitelist
   and containment check, see "Filename Security Boundary").

**Rule 3.4 fails on any duplicate broker**: duplicate broker IDs in one partition's `replicas` is
a hard constraint of Kafka reassignment JSON — duplicates are rejected by Kafka. An older version
allowed an exception for L2 degradation (`l2_exception_count` / `PASS(L2-EXCEPTION)`), but such
JSON fails on submission, i.e. delivery of an unexecutable plan, so the exception is removed:
- duplicate broker → `3.4 FAIL`;
- if the merged table marks that partition `degradation=L2`, the FAIL detail adds an explanation
  (the scenario should have been blocked at Stage 1 with `NO_OTHER_BROKER` instead of reaching the
  JSON);
- `stats` no longer emits `l2_exception_count` / `l2_exception_partitions`.

## Output

- `<output-dir>/json/*.json`: reassignment JSON split by strategy (`ensure_ascii=False`, so
  non-ASCII content such as mount paths stays readable; `indent=2` for easy human diffing. Topic
  names are constrained to `[A-Za-z0-9._-]` per the security boundary above);
- stdout returns the stage JSON, whose `stats` contains at least:

```json
{
  "total_entries": 22, "files_generated": 1,
  "validation_pass": 115, "validation_fail": 0
}
```

`validation_fail=0` is the pass line for this stage; `file_groups` lists how many partitions each
file covers, useful for comparing against execution windows.