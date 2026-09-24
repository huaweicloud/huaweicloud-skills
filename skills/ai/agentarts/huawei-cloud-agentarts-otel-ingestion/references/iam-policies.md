# IAM Policies

## Least-Privilege Policy for AgentArts OTel Ingestion

### APM Tracing Business Management

Required for creating tracing business, getting business token, and getting access point.

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "apm:tracingBusiness:create",
        "apm:tracingBusiness:getToken",
        "apm:tracingAccess:getAccessPoint"
      ]
    }
  ]
}
```

> Note: IAM action names are based on the official IAM service-authorization
> reference for APM. Verify exact action names via:
> `hcloud IAM GetAuthorizationSchemaV5 --cli-region={region} --service_code=apm`

### AgentArts Observation APIs

Required for querying trace, session, metrics, and logs in agent-ops.

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentarts:showOpsTrace",
        "agentarts:showOpsAgentMetricTrend",
        "agentarts:listOpsTrace",
        "agentarts:listOpsSession",
        "agentarts:showOpsAgentMetricGauge",
        "agentarts:listOpsAgentLog"
      ]
    }
  ]
}
```

> Note: `agentarts:showOpsTrace` and `agentarts:showOpsAgentMetricTrend` are
> officially documented. Other action names are inferred from API naming
> conventions and require verification via:
> `hcloud IAM GetAuthorizationSchemaV5 --cli-region={region} --service_code=agentarts`

### Subscription Management

Required for subscribing to observation services.

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentarts:subscribeOpsObservation",
        "agentarts:openOpsObservation"
      ]
    }
  ]
}
```

> Note: Action names require verification via IAM authorization schema query.

### System Policies

The following Huawei Cloud system policies may be used as alternatives:

| System Policy | Scope |
|---------------|-------|
| APM FullAccess | Full access to APM service |
| AgentArts FullAccess | Full access to AgentArts service (if available) |

Verify system policy names via:
```bash
hcloud IAM ListPoliciesV5 --cli-region={region}
```
