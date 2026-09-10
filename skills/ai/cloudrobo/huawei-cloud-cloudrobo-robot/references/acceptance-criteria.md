# Acceptance Criteria

## Functional Criteria

### Robot Registration

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-01 | Can create a robot with valid params | robot_id returned, status non-terminal |
| AC-02 | Robot type is validated against enum | click usage error on out-of-enum type (case-insensitive; only unknown values rejected) |
| AC-03 | Can dry-run validate robot create params | `[DRY-RUN]` message, no robot created |
| AC-04 | Can create robot with full optional description | robot_id returned |

### Robot Query

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-05 | Can list robots | JSON array returned |
| AC-06 | Can filter robots by name | Filtered results match name |
| AC-07 | Can filter robots by status | Filtered results match status |
| AC-08 | Can filter robots by manufacturer | Filtered results match manufacturer |
| AC-09 | Can filter robots by robot_model | Filtered results match robot_model |
| AC-10 | Can filter robots by type | Filtered results match type |
| AC-11 | Can paginate with --limit / --offset | Result count/offset respected |
| AC-12 | Can sort results with --sort | Results ordered by field |

### Robot Detail & Update

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-13 | Can show robot detail via `show --robot-id` | Robot object with full fields |
| AC-14 | Can update robot name/description | Field updated in subsequent show |
| AC-15 | Can dry-run validate robot update | `[DRY-RUN]` message, no update applied |

### Robot Deletion

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-16 | Can delete a robot | Robot removed |
| AC-17 | Can dry-run validate robot delete | `[DRY-RUN]` message, no deletion |

### Certificate / Access-Config Export

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-18 | Can export the robot access config (接入配置) / certificate | Access-config **zip** written to file (wb) |
| AC-19 | Export supports optional password encryption | Output file generated when `--password` provided (default None) |
| AC-20 | Access config written to `--output` path | File exists at output path (or default when omitted) |
| AC-21 | Can dry-run validate export | `[DRY-RUN]` message, no file written |
| AC-21a | Export with a running job handled + dynamic state | Robot with a running job returns `CloudRobo.04010007 "The robot can only have one running job"` (backend-verified, pending live confirmation — error code not defined in local SDK); doc/agent re-checks `show` in real time, retries on an INACTIVE/idle robot with no running job (noting state is dynamic), and never continues on an empty/partial file |

### SDK Query

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-22 | Can query robot SDK info via `show-sdk` | file_name/version/signed_url returned |
| AC-23 | SDK signed_url is an OBS temp URL | URL returned in response |

### Enum Validation

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-24 | robot_type enum has 6 states | HUMANOID/QUADRUPED/ARM/OPERATION/WHEELED/OTHER |
| AC-25 | Out-of-enum type rejected | click usage error on `--type invalid-type` (exit 2; lowercase variants of valid values are accepted — CLI is case-insensitive) |

## Non-Functional Criteria

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| NFR-01 | No hardcoded credentials | grep SKILL.md and references for AK/SK patterns |
| NFR-02 | All mutating operations prompt user confirmation | SKILL.md documents confirmation requirement |
| NFR-03 | No cross-skill invocation | grep for other skill names |
| NFR-04 | All object storage paths use `obs://` | grep for `s3://` (should be none) |
| NFR-05 | SKILL.md frontmatter has name + description + tags | YAML frontmatter check |
| NFR-06 | description includes `Triggers include:` | grep 'Triggers include:' |
| NFR-07 | references/ files use kebab-case | filename regex `^[a-z0-9-]+\.md$` |
| NFR-08 | Total files <= 30 | find -type f \| wc -l |
| NFR-09 | Total size <= 40MB | du -sh |
| NFR-10 | All file extensions in allowed list | .md/.sh/.json/.yaml/.yml/.py/.txt/.png/.svg etc. |
| NFR-11 | Certificate export password treated as sensitive | grep for password masking in SKILL.md |
| NFR-12 | Path traversal protection documented (validate_safe_id) | grep for validate_safe_id |
| NFR-13 | Resource IDs documented as dynamic | grep for no hardcoded robot_id |

## Test Cases Summary

| Case Type | Count | Coverage |
| ----------- | ------- | ---------- |
| Robot registration | 4 | AC-01 ~ AC-04 |
| Robot query | 8 | AC-05 ~ AC-12 |
| Robot detail & update | 3 | AC-13 ~ AC-15 |
| Robot deletion | 2 | AC-16 ~ AC-17 |
| Certificate export | 5 | AC-18 ~ AC-21a |
| SDK query | 2 | AC-22 ~ AC-23 |
| Enum validation | 2 | AC-24 ~ AC-25 |
| **Total** | **26** | Full coverage |
