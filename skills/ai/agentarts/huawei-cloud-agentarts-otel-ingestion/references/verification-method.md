# Verification Method

## API Verification Status

### Officially Verified APIs

These APIs are confirmed via official Huawei Cloud documentation:

| API | Method | Path | Source |
|-----|--------|------|--------|
| Create tracing business | POST | `/v1/apm2/openapi/tracing/business/create` | IAM authorization reference |
| Get business token | GET | `/v1/apm2/openapi/tracing/business/token/{business_id}` | IAM authorization reference |
| Get access point | POST | `/v1/apm2/openapi/tracing/access/get-access-point/{business_id}` | Huawei Stack APM guide |
| ShowOpsTrace | POST | AgentArts observation API | Official API docs |
| ShowOpsAgentMetricTrend | POST | AgentArts observation API | Official API docs |

### User-Provided APIs (Requires Manual Verification)

These APIs are from the existing otel-ingestion skill and require verification
in Huawei Cloud API Explorer (https://console.huaweicloud.com/apiexplorer):

| API | Method | Path | Status |
|-----|--------|------|--------|
| Create deliverConfig | POST | `/v2/trace/deliver-config` | User-provided |
| Update deliverConfig | PUT | `/v2/trace/deliver-config` | User-provided |
| Delete deliverConfig | DELETE | `/v2/trace/deliver-config/{id}` | User-provided |
| ListOpsTrace | POST | `/v1/ops/observation/traces` | Existence confirmed, path unverified |
| ListOpsSession | POST | `/v1/ops/observation/sessions` | Existence confirmed, path unverified |
| ShowOpsAgentMetricGauge | POST | `/v1/ops/observation/metrics/gauge` | Existence confirmed, path unverified |
| ListOpsAgentLog | POST | `/v1/ops/observation/logs` | Existence confirmed, path unverified |
| SubscribeOpsObservation | POST | Subscription management | Existence confirmed, path unverified |
| OpenOpsObservation | POST | Subscription management | Existence confirmed, path unverified |

### Verification Steps

1. **Check API Explorer**: Search for each API in
   https://console.huaweicloud.com/apiexplorer to confirm exact paths.

2. **Check SDK source** (if hcloud SDK installed):
   ```bash
   python3 -c "import huaweicloudsdkapm.v2 as m; import os; print(os.path.dirname(m.__file__))"
   grep "_http_info" {path}/apm_client.py
   grep -A8 "create_tracing_business_http_info" {path}/apm_client.py
   ```

3. **Check IAM authorization schema**:
   ```bash
   hcloud IAM GetAuthorizationSchemaV5 --cli-region={region} --service_code=apm
   hcloud IAM GetAuthorizationSchemaV5 --cli-region={region} --service_code=agentarts
   ```

### Verification Checklist

- [ ] APM tracing business create API path verified
- [ ] APM business token API path verified
- [ ] APM access point API path verified
- [ ] DeliverConfig API path verified in API Explorer
- [ ] ShowOpsTrace API path verified
- [ ] ShowOpsAgentMetricTrend API path verified
- [ ] ListOpsTrace API path verified
- [ ] ListOpsSession API path verified
- [ ] ShowOpsAgentMetricGauge API path verified
- [ ] ListOpsAgentLog API path verified
- [ ] Subscription API paths verified

### Official Documentation Sources

- IAM APM authorization: https://support.huaweicloud.com/intl/zh-cn/service-authorization-iam5/iam_11_0115.html
- Huawei Stack APM guide: https://support.huawei.com/enterprise/zh/doc/EDOC1100450998/d3162fbc
- AgentArts API overview: https://support.huaweicloud.com/api-agentarts/agentarts_07_0002.html
- ShowOpsTrace: https://support.huaweicloud.com/api-agentarts/ShowOpsTrace.html
- ShowOpsAgentMetricTrend: https://support.huaweicloud.com/api-agentarts/ShowOpsAgentMetricTrend.html
- Metric reporting via OTel: https://support.huaweicloud.com/ops-agentarts/agentarts_14_0126.html
- APM CLI reference: https://support.huaweicloud.com/clir-apm/APM-cli.html
