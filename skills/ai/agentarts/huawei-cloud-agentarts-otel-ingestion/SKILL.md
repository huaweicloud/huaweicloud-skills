---
name: huawei-cloud-agentarts-otel-ingestion
description: |
  OpenTelemetry ingestion skill for Huawei Cloud AgentArts observability platform.
  Provides OTel telemetry data (trace/metrics/logs) ingestion into AgentArts agent-ops,
  AI Agent observation with gen_ai semantic conventions, auto-configuration for
  Java/Python/Node.js/Go applications, and ingestion diagnostics and verification.
  Covers APM deliverConfig forwarding (Path A) and OTLP direct connection (Path B).
  Triggers include: "AgentArts OTel", "AgentArts observability", "AI agent tracing",
  "gen_ai telemetry", "AgentArts OTLP", "otel接入AgentArts", "Agent观测配置"
tags:
  - opentelemetry
  - agentarts
  - observability
  - agent-ops
  - tracing
---

# Huawei Cloud AgentArts OpenTelemetry Ingestion

## Overview

This skill enables OpenTelemetry (OTel) telemetry data ingestion into Huawei Cloud
AgentArts observability platform (agent-ops). It covers four functional areas:

1. **OTel Telemetry Ingestion** — Route trace/metrics/logs from applications to
   agent-ops via APM deliverConfig forwarding (Path A, recommended) or OTLP direct
   connection (Path B, verification only).
2. **AI Agent Observation** — Instrument AI/LLM applications with OpenTelemetry GenAI
   semantic conventions (`gen_ai.*` spans, token usage metrics, model call chains).
3. **Auto-Configuration** — Detect application language/framework and generate
   ready-to-use OTel SDK/Collector configuration.
4. **Ingestion Diagnostics** — Verify data arrival via agent-ops observation APIs
   (trace/session/metric/log queries).

### Architecture

```
Application (OTel SDK/Collector)
  │
  ├── Path A (Recommended): OTLP → APM → deliverConfig → Kafka → agent-ops
  │
  └── Path B (Verification): OTLP → Collector → agent-ops (if OTLP receiver available)
```

### Data Flow

See `references/dataflow-diagram.md` for the Mermaid diagram.

## Prerequisites

### 1. Huawei Cloud Credentials

Set credentials out-of-band. Never paste AK/SK in chat.

```bash
export HUAWEI_ACCESS_KEY="<your-access-key-id>"
read -rs HUAWEI_SECRET_KEY; export HUAWEI_SECRET_KEY
export HUAWEI_REGION="cn-southwest-301"
```

Verify by running the CLI configure list command (if hcloud CLI is installed).

### 2. hcloud CLI (KooCLI)

Install: https://support.huaweicloud.com/qs-hcli/hcli_02_003.html

### 3. APM Subscription

Confirm agent-ops has subscribed to APM observation. If not subscribed, complete
subscription first (management plane: `SubscribeOpsObservation` / `OpenOpsObservation`).

### 4. IAM Permissions

See `references/iam-policies.md` for least-privilege policy.

### 5. OTel SDK

Install language-specific OTel packages:
- **Java**: `opentelemetry-javaagent` (download JAR)
- **Python**: `pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http`
- **Node.js**: `npm install @opentelemetry/sdk-node @opentelemetry/exporter-trace-otlp-http`
- **Go**: `go get go.opentelemetry.io/otel go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp`

## Workflow

### Step 1: Confirm Application Environment

Detect the application language/framework:

| Language | Detection Method | OTel Instrument |
|----------|-----------------|-----------------|
| Java | `pom.xml` / `build.gradle` / `.jar` files | `opentelemetry-javaagent` |
| Python | `requirements.txt` / `pyproject.toml` | `opentelemetry-sdk` |
| Node.js | `package.json` | `@opentelemetry/sdk-node` |
| Go | `go.mod` | `go.opentelemetry.io/otel` |

If existing OTel config is detected, read and adjust rather than overwrite.

### Step 2: Confirm Target Environment

| Parameter | Default | Description |
|-----------|---------|-------------|
| `region` | `cn-southwest-301` | agent-ops deployment region |
| `APM_ENDPOINT` | `https://apm2.cn-southwest-301.beta.myhuaweicloud.com` | APM OTLP endpoint |
| `AGENT_OPS_ENDPOINT` | `https://agentarts.cn-southwest-301.myhuaweicloud.com` | AgentArts API endpoint |
| `apm.internal.endpoint` | Internal endpoint | For deliverConfig forwarding |
| `wushan.common.appcode` | App code | For internal endpoint auth |

### Step 3: Confirm Ingestion Scope

- Data types: traces / metrics / logs
- Application name (`appName`) and business ID (`businessId`)

### Step 4: Execute Ingestion (Path A or B)

#### Path A: APM deliverConfig Ingestion (Recommended)

**4a. Create tracing business** (official API — verified via IAM authorization reference):

```bash
hcloud APM CreateBusiness --cli-region={region} \
  --name="otel-business-<appName>" \
  --display_name="<appName>" \
  --descp="otel business" \
  --cmdb_datasource_type="AGENTRUN"
```

API equivalent (official path):

```
POST {APM_ENDPOINT}/v1/apm2/openapi/tracing/business/create
Content-Type: application/json
X-Auth-Token: {iam_token}

{
  "name": "otel-business-<appName>",
  "display_name": "<appName>",
  "descp": "otel business",
  "cmdb_datasource_type": "AGENTRUN"
}
```

**4b. Get business token** (official API):

```bash
hcloud APM ShowToken --cli-region={region} \
  --business_id={business_id}
```

API equivalent:

```
GET {APM_ENDPOINT}/v1/apm2/openapi/tracing/business/token/{business_id}
X-Auth-Token: {iam_token}
x-business-id: {business_id}
```

Record the returned token for application-side OTel exporter auth.

**4c. Get access point** (official API):

```
POST {APM_ENDPOINT}/v1/apm2/openapi/tracing/access/get-access-point/{business_id}
X-Auth-Token: {iam_token}
x-business-id: {business_id}
```

**4d. Create deliverConfig forwarding** (user-provided API — requires manual verification):

> Note: This endpoint is from user-provided reference, not found in official public docs.
> Verify the exact path in Huawei Cloud API Explorer before use.

```
POST {APM_INTERNAL_ENDPOINT}/v2/trace/deliver-config?region=cn-southwest-301
x-apply-domain-id: {domain_id}
x-apply-role-name: te_admin
Content-Type: application/json

{
  "config_name": "AgentArts-<appName>",
  "deliver_domain": "{domain_id}",
  "deliver_otel_trace": true,
  "descp": "otel trace deliver",
  "business_ids": "{business_id}",
  "application_ids": "{app_id}",
  "otel_trace_topic_name": "{kafka_topic}",
  "kafka_config": {
    "bootstrap.servers": "{bootstrap_servers}",
    "acks": "all",
    "retries": 1,
    "sasl.mechanism": "PLAIN",
    "security.protocol": "SASL_SSL",
    "username": "{kafka_user}",
    "password": "{kafka_password}"
  }
}
```

Modify: `PUT /v2/trace/deliver-config` (body: `{id, deliver_otel_trace}`)
Delete: `DELETE /v2/trace/deliver-config/{id}?region=`

**4e. Configure application-side OTel SDK/Collector**

Java Agent:
```bash
java -javaagent:opentelemetry-javaagent.jar \
  -Dotel.service.name=<appName> \
  -Dotel.exporter.otlp.endpoint={APM_ENDPOINT} \
  -Dotel.exporter.otlp.headers="Authorization=Bearer {token}" \
  -jar app.jar
```

Python SDK:
```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

exporter = OTLPSpanExporter(
    endpoint=f"{APM_ENDPOINT}/v1/traces",
    headers={"Authorization": f"Bearer {token}"},
)
```

Node.js SDK:
```javascript
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');

const traceExporter = new OTLPTraceExporter({
  url: `${APM_ENDPOINT}/v1/traces`,
  headers: { Authorization: `Bearer ${token}` },
});
const sdk = new NodeSDK({ traceExporter, serviceName: '<appName>' });
sdk.start();
```

Go SDK:
```go
import (
  "go.opentelemetry.io/otel"
  "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
  "go.opentelemetry.io/otel/sdk/resource"
  sdktrace "go.opentelemetry.io/otel/sdk/trace"
  semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
)

exporter, _ := otlptracehttp.New(ctx,
  otlptracehttp.WithEndpoint(APM_ENDPOINT),
  otlptracehttp.WithHeaders(map[string]string{"Authorization": "Bearer " + token}),
)
```

OTel Collector (`config.yaml`):
```yaml
exporters:
  otlp/apm:
    endpoint: "{APM_ENDPOINT}:443"
    headers:
      Authorization: "Bearer {token}"
service:
  pipelines:
    traces:
      exporters: [otlp/apm]
    metrics:
      exporters: [otlp/apm]
    logs:
      exporters: [otlp/apm]
```

#### Path B: OTLP Direct Connection (Verification Only)

> As of current agent-ops version, the backend contains OTLP proto definitions but
> no OTLP receiver implementation. Path B is for verification testing only.

1. Deploy OTel Collector with OTLP receiver and test exporter.
2. Generate test spans from a sample application.
3. Verify data export to confirm SDK/Collector config correctness.
4. Use management plane APIs to verify data reachability.

### Step 5: AI Agent Observation (GenAI Semantic Conventions)

Instrument AI/LLM applications with OpenTelemetry GenAI semantic conventions:

| Span Name | Description | Key Attributes |
|-----------|-------------|----------------|
| `invoke_agent` | Agent invocation | `gen_ai.system`, `gen_ai.request.model` |
| `execute_tool` | Tool execution | `gen_ai.tool.name`, `gen_ai.tool.description` |
| `inference` | Model inference | `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |

Python example (LLM tracing):
```python
from opentelemetry import trace

tracer = trace.get_tracer("agentarts-ai")

with tracer.start_as_current_span("invoke_agent") as span:
    span.set_attribute("gen_ai.system", "huawei-cloud")
    span.set_attribute("gen_ai.request.model", "pangu-4.0")
    # ... agent logic ...
    span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
```

Node.js example:
```javascript
const tracer = trace.getTracer('agentarts-ai');
const span = tracer.startSpan('invoke_agent');
span.setAttribute('gen_ai.system', 'huawei-cloud');
span.setAttribute('gen_ai.request.model', 'pangu-4.0');
// ... agent logic ...
span.setAttribute('gen_ai.usage.input_tokens', inputTokens);
span.setAttribute('gen_ai.usage.output_tokens', outputTokens);
span.end();
```

See `references/genai-semconv.md` for full attribute reference.

### Step 6: Verify Data Arrival

Query agent-ops observation APIs to confirm data ingestion.
These are management plane APIs — authenticate with IAM token (`X-Auth-Token`), not the OTel business-side Bearer token:

**ShowOpsTrace** (official — verified):
```bash
curl -X POST {AGENT_OPS_ENDPOINT}/v1/ops/observation/traces \
  -H "X-Auth-Token: {iam_token}" \
  -H "Content-Type: application/json" \
  -d '{"start_time": 1720000000000, "end_time": 1720600000000}'
```

**ShowOpsAgentMetricTrend** (official — verified):
```bash
curl -X POST {AGENT_OPS_ENDPOINT}/v1/ops/observation/metrics/trend \
  -H "X-Auth-Token: {iam_token}" \
  -H "Content-Type: application/json" \
  -d '{"start_time": 1720000000000, "end_time": 1720600000000}'
```

**ListOpsSession** (existence confirmed, path requires manual verification):
```bash
curl -X POST {AGENT_OPS_ENDPOINT}/v1/ops/observation/sessions \
  -H "X-Auth-Token: {iam_token}" \
  -H "Content-Type: application/json" \
  -d '{"start_time": 1720000000000, "end_time": 1720600000000}'
```

> Note: Exact paths for ListOpsTrace, ListOpsSession, ShowOpsAgentMetricGauge,
> ListOpsAgentLog require manual verification in Huawei Cloud API Explorer.
> See `references/verification-method.md`.

### Step 7: Ingestion Diagnostics

Common diagnostic checks:

| Symptom | Check |
|---------|-------|
| Auth failure (401/403) | Token expired → re-fetch business token; check appcode permissions |
| No subscription | Subscribe via `SubscribeOpsObservation` / `OpenOpsObservation` |
| Kafka unreachable | Check bootstrap-servers, SASL/SSL, topic existence |
| SDK/Collector mismatch | Confirm OTLP protocol version compatibility |
| No data in management plane | Check time range, region, `deliver_otel_trace=true` |
| OTLP direct unavailable | agent-ops has no OTLP receiver → fall back to Path A |

## Core Commands

| Command | Purpose | Mode |
|---------|---------|------|
| `hcloud APM CreateBusiness --cli-region={region}` | Create tracing business | CLI |
| `hcloud APM ShowToken --cli-region={region}` | Get business token | CLI |
| `POST /v1/apm2/openapi/tracing/business/create` | Create tracing business (API) | API |
| `GET /v1/apm2/openapi/tracing/business/token/{id}` | Get business token (API) | API |
| `POST /v1/apm2/openapi/tracing/access/get-access-point/{id}` | Get access point (API) | API |
| `POST /v2/trace/deliver-config` | Create deliverConfig (user-provided) | API |
| `POST {AGENT_OPS_ENDPOINT}/v1/ops/observation/traces` | Query traces | API |
| `POST {AGENT_OPS_ENDPOINT}/v1/ops/observation/metrics/trend` | Query metric trend | API |

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `region` | Yes | agent-ops deployment region | `cn-southwest-301` |
| `APM_ENDPOINT` | Yes | APM OTLP endpoint | `https://apm2.cn-southwest-301.beta.myhuaweicloud.com` |
| `AGENT_OPS_ENDPOINT` | Yes | AgentArts API endpoint | `https://agentarts.cn-southwest-301.myhuaweicloud.com` |
| `appName` | Yes | Application name | `my-ai-agent` |
| `business_id` | Yes (Path A) | Tracing business ID | From create response |
| `token` | Yes | Business token (OTel exporter auth, data plane) | From get-token response |
| `iam_token` | Yes | IAM token (management plane API auth) | From IAM STS |
| `domain_id` | Yes (Path A) | IAM domain ID | From IAM console |
| `kafka_topic` | Yes (Path A) | Kafka topic name | From deliverConfig |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | Pre-configured OTel endpoint | Env var |
| `OTEL_SERVICE_NAME` | No | Pre-configured service name | Env var |

## KooCLI Command Format Standard

```bash
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | KooCLI Service name (uppercase) | `APM` |
| Operation name | PascalCase | `CreateBusiness` |
| Region parameter | `--cli-region=<value>` | `--cli-region={region}` |
| Simple parameter | `--key=value` | `--business_id=xxx` |

> Note: AgentArts observation APIs (ShowOpsTrace, ShowOpsAgentMetricTrend, etc.)
> are not yet confirmed in KooCLI. Use API (curl) mode for these operations.

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies
- `references/cli-installation-guide.md` — hcloud CLI installation guide
- `references/verification-method.md` — Verification methods and API status
- `references/dataflow-diagram.md` — Mermaid data flow diagram
- `references/acceptance-criteria.md` — Acceptance criteria checklist
- `references/genai-semconv.md` — OpenTelemetry GenAI semantic conventions

## Edge Cases

| Scenario | Handling |
|----------|---------|
| hcloud not installed | Use API (curl) mode for all operations |
| Python/SDK not available | Use OTel Collector with YAML config instead of SDK |
| DeliverConfig API path invalid | Verify in API Explorer; mark as requires manual verification |
| agent-ops has no OTLP receiver | Use Path A (APM deliverConfig) instead of Path B |
| AI app has no OTel instrumentation | Auto-generate instrumentation config based on detected language |
| Token expired | Re-fetch business token via get-token API |
| No data in management plane | Check time range, region, deliver_otel_trace flag, Kafka connectivity |

## Notes

- **API verification status**: APM tracing APIs are officially verified. AgentArts
  observation APIs (ShowOpsTrace, ShowOpsAgentMetricTrend) are officially documented.
  DeliverConfig and some observation query APIs require manual verification.
- **Credential security**: Never hardcode AK/SK. Read from env vars or CLI profile.
- **GenAI semconv**: OpenTelemetry GenAI semantic conventions are in Development
  status (as of OTel v1.41). Attribute names may change.
- **Least privilege**: See `references/iam-policies.md` for required permissions.
