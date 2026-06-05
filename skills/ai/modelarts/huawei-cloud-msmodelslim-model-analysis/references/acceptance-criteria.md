# Acceptance Criteria

## Functional Acceptance Criteria

### 1. Implementation Source Detection

- AC-1.1: Identify transformers source
  - Verification: Check model_type in transformers.models/
- AC-1.2: Identify model-local source
  - Verification: Check auto_map and local files
- AC-1.3: Handle unsupported implementations
  - Verification: Verify error handling

### 2. Model Type Classification

- AC-2.1: Classify as pure LLM
  - Verification: Check architectures
- AC-2.2: Classify as multimodal understanding
  - Verification: Check vision components
- AC-2.3: Classify as multimodal generation
  - Verification: Check generation capabilities

### 3. Structural Feature Analysis

- AC-3.1: Identify special structures
  - Verification: Check model config
- AC-3.2: Document connections
  - Verification: Verify connection report
- AC-3.3: Assess adaptation impact
  - Verification: Check analysis report

### 4. MoE Analysis

- AC-4.1: Detect MoE presence
  - Verification: Check expert modules
- AC-4.2: Identify fused vs unfused
  - Verification: Check weight shapes
- AC-4.3: Assess unpack requirements
  - Verification: Check unpack recommendation

### 5. Report Generation

- AC-5.1: Generate complete analysis report
  - Verification: Verify all sections present
- AC-5.2: Include risk assessment
  - Verification: Check risk level
- AC-5.3: Provide next steps
  - Verification: Verify recommendations

## Correct/Error Pattern Comparison

### Source Detection

**Correct:** Check transformers models directory

```python
import transformers
import os
model_type = config.get("model_type")
path = f"transformers/models/{model_type}/modeling_{model_type}.py"
if os.path.exists(path):
    source = "transformers"
```

**Error:** Assume transformers without verification

```python
source = "transformers"  # Wrong: no verification
```

### Model Type Detection

**Correct:** Check vision components separately

```python
has_vision = "vision" in config.get("architectures", [])
has_text = "language_model" in dir(model)
if has_vision and has_text:
    model_type = "multimodal_understanding"
```

**Error:** Treat all VLMs the same

```python
if "vision" in str(config):
    model_type = "multimodal_generation"  # Wrong: too broad
```

### MoE Detection

**Correct:** Check weight dimensions

```python
# For gate/up/down weights
if weight.ndim == 3 and "gate" in name:
    # 3D weight suggests fused MoE
    moe_type = "fused"
```

**Error:** Only check module name

```python
if "MoE" in module_name:
    moe_type = "fused"  # Wrong: unfused also has MoE in name
```

## Non-Functional Acceptance Criteria

- NAC-1.1: Analysis completion time < 5 minutes
- NAC-1.2: Report completeness - All sections present
- NAC-1.3: Risk assessment accuracy > 90%

## Test Cases Summary

### Positive Test Cases

1. TC-001: Qwen3 LLM analysis
2. TC-002: Qwen3-VL analysis
3. TC-003: MoE fused model analysis
4. TC-004: MoE unfused model analysis
5. TC-005: Layer-by-layer loading assessment

### Negative Test Cases

1. TC-N01: Unsupported implementation source
2. TC-N02: Multimodal generation model
3. TC-N03: Quantized model without dequant script
4. TC-N04: MTP structure without code access
