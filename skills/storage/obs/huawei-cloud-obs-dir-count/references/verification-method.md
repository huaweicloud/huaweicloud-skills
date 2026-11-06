# Verification Method - Huawei Cloud OBS Directory Count

This document describes how to verify the skill works correctly, including both the
runtime script and the CLI it wraps.

## What "correct" means

This skill counts directories (folders) in an OBS bucket or under a prefix:

- **Immediate** mode (`--prefix`): counts only the sub-directories directly under the
  target, **excluding** the target itself.
- **Recursive** mode (`--recursive`): counts every sub-directory at all levels below the
  target, with deduplication. The target itself is not counted.
- Success prints a single integer to stdout; failure writes an English-first bilingual
  message to stderr and returns a non-zero exit code.

## Manual verification steps

### 1. Confirm credentials are configured

```bash
hcloud OBS ls -limit=1
```

Expected: a list of buckets. If you see `Please set ak, sk and endpoint in the
configuration file!`, configure obsutil credentials first (see `cli-installation-guide.md`).

### 2. Count immediate directories in a known bucket

```bash
python3 scripts/count_obs_directories.py --bucket <bucket>
```

Expected: a single integer equal to the number of top-level folders in the bucket.
Cross-check with the CLI:

```bash
hcloud OBS ls obs://<bucket> -d
# Compare the integer to the "Folder number" line.
```

> Note: obsutil's `Folder number` includes the query prefix itself only when the folder
> contains direct files. The script excludes that self-entry, so its count equals the
> number of true sub-directories. When comparing to `Folder number`, subtract 1 if the
> listing shows the target prefix itself as a folder.

### 3. Count immediate directories under a prefix

```bash
python3 scripts/count_obs_directories.py --bucket <bucket> --prefix <prefix>
```

Expected: the number of sub-folders directly under `<prefix>`.

### 4. Count recursively

```bash
python3 scripts/count_obs_directories.py --bucket <bucket> --recursive
```

Expected: the total number of directories across all levels (deduplicated). Bounded
traversal is available via `--max-depth <N>`.

### 5. JSON output

```bash
python3 scripts/count_obs_directories.py --bucket <bucket> --json
```

Expected: a JSON object `{"bucket": ..., "prefix": ..., "recursive": false, "directory_count": N}`.

### 6. Input validation (rejects injection, no shell execution)

```bash
python3 scripts/count_obs_directories.py --bucket 'bad;name'; echo $?
# Expected: an error message on stderr and exit code 2. No shell command is executed.

python3 scripts/count_obs_directories.py --bucket <ok-bucket> --prefix 'a;rm'; echo $?
# Expected: exit code 2 as well.
```

### 7. Failed-query paths

- Invalid/expired credentials or missing IAM read permission → exit 3 with an
  English-first authentication message.
- Non-existent bucket/prefix → exit 3 with a 404 message.
- `hcloud` not installed → exit 3 with an install hint.

## Automated functional test

The repository's `scripts/test-cli-commands.sh` runs a whitelist-gated suite defined in
`templates/test-vars.json`. Run it from the skill directory:

```bash
bash scripts/test-cli-commands.sh "$PWD"
```

The runner only executes commands whose first word is `hcloud` / `python3` / `curl` /
`bash`, rejects `bash -c`, `$`/backtick, shell concatenation, and known-dangerous Python
calls. A test bucket can be supplied via `TEST_BUCKET` in `templates/test-vars.json` for
live counting checks.

## References

- [acceptance-criteria.md](acceptance-criteria.md) — pass/fail patterns
- [cli-installation-guide.md](cli-installation-guide.md) — install & credential setup
- [troubleshooting.md](troubleshooting.md) — common errors and fixes