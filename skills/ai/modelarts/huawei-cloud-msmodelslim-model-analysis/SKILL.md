---
name: huawei-cloud-msmodelslim-model-analysis
description: |
  Analyze candidate models before adapter implementation. Determine model
  implementation source (transformers or model-local), structural features,
  layer-by-layer loading requirements, and MoE fused weight risks. Use this
  skill when the user wants to: (1) assess model adaptation feasibility before
  creating msModelSlim adapters, (2) analyze model structure and type
  classification, (3) evaluate MoE compatibility for quantization. Trigger:
  user mentions "model analysis", "msModelSlim", "adapter", "transformers",
  "MoE", "layer-by-layer", "model assessment", "feasibility", "模型分析",
  "适配可行性", "模型评估", "MoE分析"
compatibility:
  - transformers >= 4.40.0
tags: [msModelSlim, analysis, model, MoE]
allowed-tools:
  - python3
---

# Huawei Cloud msModelSlim Model Analysis

## Overview

This skill analyzes candidate models before adapter implementation for msModelSlim.

**Architecture**: Implementation Source Detection → Model Type Classification →
Structural Feature Analysis → Risk Assessment

**Related Skills**:

- `huawei-cloud-msmodelslim-model-adapt` - Adapter creation based on analysis
  results

## Architecture Components

This skill involves the following cloud services and components:

- **msModelSlim**: Huawei Cloud's model quantization framework
- **Transformers Library**: Hugging Face Transformers for model loading
- **ModelScope**: Model download and management platform
- **config.json**: Model configuration file for analysis

**Architecture Diagram:**

```text
┌─────────────────────────────────────────────────────────────┐
│           msModelSlim Model Analysis Skill                  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Model       │───▶│  Source      │───▶│  Structure   │ │
│  │  Input       │    │  Detection   │    │  Analysis    │ │
│  │  (config)    │    │              │    │              │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Type        │    │  MoE         │    │  Risk        │ │
│  │  Classification│   │  Assessment │    │  Assessment │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Use Cases

**Typical Problem Scenarios:**

- Assessing model adaptation feasibility before creating msModelSlim adapters
- Analyzing model structure and type classification
- Evaluating MoE compatibility for quantization
- Determining if a model can be quantized with msModelSlim
- Identifying potential risks before adapter development

**Typical User Phrases:**

- "Analyze my model for msModelSlim compatibility"
- "Check if this model can be quantized"
- "Evaluate MoE fused weights risk"
- "Assess model adaptation feasibility"
- "Analyze model structure for quantization"
- "AnalysisModelmsModelSlim"
- "ModelQuantization"
- "CheckMoE"

## Scope

**Supported:**

- Decoder-only LLM
- VLM text backbone analysis (LLM/text path only)

**Not supported:**

- Non-transformers implementations
- Multimodal generation models (image/video/audio generation)

## Required Input

- Model path or model repository identifier
- `config.json`
- Optional: `modeling_*.py`, `model.safetensors.index.json` in the model
  directory
- If files are missing locally:

  - Download non-weight files using:
    `modelscope download --model <org>/<model> --local_dir ./models/<name>
    --exclude '*.safetensors'`
  - Read `config.json` and `modeling_*.py` from the download directory as input
    for analysis.

## Hard Requirement: Parse Implementation Source First

Must complete before any structural analysis. Agent should manually parse
following these steps:

1. **Read `config.json`**:

   - Get `model_type`
   - Get `auto_map` (if present)

2. **Try parsing from transformers**:

   - Check if `transformers` library supports the `model_type`.
   - Check if path exists:
     `transformers/models/<model_type>/modeling_<model_type>.py`.
   - If exists, record as `transformers` implementation.

3. **If not parsed, try model-local implementation**:

   - Check if files pointed by `auto_map` exist in the model directory.
   - Check if `modeling_*.py` files exist in the model directory.
   - If exists, record as `model-local` implementation.

4. **If neither path available**:

   - Stop analysis.
   - Request user to provide readable model implementation code.

## Minimum Workflow

1. Parse implementation source (complete hard requirement above).

2. Determine model type, structural differences, and connections:

   - Type: Pure LLM / Multimodal understanding / Multimodal generation
   - Compare with common Qwen2-like LLMs, record special structural designs
     (e.g., MoE, non-standard attention, SSM/hybrid blocks, additional heads
     or parallel branches)
   - Check special structure connections (location, dependencies,
     serial/parallel/residual connections, impact on backbone traversal)

3. Identify structural features:

   - Decoder layer class, attention/MLP module naming, forward signature

4. Determine features affecting adaptation:

   - Layer traversal path and order
   - Whether layer-by-layer loading is needed
   - MoE fused expert weight risk
   - Quantized model dequantization script risk
   - MTP structure implementation availability and weight handling risk

5. Output structured analysis results (refer to template below).

6. Provide next steps:

   - Proceed to adapter creation workflow
   - Or block and explain what user needs to provide

### Model Type, Structural Differences, and Connection Determination

(relative to common Qwen2)

- **Pure LLM**: Text token input only, backbone is decoder-only language model.
- **Multimodal understanding**: Contains vision/audio encoders, but generation
  path centers on text backbone; only text portion can be analyzed and adapted.
- **Multimodal generation**: Core goal is image/video/audio generation; current
  workflow does not support, should block and explain reason directly.
- Structural differences only need to record "existence + impact direction",
  no deep implementation details required.
- Connection relationships should record at minimum: which stage special
  structure is located in backbone, which modules it connects to, connection
  type (serial/parallel/residual), and impact on traversal/forward alignment.

### MoE Layout Determination

- **Non-fused MoE**: Experts expanded by module/list (commonly each expert has
  its own `gate/up/down` linear layers).
- **Fused MoE**: Multiple expert weights packaged as tensor parameters, no
  longer independent linear layers.
- If any of `gate/up/down` stored in `[..., num_experts, ...]` or
  `[num_experts, ...]` form, treat as "fused".
- Three-dimensional expert weights (e.g., gate/up/down each fused into 3D
  parameters) uniformly classified as `MoE fused`, with "may need unpack"
  marked in report.

## Required Output: Analysis Report

Agent should directly generate analysis report (Markdown format), must include
following elements. Refer to template below:

```markdown
# Analysis Report

## Model Identification
- Model Path/Repository: {model_path}
- `model_type`: {model_type}
- `architectures`: {architectures}

## Implementation Source Analysis
- Result: `transformers` | `model-local` | `unsupported`
- Basis:
  - Resolved file path: {path}
  - Related configuration fields (`model_type`, `auto_map`): {details}

## Model Features and Specifications
- Hidden size: {hidden_size}
- Number of layers: {num_layers}
- Attention heads / KV heads: {num_heads} / {num_kv_heads}
- Analyze only VLM text portion: Yes/No

## Model Type, Structural Differences and Connections
- Model type: Pure LLM | Multimodal understanding | Multimodal generation
- Special structures vs common Qwen2: {special_structures}
- Special structure connections: {special_structure_connections}
- Impact on adaptation workflow: {structure_impact}

## Layer-by-Layer Loading Assessment
- Need layer-by-layer loading: Yes/No
- Reason: {reason}
- Constraints (memory/runtime environment): {constraints}

## MoE Assessment
- Contains MoE: Yes/No
- Layout type: No MoE | Non-fused MoE | Fused MoE
- Suspected fused keys/modules: {keys}
- Expert weight form: Independent linear layers | Packaged tensors
- Needs unpack: Yes/No

## Adaptation Impact Points
- Decoder traversal path: {traversal_path}
- Attention module naming: {attn_module}
- MLP module naming: {mlp_module}
- `visit/forward` strict alignment points: {alignment_points}

## Quantization and MTP Risk Assessment
- Model already quantized: Yes/No
- Quantization determination basis: {quant_evidence}
- Dequantization script provided: Yes/No
- Dequantization script status: {dequant_status}
- MTP structure exists: Yes/No
- MTP implementation code accessibility: Accessible/Not accessible
- MTP risk description: {mtp_risk}

## Risks and Next Steps
- Risk level: Low | Medium | High
- Blockers: {blockers}
- Recommended next steps:
  - Proceed to adapter creation workflow
  - Or request user to provide implementation code
```

### Risk Identification and User Communication Requirements (Mandatory)

- If identified as "model already quantized", must mark "missing dequantization
  script" as blocker, explicitly requiring user to actively provide
  dequantization script before continuing adaptation.
- If MTP structure identified but implementation code inaccessible, must
  explicitly inform:

  - Agent may not be able to fully implement MTP structure adaptation;
  - To continue, user needs to copy MTP-related weights themselves (map
    according to user-side implementation).

- When at least one of above two risk types hits, `risk level` must not be
  lower than "Medium".

## Pass/Fail Criteria

- **Pass**: Implementation source is `transformers` or `model-local`, model
  type is pure LLM or multimodal understanding, and report is complete; if
  quantization/MTP risks hit, clear user action requirements given in report.
- **Fail**: Source not parsed, unsupported implementation type, determined as
  multimodal generation model, or hits "quantized model without dequantization
  script" blocking condition.

## Enhanced Features

### Automated Compatibility Checker

This skill includes an automated model compatibility checker that scans model
architectures before migration:

**Features:**

- **Migration Blocker Detection**: Identifies unsupported operators, custom
  layers, and framework-specific features
- **Early Warning System**: Provides early warning for known issues with
  suggested workarounds
- **Compatibility Score**: Generates compatibility score with detailed breakdown
- **Operator Coverage Analysis**: Reports operator coverage rate for Ascend NPU
  support

**Compatibility Check Categories:**

| Category           | Check Items                                  |
|--------------------|----------------------------------------------|
| Operator Support   | Transformer layers, attention, normalization |
| Framework Features | Custom ops, dynamic shapes, control flow     |
| Weight Formats     | Safetensors, PyTorch, HF format compatibility|
| Special Structures | MoE, MTP, hybrid architectures               |

**Output Format:**

```markdown
## Compatibility Check Result
- Overall Score: XX/100
- Passed: X/XX checks
- Warning: X items require attention
- Blockers: X items preventing migration

### Detailed Results
| Check Item        | Status     | Details                           |
|-------------------|------------|-----------------------------------|
| Operator coverage | ✓ Pass     | 95% of operators supported         |
| Custom layers     | ⚠️ Warning | 2 custom ops need AscendC impl    |
| Weight format     | ✓ Pass     | Standard Hugging Face format      |
```

## Reference Documents

- [Analysis Checklist](references/analysis_checklist.md) - Analysis verification
  checklist
- [Acceptance Criteria](references/acceptance-criteria.md) - Functional
  acceptance criteria
- [Verification Method](references/verification-method.md) - Verification approach
- [Troubleshooting](references/troubleshooting.md) - Common issues and solutions

## Prerequisites

- transformers >= 4.40.0 installed
- Model code available for analysis
- Basic understanding of model structure

## Analysis Workflow

The analysis workflow follows these steps:

1. Parse model configuration (`config.json`)
2. Determine implementation source (transformers or model-local)
3. Analyze model architecture and structural features
4. Assess MoE layout and fused weight risks
5. Generate structured analysis report
6. Provide adaptation recommendations

## Parameter Reference

| Parameter  | Description                    | Required |
|------------|--------------------------------|----------|
| model      | Model name or path             | Yes      |
| output     | Analysis report output path    | No       |
| detailed   | Output detailed information    | No       |
