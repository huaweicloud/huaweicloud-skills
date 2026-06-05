# Troubleshooting

## 1. Model Loading Issues

### Issue: transformers version incompatibility

**Symptom:** `ImportError: cannot import name 'xxx' from 'transformers'`

**Root Cause:** Model requires newer transformers version.

**Solution:**
```bash
pip install --upgrade transformers
# Or specific version
pip install transformers>=4.40.0
```

### Issue: trust_remote_code not set

**Symptom:** `OSError: xxx requires trust_remote_code=True`

**Solution:**
```python
from transformers import AutoModel, AutoTokenizer
model = AutoModel.from_pretrained(path, trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
```

## 2. Adapter Creation Issues

### Issue: Missing required interfaces

**Symptom:** `NotImplementedError: Interface xxx not implemented`

**Solution:** Ensure all 5 required interfaces are implemented:
- handle_dataset
- init_model
- generate_model_visit
- generate_model_forward
- enable_kv_cache

### Issue: visit and forward mismatch

**Symptom:** Quantization fails with layer mismatch

**Solution:** Verify generate_model_visit and generate_model_forward process layers in the same order and access the same modules.

## 3. MoE Weight Issues

### Issue: Packed expert weights cause quantization failure

**Symptom:** Shape mismatch during quantization

**Root Cause:** MoE experts packed as 3D tensors [num_experts, hidden, intermediate]

**Solution:** Unpack before quantization:
```python
# For weights with shape [num_experts, hidden, intermediate*3]
gate = weights[0::3]    # [num_experts, hidden, intermediate]
up = weights[1::3]        # [num_experts, hidden, intermediate]
down = weights[2::3]       # [num_experts, hidden, intermediate]
```

### Issue: Incorrect unpack dimension

**Symptom:** Weight shapes don't match after unpack

**Solution:** Check the actual weight dimension ordering. Some models use [hidden, intermediate, num_experts].

## 4. Registration Issues

### Issue: Model not found after install.sh

**Symptom:** `KeyError: model_type not found in config.ini`

**Solution:**
```bash
# Verify config.ini entries
grep -A2 "\[ModelAdapter\]" config/config.ini
grep -A2 "\[ModelAdapterEntryPoints\]" config/config.ini

# Re-run installation
bash install.sh

# Verify Python can import
python3 -c "from adapters.<model_name> import model_adapter"
```

### Issue: Module import error

**Symptom:** `ModuleNotFoundError: No module named 'adapters'`

**Solution:**
```bash
# Check __init__.py exists
ls -la adapters/__init__.py

# Re-install package
pip install -e .
```

## 5. Quantization Issues

### Issue: Step 3 weight verification failed

**Symptom:** `AssertionError: Max tolerance exceeded`

**Possible Causes:**
1. Quantization changed weight values unexpectedly
2. Different tensor ordering between fallback and original

**Solution:**
```bash
# Check actual tolerance
python3 scripts/step3_verify_weights.py --model-path ./test_model --ref-path ./models/<model_name> --verbose

# If using MoE, verify unpack logic
# Increase tolerance if within acceptable range (e.g., 1e-3)
```

### Issue: Step 4 quant description validation failed

**Symptom:** Layer names don't match rules

**Solution:**
```bash
# Check which layers failed
python3 scripts/step4_verify_quant_description.py --model-path ./test_model --rules-path ./rules.json --verbose

# Update rules.json to match actual layer names
```

## 6. Performance Issues

### Issue: Model loading too slow

**Solution:**
- Use modelscope download for non-weight files only
- Enable layer-by-layer loading for large models
- Use trust_remote_code=False if not needed

### Issue: Quantization out of memory

**Solution:**
- Reduce batch size in calibration data
- Use dynamic quantization instead of static
- Process in smaller chunks

## Quick Diagnostic Commands

```bash
# Check Python environment
python3 --version && pip list | grep -E "transformers|torch|msmodelslim"

# Verify model structure
python3 -c "import json; c=json.load(open('models/<model>/config.json')); print(c.get('model_type'))"

# Test adapter import
python3 -c "from adapters.<model> import model_adapter; print('Import OK')"

# Run verification with verbose
python3 scripts/step1_generate_test_model.py --model-path ./models/<model> --output ./test --verbose
```
