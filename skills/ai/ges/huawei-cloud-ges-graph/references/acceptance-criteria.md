# Acceptance Criteria - huawei-cloud-ges-graph

**Scenario**: Huawei Cloud GES graph database operations (Cypher/GQL queries, node/edge
CRUD, schema/label management, statistics, import/export) via local Python/Node.js scripts.

## Table of Contents

- [1. Runtime & Configuration Acceptance](#1-runtime--configuration-acceptance)
- [2. Query Acceptance](#2-query-acceptance)
- [3. Node/Edge CRUD Acceptance](#3-nodeedge-crud-acceptance)
- [4. Security Criteria](#4-security-criteria)
- [5. Fault Tolerance Acceptance](#5-fault-tolerance-acceptance)

---

## 1. Runtime & Configuration Acceptance

### ✅ Correct

```bash
python3 --version  # >= 3.8
python3 -c "import requests; print('requests OK')"
node --version     # >= 14
```

Config loaded from env vars (precedence) or `config/ges_env.csv`; no required field missing.

### ❌ Incorrect

```text
ModuleNotFoundError: No module named 'requests'
ERROR: 配置缺失或不完整 -> 缺少 graph_ip / project_id / graph_name / iam_url ...
```

---

## 2. Query Acceptance

### ✅ Correct

```python
execute_query("MATCH (n) RETURN n LIMIT 10")   # -> {"results": [...]}
execute_query("MATCH (n) WHERE n.name = $name RETURN n", parameters={"name": "张三"})
execute_gql("MATCH (n) RETURN n LIMIT 10")
get_schema_info() / get_statistics()
```

### ❌ Incorrect

- Passing a non-string statement, or a property value of unsupported type (dict/list/bytes).
- Injecting a full-write statement through an unqualified delete (blocked by `validateCypher`).

---

## 3. Node/Edge CRUD Acceptance

### ✅ Correct

```python
add_node(node_id="v1", labels=["Memory"], properties={"content": "..."}, upsert=True)  # idempotent
get_node("v1") -> node
update_node("v1", {...})
delete_node("v1")
add_edge(start_node_id, end_node_id, edge_type, properties=...)
add_nodes_batch([...])  # up to 500 per call
```

### ❌ Incorrect

- `add_nodes_batch` with > 500 nodes in a single call → rejected (boundary guard).
- Passing `dict`/`list` as a property value → rejected (JSON scalars only).

---

## 4. Security Criteria

### ✅ Correct

1. Credentials read only from `os.environ`/`process.env` or `config/ges_env.csv` at runtime — **no hardcoded password/AK/SK**.
2. AK/SK, password, token **never printed or logged**.
3. Dangerous Cypher (`DETACH DELETE`, `DELETE`, `DROP`, ...) blocked unless `allow_destructive=True` + user confirmation.
4. `clear_graph()` requires explicit user confirmation.
5. No cross-skill direct calls; no local absolute path hardcoding.

### ❌ Incorrect

1. Hardcoding `password`/`access_key`/`secret_key` literals in source.
2. Printing credentials or tokens in outputs.
3. Executing unfiltered model/program output via `eval`/`exec`/`system` (all output is parsed as JSON data).
4. Hardcoding machine-local absolute paths (Windows drive-letter paths, Unix user home-directory paths) in the scripts.

---

## 5. Fault Tolerance Acceptance

### ✅ Correct

- All downstream calls have timeout + up to 3 retries (0.5s→1s→2s exponential backoff + jitter) on transient errors (408/429/5xx/timeout).
- If downstream unreachable after retries → a descriptive error is raised (no silent hang).
- `GES_DRY_RUN=1` mock mode produces structurally-identical responses for offline CI.

### ❌ Incorrect

- Silently hanging forever on a wedged downstream call.
- Raising opaque errors with no hint of the root cause.