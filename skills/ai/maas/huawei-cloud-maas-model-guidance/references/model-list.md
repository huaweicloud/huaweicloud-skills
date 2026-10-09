# MaaS Model List

The complete list of models supported by MaaS, including detailed information such as model parameters, capabilities, context length, and supported features.

## 1. Recommended Models (Deep Thinking)

| Model | Description |
|------|------|
| **DeepSeek-V4-Pro** | Flagship version of the DeepSeek-V4 series, MoE architecture, trillion-level parameters, 1M ultra-long context. Agent capabilities, world knowledge, and reasoning performance lead among open-source models. Supports 1M sequence length, max input 1M, max output 128K, max chain-of-thought 96K. Supports Function Call, prefix continuation. |
| **DeepSeek-V4-Flash** | Lightweight and efficient version of the DeepSeek-V4 series, retaining 1M ultra-long context capability, faster and more economical. Supports 1M sequence length, max input 1M, max output 128K, max chain-of-thought 96K. Supports Function Call, prefix continuation. |
| **Kimi-K2.6** | Kimi's latest and most intelligent model, with comprehensive improvements in general Agent, code, and other capabilities, supports thinking and non-thinking modes. Supports 256K sequence length, max input 256K, max output 96K, max chain-of-thought 96K. Supports Function Call, prefix continuation. |

## 2. DeepSeek Series (Text Generation)

| Model Name | Version | model Parameter | Supported Capabilities | Context Length | Max Input | Max Output | Max Chain-of-Thought | Invocation Method |
|----------|------|-----------|----------|-----------|---------|---------|-----------|---------|
| DeepSeek-V4-Pro | 20260424 | `deepseek-v4-pro` | Deep thinking (toggleable) Function Call Prefix continuation | 1M | 1M | 128K | 96K | V2, OpenAI, Anthropic |
| DeepSeek-V4-Flash | 20260424 | `deepseek-v4-flash` | Deep thinking (toggleable) Function Call Prefix continuation | 1M | 1M | 128K | 96K | V2, OpenAI, Anthropic |
| DeepSeek-V3.2 | 20251215 | `deepseek-v3.2` | Deep thinking (toggleable) Function Call Prefix continuation | 160K | 128K | 32K | 32K | V2, OpenAI, Anthropic |
| DeepSeek-V3.1 | 20251124 | `deepseek-v3.1-terminus` | Deep thinking (toggleable) Function Call Prefix continuation | 128K | 96K | 32K | 32K | V2, OpenAI, Anthropic |
| DeepSeek-V3 | 20250929 | `DeepSeek-V3` | Function Call | 128K | 128K | 64K | N/A | V2, OpenAI, Anthropic, V1 |
| DeepSeek-R1-0528 | 20250929 | `deepseek-r1-250528` | Deep thinking Function Call Prefix continuation | 128K | 96K | 32K | 32K | V2, OpenAI, Anthropic, V1 |

**Default Rate Limits**:
- V4-Pro/V4-Flash: TPM:30,000 RPM:3
- V3.2: TPM:500,000 RPM:700
- V3.1/V3/R1: TPM:500,000 RPM:1,500

## 3. Qwen3 Series (Text Generation)

| Model Name | Version | model Parameter | Supported Capabilities | Context Length | Max Input | Max Output | Max Chain-of-Thought | Invocation Method |
|----------|------|-----------|----------|-----------|---------|---------|-----------|---------|
| Qwen3-235B-A22B | 20260121 | `qwen3-235b-a22b` | Deep thinking (toggleable) Function Call Prefix continuation | 128K | 124K | 32K | 80K | V2, OpenAI, V1 |
| Qwen3-32B | 20251224 | `qwen3-32b` | Deep thinking (toggleable) | 128K | 128K | 128K | 128K | V2, OpenAI, V1 |
| Qwen3-30B-A3B | 20250710 | `qwen3-30b-a3b` | Deep thinking (toggleable) | 128K | 128K | 128K | 128K | V2, OpenAI, V1 |

**Default Rate Limits**: TPM:500,000 RPM:1,500

## 4. Kimi Series (Text Generation)

| Model Name | Version | model Parameter | Supported Capabilities | Context Length | Max Input | Max Output | Max Chain-of-Thought | Invocation Method |
|----------|------|-----------|----------|-----------|---------|---------|-----------|---------|
| Kimi-K2.6 | 20260420 | `kimi-k2.6` | Deep thinking (toggleable) Function Call Prefix continuation | 256K | 256K | 96K | 96K | V2, OpenAI, Anthropic |
| Kimi-K2 | 20250801 | `Kimi-K2` | Function Call Prefix continuation | 128K | 126K | 32K | N/A | V2, OpenAI, V1 |

**Default Rate Limits**: Kimi-K2.6: TPM:100,000 RPM:10; Kimi-K2: TPM:500,000 RPM:1,500

## 5. LongCat Series (Text Generation)

| Model Name | Version | model Parameter | Supported Capabilities | Context Length | Max Input | Max Output | Max Chain-of-Thought | Invocation Method |
|----------|------|-----------|----------|-----------|---------|---------|-----------|---------|
| LongCat-Flash-Chat | 20251029 | `longcat-flash-chat` | Function Call | 128K | 126K | 32K | N/A | V2, OpenAI, V1 |

**Default Rate Limits**: TPM:5,000,000 RPM:1,000

## 6. GLM Series (Text Generation)

| Model Name | Version | model Parameter | Supported Capabilities | Context Length | Max Input | Max Output | Max Chain-of-Thought | Invocation Method |
|----------|------|-----------|----------|-----------|---------|---------|-----------|---------|
| GLM-5 | 20260212 | `glm-5` | Deep thinking (toggleable) Function Call Prefix continuation | 198K | 192K | 64K | 64K | V2, OpenAI, Anthropic |
| GLM-5.1 | 20260407 | `glm-5.1` | Deep thinking (toggleable) Function Call Prefix continuation | 198K | 192K | 128K | 96K | V2, OpenAI, Anthropic |

**Default Rate Limits**: TPM:500,000 RPM:30

## 7. Image Understanding Models

| Model Name | Version | model Parameter | Supported Capabilities | Context Length | Max Input | Max Output | Invocation Method |
|----------|------|-----------|----------|-----------|---------|---------|---------|
| Qwen2.5-VL-72B | 20251011 | `qwen2.5-vl-72b` | Image understanding | 48K | Text:48K Image:10MB(Base64) | 16K | V1 |

**Supported image formats**: JPEG, PNG, GIF, WEBP

## 8. Image Generation Models

| Model Name | Version | model Parameter | Supported Capabilities | Input Image Format | Invocation Method |
|----------|------|-----------|----------|-------------|---------|
| Qwen_Image | 20250821 | `qwen-image` | Text-to-image | N/A | Image Generation API |
| Qwen-Image-Edit | 20251028 | `qwen-image-edit-2509` | Image editing (single/multi-image) | png,jpeg,jpg,webp,bmp,tiff | Image Generation API |

**Resolution range**:
- Qwen_Image: [512, 2048], must be divisible by 8
- Qwen-Image-Edit(20250913): [512, 2048]
- Qwen-Image-Edit(20251028): [512, 3072], aspect ratio within 1:12~12:1

## 9. Video Generation Models

| Model Name | Version | model Parameter | Supported Capabilities | Max Input | Output Format | Frame Rate | Duration | Invocation Method |
|----------|------|-----------|----------|---------|---------|------|------|---------|
| Wan2.2-I2V-A14B | 20250912 | `Wan2.2-I2V-A14B` | Image-to-video | Text:1000 chars Image:8MB(Base64) | MP4 | 16/24/30 | 3s/5s | Video Generation API |
| Wan2.2-T2V-A14B | 20250912 | `Wan2.2-T2V-A14B` | Text-to-video | Text:1000 chars | MP4 | 16/24/30 | 3s/5s | Video Generation API |

> Video generation uses an asynchronous interface; you must first create a task and then query the result. Task data is retained for 24 hours only.

## 10. Embedding Models

| Model Name | Version | model Parameter | Supported Capabilities | Max Input per Element | Max Vector Dimension | Invocation Method |
|----------|------|-----------|----------|----------------|------------|---------|
| BGE-M3 | 20250715 | `bge-m3` | Text embedding | 8192 Token | 1024 | Embedding API |

## 11. Reranker Models

| Model Name | Version | model Parameter | Supported Capabilities | Max Input per Element | Invocation Method |
|----------|------|-----------|----------|----------------|---------|
| BGE-Reranker-V2-M3 | 20250715 | `bge-reranker-v2-m3` | Reranking | 8192 Token | Rerank API |

## 12. Invocation Method Reference

| Abbreviation | Full Name | URL |
|------|------|-----|
| V2 | MaaS Standard API V2 | `https://api.modelarts-maas.com/v2/chat/completions` |
| V1 | MaaS Standard API V1 | `https://api.modelarts-maas.com/v1/chat/completions` |
| OpenAI | OpenAI Compatible Interface | `https://api.modelarts-maas.com/openai/v1/chat/completions` |
| Anthropic | Anthropic Compatible Interface | `https://api.modelarts-maas.com/anthropic/v1/messages` |

> **Note**: Not all models support all interface types. Please provide the corresponding URL based on the "Invocation Method" column for each model in the table above.
