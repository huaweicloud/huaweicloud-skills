# Verification Method - huawei-cloud-ges-graph

This document describes how to verify that the skill works correctly.

## Table of Contents

- [1. Prerequisites](#1-prerequisites)
  - [1.1 Runtime](#11-runtime)
  - [1.2 Configuration](#12-configuration)
- [2. Dry-Run Verification (no live instance)](#2-dry-run-verification-no-live-instance)
- [3. Functional Verification (live GES instance)](#3-functional-verification-live-ges-instance)
- [4. Verification Checklist](#4-verification-checklist)

---

## 1. Prerequisites

### 1.1 Runtime

```bash
python3 --version        # >= 3.8
python3 -c "import requests; print('requests OK')"
# or for Node.js
node --version           # >= 14
```

### 1.2 Configuration

```bash
# Option A: pre-provisioned token
export GES_TOKEN=...

# Option B: AK/SK
export GES_GRAPH_IP=100.95.xxx.xxx
export GES_GRAPH_PORT=80
export GES_PROJECT_ID=your_project_id
export GES_GRAPH_NAME=your_graph_name
export GES_IAM_URL=https://iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens
export GES_REGION=cn-north-4
export HUAWEI_CLOUD_AK=your_access_key
export HUAWEI_CLOUD_SK=your_secret_key

# Option C: username/password
export GES_USERNAME=...
export GES_PASSWORD=...
export GES_DOMAIN_NAME=...
```

---

## 2. Dry-Run Verification (no live instance)

Set `GES_DRY_RUN=1` (or `GES_MOCK=1`). The client returns structurally-identical mock
responses without any real network call.

```bash
GES_DRY_RUN=1 python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
from ges_graph_skill import get_skill
s = get_skill()
r = s.execute_query("MATCH (n) RETURN n LIMIT 3")
assert "results" in r or "error" in r, r
print("dry-run execute_query OK ->", str(r)[:120])
print("dry-run get_statistics OK ->", s.get_statistics())
PY
```

Node.js equivalent:

```bash
GES_DRY_RUN=1 node -e '
const { GESGraphSkill } = require("./scripts/ges_graph_skill.js");
const s = new GESGraphSkill();
s.executeQuery("MATCH (n) RETURN n LIMIT 3").then(r => {
  console.log("dry-run executeQuery OK ->", JSON.stringify(r).slice(0,120));
}).catch(e => { console.error("FAIL", e); process.exit(1); });
'
```

---

## 3. Functional Verification (live GES instance)

### 3.1 Basic query

```python
import sys; sys.path.insert(0, "scripts")
from ges_graph_skill import get_skill
s = get_skill()
print(s.execute_query("MATCH (n) RETURN n LIMIT 10"))
```

Expected: a JSON envelope `{"results": [...]}` (or `{"error": ...}` if the graph is empty/unreachable).

### 3.2 Schema / statistics

```python
print(s.get_schema_info())
print(s.get_statistics())
```

Expected: schema labels/properties and node/edge counts.

### 3.3 Node CRUD (+ upsert)

```python
s.client.add_node(node_id="v1", labels=["Test"], properties={"name": "a"}, upsert=True)
print(s.client.get_node("v1"))
s.client.update_node("v1", {"name": "b"})
s.client.delete_node("v1")
```

> Note: GES may require the `Test` label/property to be pre-defined in the graph schema.

### 3.4 Cypher safety guard

Unqualified destructive statements must be rejected:

```python
try:
    s.execute_query("MATCH (n) DETACH DELETE n")
    print("FAIL: destructive query was allowed")
except Exception as e:
    print("OK: blocked", str(e)[:80])
```

### 3.5 Import/Export (optional, needs OBS)

```python
job = s.client.import_graph(schema_path="obs://bucket/schema.xml",
                            vertex_path="obs://bucket/vertex",
                            edge_path="obs://bucket/edge")
print(job)  # {"jobId": ...}
```

---

## 4. Verification Checklist

| Check | Expected Result |
|-------|-----------------|
| Python `requests` / Node runtime | Import/execution succeeds |
| Configuration loaded | No missing-field error |
| `GES_DRY_RUN=1` mock mode | Returns structurally-identical mock envelopes |
| `execute_query` on live instance | Returns `{"results": [...]}` |
| `get_schema_info` / `get_statistics` | Returns schema / counts |
| Node CRUD (upsert) | Create → read → update → delete succeed |
| Destructive Cypher (unqualified delete) | Blocked by `validateCypher` |
| `GES_TIMEOUT` / retry | Timeouts retried up to 3× with exponential backoff; graceful error after retries |

Acceptance thresholds are detailed in [`acceptance-criteria.md`](acceptance-criteria.md).