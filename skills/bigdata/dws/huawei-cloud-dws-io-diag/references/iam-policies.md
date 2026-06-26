# IAM Policies - DWS I/O Overload Diagnosis

## Basic Diagnosis (Read-only)

| API Action | Permission | Purpose |
|------------|------------|---------|
| dws:clusters:get | View cluster details | Get cluster basic information |
| dws:clusters:list | List clusters | Confirm cluster exists, get project_id |
| dws:metricData:get | Query monitoring metrics | Get IOStat, CpuStat, cpu_io_diagnose_detail and other metric data |
| dws:hostOverview:get | Query host information | Get host_id → {host_name, ip} mapping |

## KooCLI Corresponding Commands

| Permission | hcloud Command |
|------------|----------------|
| dws:clusters:list | `hcloud DWS ListClusters --cli-region=<region> --project_id=<pid> --offset=0 --limit=200` |
| dws:metricData:get | `hcloud DWS ListMetricsData --cli-region=<region> --cluster_id=<id> --metric_name=<name> --project_id=<pid> --from=<ts> --to=<ts> --offset=0 --limit=200` |
| dws:hostOverview:get | `hcloud DWS ListHostOverview --cli-region=<region> --project_id=<pid> --cluster_id=<cid> --offset=0 --limit=200` |

## MCP Server Corresponding Tools

| Permission | MCP Tool |
|------------|----------|
| dws:clusters:list | `dws_autopilot_get_clusters` |
| dws:metricData:get | `dws_autopilot_get_metric` |
| dws:hostOverview:get | `dws_autopilot_get_hosts` |

## Minimum Permission Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dws:clusters:get",
        "dws:clusters:list",
        "dws:metricData:get",
        "dws:hostOverview:get"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Permission Failure Handling

1. When any command fails due to permission errors, read this document
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## Common Permission Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| 403 | Insufficient permissions | Check if the IAM user has the above permissions |
| 401 | Authentication failed | Check AK/SK configuration or IAM Token validity |
| 50201 | Autopilot backend unavailable | Retry later or contact operations staff |
| RDS.9999 | Autopilot backend error | Retry later or contact operations staff |
