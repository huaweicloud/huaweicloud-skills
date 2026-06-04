# Troubleshooting

Common issues and solutions.

## Deployment Issues

### 1. Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port
ss -tlnp | grep :8080

# Kill process
kill -9 <PID>

# Or use different port
```

### 2. Insufficient NPU Cards

**Error:** `Not enough NPU cards`

**Solution:**
- Check available cards: `npu-smi info -t board`
- Use model with lower card requirement
- Free up occupied NPU cards

### 3. Model Weight Loading Failed

**Error:** `Failed to load model weights`

**Solution:**
- Check model path in OBS
- Verify network connectivity
- Check disk space: `df -h /home`

### 4. NPU Type Mismatch

**Error:** `Unsupported NPU type`

**Solution:**
- This skill only supports 910B series (910B1/B2/B3/B4)
- Check NPU type: `npu-smi info`
- Use different hardware for other NPU types

## Inference Issues

### 1. OOM (Out of Memory)

**Error:** `CUDA out of memory` or `NPU out of memory`

**Solution:**
- Reduce `max_tokens`
- Use smaller batch size
- Use model with lower memory requirement

### 2. Timeout

**Error:** `Request timeout`

**Solution:**
- Increase timeout value
- Check if model is still loading
- Monitor with: `tail -f /home/modelarts-agent/deploy_*.log`

### 3. Invalid Model Name

**Error:** `Model not found`

**Solution:**
- Use exact model name from catalog
- Check deployed models: `curl http://localhost:8080/v1/models`

## Log Analysis

```bash
# View recent logs
tail -50 /home/modelarts-agent/deploy_*.log

# Search for errors
grep -i error /home/modelarts-agent/deploy_*.log

# Monitor in real-time
tail -f /home/modelarts-agent/deploy_*.log
```
