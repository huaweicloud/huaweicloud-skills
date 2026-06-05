# Acceptance Criteria

## Functional Acceptance Criteria

### 1. Model Catalog Management

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-1.1 | Should list all supported models | `python3 deploy_helper.py list` command |
| AC-1.2 | Should filter models by category | `python3 deploy_helper.py list LLM` command |
| AC-1.3 | Should fuzzy match model names | `python3 deploy_helper.py match qwen3-14b` |
| AC-1.4 | Should return model details including min_cards | `python3 deploy_helper.py info Qwen3-14B` |

### 2. Deployment Validation

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-2.1 | Should validate NPU model is 910B series | Check `npu-smi info` output |
| AC-2.2 | Should validate sufficient NPU cards | Compare available vs required cards |
| AC-2.3 | Should validate port availability | `ss -tlnp | grep :port` |
| AC-2.4 | Should reject non-910B NPU types | Attempt deployment on non-910B |

### 3. Single-machine Deployment

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-3.1 | Should deploy LLM models | Deploy Qwen3-14B |
| AC-3.2 | Should deploy VL multimodal models | Deploy Qwen3-VL-32B-Instruct |
| AC-3.3 | Should deploy Embedding models | Deploy bge-m3 |
| AC-3.4 | Should deploy Rerank models | Deploy bge-reranker-v2-m3 |
| AC-3.5 | Should deploy OpenSource models | Deploy Qwen3.6-35B-A3B |

### 4. Dual-machine Deployment

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-4.1 | Should deploy 16-card models across two nodes | Deploy Qwen3-235B-A22B-Instruct |
| AC-4.2 | Should validate SSH connectivity to both nodes | Check head/worker reachability |
| AC-4.3 | Should start Ray cluster correctly | Verify head and worker connection |

### 5. Inference Testing

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-5.1 | Should test LLM chat completions | `/v1/chat/completions` endpoint |
| AC-5.2 | Should test VL multimodal inference | Image + text prompt |
| AC-5.3 | Should test Embedding generation | `/v1/embeddings` endpoint |
| AC-5.4 | Should test Rerank functionality | `/v1/rerank` endpoint |

### 6. Deployment Monitoring

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-6.1 | Should show deployment logs | `tail -50 deploy_*.log` |
| AC-6.2 | Should check service status | `ss -tlnp | grep :port` |
| AC-6.3 | Should report deployment progress | Monitor log every 2 minutes |
| AC-6.4 | Should notify on deployment success | Port listening detection |

### 7. Safety Features

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-7.1 | Should prompt confirmation for deployment | User must reply "confirm" |
| AC-7.2 | Should allow confirmation/cancellation | Reply "confirm" or "cancel" |
| AC-7.3 | Should show full command before execution | Display command for review |

## Non-Functional Acceptance Criteria

### 1. Performance

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-1.1 | Model matching response time | < 1 second |
| NAC-1.2 | Deployment script download time | < 10 seconds |
| NAC-1.3 | Qwen3-14B deployment time | < 15 minutes |
| NAC-1.4 | Inference latency (Qwen3-14B) | < 1 second per token |

### 2. Reliability

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-2.1 | Deployment success rate | > 95% |
| NAC-2.2 | Graceful error handling | No crashes |
| NAC-2.3 | Model matching accuracy | > 90% |

### 3. Compatibility

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-3.1 | Python version compatibility | Python 3.8+ |
| NAC-3.2 | OS compatibility | Ubuntu 22.04 / EulerOS 2.0 |
| NAC-3.3 | NPU compatibility | Ascend 910B1/B2/B3/B4 |

## Deployment Acceptance Criteria

### 1. Environment Requirements

| Criteria | Description |
|----------|-------------|
| DAC-1.1 | Python 3.8 or higher installed |
| DAC-1.2 | npu-smi available in PATH |
| DAC-1.3 | Sufficient disk space (>100GB) |
| DAC-1.4 | `/home/modelarts-agent` directory exists |

### 2. Success Indicators

| Criteria | Expected Outcome |
|----------|------------------|
| Port listening | Service ready for testing |
| `/v1/models` endpoint | Returns model list |
| Inference test | Valid JSON response |
| No errors in log | Clean deployment |

## Test Cases Summary

### Positive Test Cases

1. TC-001: List all models
2. TC-002: Fuzzy model matching
3. TC-003: Single-machine LLM deployment
4. TC-004: Single-machine VL deployment
5. TC-005: Embedding deployment
6. TC-006: Rerank deployment
7. TC-007: LLM inference test
8. TC-008: VL multimodal test
9. TC-009: Deployment log viewing
10. TC-010: Service status check

### Negative Test Cases

1. TC-N01: Invalid model name
2. TC-N02: Insufficient NPU cards
3. TC-N03: Port already in use
4. TC-N04: Unsupported NPU type
5. TC-N05: Missing parameters
