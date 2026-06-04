# Troubleshooting

## 1. Server Connection Issues

### Issue: SSH connection timeout

**Symptom:** `Connection timed out`

**Solution:**
```bash
# Verify server IP and port
ping -c 3 ascend-server-01

# Check SSH service
ssh -p 22 root@ascend-server-01 "systemctl status sshd"

# Try with key-based auth
ssh -i /path/to/key -p 22 root@ascend-server-01
```

### Issue: Container not running

**Symptom:** `Error: No such container: skill-the`

**Solution:**
```bash
# Check all containers
docker ps -a | grep skill

# Start container if exists but stopped
docker start skill-the

# Or create new container
docker run -itd --name skill-the quay.io/ascend/vllm-ascend:v0.18.0
```

## 2. NPU Issues

### Issue: NPU not detected

**Symptom:** `torch.npu.is_available()` returns False

**Solution:**
```bash
# Check NPU driver
npu-smi info

# Verify CANN installation
pip list | grep ascendl

# Reinstall torch_npu
pip uninstall torch_npu
pip install torch_npu
```

### Issue: NPU memory exhausted

**Symptom:** `RuntimeError: NPU out of memory`

**Solution:**
```python
# Reduce batch size
batch_size = 1

# Clear cache
torch.npu.empty_cache()

# Use gradient checkpointing
model.gradient_checkpointing_enable()
```

## 3. Model Loading Issues

### Issue: Model architecture not supported

**Symptom:** `RuntimeError: Unsupported operator`

**Solution:**
```bash
# Check model requirements
cat /path/to/model/config.json | grep model_type

# Verify torch_npu supports the operators
python3 -c "import torch_npu; print(torch_npu.list_supported_ops())"
```

### Issue: Model weights incompatible

**Symptom:** `RuntimeError: Expected tensor for argument #1`

**Solution:**
```python
# Reload weights
model.load_state_dict(torch.load('model.pt'), strict=False)

# Or convert to NPU format
model = model.to('cpu')
model = model.to('npu:0')
```

## 4. Dependency Issues

### Issue: pip install fails

**Symptom:** `ERROR: Could not find a version that satisfies the requirement`

**Solution:**
```bash
# Update pip
pip install --upgrade pip

# Use specific version
pip install torch_npu==2.0.0

# Or install from source
pip install --no-cache-dir torch_npu
```

### Issue: Version conflict

**Symptom:** `ERROR: torch 2.x is installed but torch_npu requires torch x.x`

**Solution:**
```bash
# Check installed versions
pip list | grep torch

# Install compatible versions
pip install torch==2.1.0 torch_npu==2.1.0
```

## 5. Performance Profiling Issues

### Issue: OPPROF directory not created

**Symptom:** `ls: cannot access 'OPPROF_*': No such file or directory`

**Solution:**
```bash
# Run profiling command
msprof op --output=./profiling_data python3 inference.py

# Check permissions
chmod 755 /path/to/output_dir

# Run with full path
cd /path/to/model && msprof op --output=./profiling_data python3 inference.py
```

### Issue: Profiling data incomplete

**Symptom:** Missing CSV files in OPPROF directory

**Solution:**
```bash
# Run with default metrics
msprof op --aic-metrics=Default --output=./profiling_data python3 inference.py

# Check collection duration
# Add warmup if too short
```

## Quick Diagnostic Commands

```bash
# Check server status
ssh -p 22 root@ascend-server-01 "uptime"

# Check NPU status
ssh -p 22 root@ascend-server-01 "npu-smi info"

# Check container logs
docker logs skill-the

# Check Python environment
docker exec skill-the bash -c "pip list | grep torch"

# Test NPU inference
docker exec skill-the bash -c "python3 -c 'import torch; print(torch.npu.is_available())'"
```
