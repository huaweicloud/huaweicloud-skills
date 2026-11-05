# Verification Method

This skill provides two independent ways to measure OBS total size: the KooCLI obsutil-backed command (primary) and the `huaweicloudsdkobs` Python SDK (fallback).

## Verification Script

Run the bundled test script from the skill directory:

```bash
bash scripts/test-cli-commands.sh <skill-path>
```

The script requires a real OBS bucket name via the `TEST_OBS_BUCKET` environment variable (defaults to `obs-hd-dev-static` if unset).

## Manual Verification Steps

1. **Prerequisite check** — confirm hcloud and obsutil are available:

   ```bash
   hcloud version
   hcloud OBS ls -s -limit=1
   ```

   If the second command returns `Please set ak, sk and endpoint in the configuration file!`, obsutil credentials are not configured.

2. **Single bucket size (CLI primary)**:

   ```bash
   python3 scripts/query_obs_total_size.py --bucket <bucket_name>
   ```

   Expected: a single integer (bytes). Cross-check with:

   ```bash
   hcloud OBS ls obs://<bucket_name>/ -du -bf=raw
   ```

   The `[DU] Total bucket size: N` line must equal the script output.

3. **All buckets total**:

   ```bash
   python3 scripts/query_obs_total_size.py --all
   ```

   Expected: a single integer >= the size of any single bucket.

4. **SDK fallback** — verify the SDK path returns the same size for the same bucket:

   ```bash
   python3 scripts/query_obs_total_size.py --bucket <bucket_name> --executor sdk
   ```

5. **Unit conversion**:

   ```bash
   python3 scripts/query_obs_total_size.py --all --unit mb
   python3 scripts/query_obs_total_size.py --all --human
   ```

6. **Empty bucket** — a bucket with no objects returns `0`.

## Pass Criteria

- The CLI and SDK paths return the same bucket size for the same bucket
- The output is a single value with no surrounding text
- No create/update/delete operation is ever performed
