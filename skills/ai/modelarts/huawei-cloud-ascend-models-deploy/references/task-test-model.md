# Task: Test Model

Test deployed model inference.

## LLM Chat Completions

```bash
curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3-14B","messages":[{"role":"user","content":"hello"}],"max_tokens":256}'
```

## VL Multimodal

```bash
curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3-VL-32B-Instruct","messages":[{"role":"user","content":[{"type":"image_url","image_url":{"url":"https://example.com/image.jpg"}},{"type":"text","text":"describe the image"}]}],"max_tokens":512}'
```

## Embedding

```bash
curl -s -X POST http://localhost:8080/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"bge-m3","input":"I love shanghai"}'
```

## Rerank

```bash
curl -s -X POST http://localhost:8080/v1/rerank \
  -H 'Content-Type: application/json' \
  -d '{"model":"bge-reranker-v2-m3","query":"What is the capital of France?","documents":["Paris is the capital of France.","London is the capital of the UK."]}'
```

## Response Format

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "Qwen3-14B",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```
