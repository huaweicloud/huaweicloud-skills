# Code Examples - MaaS Model Invocation

Example code for MaaS model invocation, covering Python, Curl, OpenAI Python SDK, Java, and other languages.

> In all examples, replace `MAAS_API_KEY` with your actual API Key.

## 1. Text Generation

### Python (requests)

```python
import requests
import json

url = "https://api.modelarts-maas.com/v2/chat/completions"
api_key = "MAAS_API_KEY"  # Replace MAAS_API_KEY with your obtained API Key

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

data = {
    "model": "deepseek-v3.2",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.status_code)
print(response.text)
```

### Curl

```bash
curl -X POST "https://api.modelarts-maas.com/v2/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "deepseek-v3.2",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### OpenAI Python SDK

```python
from openai import OpenAI

base_url = "https://api.modelarts-maas.com/openai/v1"
api_key = "MAAS_API_KEY"  # Replace MAAS_API_KEY with your obtained API Key

client = OpenAI(api_key=api_key, base_url=base_url)
response = client.chat.completions.create(
    model="deepseek-v3.2",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ]
)
print(response.choices[0].message.content)
```

### Java

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

// Recommended JDK version is 15+
public class MaasChatExample {
    public static void main(String[] args) throws Exception {
        String apiUrl = "https://api.modelarts-maas.com/v2/chat/completions";
        String apiKey = "MAAS_API_KEY";  // Replace MAAS_API_KEY with your obtained API Key
        String modelName = "deepseek-v3.2";

        String requestBody = String.format("""
        {
            "model": "%s",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"}
            ]
        }""", modelName);

        HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10)).build();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(apiUrl))
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer " + apiKey)
            .POST(HttpRequest.BodyPublishers.ofString(requestBody))
            .build();

        try {
            HttpResponse<String> response = client.send(
                request, HttpResponse.BodyHandlers.ofString());
            System.out.println("HTTP Status: " + response.statusCode());
            System.out.println("Response Body:\n" + response.body());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

## 2. Deep Thinking

### Python (requests)

```python
import requests
import json

url = "https://api.modelarts-maas.com/v2/chat/completions"
api_key = "MAAS_API_KEY"

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
}

data = {
    "model": "deepseek-v3.2",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ],
    "thinking": {
        "type": "enabled"  # Enable deep thinking
    }
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.status_code)
print(response.text)
```

### Curl

```bash
curl -X POST "https://api.modelarts-maas.com/v2/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "deepseek-v3.2",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello"}
    ],
    "thinking": {"type": "enabled"}
  }'
```

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://api.modelarts-maas.com/openai/v1"
)
response = client.chat.completions.create(
    model="deepseek-v3.2",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    extra_body={"thinking": {"type": "enabled"}}
)
print(response.choices[0].message.content)
```

> To disable deep thinking, set `"thinking": {"type": "disabled"}` (only supported for models with toggle capability)

## 3. Streaming Output

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://api.modelarts-maas.com/openai/v1"
)
stream = client.chat.completions.create(
    model="deepseek-v3.2",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
```

### Curl

```bash
curl -X POST "https://api.modelarts-maas.com/v2/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MAAS_API_KEY" \
  -d '{
    "model": "deepseek-v3.2",
    "messages": [
      {"role": "user", "content": "Hello"}
    ],
    "stream": true
  }'
```

## 4. Multi-turn Conversation

> The MaaS Chat API is stateless; each request must include the full conversation history.

### OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="MAAS_API_KEY",
    base_url="https://api.modelarts-maas.com/openai/v1"
)

# First round of conversation
messages = [{"role": "user", "content": "Which is larger, 9.11 or 9.8?"}]
response = client.chat.completions.create(model="deepseek-v3.2", messages=messages)
messages.append(response.choices[0].message)
print(f"Round 1: {messages}")

# Second round of conversation
messages.append({"role": "user", "content": "What is their sum?"})
response = client.chat.completions.create(model="deepseek-v3.2", messages=messages)
messages.append(response.choices[0].message)
print(f"Round 2: {messages}")
```

For example code on image understanding, image generation, video generation, vectorization, and reranking, see `references/code-examples-advanced.md`.
