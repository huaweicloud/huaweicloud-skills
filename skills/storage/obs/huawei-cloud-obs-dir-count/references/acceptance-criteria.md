# Acceptance Criteria - Huawei Cloud OBS Directory Count

Reference for correct vs. incorrect behavior, used to decide whether a query succeeded.

## Criteria

| # | Scenario | Expected result | Pass / Fail |
|---|----------|-----------------|-------------|
| 1 | Count immediate directories in a bucket | stdout is a single integer equal to the number of top-level folders; exit code 0 | PASS |
| 2 | Count immediate directories under a prefix | stdout is a single integer equal to the number of sub-folders directly under the prefix (target itself excluded); exit code 0 | PASS |
| 3 | Count recursively | stdout is the deduplicated total number of directories across all levels; exit code 0 | PASS |
| 4 | `--json` output | valid JSON with `directory_count`; exit code 0 | PASS |
| 5 | Bucket does not exist | exit code 3; stderr says bucket/prefix not found (404) | PASS |
| 6 | Credentials not configured | exit code 3; stderr says credentials not configured and shows the secure config command | PASS |
| 7 | Invalid permissions | exit code 3; stderr mentions authentication/permission | PASS |
| 8 | Malicious bucket name (`bad;name`) | exit code 2; no shell command executed; stderr validation message | PASS |
| 9 | Malicious prefix (`a;rm`) | exit code 2; no shell command executed; stderr validation message | PASS |
| 10 | `hcloud` not installed | exit code 3; stderr install hint | PASS |
| 11 | Never create/upload/modify/delete | script performs only `hcloud OBS ls` (read-only); observed bucket unchanged | PASS |

## Failure patterns to flag

- Script prints a count but the actual `hcloud OBS ls -d` shows a different number of
  folders → investigate (likely a pagination or self-entry edge case).
- Script exits 0 for a nonexistent bucket → regression in error classification.
- Script executes a shell or accepts a value with shell metacharacters → security
  regression; reject.
- Any credential value appears in stdout/stderr → security regression; reject.

## Success condition

A query is considered delivered when the script prints the requested integer count
(immediate or recursive) for a user-confirmed bucket/prefix, with exit code 0. When the
user only needs the count, relay the integer directly and do not fabricate extra output.