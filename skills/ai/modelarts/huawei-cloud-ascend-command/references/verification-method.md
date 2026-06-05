# Verification Steps and Methods

## Prerequisite Verification

### 1. Verify Python3

```bash
python3 --version  # Python3 >= 3.8
```

### 2. Verify Local NPU Environment

```bash
# Check if npu-smi is available locally
npu-smi info -l 2>/dev/null || echo "npu-smi not found locally"
```

## Functional Verification

### Local Mode Verification

```bash
# Basic device query
python3 scripts/main.py --command "NPU list"

# Check health
python3 scripts/main.py --command "NPU health check"

# Get temperature
python3 scripts/main.py --command "NPU temperature"

# Direct npu-smi command
python3 scripts/main.py --npu-smi "info -l"
```

### SSH Remote Mode Verification

```bash
# Remote device query
python3 scripts/main.py --command "NPU list" --host 192.168.1.100 --user root --password xxx

# Remote health check
python3 scripts/main.py --command "NPU health check" --host 192.168.1.100 --user root --password xxx

# Remote temperature
python3 scripts/main.py --command "NPU temperature" --host 192.168.1.100 --user root --password xxx
```

### Interactive Mode Verification

```bash
python3 scripts/main.py
# Then type commands interactively:
# - NPU list
# - NPU health check
# - exit
```

## End-to-End Verification Script

```bash
#!/bin/bash
set -e

echo "=== 1. Verify Python3 ==="
python3 --version

echo ""
echo "=== 2. Local NPU Check ==="
python3 scripts/main.py --command "NPU list"

echo ""
echo "=== 3. Help Command ==="
python3 scripts/main.py --command "help"

echo ""
echo "=== Verification completed successfully ==="
```

## Expected Results

| Test Case | Expected Output |
|-----------|----------------|
| Python3 check | Python version >= 3.8 |
| Local NPU list | Shows NPU devices or "npu-smi not found" |
| Help command | Shows supported commands list |
| Remote command | NPU info from remote server |
