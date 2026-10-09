# API Interfaces - MaaS Model Invocation

MaaS provides multiple API interface types, and different models support different interface types. This document details each interface type and their differences.

## 1. Large Language Model Interfaces (Text Generation / Deep Thinking / Image Understanding)

### 1.1 Interface Type Overview

| Interface Type | URL | Description |
|----------|-----|------|
| **MaaS Standard API V2** | `https://api.modelarts-maas.com/v2/chat/completions` | MaaS native interface, supports all features, recommended for new projects |
| **MaaS Standard API V1** | `https://api.modelarts-maas.com/v1/chat/completions` | Legacy interface, no longer evolving, recommend using V2 first |
| **OpenAI Compatible Interface** | `https://api.modelarts-maas.com/openai/v1/chat/completions` | Compatible with OpenAI SDK, convenient for migrating from OpenAI |
| **Anthropic Compatible Interface** | `https://api.modelarts-maas.com/anthropic/v1/messages` | Compatible with Anthropic SDK, convenient for migrating from Claude |

### 1.2 Interface Differences in Detail

#### MaaS Standard API V2

- **Recommended scenario**: New projects, need to use all MaaS features
- **Advantages**:
  - Supports deep thinking control (`thinking` parameter)
  - Supports prefix continuation (`prefix: true`)
  - Supports Function Call
  - Supports streaming/non-streaming output
  - Most complete MaaS native functionality
- **Authentication**: `Authorization: Bearer <API_KEY>`
- **Request example**:
```json
{
  "model": "deepseek-v3.2",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello"}
  ],
  "thinking": {"type": "enabled"}
}
```

#### MaaS Standard API V1

- **Recommended scenario**: Existing projects already using the V1 interface
- **Note**: No longer evolving, recommend migrating to V2
- **Authentication**: `Authorization: Bearer <API_KEY>`
- **Request example**:
```json
{
  "model": "deepseek-v3",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello"}
  ]
}
```

#### OpenAI Compatible Interface

- **Recommended scenario**: Existing OpenAI SDK code, migrating from OpenAI
- **Advantages**:
  - Can directly use the `openai` Python SDK, just modify `base_url`
  - Compatible with OpenAI ecosystem tools
  - Supports deep thinking (passed via `extra_body`)
- **Authentication**: `Authorization: Bearer <API_KEY>`
- **Usage**:
```python
from openai import OpenAI
client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://api.modelarts-maas.com/openai/v1"
)
```
- **Deep thinking**:
```python
response = client.chat.completions.create(
    model="deepseek-v3.2",
    messages=[...],
    extra_body={"thinking": {"type": "enabled"}}
)
```

#### Anthropic Compatible Interface

- **Recommended scenario**: Existing Anthropic SDK code, migrating from Claude
- **Advantages**:
  - Can directly use the `anthropic` Python SDK
  - Compatible with Claude ecosystem
  - Supports deep thinking and Function Call
- **Authentication**: `x-api-key: <API_KEY>`
- **Supported models**: DeepSeek-V4-Pro, DeepSeek-V4-Flash, DeepSeek-V3.2, DeepSeek-V3.1, DeepSeek-V3, DeepSeek-R1-0528, Kimi-K2.6, GLM-5, GLM-5.1

### 1.3 Interface Selection Recommendations

| User Scenario | Recommended Interface |
|----------|----------|
| New project, no legacy constraints | MaaS Standard API V2 |
| Existing OpenAI SDK code | OpenAI Compatible Interface |
| Existing Anthropic/Claude SDK code | Anthropic Compatible Interface |
| Existing V1 project | MaaS Standard API V1 (recommend migrating to V2) |
| Need deep thinking + Function Call | V2 or OpenAI or Anthropic |
| Using OpenAI ecosystem tools | OpenAI Compatible Interface |

### 1.4 Supported Interface Types by Model

> **Important**: Not all models support all interface types. Please provide users with available interfaces based on the table below.

| Model | V2 | OpenAI | Anthropic | V1 |
|------|:--:|:------:|:---------:|:--:|
| DeepSeek-V4-Pro | ✅ | ✅ | ✅ | ❌ |
| DeepSeek-V4-Flash | ✅ | ✅ | ✅ | ❌ |
| DeepSeek-V3.2 | ✅ | ✅ | ✅ | ❌ |
| DeepSeek-V3.1 | ✅ | ✅ | ✅ | ❌ |
| DeepSeek-V3 | ✅ | ✅ | ✅ | ✅ |
| DeepSeek-R1-0528 | ✅ | ✅ | ✅ | ✅ |
| Qwen3-235B-A22B | ✅ | ✅ | ❌ | ✅ |
| Qwen3-32B | ✅ | ✅ | ❌ | ✅ |
| Qwen3-30B-A3B | ✅ | ✅ | ❌ | ✅ |
| Kimi-K2.6 | ✅ | ✅ | ✅ | ❌ |
| Kimi-K2 | ✅ | ✅ | ❌ | ✅ |
| LongCat-Flash-Chat | ✅ | ✅ | ❌ | ✅ |
| GLM-5 | ✅ | ✅ | ✅ | ❌ |
| GLM-5.1 | ✅ | ✅ | ✅ | ❌ |
| Qwen2.5-VL-72B | ❌ | ❌ | ❌ | ✅ |

## 2. Other Model Type Interfaces

### 2.1 Image Generation Interface

| Interface | URL | Description |
|------|-----|------|
| Image Generation | `https://api.modelarts-maas.com/v1/images/generations` | Synchronous interface, returns generated image result |

**Supported models**: Qwen_Image, Qwen-Image-Edit

### 2.2 Video Generation Interface

| Interface | URL | Description |
|------|-----|------|
| Create Video Generation Task | `https://api.modelarts-maas.com/v1/video/generations` | Asynchronous interface, returns task_id |
| Query Video Generation Task | `https://api.modelarts-maas.com/v1/video/generations/{task_id}` | Query result by task_id |

**Supported models**: Wan2.2-T2V-A14B, Wan2.2-I2V-A14B

> Video generation is an asynchronous interface. You need to first create a task to get a task_id, then query the generation result via task_id.

### 2.3 Text Embedding Interface

| Interface | URL | Description |
|------|-----|------|
| Create Text Embedding | `https://api.modelarts-maas.com/v1/embeddings` | Convert text to vectors |

**Supported models**: BGE-M3

### 2.4 Rerank Interface

| Interface | URL | Description |
|------|-----|------|
| Create Rerank | `https://api.modelarts-maas.com/v1/rerank` | Perform semantic reranking on documents |

**Supported models**: BGE-Reranker-V2-M3

### 2.5 Model List Query Interface

| Interface | URL | Description |
|------|-----|------|
| Get Model List | `https://api.modelarts-maas.com/v1/models` | GET request, query available model list |
