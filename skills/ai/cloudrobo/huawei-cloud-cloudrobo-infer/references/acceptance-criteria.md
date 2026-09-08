# Acceptance Criteria

## Functional Criteria

### Service Creation

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-01 | Can create an inference service with valid params | service_id returned, status non-terminal |
| AC-02 | Can dry-run validate create params | `[DRY-RUN]` message, no service created |
| AC-03 | Can create with health-check JSONs | service_id returned, probes applied |
| AC-04 | Rejects invalid JSON param (envs/health) | Click validation error on malformed JSON |

### Wait-Deploy

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-05 | Can wait-deploy a service | Service status no longer `DEPLOYING` (or timeout reports) |
| AC-06 | wait-deploy polls every ~5s | Status feedback per poll observed |
| AC-07 | wait-deploy honours `--timeout` | Times out at configured seconds |
| AC-08 | On FAILED, wait-deploy suggests logs | Failure message references list-logs |

### Service Query

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-09 | Can list inference services | JSON array returned |
| AC-10 | Can filter by status | Filtered results match status |
| AC-11 | Can filter by model-id/model-name | Filtered results match model |
| AC-12 | Can paginate with --limit/--offset | Pagination respected |
| AC-13 | Can sort with --sort-key/--sort-dir | Results ordered |

### Service Lifecycle

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-14 | Can show service detail | Service object with full fields |
| AC-15 | Can start a stopped service | status → RUNNING |
| AC-16 | Can stop a running service | status → STOPPED |
| AC-17 | Can update service description | Field updated in subsequent show |
| AC-18 | Can delete a service | Service removed |

### Logs

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-19 | Can list logs with ms start/end | Log lines returned |
| AC-20 | Can filter logs by keyword | Filtered log lines returned |
| AC-21 | Always pass ms timestamps to `list-logs` | CLI accepts both s and ms (no client validation); backend may return empty/wrong time-range for seconds — if so, convert (×1000) and retry |

### Enum / Validation

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-22 | Can dry-run validate delete | `[DRY-RUN]` message, no deletion |
| AC-23 | Path traversal rejected via validate_safe_id | Error on `../` service_id |
| AC-24 | Missing workspace rejected | Click validation error: Missing option '--workspace-id' |

### Parameter Auto-Discovery (Space Asset / Custom Models)

| # | Criterion | Verification |
| --- | ----------- | ------------- |
| AC-25 | Can auto-discover algorithm asset via ONLINE_DEPLOYMENT action | show-asset returns algorithm.asset_id |
| AC-26 | Can extract cmd/image/envs from algorithm ext_metadata | All fields present in create command |
| AC-27 | Can download skill_config.json via download-url API | File content returned |
| AC-28 | Can download r2c config with fallback (yaml → json) | At least one format returns content |
| AC-29 | Can convert envs array to map format | envs-json accepts map format |

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
| NFR-10 | internet_access documented as default OFF | grep 'internet.access\|internet_access' |
| NFR-11 | list-logs documented as ms timestamps | grep 'millisecond\|ms' in SKILL.md |
| NFR-12 | Resource IDs documented as dynamic | grep for no hardcoded model_id/service_id |

## Test Cases Summary

| Case Type | Count | Coverage |
| ----------- | ------- | ---------- |
| Service creation | 4 | AC-01 ~ AC-04 |
| Wait-deploy | 4 | AC-05 ~ AC-08 |
| Service query | 5 | AC-09 ~ AC-13 |
| Service lifecycle | 5 | AC-14 ~ AC-18 |
| Logs | 3 | AC-19 ~ AC-21 |
| Enum / validation | 3 | AC-22 ~ AC-24 |
| Parameter auto-discovery | 5 | AC-25 ~ AC-29 |
| **Total** | **29** | Full coverage |
