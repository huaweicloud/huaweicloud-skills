# Troubleshooting - Huawei Cloud OBS Directory Count

Common problems, their causes, and fixes. All credential configuration is done by the
user in their own terminal — never paste AK/SK into a chat.

## Script exit codes

| Exit code | Meaning |
|-----------|---------|
| 0 | Success (count printed) |
| 2 | Usage / input validation error (bucket/prefix failed the allow-list check) |
| 3 | Runtime error (CLI missing, credentials missing, network/API/permission error) |

## Error messages and fixes

| Symptom / stderr message | Cause | Fix |
|--------------------------|-------|-----|
| `hcloud (KooCLI) was not found on PATH` | KooCLI not installed or not in PATH | Install per `cli-installation-guide.md` (user-level, checksum-verified) |
| `OBS credentials are not configured` | obsutil AK/SK/endpoint not set | Run `hcloud obs config -i=<AK> -k=<SK> -e=obs.<region>.myhuaweicloud.com` in your own terminal |
| `Authentication or permission was denied` | Invalid AK/SK, or IAM user lacks OBS read permission | Check AK/SK; attach `OBS ReadOnlyAccess` / grant `obs:bucket:ListBucket` (see `iam-policies.md`) |
| `The bucket or prefix does not exist (404)` | Wrong bucket name or prefix | Confirm exact bucket name and prefix |
| `Invalid bucket name ...` / `Invalid prefix ...` | Bucket/prefix contains disallowed characters | Use lowercase letters/digits and `.-` for buckets; `A-Za-z0-9._/-` for prefixes |
| `Failed to list directories` (generic) | Network issue, wrong endpoint, or transient API error | Check connectivity and `obsutil` endpoint; retry |

## Validation behavior (by design)

- Bucket names and prefixes are validated with strict allow-list regexes to block shell
  metacharacters (`;`, `` ` ``, `$`, `"`, `'`, `|`, newline, etc.). Such input fails fast
  with exit code 2 and **no command is executed**.
- There is intentionally **no** `eval`, `exec`, dynamic import, or remote-code execution
  in the script — it only ever runs a fixed-argv `hcloud OBS ls`.

## Counting accuracy

- The script excludes the query prefix itself from the count (obsutil lists it as a
  "folder" only when that folder holds direct files), so the result equals the number of
  true sub-directories.
- Deep or large buckets: each `hcloud OBS ls -d` call returns at most 1000 entries; the
  script follows the `Next marker` continuation, so large listings are fully counted.

## References

- [cli-installation-guide.md](cli-installation-guide.md) — install & credential setup
- [iam-policies.md](iam-policies.md) — read-only IAM policies
- [verification-method.md](verification-method.md) — how to verify the results