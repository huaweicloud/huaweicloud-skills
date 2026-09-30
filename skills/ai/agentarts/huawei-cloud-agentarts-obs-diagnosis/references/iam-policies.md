# IAM Policies

## Least-Privilege Policy for AgentArts Observability Diagnosis

### APM Read Operations (Traces/Sessions Diagnosis)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "apm:business:list",
        "apm:business:get",
        "apm:token:get",
        "apm:accessPoint:get",
        "apm:agent:search",
        "apm:transaction:search",
        "apm:span:search",
        "apm:trace:event:get",
        "apm:region:list"
      ]
    }
  ]
}
```

> Note: Verify exact action names via:
> `hcloud IAM GetAuthorizationSchemaV5 --cli-region=cn-north-4 --service_code=apm`

### AOM Read Operations (Metrics Diagnosis)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "aom:promInstance:list",
        "aom:accessCode:list",
        "aom:prom:query",
        "aom:prom:rangeQuery",
        "aom:prom:metadata:get",
        "aom:prom:labels:list",
        "aom:metric:list",
        "aom:metricData:get"
      ]
    }
  ]
}
```

> Note: Verify exact action names via:
> `hcloud IAM GetAuthorizationSchemaV5 --cli-region=cn-north-4 --service_code=aom`

### LTS Read Operations (Logs Diagnosis)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lts:logGroup:list",
        "lts:logStream:list",
        "lts:logs:list",
        "lts:logContext:get",
        "lts:accessConfig:list"
      ]
    }
  ]
}
```

> Note: Verify exact action names via:
> `hcloud IAM GetAuthorizationSchemaV5 --cli-region=cn-north-4 --service_code=lts`

### IAM Read Operations (Permission Diagnosis)

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:policies:list",
        "iam:authorizationSchema:get"
      ]
    }
  ]
}
```

### System Policies

| System Policy | Scope |
|---------------|-------|
| APM ReadOnlyAccess | Read-only access to APM |
| AOM ReadOnlyAccess | Read-only access to AOM |
| LTS ReadOnlyAccess | Read-only access to LTS |
| IAM ReadOnlyAccess | Read-only access to IAM |

Verify system policy names via:
```bash
hcloud IAM ListPoliciesV5 --cli-region=cn-north-4
```
