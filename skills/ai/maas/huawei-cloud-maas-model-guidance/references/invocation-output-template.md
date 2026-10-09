# Invocation Output Template - MaaS Model Invocation

This file defines the template format for outputting invocation instructions to users. After the user selects a specific model, follow this template to organize and output the invocation instructions, including URL, model name, API Key, and invocation example code.

## Usage Instructions

After the user selects a model, generate the invocation instruction document based on the following template and output it to the user. The `{variables}` in the template should be replaced with actual values.

---

## Template: MaaS Model Invocation Instructions

```markdown
# MaaS Model Invocation Instructions

## 1. Basic Information

| Item | Value |
|------|-------|
| **Model Name** | {Model display name, e.g. DeepSeek-V3.2} |
| **model Parameter** | {model parameter value, e.g. deepseek-v3.2} |
| **Model Type** | {Deep Thinking/Text Generation/Image Understanding/Image Generation/Video Generation/Embedding/Reranking} |
| **Supported Region** | 西南-贵阳一 |
| **Context Length** | {e.g. 160K} |
| **Max Input Length** | {e.g. 128K} |
| **Max Output Length** | {e.g. 32K} |
| **Supported Capabilities** | {e.g. Deep Thinking(toggleable), Function Call, Prefix Completion} |

## 2. Prerequisites

### 2.1 Enable Preset Service

For first-time invocation, you need to enable the preset service first:
1. Log in to the MaaS console and select the **西南-贵阳一** region
2. In the left navigation bar, select **"Model Inference > Online Inference"**
3. On the **"Preset Service"** tab, find {Model display name}, and click **"Enable Service"**
4. Check **"I have read and agree to the above description and the MaaS Service Statement"**, and click **"One-Click Enable"**

### 2.2 Get API Key

1. Log in to the MaaS console → **Management & Statistics** → **API Key Management** → **Create API Key**
2. Copy and securely save the API Key

> ⚠️ **Important**: The API Key will only be displayed once after creation. Please copy and save it promptly. If the API Key is lost, create a new API Key.

## 3. Invocation API

{Provide the corresponding API interface information based on model type and user preference}

### {Interface name, e.g. MaaS Standard API V2}

| Item | Value |
|------|-------|
| **Interface URL** | {API URL} |
| **Request Method** | POST |
| **Authentication** | Authorization: Bearer {API_KEY} |
| **Content-Type** | application/json |

{If it is a large language model and the user has not explicitly specified, provide all supported interface types and their differences}

#### Interface Differences

| Interface Type | URL | Features |
|----------------|-----|----------|
| MaaS Standard API V2 | `https://api.modelarts-maas.com/v2/chat/completions` | MaaS native interface, most complete features, supports deep thinking control |
| OpenAI Compatible Interface | `https://api.modelarts-maas.com/openai/v1/chat/completions` | Compatible with OpenAI SDK, easy migration |
| Anthropic Compatible Interface | `https://api.modelarts-maas.com/anthropic/v1/messages` | Compatible with Anthropic SDK, easy migration from Claude |

> **Note**: {Explain which interfaces this model actually supports, e.g. "This model supports V2, OpenAI, and Anthropic interfaces, but does not support the V1 interface"}

## 4. Request Parameters

### Request Body Example

```json
{
  "model": "{model parameter value}",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello"}
  ]
}
```

### Key Parameter Description

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | string | Yes | Model name, value is `{model parameter value}` |
| messages | array | Yes | Conversation message list |
| stream | boolean | No | Whether to use streaming output, default false |
| max_tokens | integer | No | Maximum output token count |
| thinking | object | No | Deep thinking control, e.g. `{"type": "enabled"}` (only for models that support deep thinking) |

## 5. Invocation Example Code

### Python (requests)

```python
import requests
import json

url = "{API URL}"
api_key = "MAAS_API_KEY"  # Replace MAAS_API_KEY with your obtained API Key

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

data = {
    "model": "{model parameter value}",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.status_code)
print(response.text)
```

### Curl

```bash
curl -X POST "{API URL}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "{model parameter value}",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://api.modelarts-maas.com/openai/v1"
)
response = client.chat.completions.create(
    model="{model parameter value}",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ]
)
print(response.choices[0].message.content)
```

### Java

```java
// Recommended JDK version is 15+
String apiUrl = "{API URL}";
String apiKey = "MAAS_API_KEY";
String modelName = "{model parameter value}";

String requestBody = String.format("""
{
    "model": "%s",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
}""", modelName);
// ... Send request using HttpClient
```

{If it is a deep thinking model, supplement deep thinking example}

{If it is an image understanding model, supplement image understanding example}

{If it is an image/video generation model, supplement the corresponding example}

## 6. Pricing Information

For specific pricing, please refer to the MaaS pricing details: https://www.huaweicloud.com/pricing/calculator.html#/maas

{Explain the billing method for this model type, e.g. "Text generation models are billed by tokens (input + output)"}
```

---

## Output Example: DeepSeek-V3.2 Invocation Instructions

The following is a complete output example for reference:

```markdown
# MaaS Model Invocation Instructions

## 1. Basic Information

| Item | Value |
|------|-------|
| **Model Name** | DeepSeek-V3.2 |
| **model Parameter** | deepseek-v3.2 |
| **Model Type** | Text Generation/Deep Thinking |
| **Supported Region** | 西南-贵阳一 |
| **Context Length** | 160K |
| **Max Input Length** | 128K |
| **Max Output Length** | 32K |
| **Max Thinking Chain Length** | 32K |
| **Supported Capabilities** | Deep Thinking(toggleable), Function Call, Prefix Completion |

## 2. Prerequisites

### 2.1 Enable Preset Service

For first-time invocation, you need to enable the preset service first:
1. Log in to the MaaS console and select the **西南-贵阳一** region
2. In the left navigation bar, select **"Model Inference > Online Inference"**
3. On the **"Preset Service"** tab, find DeepSeek-V3.2, and click **"Enable Service"**
4. Check **"I have read and agree to the above description and the MaaS Service Statement"**, and click **"One-Click Enable"**

### 2.2 Get API Key

1. Log in to the MaaS console → **Management & Statistics** → **API Key Management** → **Create API Key**
2. Copy and securely save the API Key

> ⚠️ **Important**: The API Key will only be displayed once after creation. Please copy and save it promptly. If the API Key is lost, create a new API Key.

## 3. Invocation API

This model supports three interface types:

| Interface Type | URL | Features |
|----------------|-----|----------|
| **MaaS Standard API V2** | `https://api.modelarts-maas.com/v2/chat/completions` | MaaS native interface, most complete features, recommended for new projects |
| **OpenAI Compatible Interface** | `https://api.modelarts-maas.com/openai/v1/chat/completions` | Compatible with OpenAI SDK, easy migration from OpenAI |
| **Anthropic Compatible Interface** | `https://api.modelarts-maas.com/anthropic/v1/messages` | Compatible with Anthropic SDK, easy migration from Claude |

> **Note**: This model does not support the V1 interface.

## 4. Invocation Example Code

### Curl

```bash
curl -X POST "https://api.modelarts-maas.com/v2/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "deepseek-v3.2",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="MAAS_API_KEY",  # Replace with your API Key
    base_url="https://api.modelarts-maas.com/openai/v1"
)
response = client.chat.completions.create(
    model="deepseek-v3.2",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ]
)
print(response.choices[0].message.content)
```

### Enable Deep Thinking

```bash
curl -X POST "https://api.modelarts-maas.com/v2/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "deepseek-v3.2",
    "messages": [
      {"role": "user", "content": "Which is larger, 9.11 or 9.8?"}
    ],
    "thinking": {"type": "enabled"}
  }'
```

## 5. Pricing Information

For specific pricing, please refer to the MaaS pricing details: https://www.huaweicloud.com/pricing/calculator.html#/maas

```
