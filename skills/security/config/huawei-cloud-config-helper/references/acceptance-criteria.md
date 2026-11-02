# Acceptance Criteria 验收标准

## Functional Criteria 功能标准

### Resource Summary 资源概览

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-01 | Returns per-provider/type/region resource counts | Run `query_Config_resource_summary.py`, verify JSON array with `provider`/`type`/`region_id`/`cnt` | ☐ |
| AC-02 | Filters by `--provider` | Run with `--provider=obs`, verify only obs rows returned | ☐ |
| AC-03 | Supports `provider.type` in `--provider` | Run with `--provider=obs.buckets`, verify only bucket rows returned | ☐ |
| AC-04 | Filters by `--region_id` | Run with `--region_id=cn-north-4`, verify only that region's rows | ☐ |

### Resource Schema 资源 Schema

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-05 | Returns schema for a valid `provider.type` | Run `query_Config_resource_schema.py --resource_type=obs.buckets`, verify JSON with field names/types | ☐ |
| AC-06 | Handles types not in first schema page (marker pagination) | Run with a type alphabetically late (e.g. `vpc.securityGroups`), verify result returned | ☐ |
| AC-07 | Missing required `--resource_type` fails fast | Run without the option, expect argparse usage error | ☐ |

### SQL Query 高级查询

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-08 | Executes a SELECT on `resources` | Run `query_Config_resource_by_sql.py --sql="select id, name from resources where provider = 'ecs' and type = 'cloudservers'"`, verify JSON array | ☐ |
| AC-09 | Supports `properties.<field>` access | Query `properties.status` for ECS, verify values match console | ☐ |
| AC-10 | Supports aggregation | `select region_id, count(*) from resources group by region_id`, verify counts | ☐ |
| AC-11 | Empty result handled | Query with non-existent provider, expect `没有找到数据` and exit 0 | ☐ |

### Builtin Compliance Rules 预置合规规则

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-12 | Returns builtin rules filtered by keyword | Run `query_Config_builtin_rule.py --keyword=obs --limit=10`, verify ≤10 obs-related rules | ☐ |
| AC-13 | Default limit applied | Run without `--limit`, verify default 20 respected | ☐ |

### Non-Functional 非功能

| # | Criterion | Verification | Status |
|---|-----------|--------------|--------|
| AC-14 | Read-only: no write API called | Grep scripts for create/update/delete API usage — none exist | ☐ |
| AC-15 | No credential leakage in output | Run any script with `--upgrade`-style failures; output contains error codes only, never AK/SK values | ☐ |
| AC-16 | Scripts executed via `skill action=exec` | SKILL.md declares the execution contract; no direct shell python invocation documented | ☐ |
| AC-17 | Exit code semantics | Success/empty → 0; failure → 1; missing args → 2 | ☐ |

