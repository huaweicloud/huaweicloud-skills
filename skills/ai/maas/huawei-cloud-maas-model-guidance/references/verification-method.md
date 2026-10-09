# Verification Method - MaaS Model Invocation

This document describes methods to verify that MaaS model invocation is working correctly.

## 1. Prerequisites Verification

### 1.1 Verify Account and Authorization

| Verification Item | Method | Expected Result |
|-------------------|--------|-----------------|
| Huawei Cloud account registered | Log in to Huawei Cloud console | Successful login |
| Real-name authentication completed | Check account settings | Authentication status: verified |
| ModelArts delegation authorized | Open ModelArts console → Permission Management | Delegation exists with MaaS permissions |
| Region selected | Check MaaS console region selector | 西南-贵阳一 selected |

### 1.2 Verify Preset Service Activation

1. Log in to MaaS console
2. Navigate to "Model Inference > Online Inference > Preset Services"
3. Check the target model service status:
   - **Payment Status**: Should show "Activated"
   - If not activated, click "Activate Service" to activate

### 1.3 Verify API Key

1. Navigate to "Management & Statistics > API Key Management"
2. Verify API Key exists and is in effective status
3. If newly created, wait a few minutes for it to become effective

## 2. API Connectivity Verification

### 2.1 Basic Connectivity Test (Curl)

Use the simplest request to verify API connectivity:

```bash
curl -X POST "https://api.modelarts-maas.com/v2/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "deepseek-v3.2",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

**Expected Result**:
- HTTP status code: 200
- Response body contains model output text

**If Failed**:
- 401: Check API Key
- 404: Check model parameter
- 429: Rate limited, wait and retry
- See `troubleshooting-guide.md` for detailed solutions

### 2.2 Python Connectivity Test

```python
import requests
import json

url = "https://api.modelarts-maas.com/v2/chat/completions"
api_key = "MAAS_API_KEY"  # Replace with your API Key

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

data = {
    "model": "deepseek-v3.2",
    "messages": [
        {"role": "user", "content": "Hello"}
    ]
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
    print(f"HTTP Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ API connectivity verified successfully!")
        result = response.json()
        if 'choices' in result:
            print(f"Model response: {result['choices'][0]['message']['content']}")
        else:
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ API call failed: {response.text}")
except Exception as e:
    print(f"❌ Connection error: {e}")
```

### 2.3 OpenAI SDK Connectivity Test

```python
from openai import OpenAI

try:
    client = OpenAI(
        api_key="MAAS_API_KEY",  # Replace with your API Key
        base_url="https://api.modelarts-maas.com/openai/v1"
    )
    response = client.chat.completions.create(
        model="deepseek-v3.2",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("✅ OpenAI SDK connectivity verified successfully!")
    print(f"Model response: {response.choices[0].message.content}")
except Exception as e:
    print(f"❌ OpenAI SDK call failed: {e}")
```

## 3. Feature-Specific Verification

### 3.1 Verify Deep Thinking

```python
import requests
import json

url = "https://api.modelarts-maas.com/v2/chat/completions"
api_key = "MAAS_API_KEY"
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

# Test with deep thinking enabled
data = {
    "model": "deepseek-v3.2",
    "messages": [
        {"role": "user", "content": "Which is larger, 9.11 or 9.8?"}
    ],
    "thinking": {
        "type": "enabled"
    }
}

response = requests.post(url, headers=headers, data=json.dumps(data))
result = response.json()

if response.status_code == 200:
    # Check if reasoning_content exists (thinking chain)
    message = result['choices'][0]['message']
    if 'reasoning_content' in message:
        print("✅ Deep thinking verified - thinking chain present")
    else:
        print("⚠️ Deep thinking may not be working - no thinking chain found")
    print(f"Final answer: {message['content']}")
else:
    print(f"❌ Deep thinking test failed: {response.text}")
```

### 3.2 Verify Streaming Output

```python
from openai import OpenAI

client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://api.modelarts-maas.com/openai/v1"
)

try:
    stream = client.chat.completions.create(
        model="deepseek-v3.2",
        messages=[{"role": "user", "content": "Write a poem about spring"}],
        stream=True
    )
    print("✅ Streaming output verified:")
    full_content = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_content += content
    print()
    if full_content:
        print("✅ Streaming content received successfully")
    else:
        print("⚠️ No streaming content received")
except Exception as e:
    print(f"❌ Streaming test failed: {e}")
```

### 3.3 Verify Image Understanding

```python
import requests
import json
import base64

# Create a simple test image (1x1 white PNG) or use an actual image
def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# Replace with your test image path
base64_image = encode_image("test.png")

url = "https://api.modelarts-maas.com/v1/chat/completions"
api_key = "MAAS_API_KEY"
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

data = {
    "model": "qwen2.5-vl-72b",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe the content of the image"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                }
            ]
        }
    ]
}

response = requests.post(url, headers=headers, data=json.dumps(data))
if response.status_code == 200:
    print("✅ Image understanding verified successfully!")
else:
    print(f"❌ Image understanding test failed: {response.text}")
```

### 3.4 Verify Embedding

```python
import requests
import json

url = "https://api.modelarts-maas.com/v1/embeddings"
api_key = "MAAS_API_KEY"
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

data = {
    "model": "bge-m3",
    "input": ["This is a cat", "This is a dog"],
    "encoding_format": "float"
}

response = requests.post(url, headers=headers, data=json.dumps(data))
if response.status_code == 200:
    result = response.json()
    if 'data' in result and len(result['data']) == 2:
        print("✅ Embedding verified successfully!")
        print(f"Vector dimension: {len(result['data'][0]['embedding'])}")
    else:
        print("⚠️ Embedding response format unexpected")
else:
    print(f"❌ Embedding test failed: {response.text}")
```

## 4. Development Tool Integration Verification

### 4.1 Verify Cursor Integration

1. Open Cursor Settings → Models
2. Verify MaaS model is listed and checked
3. Click "Verify" button - should show no errors
4. Start a chat and verify model responds

### 4.2 Verify Cline Integration

1. Open Cline in VS Code
2. Select the configured MaaS service
3. Send a test message and verify response

### 4.3 Verify OpenClaw Integration

1. Run `openclaw tui`
2. Use `/model <model_name>` to switch to MaaS model
3. Send a test message and verify response

## 5. Comprehensive Verification Checklist

Use this checklist to verify all aspects of MaaS model invocation:

### Pre-invocation
- [ ] Huawei Cloud account registered and authenticated
- [ ] ModelArts delegation authorization completed
- [ ] Preset service activated for target model
- [ ] API Key created and effective
- [ ] Correct region selected (西南-贵阳一)

### Basic Invocation
- [ ] API connectivity test passes (HTTP 200)
- [ ] Model responds with expected content
- [ ] Authentication works correctly (Bearer token)

### Feature Verification
- [ ] Deep thinking works (if applicable)
- [ ] Streaming output works
- [ ] Multi-turn conversation works
- [ ] Function Call works (if applicable)
- [ ] Image understanding works (if applicable)

### Integration Verification
- [ ] Development tool connection works (if applicable)
- [ ] Custom access point works (if configured)

### Performance Verification
- [ ] Response latency is acceptable
- [ ] Rate limits are not exceeded under normal usage
- [ ] Token usage is within expected range

## 6. Verification Result Interpretation

| Result | Meaning | Next Step |
|--------|---------|-----------|
| ✅ All checks pass | MaaS invocation is fully functional | Proceed with development |
| ⚠️ Some warnings | Non-critical issues detected | Review and address if needed |
| ❌ Critical failures | Essential functionality not working | Follow troubleshooting guide |

For troubleshooting, see `references/troubleshooting-guide.md`.
