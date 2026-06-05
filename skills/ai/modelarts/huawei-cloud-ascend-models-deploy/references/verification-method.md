# Verification Method

Steps to verify deployment and functionality.

## Pre-deployment Verification

### 1. NPU Check

```bash
# Check NPU type (must be 910B series)
npu-smi info | grep "Product Name"

# Expected output: IT21HMDA (910B3) or similar 910B variant
```

### 2. NPU Card Count

```bash
# Count available NPU cards
npu-smi info -t board | wc -l

# Verify >= required cards for model
```

### 3. Port Availability

```bash
# Check if port is free
ss -tlnp | grep :8080

# Empty output = port available
```

## Post-deployment Verification

### 1. Service Status

```bash
# Check if service is listening
ss -tlnp | grep :8080

# Expected: LISTEN state
```

### 2. API Endpoint

```bash
# List available models
curl -s http://localhost:8080/v1/models

# Expected: {"object":"list","data":[{"id":"Qwen3-14B",...}]}
```

### 3. Inference Test

```bash
# Simple inference test
curl -s -X POST http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen3-14B","messages":[{"role":"user","content":"hello"}],"max_tokens":32}'

# Expected: Valid JSON response with content
```

## Success Criteria

| Check | Expected |
|-------|----------|
| NPU type | 910B series |
| Port listening | Yes |
| /v1/models | Returns model list |
| Inference | Returns valid response |
| No errors in log | Clean deployment |
