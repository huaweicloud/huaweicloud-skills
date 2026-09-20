# Workflow Design

## Overview

This document describes the multi-round interaction design, SSE parsing approach, and state management for the OptVerse Solver Assistant skill.

## 1. Multi-Round Conversation Flow

```
Round 1: Requirement Submission
  Upload file → CreateChat (message=requirement, filenames=[filename])
  → Artifacts: requirement analysis output
  → User confirms

Round 2: Requirement Confirmation
  CreateChat (message="确认", chat_id=same)
  → Artifacts: modeling code, modeling docs
  → User confirms

Round 3: Modeling Confirmation
  CreateChat (message="确认", chat_id=same)
  → Wait for data upload

Round 4: Data Upload & Check
  UploadFile (xlsx) → CreateChat (message="进行数据检查", chat_id=same)
  → Data validation results
  → User confirms

Round 5: Data Confirmation & Final Output
  CreateChat (message="确认", chat_id=same)
  → Final artifacts: solver results, reports
  → PublishChat (name=asset_name, type=optverse)
```

## 2. State Management

### 2.1 Critical State Variables

| Variable | Scope | Storage | Purpose |
|----------|-------|---------|---------|
| chat_id | Per conversation | Agent context (passed as arg) | Identifies the conversation thread |
| X-Chat-Route-Id | Per machine | Script cache file | Routes requests to same backend node |
| OPTVERSE_AK | Per session | Environment variable | AKSK V4 signing |
| OPTVERSE_SK | Per session | Environment variable | AKSK V4 signing |
| project_id | Per region | Auto-detected from hcloud | URL path parameter |

### 2.2 State Persistence Rules

- **chat_id**: MUST be passed explicitly as `--chat_id` in every subsequent createChat call
- **X-Chat-Route-Id**: Auto-generated on first call, cached in `%TEMP%/optverse_chat_route_id.txt`; CAN be overridden with `--x-chat-route-id`
- **AK/SK**: Read from environment variables each invocation; NEVER cached to disk

### 2.3 chat_id and X-Chat-Route-Id Relationship

These two IDs are **one-to-one correlated** on the server side:
- The same `X-Chat-Route-Id` must be used for all rounds of the same conversation
- If `chat_id` is from a previous conversation, the matching `X-Chat-Route-Id` must be used
- Mismatching them will result in routing errors or data inconsistency

## 3. SSE Streaming Design

### 3.1 Why SSE?

The createChat endpoint uses Server-Sent Events (`text/event-stream`) because:
- The decision engine generates long responses incrementally
- Real-time streaming provides better UX (user sees progress)
- The server pushes data chunks as they are generated

### 3.2 SSE Parsing Logic

```python
for line in resp.iter_lines():
    if line:
        line = line.decode('utf-8')
        if line.startswith("data:"):
            data_str = line[5:].strip()
            data = json.loads(data_str)
            # Extract: chat_id, id, message.content, message.tool_calls
            # Content accumulates across chunks
```

### 3.3 SSE Event Format

```
data: {"chat_id": "xxx", "id": "yyy", "type": "chat_call", "create_time": "...", "message": {"content": "chunk1", "tool_calls": []}}

data: {"chat_id": "xxx", "id": "yyy", "message": {"content": "chunk2", "tool_calls": []}}

data: [DONE]
```

### 3.4 Content Accumulation

The `message.content` field in each SSE chunk is **appended** to form the complete response:

```
Chunk 1: content = "Based on the requirement..."
Chunk 2: content = " the optimal model is..."
Chunk 3: content = " a mixed integer program."

Final content: "Based on the requirement... the optimal model is... a mixed integer program."
```

## 4. AKSK V4 Signing Design

### 4.1 Why AKSK Instead of Tokens?

| Approach | Pros | Cons |
|----------|------|------|
| IAM Token (X-Auth-Token) | Simple header | Requires username/password; token expires in 24h |
| AKSK V4 Signing | No passwords needed; uses same credentials as hcloud | More complex signing algorithm |

### 4.2 Signing Process

1. Build canonical request: `METHOD\nURI\nQUERY\nHEADERS\nSIGNED_HEADERS\nPAYLOAD_HASH`
2. Build string to sign: `SDK-HMAC-SHA256\nTIMESTAMP\nSHA256(canonical_request)`
3. Derive signing key: `HMAC chain: date → region → service → sdk_request`
4. Calculate signature: `HMAC-SHA256(signing_key, string_to_sign)`
5. Build Authorization header: `SDK-HMAC-SHA256 Access=AK, SignedHeaders=..., Signature=...`

### 4.3 Security

- AK/SK are read from environment variables only
- Never written to files, logs, or debug output
- Script debug output masks AK as `XXXX****XXX`
- HTTPS is used for all requests (SSL verification can be disabled for cn-east-3)

## 5. Error Handling Design

### 5.1 Retry Strategy

| Error Type | Retry | Max Retries | Backoff |
|------------|-------|-------------|--------|
| Network timeout | Yes | 3 | 2s, 4s, 8s |
| 5xx server error | Yes | 2 | 5s, 10s |
| 4xx client error | No | 0 | — |
| SSE parse error | No | 0 | Return partial result |

### 5.2 User-Facing Error Messages

| Error | Message to User |
|-------|----------------|
| AK/SK not set | "Please set OPTVERSE_AK and OPTVERSE_SK environment variables" |
| Project ID not found | "Could not determine project_id. Please provide --project_id or ensure hcloud is configured" |
| SSE connection failed | "Failed to connect to OptVerse service. Check network and region settings" |
| Permission denied | "Permission denied. Please check IAM policies (see references/iam-policies.md)" |
| Publish failed | "Publish failed. Ensure all conversation stages are confirmed before publishing" |

## 6. Design Patterns Applied

| Pattern | Implementation |
|---------|---------------|
| Step-by-step confirmation | Each round requires explicit user "确认" before proceeding |
| Status board | Workflow table with ○/✅/⏳ status markers |
| Anti-skip | Each step depends on previous step's chat_id |
| Dual output | JSON (machine) + readable content (human) |
| Config externalization | AK/SK from env vars, not hardcoded |
| Safe-by-default | Read-only operations first, write operations need confirmation |
| Progressive depth | Requirement → Modeling → Data → Solver → Report (progressive stages) |
