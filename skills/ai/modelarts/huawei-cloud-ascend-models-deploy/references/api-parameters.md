# API Parameters

Detailed API parameter reference.

## Chat Completions (/v1/chat/completions)

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| model | string | Yes | - | Model name |
| messages | array | Yes | - | Message list |
| max_tokens | integer | No | 16 | Max output tokens |
| temperature | float | No | 1.0 | Sampling randomness |
| top_p | float | No | 1.0 | Nucleus sampling |
| top_k | integer | No | -1 | Top-K sampling |
| stream | boolean | No | false | Stream output |
| stop | array | No | null | Stop sequences |
| presence_penalty | float | No | 0.0 | Presence penalty |
| frequency_penalty | float | No | 0.0 | Frequency penalty |
| repetition_penalty | float | No | 1.0 | Repetition penalty |
| chat_template_kwargs | object | No | {} | Template params |

### Message Format

```json
{
  "role": "user|assistant|system",
  "content": "text or array"
}
```

### Multimodal Content

```json
{
  "role": "user",
  "content": [
    {"type": "image_url", "image_url": {"url": "image_url"}},
    {"type": "text", "text": "prompt"}
  ]
}
```

## Embeddings (/v1/embeddings)

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| model | string | Yes | Model name |
| input | string/array | Yes | Text to embed |
| encoding_format | string | No | float/base64 |

## Rerank (/v1/rerank)

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| model | string | Yes | Model name |
| query | string | Yes | Query text |
| documents | array | Yes | Documents to rerank |
| top_n | integer | No | Return top N |

## Thinking Mode

For Qwen3/Qwen3.6 models:

```json
{
  "chat_template_kwargs": {
    "enable_thinking": false
  }
}
```

- `true` (default): Output reasoning process
- `false`: Direct output only
