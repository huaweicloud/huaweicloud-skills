# Troubleshooting

## 1. Model Loading Issues

### Issue: transformers version too old

**Symptom:** `AttributeError: 'xxx' object has no attribute 'yyy'`

**Solution:**

```bash
# Upgrade transformers
pip install --upgrade transformers

# Or specific version
pip install transformers>=4.40.0
```

### Issue: config.json not found

**Symptom:** `FileNotFoundError: config.json`

**Solution:**

```bash
# Download model non-weight files
modelscope download --model <org>/<model> --local_dir ./models/<name> \
  --exclude '*.safetensors'

# Or from HuggingFace
huggingface-cli download <org>/<model> --include "config.json" \
  --local-dir ./models/<name>
```

### Issue: trust_remote_code required

**Symptom:** `OSError: xxx requires trust_remote_code=True`

**Solution:**

```python
from transformers import AutoModel, AutoTokenizer
model = AutoModel.from_pretrained(path, trust_remote_code=True)
```

## 2. Implementation Source Issues

### Issue: Cannot determine source

**Symptom:** Both transformers and model-local paths exist

**Solution:**

```python
# Check auto_map first
if auto_map and any(auto_map.values()):
    source = "model-local"
else:
    source = "transformers"
```

### Issue: Model type not in transformers

**Symptom:** Modeling file not found

**Solution:**

```bash
# List available models
ls transformers/models/

# Check for similar model types
# May need model-local implementation
```

## 3. Model Type Classification Issues

### Issue: Cannot distinguish VLM types

**Symptom:** Multimodal generation vs understanding unclear

**Solution:**

```python
# Check generation capability
has_generate = 'generate' in dir(model)
has_vision = hasattr(model, 'visual') or hasattr(model, 'vision_tower')

if has_generate and has_vision:
    model_type = "multimodal_generation"
elif has_vision:
    model_type = "multimodal_understanding"
```

### Issue: Mixed architectures

**Symptom:** Model has both LLM and vision components

**Solution:**

```python
# Check primary use case
if 'vision' in architectures[0].lower():
    primary = "vision"
else:
    primary = "language"
```

## 4. MoE Analysis Issues

### Issue: Cannot detect MoE type

**Symptom:** Unclear if fused or unfused

**Solution:**

```python
# Check weight shapes
for name, tensor in state_dict.items():
    if 'gate' in name.lower():
        print(f"{name}: {tensor.shape}")
        # [num_experts, hidden, intermediate] -> fused
        # [hidden, intermediate] -> unfused
```

### Issue: MoE unpack requirements unclear

**Solution:**

```python
# Check for 3D expert weights
if any(t.ndim == 3 and 'expert' in k.lower()
       for k, t in state_dict.items()):
    needs_unpack = True
    # Document which weights need unpack
```

## 5. Report Generation Issues

### Issue: Report missing sections

**Solution:**

```python
# Check required sections
required_sections = [
    "Model Identification",
    "Implementation Source Analysis",
    "Model Features and Specifications",
    "Model Type",
    "Layer-by-Layer Loading Assessment",
    "MoE Assessment",
    "Adaptation Impact Points",
    "Quantization and MTP Risk Assessment",
    "Risks and Next Steps",
]
```

### Issue: Risk level too high/low

**Solution:**

```python
# Re-evaluate blockers
blockers = []
if quantized_without_script:
    blockers.append("Quantized model without dequant script")
if mtp_without_code:
    blockers.append("MTP structure without implementation code")

risk_level = "High" if len(blockers) >= 2 else "Medium" if blockers else "Low"
```

## Quick Diagnostic Commands

```bash
# Check model structure
ls -la models/<model>/

# Read config
cat models/<model>/config.json | python3 -m json.tool | head -50

# Check transformers support
python3 -c "
import transformers
import os
ct = 'Qwen2ForCausalLM'
path = os.path.join(os.path.dirname(transformers.__file__), 'models', ct)
print(f'Exists: {os.path.exists(path)}')
"

# Analyze model
python3 scripts/analyze_model.py --model-path models/<model> --verbose
```
