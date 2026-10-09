# Development Tool Integration - MaaS Model Invocation

MaaS supports integration with various development tools. This document provides integration guidance for each tool.

## 1. Supported Development Tools

| Tool | Type | Description |
|------|------|------|
| **OpenClaw** | AI Assistant Platform | Open-source personal AI assistant platform, supports deep thinking mode |
| **OpenCode** | AI Programming Tool | AI programming tool, supports code development and debugging |
| **Claude Code** | AI Programming Tool | Anthropic's AI programming tool, supports MaaS API configuration |
| **Dify** | AI Application Platform | Open-source Agent platform, build AI chatbots and customer service |
| **Cherry Studio** | Multi-model Desktop Client | Open-source desktop client, supports Windows/macOS/Linux |
| **Cursor** | AI Code Editor | AI-driven code editor, intelligent code completion |
| **Cline** | VS Code Plugin | VS Code plugin, AI-assisted programming |
| **RAGFlow** | RAG Engine | Open-source RAG engine, knowledge base Q&A |
| **Deep Research** | Deep Research Tool | AI deep research tool, generates professional research reports |

> All integrations only support the **西南-贵阳一** region.

## 2. OpenClaw

### Installation

- Windows: `iwr -useb https://openclaw.ai/install.ps1 | iex` or `npm install -g openclaw@latest` (requires Node.js 22+)
- macOS/Linux: `curl -fsSL https://openclaw.ai/install.sh | bash` or `npm install -g openclaw@latest`

### Configure MaaS API

Set the MaaS API Key and base URL (`https://api.modelarts-maas.com/openai/v1`) in the OpenClaw configuration.

- Web UI method: Left menu → Settings → RAW, modify the models, agents, and gateway nodes
- Terminal method: Edit `~/.openclaw/openclaw.json`

### Deep Thinking Mode

- Inline message command: `/think:<level>` or `/t <level>` (level: off, minimal, low, medium, high, xhigh)
- Session level: Send `/think:high` separately
- Global setting: `openclaw config set agents.defaults.thinkingDefault high`

### Common Issues

- **"Gateway service disabled"**: Start manually with `openclaw gateway`

## 3. OpenCode

### Installation

1. Install Node.js 18+
2. `npm install -g opencode-ai`
3. Verify: `opencode -v`

### Configure MaaS API

Edit `~/.config/opencode/opencode.json` (Windows: `C:\Users\<username>\.config\opencode\opencode.json`), configure the API Key and model information.

### Usage

1. Run `opencode`
2. Enter `/models` to select the configured model
3. Start the conversation

### Deep Thinking Mode

Edit the configuration file, add `options: {"thinking": {"type": "enabled"}}` in the models configuration, and restart for it to take effect.

## 4. Claude Code

### Installation

1. Install Node.js 18+
2. Windows users install Git for Windows
3. `npm install -g @anthropic-ai/claude-code`
4. Verify: `claude --version`

### Configure MaaS API

Edit `~/.claude/settings.json` (Windows: `C:\Users\<username>\.claude\settings.json`), set the API Key and model name.

### Usage

1. Navigate to the project directory, run `claude`
2. Enter `/status` to confirm model status
3. Start the conversation

## 5. Dify

### Deploy Dify Platform

Deploy the Dify platform on a Flexus cloud server X instance in the **西南-贵阳一** region. See [Quick Setup for Dify](https://support.huaweicloud.com/bestpractice-flexusx/bestpractice_0001.html).

### Obtain MaaS Integration Information

1. MaaS Console → Model Inference → Online Inference → Preset Services → Enable Service
2. Click "Invocation Instructions" → "Create API Key" → Copy and save
3. View the API address and model name

### Configure Dify

1. Dify Platform → Settings → Model Providers → Find "OpenAI-API-compatible" → Add Model
2. Configure parameters:
   - API Key: MaaS API Key
   - API Base URL: MaaS OpenAI-compatible interface address
   - Model Name: e.g., `deepseek-v3.2`

### Build a Customer Service Bot

1. Create a knowledge base (optional)
2. Create an Agent application, set the Prompt and context
3. Publish and embed into a webpage

## 6. Cherry Studio

### Installation

Download and install from the [official website](https://cherry-studio.com/) or open-source repository.

### Configure MaaS

1. Add provider: Settings → Model Services → Add, configure provider name and type
2. Configure API Key and API address
3. Add model: Configure model ID, name, and group

### Usage

Select the configured model and start the conversation.

## 7. Cursor

> Cursor membership is required.

### Installation

Download and install from the [Cursor official website](https://cursor.sh/).

### Configure MaaS API

1. Cursor Settings → Models → Add model
2. Enter the model name (e.g., `deepseek-v3.2`)
3. Check only the MaaS model (uncheck other models, otherwise verification may fail)
4. Enter the API Key in the "OpenAI Key" area
5. Click "Override Openai Base URL" and enter the MaaS interface address (**remove the trailing `/chat/completions`**)
6. Click "Verify" to test connectivity

### Usage

Select the configured model in the code editor page for conversation, code generation, etc.

## 8. Cline

### Installation

Search for the "Cline" plugin in VS Code and install it.

### Configure MaaS API

1. Open the Cline plugin → Settings
2. Select the "OpenAI Compatible" provider
3. Enter the API Key and Base URL
4. Click "Done"

### Usage

Select the configured MaaS service in VS Code for conversation and AI-assisted code generation.

> Supported models: Text generation models with context length ≥ 32K.

## 9. RAGFlow

### Installation

Download and install from the [official website](https://ragflow.io/) or GitHub.

### Configure MaaS

1. RAGFlow → User Avatar → Model Providers → "OpenAI-API-Compatible" → Add Model
2. Configure LLM parameters:
   - API Key: MaaS API Key
   - Base URL: MaaS OpenAI-compatible interface address
   - Model Name: e.g., `deepseek-v3.2`
3. System Model Settings → Set the chat model to the MaaS model

### Usage

1. Create a knowledge base, upload documents
2. Create an assistant, select the knowledge base
3. Perform document Q&A

## 10. Deep Research

### Installation

Download and install from the official website or GitHub.

### Configure MaaS API

1. Deep Research → Settings
2. Configure the MaaS API Key and model
3. Configure the Tavily AI API Key (used for web search, has a free monthly quota)

### Usage

1. Fill in the research topic, set the number of questions, research depth and breadth
2. Click "Start Research"
3. The model generates a research report
