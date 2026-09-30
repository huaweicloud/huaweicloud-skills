# Verification Method

## CLI Verification Status

### APM Operations (All Verified in KooCLI)

| Operation | Purpose | Status |
|-----------|---------|--------|
| ListBusiness | List APM businesses | Verified |
| ShowBusinessDetail | Show business details | Verified |
| ShowToken | Get business token | Verified |
| ShowAccessPoint | Get access point | Verified |
| ShowAkSks | Show AK/SKs | Verified |
| SearchAgent | Search agents | Verified |
| SearchTransaction | Search transactions (traces) | Verified |
| ShowSpanSearch | Search spans | Verified |
| ListOpenRegion | List open regions | Verified |

### AOM Operations (All Verified in KooCLI)

| Operation | Purpose | Status |
|-----------|---------|--------|
| ListPromInstance | List Prometheus instances | Verified |
| ListAccessCode | List access codes | Verified |
| ListInstantQueryAomPromGet | Instant Prometheus query | Verified |
| ListRangeQueryAomPromGet | Range Prometheus query | Verified |
| ListMetadataAomPromGet | List Prometheus metadata | Verified |
| ListLabelsAomPromGet | List Prometheus labels | Verified |
| ShowMetricsData | Show metrics data | Verified |

### LTS Operations (All Verified in KooCLI)

| Operation | Purpose | Status |
|-----------|---------|--------|
| ListLogGroups | List log groups | Verified |
| ListLogStreams | List log streams | Verified |
| ListLogs | List logs | Verified |
| ListLogContext | Get log context | Verified |
| ListAccessConfig | List access configs | Verified |

### IAM Operations (All Verified in KooCLI)

| Operation | Purpose | Status |
|-----------|---------|--------|
| ListPoliciesV5 | List IAM policies | Verified |
| GetAuthorizationSchemaV5 | Get auth schema | Verified |

### AgentArts Observation APIs (API Only — Not in KooCLI)

| API | Purpose | Status |
|-----|---------|--------|
| ShowOpsTrace | Query traces in agent-ops | Official docs confirmed, path needs verification |
| ShowOpsAgentMetricTrend | Query metric trends | Official docs confirmed |
| ListOpsSession | Query sessions | Existence confirmed, path needs verification |
| ListOpsAgentLog | Query logs | Existence confirmed, path needs verification |

> For agent-ops observation APIs, use API (curl) mode. Verify exact paths in
> Huawei Cloud API Explorer: https://console.huaweicloud.com/apiexplorer
