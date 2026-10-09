# Acceptance Criteria - MaaS Model Invocation

This document defines the acceptance criteria for the MaaS model invocation guidance skill.

## 1. Model Selection Criteria

### 1.1 Model List Presentation

- [ ] When customer doesn't specify a model, all available models are listed with key information (model name, model parameter, capabilities, context length)
- [ ] Models are categorized by type (deep thinking, text generation, image understanding, image generation, video generation, embedding, reranking)
- [ ] Each model listing includes: model name, version, model parameter value, supported capabilities, context length, max input/output lengths

### 1.2 Model Recommendation

- [ ] When customer describes a use case/scenario, appropriate models are recommended with justification
- [ ] Recommendation considers: task type, context length requirements, cost efficiency, capability requirements (deep thinking, function call, etc.)
- [ ] At minimum, the following scenarios are covered: code generation, complex reasoning, general chat, long context, image understanding, image generation, video generation, embedding, reranking

## 2. API Invocation Guidance Criteria

### 2.1 API URL and Format

- [ ] Correct API URL is provided based on model type and preferred API format
- [ ] For large language models, three API formats are available when customer hasn't specified preference:
  - MaaS Standard API V2: `https://api.modelarts-maas.com/v2/chat/completions`
  - OpenAI Compatible API: `https://api.modelarts-maas.com/openai/v1/chat/completions`
  - Anthropic Compatible API: `https://api.modelarts-maas.com/anthropic/v1/messages`
- [ ] Differences between API formats are clearly explained
- [ ] MaaS Standard API V1 is mentioned as legacy (no longer evolving)

### 2.2 Model Parameter

- [ ] Correct `model` parameter value is provided for each model (e.g., `deepseek-v3.2`, not `DeepSeek-V3.2`)
- [ ] Model parameter values match the official MaaS documentation exactly

### 2.3 API Key Guidance

- [ ] API Key creation steps are provided
- [ ] Critical warning is displayed: "The API Key will only be displayed once after creation. Please copy and save it promptly. If the API Key is lost, create a new API Key."
- [ ] API Key creation URL/path is provided: MaaS Console → Management & Statistics → API Key Management
- [ ] API Key limitations are mentioned: max 30 per account, region-specific, takes minutes to take effect

## 3. Code Example Criteria

### 3.1 Code Completeness

- [ ] Python (requests library) examples are provided for all model types
- [ ] Curl examples are provided for all model types
- [ ] OpenAI Python SDK examples are provided for text generation, deep thinking, and streaming
- [ ] Java examples are provided for text generation (JDK 15+)

### 3.2 Code Correctness

- [ ] All examples use correct API URLs
- [ ] All examples include proper authentication header (`Authorization: Bearer <MAAS_API_KEY>`)
- [ ] All examples include placeholder comment to replace API Key: `Replace MAAS_API_KEY with your obtained API Key`
- [ ] All examples use correct model parameter values
- [ ] Request body structure matches MaaS API specification

### 3.3 Feature-Specific Examples

- [ ] Deep thinking examples include `"thinking": {"type": "enabled"}` parameter
- [ ] Streaming examples include `stream=True` parameter
- [ ] Multi-turn conversation examples include message history management
- [ ] Image understanding examples include Base64 image encoding
- [ ] Video generation examples include both create task and query task steps

## 4. Prerequisites Guidance Criteria

- [ ] Preset service activation steps are provided (Model Inference > Online Inference > Preset Services)
- [ ] API Key creation guidance is provided
- [ ] ModelArts delegation authorization requirement is mentioned
- [ ] Region constraint (西南-贵阳一) is clearly stated
- [ ] No CLI installation is required (guidance only, no command execution)

## 5. Development Tool Integration Criteria

- [ ] Available tools are listed: OpenClaw, OpenCode, Claude Code, Dify, Cherry Studio, Cursor, Cline, RAGFlow, Deep Research
- [ ] Customer is asked: "Would you like to see the integration guidance for a specific development tool?"
- [ ] Each tool integration includes: installation steps, configuration steps, usage guidance
- [ ] Tool-specific features are mentioned (e.g., OpenClaw deep thinking mode, Cursor API configuration)

## 6. Pricing Guidance Criteria

- [ ] Pricing information uses the standard message: "For specific pricing, please refer to the MaaS pricing details: https://www.huaweicloud.com/pricing/calculator.html#/maas"
- [ ] Direct pricing/fee amounts are NOT provided
- [ ] Billing methods are explained (pay per Token, pay by package/resource pack)

## 7. Workflow Criteria

- [ ] Step 1: Understand customer needs (model type, specific model, or scenario)
- [ ] Step 2: Provide model information (name, parameter, API URL, API Key guidance)
- [ ] Step 3: Provide code examples in customer's preferred language
- [ ] Step 4: Ask about additional needs (deep thinking, development tools, etc.)
- [ ] Step 5: Remind about prerequisites if not completed
