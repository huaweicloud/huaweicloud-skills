# Acceptance Criteria

## Functional Acceptance Criteria

### 1. Model Analysis

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-1.1 | Should correctly identify model implementation source | Check transformers or model-local detection |
| AC-1.2 | Should identify model type (LLM/VLM/MoE) | Verify output matches expected type |
| AC-1.3 | Should detect layer-by-layer loading requirements | Check output analysis report |

### 2. Adapter Creation

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-2.1 | Should generate adapter code from template | Compare with expected template output |
| AC-2.2 | Should implement all 5 required interfaces | Run verification scripts |
| AC-2.3 | Should handle MoE unpack for fused weights | Verify unpack logic correctness |

### 3. Adapter Registration

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-3.1 | Should register model in config.ini | Check config file entries |
| AC-3.2 | Should execute install.sh successfully | Verify no errors during installation |
| AC-3.3 | Should import adapter module correctly | Test Python import |

### 4. Verification Workflow

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-4.1 | Step 1: Generate test model succeeds | Check step1 output |
| AC-4.2 | Step 2: Full fallback quantization passes | Check step2 output |
| AC-4.3 | Step 3: Weight verification matches float | Check tolerance within 1e-5 |
| AC-4.4 | Step 4: Quant description validation passes | Check step4 output |

## Correct/Error Pattern Comparison

### Adapter Interface Implementation

**Correct:** All 5 required interfaces implemented
```python
class MyModelAdapter(TransformersModel, ModelSlimPipelineInterfaceV1):
    def handle_dataset(self, raw_data, device): ...
    def init_model(self, config, device): ...
    def generate_model_visit(self): ...
    def generate_model_forward(self): ...
    def enable_kv_cache(self, model): ...
```

**Error:** Missing required interfaces
```python
class MyModelAdapter:
    def init_model(self, config, device): ...
    # Missing: handle_dataset, generate_model_visit, generate_model_forward, enable_kv_cache
```

### MoE Weight Handling

**Correct:** Unpack fused weights before quantization
```python
# For 3D packed experts [num_experts, hidden, intermediate]
gate = weight[0::3]  # Split by 3
up = weight[1::3]
down = weight[2::3]
```

**Error:** Quantize without unpacking
```python
quantize(weight)  # Wrong: fused 3D weights
```

## Non-Functional Acceptance Criteria

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-1.1 | Adapter code generation time | < 5 seconds |
| NAC-1.2 | Weight verification tolerance | <= 1e-5 |
| NAC-1.3 | Model loading compatibility | Python 3.8+ |

## Test Cases Summary

### Positive Test Cases

1. TC-001: Decoder-only LLM adapter creation
2. TC-002: VLM text backbone adapter creation
3. TC-003: MoE model adapter with unpacking
4. TC-004: Full 4-step verification workflow
5. TC-005: Adapter registration and import

### Negative Test Cases

1. TC-N01: Unsupported model type (multimodal generation)
2. TC-N02: Missing required interfaces
3. TC-N03: MoE weights without unpacking
4. TC-N04: Registration without install.sh
5. TC-N05: Weight verification tolerance exceeded
