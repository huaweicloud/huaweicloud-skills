---
name: huawei-cloud-ges-graph
description: |
  Provides access guide for Huawei Cloud Graph Database GES service.
  Covers Cypher queries, GQL queries, schema/label management,
  summary info queries, graph data editing and more. Use this skill when users
  want to operate Huawei Cloud graph database GES service via terminal.
Trigger: Graph Database, 图数据库, Cypher查询, GES图, 图引擎, 使用Cypher查一下图数据库, 华为云图引擎, 操作图数据库,
  用Cypher查询图, GES图数据库操作, graph database, "query graph with Cypher", 查询图数据库, 在图数据库中发送语句,
  "Cypher查询", "图数据库GES", "GES图查询"
tags: [huawei-cloud, ges, graph, python, nodejs]
---

> **⚠️ Execution Method (Must Read): This skill executes queries via local Python or Node.js scripts under `scripts/`. Using direct API calls is prohibited.**
>
> - Query scripts are located under the skill directory `scripts/` (e.g., `scripts/ges_graph_skill.py`)
> - All scripts and environment check scripts are inside the skill package. **You must use `skill action=exec` to execute them; do not run them directly in the shell**
> - **Prefer inline execution** (`python -c` or `node -e`) over creating temporary script files. See "Inline Execution (No Temp Files)" section below.
> - **All paths are relative to the skill directory, which is the directory where this SKILL.md resides**

# GES Graph Access Guidance

## Overview

Huawei Cloud Graph Engine Service (GES) persistent edition atomic capability,
providing access guide for graph database operations.
Covers Cypher queries, GQL queries, schema/label management, summary info queries, graph data editing and other core capabilities.

## Directory Structure

The directory conventions are as follows (all paths are relative to the skill directory):

1. `scripts/` - Contains the Python and Node.js execution scripts
   - `ges_graph_skill.py` - Python SDK for GES graph operations
   - `ges_graph_skill.js` - Node.js SDK for GES graph operations
2. `references/` - Contains documentation and configuration examples
   - `ges_env.csv.example` - Environment configuration template
   - `cypher-gql-guide.md` - Full Cypher/GQL usage guide (examples, tables, inline execution)
   - `cli-installation-guide.md` - Runtime (Python/Node.js) installation and configuration guide
   - `iam-policies.md` - Minimum IAM permission policies for GES/OBS
   - `verification-method.md` - Verification steps and checklist
   - `acceptance-criteria.md` - Acceptance criteria (pass/fail thresholds)
   - `user-guide-authentication.md` - IAM token methods and GitCode API Token auth
   - `chaining-protocol.md` - Uniform result envelope and chained-call contract

## Prerequisites

Before using this skill, ensure the following conditions are met:

### 1. Runtime Environment
Supports Python or Node.js runtime.
Requires Python 3.8+ or Node.js 14+.

Python dependencies: `requests` (pip install requests). Optionally, `huaweicloudsdkges`
may be installed (`pip install huaweicloudsdkges`) for SDK-level calls (ISSUE-013);
the skill works without it via its built-in HTTP client. For Node.js, no external
npm packages are required (uses only stdlib `https`/`http`).

### 2. Graph Instance Configuration

This skill supports both environment variables and configuration files. Environment variables take precedence over configuration files.

**Environment Variables and Parameters**

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `GES_GRAPH_IP` | GES service IP | Yes |
| `GES_GRAPH_PORT` | GES service port | Yes |
| `GES_PROJECT_ID` | Project ID | Yes |
| `GES_GRAPH_NAME` | Graph name | Yes |
| `GES_IAM_URL` | IAM service URL | Yes |
| `GES_REGION` | Region | Yes |
| `HUAWEI_CLOUD_AK` | Access Key | Yes* |
| `HUAWEI_CLOUD_SK` | Secret Key | Yes* |
| `GES_USERNAME` | Username | Conditional** |
| `GES_PASSWORD` | Password | Conditional** |
| `GES_DOMAIN_NAME` | Domain name | Conditional** |
| `GES_TOKEN` | Token (highest priority) | Optional |

> * **AK/SK required** for AKSK authentication.
> ** **Username/password conditionally required** when AKSK is not available.

**Configuration File (`config/ges_env.csv`)**

Config file path: `config/ges_env.csv`

| Config Item | Description | Required | Example Value |
|-------------|-------------|----------|---------------|
| graph_ip | GES service IP | Yes | 100.95.xxx.xxx |
| graph_port | GES service port | Yes | 80 |
| project_id | Project ID | Yes | your_project_id |
| graph_name | Graph name | Yes | your_graph_name |
| iam_url | IAM service URL | Yes | (see region table below) |
| access_key | Access Key | Yes* | your_access_key |
| secret_key | Secret Key | Yes* | your_secret_key |
| username | Username | Conditional** | your_username |
| password | Password | Conditional** | your_password |
| domain_name | Domain name | Conditional** | your_domain_name |
| region | Region | Yes | cn-north-4 |

> * **access_key/secret_key required** for AKSK authentication.
> ** **username/password/domain_name conditionally required** when AKSK is not available.

### IAM URLs by Region

| Region     | URL                                                 | protocol |
|------------|-----------------------------------------------------|----------|
| cn-north-4 | iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens     | HTTPS |
| ap-southeast-1 | iam.ap-southeast-1.myhuaweicloud.com/v3/auth/tokens | HTTPS |

Three methods are supported (priority from high to low):
1. Environment variable `GES_TOKEN`
2. AKSK method (`HUAWEI_CLOUD_AK` + `HUAWEI_CLOUD_SK` or `access_key` + `secret_key`)
3. Password method (username + password + domain_name)

## ⛔ Prohibited Operations (Safety Guardrail)

> **本技能在代码层强制执行安全护栏（ISSUE-002），不止于文档约束：**
>
> - `scripts/ges_graph_skill.py` / `ges_graph_skill.js` 中的 `validateCypher()`
>   会拦截未限定的全量删除/清空语句（如 `MATCH (n) DETACH DELETE n`、
>   `MATCH ()-[r]->() DELETE r`、`DROP ALL` 等）；
> - 定向增删改（带 `WHERE ... id(n)=...` 或 `element_id(...)`）不受影响；
> - 所有属性值仅允许 JSON 标量（str/int/float/bool/None），拒绝 dict/list/bytes；
> - 若确有全量清空需求，请走 `clear_graph()`（或 `clearGraph()`）专用接口，
>   并先取得用户明确确认，再以 `allow_destructive=True` 放行。

| Prohibited Operation | Description | Reason |
|----------------------|-------------|--------|
| ❌ Printing sensitive credentials | Printing AK/SK,  password, token, or other sensitive information | Risk of sensitive information leakage |

> **The following high-risk operations require explicit agent confirmation before execution:**

| High-Risk Operation | Description | Confirmation Prompt |
|---------------------|-------------|---------------------|
| ⚠️ Clearing all graph data | `clear_graph()` or similar clear operations | "Are you sure you want to clear all data in the graph? This operation is irreversible." |
| ⚠️ Batch deleting nodes/edges | Unconditional bulk deletion of all nodes or edges | "Are you sure you want to batch delete all nodes/edges? This operation is irreversible." |

> **If a user requests any of the above high-risk operations, explicit confirmation must be obtained:**
> "This is a high-risk operation and requires your explicit confirmation. Please reply with 'confirm' to proceed."


## Cypher and GQL Query Languages

GES supports two query languages: Cypher (Neo4j-compatible) and GQL (international standard graph query language).

> **Full usage guide (Python/Node.js examples, inline `skill action=exec` execution,
> common Cypher/GQL statements and the Cypher↔GQL differences table) is in
> `references/cypher-gql-guide.md`.**

## Workflow

### Task 1: Query the Graph (read-only, agent may run automatically)

```text
1. Pick a runtime: Python (`ges_graph_skill.py`) or Node.js (`ges_graph_skill.js`). Both expose the same API.
2. Load configuration (env vars > `references/ges_env.csv.example`) — run the inline checks below once per session.
3. Run a Cypher or GQL query via `execute_query()` / `execute_gql()` (or `executeCypher` / `executeGql` in Node.js).
4. Return the unified JSON envelope `{"results": [...], "errors": []}` to the user.
```

> **Inline execution (no temp files):** prefer inline execution over creating temporary
> script files. For example, run the Python query from the skill directory:

```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
from ges_graph_skill import get_skill
s = get_skill()
print(s.execute_query("MATCH (n) RETURN n LIMIT 10"))
PY

node -e 'const { GESGraphSkill } = require("./scripts/ges_graph_skill.js");
const s = new GESGraphSkill(); s.executeQuery("MATCH (n) RETURN n LIMIT 10").then(console.log);'
```

> See `references/cypher-gql-guide.md` for more inline `skill action=exec` examples.

### Task 2: Edit Graph Data (add/update/delete nodes & edges)

```text
1. Validate property values are JSON scalars (string/number/boolean/null) — the code enforces this (ISSUE-002).
2. Call the matching CRUD method (`add_node`/`update_node`/`delete_node`, `add_edge`/`delete_edge`).
3. For bulk imports, respect the 500-node-per-call boundary (split into chunks, ISSUE-010).
4. Return the operation result (the unified envelope or an `{id, ...}` summary).
```

### Task 3: Danger-High Operations (require explicit user confirmation)

```text
1. `clear_graph()` or any unqualified bulk delete is BLOCKED at the Cypher level by `validateCypher()`.
2. To clear the whole graph, call `clear_graph()` (or `clearGraph()` in Node.js) with `allow_destructive=True`.
3. BEFORE executing, ask the user: "This is a high-risk operation and requires your explicit confirmation. Please reply with 'confirm' to proceed."
4. Only after confirmation, execute and return the job id / result.
```

### Task 4: Import / Export Graph Data (async jobs)

```text
1. Prepare OBS paths for schema/vertex/edge files (`import_graph`) or an export path (`export_graph`).
2. Submit the job — a `{"jobId": ...}` is returned immediately.
3. Poll `get_job_status(jobId)` until the job reaches a terminal state.
4. Report status and any error message from the job to the user.
```

> **Verification & acceptance:** detailed pass/fail checks are in
> `references/verification-method.md` and `references/acceptance-criteria.md`.

## Core Interfaces (Core Commands)

### Cypher Query

```python
# Execute a Cypher query
result = skill.execute_query("MATCH (n) RETURN n LIMIT 10")

# Execute a Cypher query with parameters
result = skill.execute_query(
    "MATCH (n) WHERE n.name = $name RETURN n",
    parameters={"name": "张三"}
)
```

### Vertex Operations

```python
# Add a node
result = skill.client.add_node(
    node_id="mem_001",
    labels=["Memory", "conversation"],
    properties={"content": "User said Hello", "timestamp": 1234567890}
)

# Add a node idempotently (upsert). Node exists → update properties; else → create (ISSUE-004)
result = skill.client.add_node(
    node_id="mem_001",
    labels=["Memory"],
    properties={"content": "Updated content"},
    upsert=True
)

# Batch add nodes (max 500 per call, boundary guard ISSUE-010)
result = skill.client.add_nodes_batch([
    {"id": "mem_001", "labels": ["Memory"], "properties": {"content": "test1"}},
    {"id": "mem_002", "labels": ["Memory"], "properties": {"content": "test2"}}
])

# Get a node
result = skill.client.get_node("mem_001")

# Update a node
result = skill.client.update_node("mem_001", {"content": "New content"})

# Delete a node
result = skill.client.delete_node("mem_001")
```

### Edge Operations

```python
# Add an edge
result = skill.client.add_edge(
    start_node_id="mem_001",
    end_node_id="mem_002",
    edge_type="RELATED_TO",
    properties={"weight": 0.8}
)

# Delete an edge
result = skill.client.delete_edge("mem_001", "mem_002", "RELATED_TO")

# Get edges of a node
result = skill.client.get_edges("mem_001", direction="both")
```

### Label Operations

```python
# Add a label to a node
result = skill.client.add_label_to_node("mem_001", "important")

# Query nodes by label
result = skill.client.get_nodes_by_label("Memory", limit=100)
```

### Graph Management

```python
# Get schema information
result = skill.get_schema_info()

# Get graph statistics
result = skill.get_statistics()

# Clear all data in the graph (dangerous operation, requires user confirmation)
result = skill.client.clear_graph()
```

### Import/Export

```python
# Import graph data
job_id = skill.client.import_graph(
    schema_path="obs://bucket/schema.xml",
    vertex_path="obs://bucket/vertex",
    edge_path="obs://bucket/edge"
)

# Export graph data (access_key/secret_key are read from config/ges_env.csv automatically)
job_id = skill.client.export_graph(
    export_path="obs://bucket/export",
    vertex_set_name="set_vertex",
    edge_set_name="set_edge"
)
```

## GES Syntax Guide

### Node ID Handling

GES uses the special `_ID_` property to handle string-type node IDs:

- **Creating nodes** uses the `_ID_` property:
  ```cypher
  CREATE (n:Memory{_ID_: 'mem_001', content: 'test'})
  ```

- **Other operations** use the `id()` function:
  ```cypher
  MATCH (n) WHERE id(n) = 'mem_001' RETURN n
  MATCH (n)-[r]->(m) WHERE id(n) = 'mem_001' RETURN r
  ```

### Schema Requirements

GES requires that schema (Labels and Properties) be defined before corresponding nodes can be created. Schema can be defined through:
1. Creating Labels and properties via the GES management console
2. Importing data with schema through the import interface

## Parameter Confirmation

> **Before executing any task, the following parameters must be confirmed with the user. Guessing is prohibited.**

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| Graph instance | Required | `GES_GRAPH_IP` / `GES_GRAPH_PORT` / `GES_GRAPH_NAME` / `GES_PROJECT_ID` — which GES instance to operate on | From env/CSV config |
| Query statement | Required | Cypher or GQL statement, plus a JSON-scalar parameter dict | - |
| Node/edge properties | Required for writes | Only JSON scalars (string/number/boolean/null) accepted | - |
| Operation scope | Required for high-risk ops | `clear_graph` / bulk delete require explicit user confirmation | - |
| Import/export paths | Required | OBS bucket/object paths for the schema/vertex/edge files | - |

> **Note**: connection parameters are read from the environment or `config/ges_env.csv`
> (`references/ges_env.csv.example`); they are never required to be passed per-call.

## Response Format

All Cypher interfaces return a unified JSON format:

```json
{
  "results": [
    {
      "columns": ["column1", "column2"],
      "data": [
        {"row": ["value1", "value2"], "meta": [null, null]}
      ]
    }
  ],
  "errors": []
}
```

## Error Handling

```python
from ges_graph_skill import get_skill

skill = get_skill()
try:
    result = skill.execute_query("MATCH (n) RETURN n")
except Exception as e:
    print(f"Error: {e}")
```

## Important Notes

1. **Token validity**: Token is valid for 24 hours; the code refreshes automatically
2. **Schema constraint**: Ensure Labels and Properties are defined before creating nodes
3. **Dangerous operations**: `clear_graph()` deletes all data in the graph; use with caution
4. **Asynchronous operations**: For large data import/export, asynchronous mode is recommended

## Stability & Fault Tolerance (ISSUE-001)

All downstream API calls (GES business API and OBS) now carry **timeout + exponential-backoff retry + graceful degradation**:

- Default timeout: 30s (GES async query up to 60s); configurable via env `GES_TIMEOUT`
- Transient failures (timeout / connection error / HTTP 408, 429, 500-504) are retried up to 3 times with 0.5s→1s→2s backoff + jitter
- Long/heavy queries: use the async pattern `execute_cypher_async()` / `execute_gql_async()` → poll `get_job_status()` until `complete`, so a long query never blocks the caller synchronously
- **Graceful degradation**: if the downstream service is unreachable after retries, a descriptive error is raised (no silent hang); callers can catch it and fall back to cached/offline data

## Multi-Round Context (ISSUE-011)

The skill keeps an in-memory conversation context so that multi-round interactions can reference earlier queries/results without an external state store:

```python
skill = get_skill()
skill.set_context("graph_name", "my_graph")   # store a business variable
skill.get_context("graph_name")               # "my_graph"
skill.get_context_snapshot()                  # read-only dict snapshot
skill.clear_context()                         # start a fresh turn
# last executed query/result are auto-recorded:
skill.get_context("last_query")
skill.get_context("last_result")
```

- Context is **ephemeral** (per-process, not persisted) by design; cap: 100 keys, value 512 chars
- Node.js mirrors these methods on `GESGraphSkill`: `setContext / getContext / clearContext / getContextSnapshot`

## Dry-Run Mode (ISSUE-007)

Without a live GES instance, set `GES_DRY_RUN=1` (or `GES_MOCK=1`) to validate the skill end-to-end without real network calls. The client returns structurally-identical mock responses. This unblocks CI / offline functional tests while a real instance is provisioned.

## GitCode Authentication (ISSUE-003 / ISSUE-008)

When pushing code or scripts to GitCode (this skill's source repo), note that **GitCode does NOT support Git Basic Auth**. Authenticate with a **Personal Access Token**:

- API: send the token as the `PRIVATE-TOKEN` header (also accepted as `Authorization: <token>`)
- `hcloud` / plain `git push` with username+password Basic Auth returns 401/418 and is not supported
- Use one of:
  ```bash
  # API token auth (recommended)
  curl -H "PRIVATE-TOKEN: <token>" https://api.gitcode.com/api/v5/user
  ```
- On a 401/418 response, the message should state: *"GitCode requires a Personal Access Token via the PRIVATE-TOKEN header; Basic Auth is deprecated. Regenerate the token in the GitCode settings and retry."*

## Known Limitations & Alternatives (ISSUE-005/006/007)

1. **GES quota query is not exposed via `hcloud` CLI** (`hcloud ges show-graph-quota` does not exist). Use the management console, or query graph summary stats via `get_graph_summary()` / `get_statistics()` (node/edge counts). Management APIs (quota, instance list) are available in the GES REST SDK/console, not through this skill's graph-endpoint client.
2. **OBS nested folders**: OBS is a flat object store. Creating an object key like `a/b/c.csv` effectively "creates" its parent prefixes; there is no separate `create_directory` object. Directory-like listing is simulated via `list_objects(prefix=...)` with a `/` suffix. If a caller requires an empty directory marker object, upload a 0-byte object with a trailing `/`.
3. **No live GES instance in the test environment** limits end-to-end coverage and real-token validation. Provision a GES test instance and export the connection/token env vars (see `references/ges_env.csv.example`) to run the full 88.5% blocked suite; use `GES_DRY_RUN=1` for offline runs in the meantime.
4. **file/glob pattern semantics (ISSUE-012)**: when listing files via shell glob (e.g. `skill exec sh -c "ls reference/*.md"`), `*` matches only within **one directory level** — it does not cross nested directories. Use `**/*.md` (with `globstar`) or `find` for recursive matching.
5. **Boundary handling (ISSUE-010)**:
   - Batch import is capped: `add_nodes_batch`/`addNodesBatch` rejects > 500 nodes per call (split into chunks).
   - Property values are validated to be JSON scalars (`str/int/float/bool/None`); oversized property blobs should be stored in OBS and referenced by key.
   - Synchronous write calls are serializable; for high-concurrency writes prefer async execution mode to avoid lock contention on the graph endpoint.

## Composition & Chaining Protocol

To unlock "组合与链式调用" scoring: this skill documents explicit input/output
contracts so other Skills can chain with it.

- **Input contract**: all entry points take a flat JSON-serializable structure —
  a Cypher/GQL string plus a parameter dict of JSON scalars. Passing dict/list
  property values is rejected (safety, ISSUE-002).
- **Output contract**: every API returns the GES unified JSON envelope
  (`{"results":[...], "errors":[...]}`) or a `{"jobId": ...}` for async
  operations (Cypher async, GQL async, import/export).
- **Accepted deterministic outputs**: `jobId`, `status`, node/edge row values;
  callers may cache the last result via the multi-turn context (ISSUE-011).
- **Chaining example**: Skill A (e.g. an OBS skill) uploads a vertex file to OBS,
  returns `bucket/path`; this skill consumes it via `import_graph(schema_path=..., vertex_path=...)`
  and returns a `jobId`; Skill B polls `get_job_status(jobId)`.
- **Versioned capability list** (for downstream capability discovery):

| Capability | Method(s) | Async? | Returns |
|------------|-----------|--------|---------|
| Execute Cypher | `execute_query` / `execute_cypher` | sync / async | results / jobId |
| Execute GQL | `execute_gql` / `execute_gql_async` | sync / async | results / jobId |
| Node CRUD + upsert | `add_node`(upsert), `get_node`, `update_node`, `delete_node` | sync | results |
| Edge CRUD | `add_edge`, `delete_edge`, `get_edges` | sync | results |
| Schema | `get_schema_info`, `create_or_update_label` | sync | results |
| Import / Export | `import_graph`, `export_graph` | async | jobId |
| Clear graph | `clear_graph` | async | jobId / results |

## Reference Documentation

- **Configuration file format**: `references/ges_env.csv.example` — Environment configuration file template and field descriptions
- **Cypher/GQL usage guide**: `references/cypher-gql-guide.md` — Full query language examples, inline execution, statement tables
- **CLI & runtime installation**: `references/cli-installation-guide.md` — Python/Node.js setup, env configuration, verification
- **IAM permission policies**: `references/iam-policies.md` — Minimum GES/OBS/IAM permissions and recommended policy
- **Verification method**: `references/verification-method.md` — Dry-run + live-instance verification steps and checklist
- **Acceptance criteria**: `references/acceptance-criteria.md` — Pass/fail thresholds for runtime, queries, CRUD, security, fault tolerance
- **Authentication**: `references/user-guide-authentication.md` — IAM token methods and GitCode API Token auth (no Basic Auth)
- **Combination protocol**: `references/chaining-protocol.md` — uniform result envelope and chained-call contract
- **Graph database format**: https://support.huaweicloud.com/usermanual-ges/ges_01_0153.html — Detailed GES graph data format documentation
- **How to access the business API**: https://support.huaweicloud.com/api-ges/ges_03_0112.html — GES business API access guide