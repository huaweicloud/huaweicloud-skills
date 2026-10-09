# Code Examples (Advanced) - MaaS Model Invocation

Example code for image understanding, image generation, video generation, text embedding, and reranking.

> In all examples, replace `MAAS_API_KEY` with your actual API Key.

## 1. Image Understanding

### Python (requests)

```python
import requests
import json
import base64

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

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
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
        }
    ]
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.status_code)
print(response.text)
```

### Curl

```bash
curl -X POST "https://api.modelarts-maas.com/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "qwen2.5-vl-72b",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "Describe the content of the image"},
          {"type": "image_url", "image_url": {"url": "data:image/png;base64,$BASE64_IMAGE"}}
        ]
      }
    ]
  }'
```

### OpenAI Python SDK

```python
from openai import OpenAI
import base64

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

base64_image = encode_image("test.png")

client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://api.modelarts-maas.com/v1"
)
response = client.chat.completions.create(
    model="qwen2.5-vl-72b",
    messages=[
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
)
print(response.choices[0].message.content)
```

## 2. Image Generation

### Python (requests)

```python
import requests
import json

url = "https://api.modelarts-maas.com/v1/images/generations"
api_key = "MAAS_API_KEY"

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

data = {
    "model": "qwen-image",
    "input": {
        "prompt": "A cute cat playing in a garden"
    },
    "parameters": {
        "size": "1024x1024",
        "seed": 42
    }
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.status_code)
print(response.text)
```

### Curl

```bash
curl -X POST "https://api.modelarts-maas.com/v1/images/generations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "qwen-image",
    "input": {"prompt": "A cute cat playing in a garden"},
    "parameters": {"size": "1024x1024", "seed": 42}
  }'
```

## 3. Video Generation

> Video generation is an asynchronous API. You need to create a task first, then query the result.

### Create Video Generation Task

```python
import requests
import json

url = "https://api.modelarts-maas.com/v1/video/generations"
api_key = "MAAS_API_KEY"

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

data = {
    "model": "Wan2.2-T2V-A14B",
    "input": {"prompt": "A kitten taking a walk"},
    "parameters": {
        "size": "720x1280",
        "fps": 16,
        "duration": 5,
        "seed": 0
    }
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.status_code)
print(response.text)
# The response contains task_id
```

### Curl - Create Video Generation Task

```bash
curl -X POST "https://api.modelarts-maas.com/v1/video/generations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "Wan2.2-T2V-A14B",
    "input": {"prompt": "A kitten taking a walk"},
    "parameters": {"size": "720x1280", "fps": 16, "duration": 5, "seed": 0}
  }'
```

### Query Video Generation Task

```python
task_id = "your_task_id"  # Replace with the actual task ID
query_url = f"https://api.modelarts-maas.com/v1/video/generations/{task_id}"

response = requests.get(query_url, headers=headers)
print(response.status_code)
print(response.text)
```

## 4. Text Embedding

### Python (requests)

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
    "input": ["This is a kitten", "This is a puppy"],
    "encoding_format": "float"
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.status_code)
print(response.text)
```

### Curl

```bash
curl -X POST "https://api.modelarts-maas.com/v1/embeddings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "bge-m3",
    "input": ["This is a kitten", "This is a puppy"],
    "encoding_format": "float"
  }'
```

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://api.modelarts-maas.com/openai/v1"
)
response = client.embeddings.create(
    model="bge-m3",
    input=["This is a kitten", "This is a puppy"]
)
print(response.data)
```

## 5. Reranking

### Curl

```bash
curl -X POST "https://api.modelarts-maas.com/v1/rerank" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "bge-reranker-v2-m3",
    "input": "How to brew a good cup of coffee?",
    "documents": [
      "Coffee beans are mainly grown near the equator, an area known as the Coffee Belt.",
      "French press steps: 1. Grind coffee beans. 2. Add hot water. 3. Press down the plunger. 4. Pour into cup.",
      "Espresso requires a high-pressure machine to quickly extract at 9 atmospheres of pressure.",
      "When selecting coffee beans, pay attention to the roast date; fresher beans have better flavor.",
      "Pour-over coffee tips: controlling water flow speed, pouring evenly, and using the right water temperature (90-96C) are key."
    ]
  }'
```

### Python (requests)

```python
import requests
import json

url = "https://api.modelarts-maas.com/v1/rerank"
api_key = "MAAS_API_KEY"

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

data = {
    "model": "bge-reranker-v2-m3",
    "input": "How to brew a good cup of coffee?",
    "documents": [
        "Coffee beans are mainly grown near the equator, an area known as the Coffee Belt.",
        "French press steps: 1. Grind coffee beans. 2. Add hot water. 3. Press down the plunger. 4. Pour into cup.",
        "Espresso requires a high-pressure machine to quickly extract at 9 atmospheres of pressure."
    ]
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.status_code)
print(response.text)
```
