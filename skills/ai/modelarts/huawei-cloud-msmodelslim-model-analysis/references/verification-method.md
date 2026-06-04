# Verification Methods

## Prerequisite Verification

### 1. Verify Model Files

```bash
# Check model directory
ls -la models/<model_name>/

# Verify config.json exists
cat models/<model_name>/config.json

# Check model_type field
python3 -c "import json; c=json.load(open('models/<model_name>/config.json')); \
  print(c.get('model_type'))"
```

### 2. Verify transformers Installation

```bash
# Check transformers version
pip show transformers

# Check transformers models directory
python3 -c "import transformers; print(transformers.__file__)"
ls -la $(python3 -c "import transformers; print(transformers.__file__)" \
  | tr -d '\n')/../models/
```

### 3. Verify Python Environment

```bash
# Python version
python3 --version  # Should be >= 3.8

# Required packages
pip list | grep -E "torch|transformers"
```

## Functional Verification

### 1. Implementation Source Verification

```python
# Read config.json
import json
config = json.load(open('models/<model_name>/config.json'))
model_type = config.get('model_type')
architectures = config.get('architectures')

# Check transformers source
import transformers
import os
transformers_path = os.path.dirname(transformers.__file__)
model_path = f"{transformers_path}/models/{model_type}/modeling_{model_type}.py"

if os.path.exists(model_path):
    print(f"Source: transformers ({model_path})")
else:
    print("Source: model-local")

# Check auto_map
auto_map = config.get('auto_map', {})
if auto_map:
    print(f"Source: model-local (auto_map)")
```

### 2. Model Type Verification

```python
# Check architectures
if any(x in architectures for x in ['LlamaForCausalLM', 'Qwen2ForCausalLM']):
    model_type = "pure_LLM"
elif any(x in architectures for x in ['Qwen2VLForConditionalGeneration']):
    model_type = "multimodal_understanding"
elif any(x in architectures for x in ['LlamaForCausalLM']):
    # Check if has vision
    if 'vision' in str(config):
        model_type = "multimodal_understanding"
```

### 3. MoE Verification

```python
# Check for expert modules
import torch
state_dict = torch.load('model.safetensors', map_location='cpu')

# Check weight shapes
for name, tensor in list(state_dict.items())[:10]:
    print(f"{name}: {tensor.shape}")

# Look for MoE indicators
has_moe = any('expert' in k.lower() for k in state_dict.keys())
print(f"Has MoE: {has_moe}")
```

### 4. Report Verification

```bash
# Generate analysis report
python3 scripts/analyze_model.py --model-path models/<model_name> \
  --output analysis_report.md

# Verify report structure
head -50 analysis_report.md

# Check all sections present
grep -E "^## " analysis_report.md
```

## End-to-End Verification Script

```bash
#!/bin/bash
set -e

MODEL_PATH="models/Qwen3-14B"

echo "=== 1. Verify Prerequisites ==="
python3 --version
pip list | grep -E "torch|transformers"

echo "=== 2. Verify Model Files ==="
ls -la ${MODEL_PATH}/config.json
cat ${MODEL_PATH}/config.json | grep -E "model_type|architectures"

echo "=== 3. Analyze Implementation Source ==="
python3 -c "
import json
import os
import transformers
config = json.load(open('${MODEL_PATH}/config.json'))
model_type = config.get('model_type')
path = os.path.join(os.path.dirname(transformers.__file__), \
  'models', model_type, f'modeling_{model_type}.py')
print(f'Model type: {model_type}')
print(f'Transformers path exists: {os.path.exists(path)}')
"

echo "=== 4. Generate Analysis Report ==="
python3 scripts/analyze_model.py --model-path ${MODEL_PATH} \
  --output analysis_report.md

echo "=== 5. Verify Report ==="
grep -E "^## " analysis_report.md

echo "=== All verifications passed ==="
```

## Verification Checklist

- Python version: >= 3.8
- transformers installed: Import successful
- config.json exists: File readable
- model_type identified: Valid type string
- Source detected: transformers or model-local
- Report generated: File created
- All sections present: 10+ sections
- Risk level assigned: Low/Medium/High
