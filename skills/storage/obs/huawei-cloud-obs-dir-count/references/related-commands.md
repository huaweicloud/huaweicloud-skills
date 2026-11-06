# Related Commands and Notes - Huawei Cloud OBS Directory Count

Reference for the CLI and script commands this skill uses, and the counting semantics.

## Execution mode

This skill runs in **CLI mode**: `hcloud OBS ls` (KooCLI OBS module, which embeds
obsutil). This is the primary and only execution mode used by the runtime script.

## CLI listing command

```
hcloud OBS ls obs://<bucket>[/<prefix>] -d [-limit=<N>] [-marker=<X>]
```

| Option | Meaning |
|--------|---------|
| `-d` | List objects and directories in the current folder (one level) |
| `-limit=<N>` | Max entries per call (default 1000) |
| `-marker=<X>` | Continue from the marker returned as `Next marker` |

### Parsed output

`hcloud OBS ls obs://<bucket> -d` prints:

```
Folder list:
obs://<bucket>/dir1/
obs://<bucket>/dir2/

Next marker: dir2/          (present only when there are more results)
Folder number: N
File number: M
```

The script reads the folder entries under `Folder list:` and follows `Next marker` pages
to collect every directory.

## Counting semantics

- **Immediate** count = number of distinct sub-directories directly under the target,
  **excluding the target itself**. obsutil lists the query prefix itself as a "folder"
  entry only when that folder contains direct files; the script excludes that self-entry
  so the result is always the number of true sub-directories.
- **Recursive** count = deduplicated total of every sub-directory at all levels under the
  target (the target itself is not counted). Use `--max-depth <N>` to bound traversal.

## SDK / API fallback (informational)

The listing relies on OBS ListBuckets / ListObjects operations. Should the CLI ever be
unavailable, the equivalent read-only calls are OBS SDK `list_buckets` /
`list_objects` (OBS Python SDK `esdk-obs-python`) or the OBS REST `GET /` and
`GET /?list-type=2` APIs. This skill ships and documents the CLI path only; no SDK/API
fallback is executed by the runtime script.

## Example commands

```bash
# Immediate directories in a bucket
python3 scripts/count_obs_directories.py --bucket my-bucket

# Immediate directories under a prefix
python3 scripts/count_obs_directories.py --bucket my-bucket --prefix logs/2026

# All directories recursively
python3 scripts/count_obs_directories.py --bucket my-bucket --recursive

# Recursive, bounded to shallow levels
python3 scripts/count_obs_directories.py --bucket my-bucket --prefix logs --recursive --max-depth 2

# JSON output
python3 scripts/count_obs_directories.py --bucket my-bucket --json
```