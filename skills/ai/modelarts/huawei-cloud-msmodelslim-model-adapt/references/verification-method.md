# Verification Methods

## Prerequisite Verification

### 1. Verify Python Environment

```bash
python3 --version  # Python >= 3.8
pip list | grep transformers  # transformers installed
pip list | grep msmodelslim  # msmodelslim installed
```

### 2. Verify Model Files

```bash
# Check model directory structure
ls -la models/<model_name>/
# Expected: config.json, modeling_*.py, configuration_*.py

# Verify config.json exists
cat models/<model_name>/config.json | grep model_type
```

### 3. Verify Adapter Registration

```bash
# Check config.ini entries
grep -A5 "\[ModelAdapter\]" config/config.ini
grep -A5 "\[ModelAdapterEntryPoints\]" config/config.ini

# Test import
python3 -c "from adapters.<model_name> import model_adapter; print('OK')"
```

## Functional Verification

### 1. Model Analysis Verification

```bash
# Read config.json
cat models/<model_name>/config.json

# Check model_type
python3 -c "import json; c=json.load(open('models/<model_name>/config.json')); print(c.get('model_type'))"

# Check architectures
python3 -c "import json; c=json.load(open('models/<model_name>/config.json')); print(c.get('architectures'))"
```

### 2. Adapter Creation Verification

```bash
# Step 1: Generate test model
python3 scripts/step1_generate_test_model.py --model-path ./models/<model_name> --output ./test_model

# Step 2: Run quantization (fallback)
python3 scripts/step2_run_quantization.py --model-path ./test_model --config ./references/llm/fallback_config.yaml

# Step 3: Verify weights
python3 scripts/step3_verify_weights.py --model-path ./test_model --ref-path ./models/<model_name>

# Step 4: Verify quant description
python3 scripts/step4_verify_quant_description.py --model-path ./test_model --rules-path ./rules.json
```

### 3. Interface Implementation Verification

```python
# Test all required interfaces
from adapters.<model_name>.model_adapter import <ModelName>Adapter

adapter = <ModelName>Adapter()

# Test handle_dataset
data = adapter.handle_dataset(["test input"], "cuda:0")
assert data is not None, "handle_dataset failed"

# Test init_model
import json
config = json.load(open("models/<model_name>/config.json"))
model = adapter.init_model(config, "cuda:0")
assert model is not None, "init_model failed"

# Test generate_model_visit
visit = adapter.generate_model_visit()
assert len(visit) > 0, "generate_model_visit failed"

# Test generate_model_forward
forward = adapter.generate_model_forward()
assert forward is not None, "generate_model_forward failed"

# Test enable_kv_cache
adapter.enable_kv_cache(model)
print("All interfaces verified successfully")
```

## End-to-End Verification Script

```bash
#!/bin/bash
set -e

MODEL_NAME="Qwen3-14B"
MODEL_PATH="./models/${MODEL_NAME}"

echo "=== 1. Verify Prerequisites ==="
python3 --version
pip list | grep -E "transformers|msmodelslim"

echo "=== 2. Verify Model Files ==="
ls -la ${MODEL_PATH}/config.json

echo "=== 3. Run Step 1: Generate Test Model ==="
python3 scripts/step1_generate_test_model.py --model-path ${MODEL_PATH} --output ./test_model

echo "=== 4. Run Step 2: Full Fallback Quantization ==="
python3 scripts/step2_run_quantization.py --model-path ./test_model --config ./references/llm/fallback_config.yaml

echo "=== 5. Run Step 3: Weight Verification ==="
python3 scripts/step3_verify_weights.py --model-path ./test_model --ref-path ${MODEL_PATH}

echo "=== 6. Run Step 4: Quant Description ==="
python3 scripts/step4_verify_quant_description.py --model-path ./test_model --rules-path ./rules.json

echo "=== All verifications passed ==="
```

## Verification Checklist

| Check | Expected Result |
|-------|-----------------|
| Python version | >= 3.8 |
| transformers installed | Import successful |
| msmodelslim installed | Import successful |
| config.json exists | File readable |
| model_type identified | Valid type string |
| Step 1 success | Test model generated |
| Step 2 success | Quantization completed |
| Step 3 tolerance | <= 1e-5 |
| Step 4 success | Description validated |
| All interfaces | Import and call successful |
