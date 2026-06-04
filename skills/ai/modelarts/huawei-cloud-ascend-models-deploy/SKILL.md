---
name: huawei-cloud-ascend-models-deploy
description: |
  Huawei Cloud Ascend model deployment and testing skill for large language models on Ascend DevServer (910B series). Supports single-machine and dual-machine deployment for LLM, VL (vision-language), Embedding, and Rerank models. Provides model inference testing, deployment log viewing, and status monitoring with automated model matching and deployment script generation.
  Use this skill when the user wants to: (1) deploy a model on Ascend DevServer, (2) test model inference, (3) view deployment logs or status, (4) list supported models, (5) check deployment prerequisites.
  Trigger: deploy, test, model list, deployment log, Ascend, DevServer, 910B, ModelArts, LLM, VL, Embedding, Rerank, multimodal, inference, model catalog, 昇腾, 部署模型, 测试模型, 模型列表, 部署日志, 模型部署, 推理测试
tags: [Ascend, LLM, deploy, inference]
---

# Huawei Cloud Ascend Models Deploy

Deploy and test large language models on Huawei Cloud Ascend DevServer (910B series). Supports single-machine and dual-machine deployment, model inference testing, and deployment monitoring.

## Overview

This skill deploys and tests large language models on Huawei Cloud Ascend DevServer (910B series). Supports single-machine and dual-machine deployment for LLM, VL, Embedding, and Rerank models.

**Related Skills** (Agent orchestrated, no direct call, Rule 3):
- `huawei-cloud-ascend-remote-connect` - SSH connection to DevServer (prerequisite for deployment)
- `huawei-cloud-ascend-command` - NPU status check and monitoring (prerequisite and post-deploy monitoring)

**Capabilities**:
- Model deployment (single-node, dual-node)
- Inference testing (LLM chat, VL multimodal, Embedding, Rerank)
- Deployment log and status monitoring
- Model catalog and script auto-matching

**Deployment Workflow** (Agent orchestrated):
1. Agent calls `huawei-cloud-ascend-remote-connect` to establish SSH connection
2. Agent calls `huawei-cloud-ascend-command` to check NPU health and availability
3. Agent calls this skill (`huawei-cloud-ascend-models-deploy`) to deploy model
4. Agent calls `huawei-cloud-ascend-command` to monitor NPU status during deployment

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent Orchestration                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  1. SSH connect (remote-connect)                             │    │
│  │  2. NPU health check (ascend-command)                        │    │
│  │  3. Deploy model (this skill)                                 │    │
│  │  4. Monitor NPU (ascend-command)                             │    │
│  └────────────────────────────┬────────────────────────────────┘    │
│                               │ Explicit param passing (Rule 1)    │
│                               ▼                                     │
├─────────────────────────────────────────────────────────────────────┤
│              Huawei Cloud Ascend Models Deploy                      │
│                      (Stateless, Rule 2)                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐    ┌──────────────────────────────────┐      │
│  │  Natural Language│    │          Deploy Helper           │      │
│  │     Commands     │───▶│  - Model Matching & Catalog      │      │
│  └──────────────────┘    │  - Script Auto-Match             │      │
│                          │  - Command Generation            │      │
│                          └──────────────────────────────────┘      │
│                                           │                         │
│          ┌─────────────────────────────────┼──────────────┐        │
│          ▼                                 ▼              ▼        │
│  ┌───────────────┐              ┌─────────────────┐ ┌────────┐    │
│  │ Model         │              │ Inference       │ │ Log    │    │
│  │ Deployment    │              │ Testing         │ │ Status │    │
│  │               │              │                 │ │        │    │
│  │ • Single-node │              │ • LLM Chat      │ │ • View │    │
│  │ • Dual-node   │              │ • VL Multimodal │ │ • Check│    │
│  │ • 910B Series │              │ • Embedding     │ │        │    │
│  └───────────────┘              │ • Rerank        │ └────────┘    │
│                                 └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Orchestration Flow

```
User request: "Deploy Qwen2.5-72B on DevServer 116.204.23.145"
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent Step 1: SSH Connection                                 │
│   → Call huawei-cloud-ascend-remote-connect                  │
│   → Pass: host, user, password (explicit, Rule 1)            │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent Step 2: NPU Health Check                               │
│   → Call huawei-cloud-ascend-command                         │
│   → Check: NPU list, health, HBM availability                │
│   → Fail if NPU not healthy or insufficient HBM              │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent Step 3: Deploy Model (this skill)                      │
│   → Match model from catalog                                 │
│   → Generate deploy script                                   │
│   → Execute deployment                                        │
│   → Stateless execution (Rule 2)                             │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent Step 4: Monitor NPU                                    │
│   → Call huawei-cloud-ascend-command                         │
│   → Monitor: HBM usage, temperature, processes               │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
      Deployment Complete
```

### Related Skills Table

| Skill | Purpose | Orchestration Stage |
|-------|---------|---------------------|
| `huawei-cloud-ascend-remote-connect` | SSH connection | Pre-deploy: Establish connection to DevServer |
| `huawei-cloud-ascend-command` | NPU management | Pre-deploy: Health check; Post-deploy: Monitoring |

**Note**: No direct calls between Skills. All orchestration by Agent based on user intent (Rule 3).


## Prerequisites

> **Prerequisite check: Ascend 910B series required**
> - Supported: 910B1, 910B2, 910B3, 910B4
> - Unsupported: 910A, 310, 310P, etc.
> - Check with: `npu-smi info`

---

## Mandatory Rules (AI Must Follow)

1. **Never guess commands from memory** — Must read "Deploy Script Auto-Match" section
2. **Must call deploy_helper.py first** — Confirm model category and script URL
3. **Different models use different scripts**:
   - LLM / Embedding / Rerank → `deploy-large-models.sh`
   - VL → `deploy-qwen3-vl-model.sh`
   - OpenSource → `deploy-ai-models.sh`
4. **Must validate before deployment** — Port, NPU, model, card count
5. **Show command and wait for confirmation** — Sensitive operation, never execute directly

---

## Natural Language Understanding Rules

Extract key information from user natural language and assemble commands accurately.

### Operation Type Detection
| Keywords | Operation |
|----------|-----------|
| deploy / start / launch | Single-machine deployment |
| dual-machine / two-node / dual-node | Dual-machine deployment |
| test / inference / call | Test (execute) |
| write command / generate command | Write test command (generate only, no execute) |
| deployment log / view log | View deployment log |
| deployment status / is ready | View deployment status |
| model list / supported models | Show model catalog |
| parameter help / API parameters | Show parameter manual |

### Information Extraction Rules

**Model Name (fuzzy match, case-insensitive, supports card count filter):**
- "qwen3-14b" → Qwen3-14B
- "qwen3-235b" → Multiple matches, prefer Instruct version (Qwen3-235B-A22B-Instruct-2507), or ask user
- "vl-32b" → Qwen3-VL-32B-Instruct
- "bge-m3" → bge-m3
- "qwen3-vl" + 2 cards → Match VL models with ≤2 cards, list for user to choose
- "qwen3" + 2 cards → Match all Qwen3 models with ≤2 cards, list for user to choose
- Multiple candidates → List all candidates (with card count and category), let user confirm
- No match → Show full model catalog for user to select

**Card Count:**
- "2 cards" / "use 2 cards" / "2 npus" → 2
- "16 cards" / "16 npus" → 16
- "dual-machine" → 16
- Not specified → Use minimum card count from model catalog

**Port:**
- "port 8022" / "port:8022" → 8022
- Not specified → Default 8080

**Missing Parameters (check each, prompt what is missing):**
- Missing model name → "Please specify model name" + show model list
- Missing card count → "Please specify card count, e.g.: 2 cards" + show minimum cards for this model
- Missing port → "Please specify port (default 8080), e.g.: port 8001"
- Dual-machine missing head IP → "Please specify head node IP, e.g.: head:192.168.1.1"
- Dual-machine missing worker IP → "Please specify worker node IP, e.g.: worker:192.168.1.2"

**Head/Worker IP (dual-machine deployment):**
- "head:1.1.1.1" / "head node 1.1.1.1" → Head node IP
- "worker:2.2.2.2" / "worker node 2.2.2.2" → Worker node IP

**Prompt:**
- "prompt:hello" / "ask:hello" → Prompt text
- Not specified → LLM default "hello", VL default "describe the image", Embedding default "I love shanghai", Rerank default "What is the capital of France?"

**Image URL (VL test):**
- "image:https://xxx.jpg" / direct URL → Image URL
- User sends image attachment → Auto-convert to base64 data URL
- Not specified and testing multimodal model → Prompt user for image URL

**Multimodal Capability Auto-Detection:**
- VL category → Supports multimodal
- OpenSource: Qwen3.6-35B-A3B, Qwen3.6-27B → Supports multimodal
- LLM category → Text only
- Embedding → Text only
- Rerank → Text only

**Image URL Conversion (local image → data URL):**
```bash
# Efficient base64 conversion
IMG_B64=$(base64 -w 0 ${local_image_path})
IMG_URL="data:image/jpeg;base64,${IMG_B64}"
```

**Advanced Parameters (optional):**
- "max_tokens:64" → max_tokens=64
- "temperature:0.7" → temperature=0.7
- "stream" → stream=true
- "system:You are assistant" → system_prompt
- "disable thinking" / "no thinking" → chat_template_kwargs: {"enable_thinking": false}
- (Default = thinking mode enabled)

**Thinking Mode:**
Qwen3/Qwen3.6 models default to thinking mode, outputting reasoning process before final response.
- Enable thinking: Higher quality, more token consumption
- Disable thinking: Direct output, less token consumption, suitable for simple queries
- Request-level control via `"chat_template_kwargs": {"enable_thinking": false/true}`

---

## Supported Machine Types

Only **Ascend 910B series** (910B1 / 910B2 / 910B3 / 910B4). Must check NPU model before deployment, reject non-910B series.

---

## Model Catalog

### Large Language Models (LLM) — Endpoint: /v1/chat/completions
| Model | Min Cards |
|-------|-----------|
| Qwen3-14B | 1 |
| Qwen3-30B-A3B-Instruct-2507 | 2 |
| Qwen3-32B | 2 |
| Qwen3-235B-A22B-Thinking-2507 | 16 |
| Qwen3-235B-A22B-Instruct-2507 | 16 |
| DeepSeek-R1-Distill-Llama-70B | 4 |

### Vision-Language (VL) — Endpoint: /v1/chat/completions
| Model | Min Cards |
|-------|-----------|
| Qwen3-VL-30B-A3B-Instruct | 2 |
| Qwen3-VL-32B-Instruct | 2 |
| Qwen3-VL-235B-A22B-Instruct | 16 |
| Qwen3-VL-235B-A22B-Instruct-W8A8 | 8 |

### Embedding — Endpoint: /v1/embeddings (V0 backend only, single card only)
| Model | Min Cards | Multi-card |
|-------|-----------|------------|
| Qwen3-Embedding-8B | 1 | No |
| bge-large-zh-v1.5 | 1 | No |
| bge-m3 | 1 | No |

### Rerank — Endpoint: /v1/rerank (single card only)
| Model | Min Cards | Multi-card |
|-------|-----------|------------|
| Qwen3-Reranker-8B | 1 | No |
| bge-reranker-v2-m3 | 1 | No |

### OpenSource (Multimodal)
| Model | Min Cards | Capability |
|-------|-----------|------------|
| Qwen3.6-35B-A3B | 2 | Text + Image (MoE) |
| Qwen3.6-27B | 2 | Text + Image (MoE) |
| Qwen3-Next-80B-A3B-Instruct | 4 | Large language model |
| DeepSeek-V4-Flash-w8a8-mtp | 8 | Large language model |

---

## Deploy Script Auto-Match (Must use, never guess script URL)

**Script Path:** `scripts/deploy_helper.py`

**Match Rules (hardcoded, 100% accurate):**

| Model Category | Deploy Script | Notes |
|----------------|---------------|-------|
| LLM | `deploy-large-models.sh` | Shared with Embedding/Rerank |
| Embedding | `deploy-large-models.sh` | Same as above |
| Rerank | `deploy-large-models.sh` | Same as above |
| VL | `deploy-qwen3-vl-model.sh` | Multimodal specific |
| OpenSource | `deploy-ai-models.sh` | OpenSource specific |

**Usage:**

```bash
# Match model (returns category, script URL, min cards, etc.)
python3 scripts/deploy_helper.py match <model_name>

# Generate deploy command directly
python3 scripts/deploy_helper.py command <model_name> <cards> <port>

# List all models (optional category filter)
python3 scripts/deploy_helper.py list [LLM|VL|Embedding|Rerank|OpenSource]
```

**AI must call `deploy_helper.py match` first to confirm category and script, then use returned `deploy_url` to assemble command. Never guess from memory!**

---

## Core Commands

Core commands for model deployment and testing. See [Operation Flow](#operation-flow) for detailed steps.

| Command | Description |
|---------|-------------|
| `deploy <model> <port>` | Deploy model on single machine |
| `deploy <model> <port> <cards>` | Deploy with specified card count |
| `dual-machine deploy <model> head:<IP> worker:<IP> port:<PORT>` | Deploy on dual-machine cluster |
| `test <model> <port>` | Test model inference |
| `deployment log` | View deployment log |
| `deployment status` | Check deployment status |
| `model list` | Show supported models |

## Operation Flow

### I. Deployment

#### 1. Pre-deployment Check (Must execute every time, cannot skip)

Check in order, stop if any fails:

1. **NPU Model Check** — Agent calls `huawei-cloud-ascend-command` to check chip model, reject non-910B series
2. **NPU Card Count Check** — Agent calls `huawei-cloud-ascend-command` to check available cards, confirm >= required cards
3. **User Card Count Check** — User-specified cards must be >= minimum and within supported range (1,2,4,8,16)
4. **Embedding/Rerank Single Card Check** — Embedding and Rerank only support single card, reject multi-card
5. **Port Occupancy Check** — Agent calls `huawei-cloud-ascend-remote-connect` to run `ss -tlnp | grep :port`, notify if occupied
6. **SSH Connectivity Check** — For dual-machine, verify both head and worker nodes are SSH accessible

#### 2. Single-machine Deployment

User says: "deploy model_name port XXXX" or "deploy model_name port XXXX N cards"

**Before deploying, must SSH execute `mkdir -p /home/modelarts-agent` to ensure directory exists.**

**LLM / Embedding / Rerank Command Template:**
```bash
nohup bash -c 'export model_name=${model} && export required_cards=${cards} && export port=${port} && wget -P /home/modelarts-agent/ https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata/deploy-large-models/single-machine/deploy-large-models.sh && chmod 755 /home/modelarts-agent/deploy-large-models.sh && sh /home/modelarts-agent/deploy-large-models.sh ${model} ${cards} ${port}' > /home/modelarts-agent/deploy_${model}.log 2>&1 &
```

**VL Multimodal Command Template:**
```bash
nohup bash -c 'export model_name=${model} && export required_cards=${cards} && export port=${port} && wget -P /home/modelarts-agent/ https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata/deploy-vl-model/single-machine/deploy-qwen3-vl-model.sh && chmod 755 /home/modelarts-agent/deploy-qwen3-vl-model.sh && sh /home/modelarts-agent/deploy-qwen3-vl-model.sh ${model} ${cards} ${port}' > /home/modelarts-agent/deploy_${model}.log 2>&1 &
```

**OpenSource Command Template:**
```bash
nohup bash -c 'export model_name=${model} && export required_cards=${cards} && export port=${port} && wget -P /home/modelarts-agent/ https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata/deploy-large-models/single-machine/open_source/deploy-ai-models.sh && chmod 755 /home/modelarts-agent/deploy-ai-models.sh && sh /home/modelarts-agent/deploy-ai-models.sh ${model} ${cards} ${port}' > /home/modelarts-agent/deploy_${model}.log 2>&1 &
```

#### 3. Dual-machine Deployment

User says: "dual-machine deploy model_name head:IP worker:IP port XXXX"

**Before dual-machine deploy, both head and worker nodes need `mkdir -p /home/modelarts-agent`.**

**Head Node Command Template:**
```bash
nohup bash -c 'export ray_head_ip=${head_ip} && export model_name=${model} && export port=${port} && wget -P /home/modelarts-agent/ https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata/deploy-large-models/dual-machine/qwen3-235b-a22b.sh && chmod 755 /home/modelarts-agent/qwen3-235b-a22b.sh && sh /home/modelarts-agent/qwen3-235b-a22b.sh head ${head_ip} ${model} ${port}' > /home/modelarts-agent/deploy_${model}_head.log 2>&1 &
```

**Worker Node Command Template:**
```bash
nohup bash -c 'export ray_head_ip=${head_ip} && export model_name=${model} && export port=${port} && wget -P /home/modelarts-agent/ https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata/deploy-large-models/dual-machine/qwen3-235b-a22b.sh && chmod 755 /home/modelarts-agent/qwen3-235b-a22b.sh && sh /home/modelarts-agent/qwen3-235b-a22b.sh worker ${head_ip} ${model} ${port}' > /home/modelarts-agent/deploy_${model}_worker.log 2>&1 &
```


**VL Dual-machine Deployment:**

For VL models (Qwen3-VL-235B-A22B-Instruct, etc.), use the following scripts:

**VL Head Node Command:**
```bash
nohup bash -c 'export ray_head_ip=${head_ip} && export model_name=${model} && export port=${port} && wget -P /home/modelarts-agent/ https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata/deploy-vl-model/dual-machine/qwen3-vl-235b-a22b.sh && chmod 755 /home/modelarts-agent/qwen3-vl-235b-a22b.sh && sh /home/modelarts-agent/qwen3-vl-235b-a22b.sh head ${head_ip} ${model} ${port}' > /home/modelarts-agent/deploy_${model}_head.log 2>&1 &
```


**VL Worker Node Command:**
```bash
nohup bash -c 'export ray_head_ip=${head_ip} && export model_name=${model} && export port=${port} && wget -P /home/modelarts-agent/ https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata/deploy-vl-model/dual-machine/qwen3-vl-235b-a22b.sh && chmod 755 /home/modelarts-agent/qwen3-vl-235b-a22b.sh && sh /home/modelarts-agent/qwen3-vl-235b-a22b.sh worker ${head_ip} ${model} ${port}' > /home/modelarts-agent/deploy_${model}_worker.log 2>&1 &
```


#### 4. Deployment Confirmation Flow

**Sensitive operation, must show full command and wait for user "confirm" before executing.**

After deploy command sent:
1. Notify user: Ready, starting deployment of ${model}, log at `/home/modelarts-agent/deploy_${model}.log`
2. **Check log every 2 minutes**, report progress (loading weights, Dynamo compiling, service starting, etc.)
3. When port is listening, notify deployment success
4. **Deployment failure handling (strict compliance):**
   - Deployment failed = Report failure reason, no automatic retry
   - Never auto-change image and retry
   - Never auto-modify parameters and retry
   - Never try other deployment methods
   - Only report error, let user decide next step
5. **Output API sample** for user:

```
Deployment successful! ${model} is ready

Service URL: http://${IP}:${PORT}/v1/chat/completions

Example request:
curl -X POST http://${IP}:${PORT}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"${model}","messages":[{"role":"user","content":"hello"}],"max_tokens":256}'

Multimodal request (if supported):
curl -X POST http://${IP}:${PORT}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"${model}","messages":[{"role":"user","content":[{"type":"image_url","image_url":{"url":"image_url"}},{"type":"text","text":"describe the image"}]}],"max_tokens":512}'
```

---

### II. Deployment Log

User says: "deployment log model_name"

Agent uses `huawei-cloud-ascend-remote-connect` to execute:
```bash
tail -50 /home/modelarts-agent/deploy_${model}.log
```

---

### III. Deployment Status

User says: "deployment status port XXXX"

Agent uses `huawei-cloud-ascend-remote-connect` to execute:
```bash
ss -tlnp | grep :
```

Port listening = Service ready for testing.

---

### IV. Test (Execute)

User says: "test model_name prompt:xxx" or "test model_name image:URL"

**Test flow (strict compliance):**
1. **Show full curl command** for user to review
2. Wait for user "confirm" or "send" before executing
3. **Structured result output:**

```
Test Result

| Field | Value |
|-------|-------|
| id | chatcmpl-xxx |
| model | Qwen3-VL-32B-Instruct |
| prompt_tokens | 93 |
| completion_tokens | 400 |
| total_tokens | 493 |
| finish_reason | stop |

Model Response:
[Extract full content, no truncation]

Raw Response:
[Full JSON, no truncation]
```

#### LLM Chat Completions
```bash
curl -s -X POST http://${IP}:${PORT}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"${model}","messages":[{"role":"user","content":"${prompt}"}],"max_tokens":1024,"temperature":0.7}'
```

#### Multimodal VL
```bash
curl -s -X POST http://${IP}:${PORT}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"${model}","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":[{"type":"image_url","image_url":{"url":"${image_url}"}},{"type":"text","text":"${prompt}"}]}],"max_tokens":512,"temperature":0.7}'
```

#### Embedding
```bash
curl -s -X POST http://${IP}:${PORT}/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"${model}","input":"${text}"}'
```

#### Rerank
```bash
curl -s -X POST http://${IP}:${PORT}/v1/rerank \
  -H 'Content-Type: application/json' \
  -d '{"model":"${model}","query":"${query}","documents":["${doc1}","${doc2}"]}'
```

---

### V. Write Test Command (Generate Only)

User says: "write test command model_name prompt:xxx"

Same logic as "test", but **only output command text, no execution**.

---

## API Parameter Manual

### LLM Parameters (/v1/chat/completions)

| Parameter | Required | Default | Description |
|-----------|:--------:|---------|-------------|
| model | Yes | — | Model name, same as deployment |
| messages | Yes | — | Message list, each with role and content |
| max_tokens | No | 16 | Max generation tokens |
| temperature | No | 1.0 | Sampling randomness, 0=greedy |
| top_p | No | 1.0 | Nucleus sampling threshold |
| top_k | No | -1 | Only consider top-K tokens |
| stream | No | false | Streaming output (SSE) |
| chat_template_kwargs | No | {} | Template params, e.g. {"enable_thinking": false} |

### VL Extra Parameters
| Parameter | Description |
|-----------|-------------|
| content[] | Array format: image_url object + text object |
| detail | Image precision: auto/high/low |

### Embedding Parameters (/v1/embeddings)
| Parameter | Required | Description |
|-----------|:--------:|-------------|
| model | Yes | Model name |
| input | Yes | String or string list |
| encoding_format | No | float/base64 |

### Rerank Parameters (/v1/rerank)
| Parameter | Required | Description |
|-----------|:--------:|-------------|
| model | Yes | Model name |
| query | Yes | Query text |
| documents | Yes | Document list to rerank |
| top_n | No | Return top N |

---

## Execution Mode

This skill operates in **stateless mode** (Rule 2). All context (host, credentials, model info) must be explicitly passed by Agent (Rule 1).

### Prerequisites (Agent orchestrated)

Before calling this skill, Agent MUST:

1. **Establish SSH connection** using `huawei-cloud-ascend-remote-connect`
   - Agent receives: host, port, user, password from user
   - Agent validates connection is successful

2. **Check NPU status** using `huawei-cloud-ascend-command`
   - Agent checks: NPU health, HBM availability
   - Agent validates: sufficient cards for model deployment

### Skill Execution

This skill receives explicit parameters from Agent:

```bash
# Model matching (local operation)
python3 scripts/deploy_helper.py match <model_name>

# Script URL generation (local operation)
python3 scripts/deploy_helper.py script <model_name>

# Deploy command generation (local operation)
python3 scripts/deploy_helper.py command <model> <cards> <port>
```

### Remote Deployment Execution

Agent executes deployment commands on remote server:

```bash
# Agent uses SSH to execute deployment on DevServer
ssh root@<host> "cd /path/to/model && bash deploy.sh"
```

### Post-Deployment (Agent orchestrated)

After deployment, Agent calls `huawei-cloud-ascend-command` to:
- Monitor NPU HBM usage
- Check deployment process status
- Verify model endpoint is responding

### Parameter Flow

```
User Input                    Agent                      This Skill
    │                          │                            │
    │ host, password           │                            │
    ├─────────────────────────▶│                            │
    │                          │ SSH connect                │
    │                          ├───────────────────────────▶│
    │                          │                            │ (remote-connect)
    │                          │◀───────────────────────────┤
    │                          │                            │
    │                          │ NPU check                  │
    │                          ├───────────────────────────▶│
    │                          │                            │ (ascend-command)
    │                          │◀───────────────────────────┤
    │                          │                            │
    │ model_name, cards        │                            │
    ├─────────────────────────▶│                            │
    │                          │ match model                │
    │                          ├───────────────────────────▶│
    │                          │                            │ deploy_helper.py
    │                          │◀───────────────────────────┤
    │                          │                            │
    │                          │ execute deploy             │
    │                          ├───────────────────────────▶│
    │                          │                            │ (via SSH)
    │                          │◀───────────────────────────┤
    │                          │                            │
    │                          │ monitor NPU                │
    │                          ├───────────────────────────▶│
    │                          │                            │ (ascend-command)
    │                          │◀───────────────────────────┤
    │                          │                            │
    ▼                          ▼                            ▼
```

**Note**: No direct skill-to-skill calls. All orchestration by Agent (Rule 3).

---

## References

| Document | Description |
|----------|-------------|
| [task-deploy-model.md](references/task-deploy-model.md) | Deployment task steps |
| [task-test-model.md](references/task-test-model.md) | Testing task steps |
| [model-catalog.md](references/model-catalog.md) | Complete model catalog |
| [api-parameters.md](references/api-parameters.md) | API parameter reference |
| [prerequisites.md](references/prerequisites.md) | Prerequisites checklist |
| [verification-method.md](references/verification-method.md) | Verification steps |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting guide |
| [scripts/deploy_helper.py](scripts/deploy_helper.py) | Model matching helper |
