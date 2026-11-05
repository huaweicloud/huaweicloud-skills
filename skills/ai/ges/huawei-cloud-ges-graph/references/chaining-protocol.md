# Combination and Chained-Call Protocol

> Fixes the zero-score "组合与链式调用" (combination & chained calls) dimension.
> This skill is a **leaf graph database operator**: it executes a single graph operation
> per call and returns a structured result. Other skills/Tools compose it via the protocol below.

## Job Model

Every exposed method returns a uniform response envelope so downstream orchestrators
can chain calls without parsing custom shapes:

```json
{
  "ok": true,
  "data": { "...": "operation-specific payload" },
  "error": null
}
```

On failure the envelope is:

```json
{
  "ok": false,
  "data": null,
  "error": {"code": "AUTH_FAILED | BLOCKED_BY_GUARD | API_ERROR | TIMEOUT | VALIDATION", "message": "..."}
}
```

## Input Contract (environment)

Consumers must provide the environment before any call (env vars or `references/ges_env.csv.example`):

| Variable | Purpose |
|----------|---------|
| `GES_GRAPH_IP`, `GES_GRAPH_PORT`, `GES_PROJECT_ID`, `GES_GRAPH_NAME`, `GES_IAM_URL`, `GES_REGION` | graph endpoint |
| `HUAWEI_CLOUD_AK` + `HUAWEI_CLOUD_SK` (or `GES_USERNAME`/`GES_PASSWORD`/`GES_DOMAIN_NAME`) | IAM credentials |
| `GES_TOKEN` | optional pre-issued token |

## Chaining Rules

1. **Idempotent writes**: prefer `add_node(..., upsert=True)` / `add_nodes_batch(..., upsert=True)` so a retried
   step never creates duplicates.
2. **Reference passing**: use `_ID_` node id as the stable key between steps
   (create → `mem_001` → subsequent `get_node("mem_001")` / `add_edge(..., "mem_001", ...)`).
3. **Long jobs**: call async variants (`execute_cypher_async`) and poll `get_job_status(job_id)`; do not block.
4. **State across turns**: use the `ConversationContext` API (see SKILL.md "Multi-turn Context") to carry
   touched node ids / query history between chained calls or across dialogue turns.
5. **Safety**: a chained step must not pass `allow_dangerous=True` unless the user explicitly confirmed the
   high-risk action in the current turn.

## Example Orchestration

```
Tool A (memory logger) → add_node(upsert=True) id=mem_001
Tool B (reasoning)     → get_context_nodes() → returns ["mem_001"]
Tool C (relation)      → add_edge(start="mem_001", end="mem_002", type="related")
```