# Model Catalog

Complete list of supported models.

## Large Language Models (LLM)

| Model | Min Cards | Endpoint |
|-------|-----------|----------|
| Qwen3-14B | 1 | /v1/chat/completions |
| Qwen3-30B-A3B-Instruct-2507 | 2 | /v1/chat/completions |
| Qwen3-32B | 2 | /v1/chat/completions |
| Qwen3-235B-A22B-Thinking-2507 | 16 | /v1/chat/completions |
| Qwen3-235B-A22B-Instruct-2507 | 16 | /v1/chat/completions |
| DeepSeek-R1-Distill-Llama-70B | 4 | /v1/chat/completions |

## Vision-Language (VL)

| Model | Min Cards | Multimodal |
|-------|-----------|------------|
| Qwen3-VL-30B-A3B-Instruct | 2 | Yes |
| Qwen3-VL-32B-Instruct | 2 | Yes |
| Qwen3-VL-235B-A22B-Instruct | 16 | Yes |
| Qwen3-VL-235B-A22B-Instruct-W8A8 | 8 | Yes |

## Embedding

| Model | Min Cards | Multi-card |
|-------|-----------|------------|
| Qwen3-Embedding-8B | 1 | No |
| bge-large-zh-v1.5 | 1 | No |
| bge-m3 | 1 | No |

## Rerank

| Model | Min Cards | Multi-card |
|-------|-----------|------------|
| Qwen3-Reranker-8B | 1 | No |
| bge-reranker-v2-m3 | 1 | No |

## OpenSource

| Model | Min Cards | Capability |
|-------|-----------|------------|
| Qwen3.6-35B-A3B | 2 | Text + Image (MoE) |
| Qwen3.6-27B | 2 | Text + Image (MoE) |
| Qwen3-Next-80B-A3B-Instruct | 4 | LLM |
| DeepSeek-V4-Flash-w8a8-mtp | 8 | LLM |

| DeepSeek-V4-Flash-w8a8-mtp | 8 | LLM |
## Card Count Rules

- Supported values: 1, 2, 4, 8, 16
- Embedding/Rerank: Single card only
- Dual-machine: 16 cards (8+8)
