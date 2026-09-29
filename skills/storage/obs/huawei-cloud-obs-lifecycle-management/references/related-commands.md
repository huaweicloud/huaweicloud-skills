# Related Commands — Quick Reference

## Command map (skill action → CLI → OBS REST API)

| # | Skill action | hcloud obs command | OBS REST API | Risk |
|---|-------------|--------------------|--------------|------|
| 1 | `huawei_list_obs_lifecycle_rules` | `hcloud obs lifecycle obs://{bucket} -method=get` | `GET /{bucket}?lifecycle` | R3 |
| 2 | `huawei_get_obs_lifecycle_rule` | `hcloud obs lifecycle obs://{bucket} -method=get -localfile={file}` + JSON filter by `ID` | `GET /{bucket}?lifecycle` | R3 |
| 3 | `huawei_list_obs_objects` | `hcloud obs ls obs://{bucket}[/{prefix}] -limit={n} -s` | `GET /{bucket}?list-type=2` (ListObjectsV2) | R3 |
| 4 | `huawei_diagnose_obs_lifecycle` | analyzer script `diagnose` (rules + objects + stat) | `GET /{bucket}?lifecycle` + ListObjectsV2 | R3 |
| 5 | `huawei_analyze_obs_lifecycle_cost` | analyzer script `cost` (rules + objects) | `GET /{bucket}?lifecycle` + ListObjectsV2 | R3 |
| 6 | `huawei_preview_obs_lifecycle` | analyzer script `preview` (rules + objects) | `GET /{bucket}?lifecycle` + ListObjectsV2 | R3 |
| 7 | `huawei_create_obs_lifecycle_rule` | `hcloud obs lifecycle obs://{bucket} -method=put -localfile={merged_rules}` | `PUT /{bucket}?lifecycle` | R2 |
| 8 | `huawei_update_obs_lifecycle_rule` | `hcloud obs lifecycle obs://{bucket} -method=put -localfile={modified_rules}` | `PUT /{bucket}?lifecycle` | R2 |
| 9 | `huawei_delete_obs_lifecycle_rule` | `hcloud obs lifecycle obs://{bucket} -method=put -localfile={rules_without_rule}` | `PUT /{bucket}?lifecycle` | R1 |

> Official OBS API reference: `https://support.huaweicloud.com/api-obs/obs_04_0006.html` (lifecycle configuration: `obs_04_0113.html` / `obs_04_0114.html`). Endpoints come from the official OBS
> endpoint list — never inferred.

## Read-only snippets

```bash
# List buckets (verify credentials)
hcloud obs ls -limit=1

# Bucket statistics (region, storage class, object count, size)
hcloud obs stat obs://{bucket}

# All lifecycle rules, pretty JSON
hcloud obs lifecycle obs://{bucket} -method=get

# Objects with sizes in raw bytes (for cost math)
hcloud obs ls obs://{bucket} -limit=1000 -s -bf=raw

# Bucket size summary
hcloud obs ls obs://{bucket} -limit=1 -du
```

## Mutating snippets (always preview + confirm first)

```bash
# Create/update rule: write merged rules JSON then PUT
hcloud obs lifecycle obs://{bucket} -method=put -localfile=/tmp/rules.json

# Delete ONE rule safely: analyzer removes it from Rules[] and PUTs back
python3 scripts/obs_lifecycle_analyzer.py delete-rule --bucket {bucket} --rule-id {rule_id}

# DESTRUCTIVE — wipe ALL rules (double-confirm before use)
hcloud obs lifecycle obs://{bucket} -method=delete
```

## Common pitfalls

| Pitfall | Truth |
|---------|-------|
| `hcloud obs` takes `--cli-region` | No — region lives in the endpoint (`obs.{region}.myhuaweicloud.com`), configured via `hcloud obs config` |
| `hcloud obs lifecycle -method=put` appends a rule | No — **PUT replaces the entire lifecycle configuration**; merge existing rules first |
| `-method=delete` deletes one rule | No — it deletes **all** lifecycle rules of the bucket |
| Lifecycle requires object write permission | No — only `obs:bucket:PutLifecycleConfiguration`; the OBS service performs object expiry itself |
| Expiration deletes versions too | Only current versions; non-current needs `NoncurrentVersionExpiration` |
| Object age = upload time | Yes, `LastModified`; objects younger than `Days` are never affected, even if the rule matches the prefix |