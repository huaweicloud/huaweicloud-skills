---
name: huawei-cloud-msmodelslim-model-adapt
description: |-
  Create basic Transformers model adapters for msModelSlim. Implements required interfaces and completes a four-step verification workflow:
  generate test model -> full fallback quantization -> weight verification -> quantization description validation. Use this skill when the user wants to: (1) create msModelSlim adapters for decoder-only LLM, (2) adapt understanding VLM text backbones for quantization, (3) implement W8A8/W4A16 quantization workflow for new models. Trigger: user mentions "msModelSlim", "adapter", "model adapter","quantization", "W8A8","W4A16", "transformers", "LLM", "VLM", "adapter creation", "适配器","模型适配", "量化", "模型适配器", "LLM量化"
compatibility:
  - transformers >= 4.40.0
  - msmodelslim >= 1.0.0
tags: [msModelSlim, adapter, quantization, model]
allowed-tools:
  - python3
  - bash
---

# Huawei Cloud msModelSlim Model Adapter

## Overview

This skill guides how to create basic adapters for new models to run
W8A8/W4A16 quantization workflows in msModelSlim.

**Architecture**: Model Analysis -> Adapter Creation -> Registration ->
Verification (4 Steps)

**Related Skills**:

- `huawei-cloud-msmodelslim-model-analysis` - Model structure analysis
  before adapter implementation
- `huawei-cloud-ascend-profiler-db-explorer` - Optional: Performance
  analysis after deployment

## Scope

**Supported**:

- Decoder-only LLM
- Understanding VLM (text/LLM backbone only)

**Not supported**:

- Multimodal generation (Stable Diffusion/Flux/Wan)
- Encoder-only models
- Non-Transformers architectures

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│              msModelSlim Model Adapter Skill                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │  Model Analysis │───▶│    Adapter Creation          │  │
│  │  - config.json  │    │    - LLM Adapter Template     │  │
│  │  - modeling_*.py│    │    - VLM Adapter Template     │  │
│  └──────────────────┘    │    - Required Interfaces     │  │
│                          └──────────────────────────────┘  │
│                                    │                       │
│                                    ▼                       │
│                          ┌──────────────────┐             │
│                          │  Registration    │             │
│                          │  & Installation  │             │
│                          └──────────────────┘             │
│                                    │                       │
│                                    ▼                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                   Verification (4 Steps)              │ │
│  │  1. Generate Test Model → 2. Full Fallback Quant     │ │
│  │  3. Weight Verification → 4. Quant Description     │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Architecture Components

This skill involves the following cloud services and components:

- **msModelSlim**: Huawei Cloud's model quantization framework for
  efficient model compression
- **Transformers Library**: Hugging Face Transformers for model loading
  and processing
- **ModelScope**: Model download and management platform
- **Ascend NPU**: Target hardware for quantized model deployment

## Use Cases

**Typical Problem Scenarios:**

- Need to deploy LLM models with reduced memory footprint on Ascend NPU
- Want to optimize inference speed without significant accuracy loss
- Migrating models that don't have built-in msModelSlim support
- Need W8A8/W4A16 quantization for decoder-only LLM or VLM text backbones

**Typical User Phrases:**

- "How to quantize my custom LLM model for Ascend?"
- "Create msModelSlim adapter for Qwen model"
- "Implement W4A16 quantization workflow"
- "Adapt my VLM text backbone for quantization"
- "How to add quantization support for new models?"

## Core Workflow

### 1. Preparation

- **Download Model**: Recommended to use `modelscope download` for
  non-weight files.
  - Example: `modelscope download --model <org>/<model> --local_dir
    ./models/<name> --exclude '*.safetensors'`
- **Analyze Model**: Read `config.json` and `modeling_*.py` to confirm
  structure and implementation.
  - See: [Model Analysis Guide](references/model_analysis.md)

### 2. Create Adapter

- **Use Templates**:
  - LLM: `assets/model_adapter_template.py`
  - VLM: `assets/vlm_model_adapter_template.py`
- **Implement Interfaces**: Implement `handle_dataset`, `init_model`,
  `generate_model_visit`, `generate_model_forward`, `enable_kv_cache`.
- **Key Principles**:
  - `visit` and `forward` must be strictly consistent.
  - MoE models recommended to unpack to pure linear layers.
  - See: [Implementation Guide](references/implementation_guide.md)

### 3. Registration & Installation

- Register model and entry in `config/config.ini`, then execute
  `bash install.sh`.
- See: [Registration Guide](references/registration_guide.md)

### 4. Verify Adapter (Required)

- Must execute four-step verification: Generate test model -> Full
  fallback quantization -> Verify full fallback model matches float
  weights exactly and can load/save completely -> Verify actual
  quantization workflow works (including description file rule
  validation).
- See: [Verification Guide](references/verification_guide.md)

## Common Scripts

Scripts located in `scripts/` directory:

- `scripts/step1_generate_test_model.py`
- `scripts/step2_run_quantization.py`
- `scripts/step3_verify_weights.py`
- `scripts/step4_verify_quant_description.py`

## Prerequisites

### System Requirements

- Python 3.8+
- transformers >= 4.40.0
- msmodelslim >= 1.0.0

### Environment Check

> **Prerequisite check: Python3 + transformers + msmodelslim required**
>
> ```bash
> python3 --version  # Python3 >= 3.8
> python3 -c "import transformers; print('OK')"  # Transformers library
> python3 -c "import msmodelslim; print('OK')"  # msModelSlim library
> ```
>
> If not installed: `pip3 install --user transformers msmodelslim`

## Reference Documents

| Document | Description |
| ---------- | ------------- |
| [Model Analysis Guide](references/model_analysis.md) | Model structure analysis guide |
| [Implementation Guide](references/implementation_guide.md) | Adapter implementation instructions |
| [Registration Guide](references/registration_guide.md) | Registration and installation guide |
| [Verification Guide](references/verification_guide.md) | Four-step verification workflow |
| [Interface Checklist](references/interface_checklist.md) | Required interface implementation checklist |
| [Core Workflow](references/core_workflow.md) | Core workflow documentation |
| [Acceptance Criteria](references/acceptance-criteria.md) | Functional acceptance criteria |
| [Troubleshooting](references/troubleshooting.md) | Common issues and solutions |

## Requirements

- transformers >= 4.40.0 installed
- msmodelslim >= 1.0.0 installed
- Transformers model to be adapted
- Understanding of target quantization scheme (W8A8/W4A16)

## Core Commands

```bash
# Create model adapter
python3 scripts/create_adapter.py \
  --model Qwen2-7B \
  --quantization W8A8

# Run four-step verification
python3 scripts/verify_adapter.py --adapter ./adapter.py
```

## Parameter Confirmation

| Parameter | Description | Required |
| ---------- | ------------- | ---------- |
| model | Model name or path | Yes |
| quantization | Quantization scheme (W8A8/W4A16) | Yes |
| output | Adapter output path | No |
