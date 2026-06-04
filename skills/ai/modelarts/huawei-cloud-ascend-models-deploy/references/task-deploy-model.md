# Task: Deploy Model

Deploy a large language model on Huawei Cloud Ascend DevServer.

## Prerequisites

1. Ascend 910B series NPU (910B1/B2/B3/B4)
2. Sufficient NPU cards (check model catalog for minimum)
3. Port not occupied
4. `/home/modelarts-agent` directory exists

## Steps

### 1. Pre-deployment Validation

```bash
# Check NPU model
npu-smi info

# Check NPU cards
npu-smi info -t board

# Check port occupancy
ss -tlnp | grep :8080

# Ensure directory exists
mkdir -p /home/modelarts-agent
```

### 2. Deploy Model

**LLM/Embedding/Rerank:**
```bash
nohup bash -c 'export model_name=Qwen3-14B && export required_cards=1 && export port=8080 && wget -P /home/modelarts-agent/ https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata/deploy-large-models/single-machine/deploy-large-models.sh && chmod 755 /home/modelarts-agent/deploy-large-models.sh && sh /home/modelarts-agent/deploy-large-models.sh Qwen3-14B 1 8080' > /home/modelarts-agent/deploy_Qwen3-14B.log 2>&1 &
```

**VL Multimodal:**
```bash
nohup bash -c 'export model_name=Qwen3-VL-32B-Instruct && export required_cards=2 && export port=8080 && wget -P /home/modelarts-agent/ https://documentation-samples-17.obs.cn-north-9.myhuaweicloud.com/solution-as-code-publicbucket/solution-as-code-module/quickly-deploy-llm-on-modelarts-lite-devserver/userdata/deploy-vl-model/single-machine/deploy-qwen3-vl-model.sh && chmod 755 /home/modelarts-agent/deploy-qwen3-vl-model.sh && sh /home/modelarts-agent/deploy-qwen3-vl-model.sh Qwen3-VL-32B-Instruct 2 8080' > /home/modelarts-agent/deploy_Qwen3-VL-32B-Instruct.log 2>&1 &
```

### 3. Monitor Deployment

```bash
# View deployment log
tail -f /home/modelarts-agent/deploy_Qwen3-14B.log

# Check if service is ready
ss -tlnp | grep :8080
```

### 4. Verify Deployment

```bash
# Test API endpoint
curl -s http://localhost:8080/v1/models
```

## Expected Output

```
Deployment successful! Qwen3-14B is ready

Service URL: http://<IP>:8080/v1/chat/completions
```
