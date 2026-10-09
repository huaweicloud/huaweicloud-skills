# Best Practices - MaaS Model Invocation

This document provides best practices for invoking MaaS models, based on the official MaaS documentation.

## 1. Model Selection Best Practices

### 1.1 General Selection Guidelines

- **Choose the latest model version**: If you are selecting a model for the first time, recommend choosing the latest version. Newer models have significantly improved capabilities in text classification, content creation, and other areas.
- **Choose models with corresponding capabilities**: Check the capability support column in the model list to ensure the model supports the features you need (deep thinking, function call, prefix continuation, etc.).
- **Consider cost-effectiveness**: For simple tasks, use lighter models (e.g., DeepSeek-V4-Flash instead of DeepSeek-V4-Pro). For complex reasoning, use flagship models.

### 1.2 Scenario-Based Recommendations

| Scenario | Recommended Model | Reason |
|----------|-------------------|--------|
| Complex reasoning/Math/STEM | DeepSeek-V4-Pro / DeepSeek-R1-0528 | Top-tier reasoning with deep thinking |
| Agent/Coding tasks | Kimi-K2.6 / DeepSeek-V4-Pro | Strong Agent and coding capabilities |
| General chat/Content creation | DeepSeek-V3.2 / GLM-5.1 | Balanced performance and cost |
| Long document processing | DeepSeek-V4-Pro (1M context) | Ultra-long context window |
| Cost-sensitive applications | DeepSeek-V4-Flash | Lightweight, efficient, economical |
| Image analysis/OCR | Qwen2.5-VL-72B | Strong visual understanding |
| Text-to-image | Qwen_Image | High-quality image generation |
| Image editing | Qwen-Image-Edit | Multi-image fusion and editing |
| Text embedding/RAG | BGE-M3 | 1024-dim vectors, good quality |
| Document reranking | BGE-Reranker-V2-M3 | Semantic reranking for search |

## 2. API Invocation Best Practices

### 2.1 API Format Selection

- **New projects**: Use MaaS Standard API V2 (`/v2/chat/completions`) for full feature support
- **OpenAI SDK migration**: Use OpenAI Compatible API (`/openai/v1/chat/completions`) for seamless migration
- **Anthropic SDK migration**: Use Anthropic Compatible API (`/anthropic/v1/messages`) for Claude SDK users
- **Legacy systems**: MaaS Standard API V1 (`/v1/chat/completions`) is available but no longer evolving

### 2.2 Multi-turn Conversation Best Practices

MaaS Chat API is **stateless** - the server does not store conversation context. Best practices for multi-turn conversations:

1. **Maintain message history on the client side**: Append each response to the messages array
2. **Include all history in each request**: Send the complete message history with every API call
3. **Use correct role values**: `system` for system prompts, `user` for user messages, `assistant` for model responses
4. **For deep thinking models**: Only keep `role` and `content` fields in history; do not include `reasoning_content` as input

Example of proper message history management:
```python
# First turn
messages = [{"role": "user", "content": "Which is larger, 9.11 or 9.8?"}]
response = client.chat.completions.create(model="deepseek-v3.2", messages=messages)
messages.append(response.choices[0].message)  # Add model response to history

# Second turn
messages.append({"role": "user", "content": "What is their sum"})  # Add new user question
response = client.chat.completions.create(model="deepseek-v3.2", messages=messages)
messages.append(response.choices[0].message)
```

### 2.3 Streaming Output Best Practices

- Use streaming (`stream=True`) for interactive applications to improve user experience
- Streaming returns content incrementally, reducing perceived latency
- For batch processing or non-interactive scenarios, non-streaming may be simpler

### 2.4 Deep Thinking Best Practices

- **Enable for complex tasks**: Math problems, logical reasoning, strategy analysis, multi-step planning
- **Disable for simple tasks**: Simple Q&A, content generation without reasoning, to save tokens and reduce latency
- **Models with toggle support**: DeepSeek-V4-Pro, DeepSeek-V4-Flash, DeepSeek-V3.2, DeepSeek-V3.1, Kimi-K2.6, GLM-5, GLM-5.1, Qwen3 series
- **Models without toggle**: DeepSeek-R1-0528 always uses deep thinking
- **Constraints for DeepSeek-V3.1**: Function Call and deep thinking are not compatible; do not use simultaneously. Deep thinking does not support prefix continuation.

### 2.5 Prompt Engineering Best Practices

- **Clear task definition**: Tell the model exactly what to do (translate, summarize, create, reason, etc.)
- **Provide context**: Add background information for more relevant responses
- **Constrain output format**: Specify the desired structure (list, JSON, code, etc.)
- **Control style**: Adjust professionalism, brevity, or creativity of responses
- **System message placement**: If using system message, place it first in the messages array

### 2.6 Token Management Best Practices

- **Set max_tokens**: Control costs by setting `max_tokens` to limit output length
- **Monitor token usage**: Track input/output tokens in API responses
- **Image token calculation**: Image tokens = min(width × height ÷ 784, per-image token limit)
- **Use appropriate context length**: Don't send unnecessarily long contexts

## 3. Function Call Best Practices

### 3.1 Task Definition

- Keep task definitions simple and direct
- Avoid including task-irrelevant information that may interfere with model reasoning
- Use code for deterministic tasks instead of calling the model

### 3.2 Tool Definition

- Provide clear and specific function descriptions
- Define parameter types and constraints precisely
- Use `required` field to specify mandatory parameters
- Set `tool_choice` to `"auto"` for automatic tool selection, or specify a function name for forced selection

### 3.3 Error Handling

- **JSON format tolerance**: Use `json-repair` library for slightly malformed JSON
- **Retry mechanism**: Implement retry for occasional failures due to model hallucination
- **max_tokens caution**: Setting `max_tokens` too small may truncate `tool_calls` output, making it unparseable

### 3.4 Compatibility Notes

- `tool_choice` supports `auto` and `named` modes only (not `required`)
- DeepSeek-V3.1: Function Call and deep thinking are not compatible
- System Prompt output format settings may conflict with tool_calls parsing

## 4. Image Understanding Best Practices

### 4.1 Image Input

- **Base64 encoding**: Convert local images to Base64, format as `data:[MIME_Type];base64,{base64_image}`
- **MIME type matching**: Ensure MIME type matches actual image format (e.g., `image/png` for PNG)
- **Size limit**: Base64-encoded image must be < 10MB
- **Re-send for each request**: If you need the model to understand the same image multiple times, send it with each request

### 4.2 Multi-image Input

- API supports multiple images in a single request
- Convert each image to Base64 and include in the content array
- **Text placement**: When mixing images and text, place text after images for best results

### 4.3 Image Format Support

| Format | MIME Type |
|--------|-----------|
| JPEG | image/jpeg |
| PNG | image/png |
| GIF | image/gif |
| WEBP | image/webp |

## 5. Image Generation Best Practices

### 5.1 Resolution Settings

- **Qwen-Image model**: Width and height range [512, 2048], must be divisible by 8
- **Qwen-Image-Edit (20250913)**: Width and height range [512, 2048]; if size not specified, uses input image size
- **Qwen-Image-Edit (20251028)**: Width and height range [512, 3072]; aspect ratio within 1:12 to 12:1

Recommended resolutions:
- 1:1 → 1024×1024, 2048×2048
- 16:9 → 2560×1440
- 9:16 → 1440×2560
- 4:3 → 2304×1728
- 3:4 → 1728×2304

### 5.2 Prompt Guidelines

- **Prompt length**: Maximum 800 characters (2000 tokens)
- **Language**: Supports both Chinese and English
- **Be specific**: More detailed prompts yield better results

## 6. Video Generation Best Practices

- **Asynchronous API**: Video generation is async - create task first, then query result
- **Task data retention**: Task data (status, video URL) is retained for 24 hours only
- **Patience**: Video generation takes time; wait patiently when querying results
- **Parameters**: Set `size`, `fps`, `duration`, and `seed` as needed

## 7. API Key Management Best Practices

- **Save immediately**: Copy and save API Key upon creation - it cannot be retrieved later
- **Use separate keys**: Create different API Keys for different applications for better tracking and security
- **Rotate regularly**: Delete old keys and create new ones periodically
- **Limit permissions**: Set appropriate permissions when creating API Keys
- **Region awareness**: API Keys are region-specific; create in the region where you'll use them
- **Wait for activation**: API Keys take a few minutes to become effective after creation

## 8. Rate Limiting Best Practices

- **Send requests evenly**: Avoid burst requests in short time periods
- **Respect limits**: Default limits vary by model (TPM and RPM)
- **Implement retry**: Use exponential backoff when receiving rate limit errors (ModelArts.81101)
- **Consider custom endpoints**: Create custom access points with higher rate limits if needed

## 9. Security Best Practices

- **Never expose API Key in code**: Use environment variables or secure configuration
- **Use HTTPS**: All MaaS APIs use HTTPS
- **Data privacy**: MaaS does not retain user data (images, videos, text) for model training
- **Content moderation**: Input and output content has content review enabled by default

## 10. Cost Optimization Best Practices

- **Choose appropriate models**: Use lighter models for simple tasks
- **Control max_tokens**: Set appropriate `max_tokens` to avoid unnecessary token consumption
- **Use streaming wisely**: Streaming doesn't reduce total tokens but improves perceived performance
- **Monitor usage**: Check token consumption through MaaS console or API response
- **Purchase resource packages**: For high-volume usage, consider resource packages for cost savings
- **For specific pricing, please refer to the MaaS pricing details**: https://www.huaweicloud.com/pricing/calculator.html#/maas
