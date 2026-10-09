# Verification Method

## Prerequisite Verification

1. `hcloud version` — CLI installed
2. `hcloud configure list` — valid AK/SK profile
3. `hcloud dli --help` — DLI service metadata present

## Smoke Tests (read-only)

| Test | Command | Pass Criteria |
|------|---------|---------------|
| Queue read | `hcloud dli ListQueues --cli-region={region} --queue_type=all` | JSON with `is_success: true`; queues array present |
| Database read | `hcloud dli ListDatabases --cli-region={region} --limit=5` | `is_success: true`; databases array present |
| Job list read | `hcloud dli ListSqlJobs --cli-region={region} --page-size=2` | `is_success: true`; jobs array present |
| Quota read | `hcloud dli ShowQuota --cli-region={region}` | `is_success: true`; quotas with CU type |
| Elastic pool read | `hcloud dli ListElasticResourcePools --cli-region={region} --limit=2` | `is_success: true` |

## Query Verification (per capability group)

Run one representative read command per group and confirm the response shape:

| Group | Probe Command |
|-------|---------------|
| Queue plans | `hcloud dli ListQueuePlans --cli-region={region} --queue_name={queue}` |
| Spark jobs | `hcloud dli ListSparkJobs --cli-region={region} --size=2` |
| Flink jobs | `hcloud dli ListFlinkJobs --cli-region={region} --limit=2` |
| Tables | `hcloud dli ListTables --cli-region={region} --database_name={db} --page-size=2` |
| Connections | `hcloud dli ListEnhancedConnections --cli-region={region} --limit=2` |
| Resources | `hcloud dli ListJobResources --cli-region={region}` |
| Variables | `hcloud dli ListGlobalVariables --cli-region={region} --limit=2` |
| Templates | `hcloud dli ListSqlJobTemplates --cli-region={region}` |
| Privileges | `hcloud dli ListAuthorizationPrivileges --cli-region={region} --object={object}` |
| Agency | `hcloud dli ShowDliAgency --cli-region={region}` |

## Write-Operation Verification

Mutating commands (Create/Update/Delete/scaling) are **not** executed in
verification by default — they require user double confirmation per this
Skill's safety policy. When authorized:

1. Capture a pre-change snapshot (relevant `List*` output).
2. Execute the confirmed command.
3. Re-run the corresponding `List*`/`Show*` to confirm the change.
4. Record the change snapshot in the output report.

## Parameter Verification

For any operation, confirm parameter spelling against CLI help:

```bash
hcloud dli <Operation> --cli-region=cn-north-4 --help
```

Check that `required` params appear in the command and optional params use exact
names from the `Params:` section.