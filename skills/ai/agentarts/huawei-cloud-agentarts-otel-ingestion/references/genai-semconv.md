# OpenTelemetry GenAI Semantic Conventions

## Overview

This reference covers OpenTelemetry semantic conventions for GenAI/AI Agent
instrumentation in AgentArts. These conventions enable agent-ops to aggregate
AI-specific metrics (token usage, model calls, agent invocations).

> Note: GenAI semantic conventions are in Development status (as of OTel v1.41).
> Attribute names may change in future versions.

## Span Names

| Span Name | Description | When to Use |
|-----------|-------------|-------------|
| `invoke_agent` | Agent invocation | When an AI agent is invoked |
| `execute_tool` | Tool execution | When an agent calls a tool |
| `inference` | Model inference | When calling an LLM model |
| `chat` | Chat completion | For chat-based interactions |
| `embeddings` | Embedding generation | For embedding API calls |

## Key Attributes

### Model Identification

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.system` | string | AI system identifier | `huawei-cloud` |
| `gen_ai.request.model` | string | Requested model name | `pangu-4.0` |
| `gen_ai.response.model` | string | Actual model used (may differ) | `pangu-4.0-turbo` |

### Token Usage

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.usage.input_tokens` | int | Input/prompt tokens | `1500` |
| `gen_ai.usage.output_tokens` | int | Output/completion tokens | `800` |
| `gen_ai.usage.total_tokens` | int | Total tokens consumed | `2300` |

### Tool Execution

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.tool.name` | string | Tool name | `web_search` |
| `gen_ai.tool.description` | string | Tool description | `Search the web` |
| `gen_ai.tool.call.id` | string | Unique call ID | `call_abc123` |

### Agent-Specific

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.agent.id` | string | Agent identifier | `agent-001` |
| `gen_ai.agent.name` | string | Agent name | `customer-support` |
| `gen_ai.agent.type` | string | Agent type | `ReAct` |
| `gen_ai.resource_type` | string | Resource type | `agent_instance` |

### Session

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `gen_ai.session.id` | string | Session identifier | `session-xyz` |
| `gen_ai.conversation.id` | string | Conversation ID | `conv-123` |

## Language Examples

### Python

```python
from opentelemetry import trace

tracer = trace.get_tracer("agentarts-ai")

with tracer.start_as_current_span("invoke_agent") as span:
    span.set_attribute("gen_ai.system", "huawei-cloud")
    span.set_attribute("gen_ai.request.model", "pangu-4.0")
    span.set_attribute("gen_ai.agent.id", "agent-001")
    span.set_attribute("gen_ai.session.id", session_id)

    result = agent.invoke(input)

    span.set_attribute("gen_ai.usage.input_tokens", result.input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", result.output_tokens)
    span.set_attribute("gen_ai.usage.total_tokens",
                       result.input_tokens + result.output_tokens)
```

### Node.js

```javascript
const tracer = trace.getTracer('agentarts-ai');
const span = tracer.startSpan('invoke_agent');
span.setAttribute('gen_ai.system', 'huawei-cloud');
span.setAttribute('gen_ai.request.model', 'pangu-4.0');
span.setAttribute('gen_ai.agent.id', 'agent-001');
span.setAttribute('gen_ai.session.id', sessionId);

const result = await agent.invoke(input);

span.setAttribute('gen_ai.usage.input_tokens', result.inputTokens);
span.setAttribute('gen_ai.usage.output_tokens', result.outputTokens);
span.setAttribute('gen_ai.usage.total_tokens',
                  result.inputTokens + result.outputTokens);
span.end();
```

### Java

```java
Tracer tracer = GlobalOpenTelemetry.getTracer("agentarts-ai");
Span span = tracer.spanBuilder("invoke_agent").startSpan();
try (Scope scope = span.makeCurrent()) {
    span.setAttribute("gen_ai.system", "huawei-cloud");
    span.setAttribute("gen_ai.request.model", "pangu-4.0");
    span.setAttribute("gen_ai.agent.id", "agent-001");

    var result = agent.invoke(input);

    span.setAttribute("gen_ai.usage.input_tokens", result.getInputTokens());
    span.setAttribute("gen_ai.usage.output_tokens", result.getOutputTokens());
} finally {
    span.end();
}
```

### Go

```go
tracer := otel.Tracer("agentarts-ai")
ctx, span := tracer.Start(ctx, "invoke_agent")
defer span.End()

span.SetAttributes(
    attribute.String("gen_ai.system", "huawei-cloud"),
    attribute.String("gen_ai.request.model", "pangu-4.0"),
    attribute.String("gen_ai.agent.id", "agent-001"),
)

result, err := agent.Invoke(ctx, input)
if err != nil {
    return err
}

span.SetAttributes(
    attribute.Int("gen_ai.usage.input_tokens", result.InputTokens),
    attribute.Int("gen_ai.usage.output_tokens", result.OutputTokens),
    attribute.Int("gen_ai.usage.total_tokens",
                  result.InputTokens + result.OutputTokens),
)
```

## Data Security

Never include in trace attributes:
- Authentication credentials of any kind
- User login secrets
- Personally identifiable information (PII)
- Full request/response payloads (use summaries or hashes instead)
