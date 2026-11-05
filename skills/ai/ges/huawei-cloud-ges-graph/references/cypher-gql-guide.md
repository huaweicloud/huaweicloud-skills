# Cypher and GQL Query Language Guide

GES supports two query languages: Cypher (Neo4j-compatible) and GQL (international standard graph query language).

## Cypher Usage

**Python:**
```python
# Execute a Cypher query
result = skill.execute_query("MATCH (n) RETURN n LIMIT 10")

# Create a node (_ID_ is used only during creation to set a custom ID)
result = skill.execute_query(
    "CREATE (n:Person {_ID_: 'p001', name: '张三'}) RETURN n"
)

# Match query
result = skill.execute_query(
    "MATCH (n:Person)-[:KNOWS]->(m) WHERE n.name = '张三' RETURN m"
)

# Update a node (match via id() function)
result = skill.execute_query(
    "MATCH (n) WHERE id(n) = 123 SET n.name = '李四' RETURN n"
)

# Delete a node (directed delete, allowed by the safety guardrail)
result = skill.execute_query(
    "MATCH (n) WHERE id(n) = 123 DETACH DELETE n"
)

# Aggregate query
result = skill.execute_query(
    "MATCH (n:Person) RETURN n.city, count(*) as cnt ORDER BY cnt DESC"
)
```

**Node.js:**
```javascript
const { GESGraphSkill } = require('./ges_graph_skill.js');
const skill = new GESGraphSkill();

// Execute a Cypher query
const result = await skill.executeQuery("MATCH (n) RETURN n LIMIT 10");

// Match query
const result = await skill.executeQuery(
    "MATCH (n:Person)-[:KNOWS]->(m) WHERE n.name = '张三' RETURN m"
);

// Update a node
const result = await skill.executeQuery(
    "MATCH (n) WHERE id(n) = 123 SET n.name = '李四' RETURN n"
);

// Delete a node (directed delete, allowed by the safety guardrail)
const result = await skill.executeQuery(
    "MATCH (n) WHERE id(n) = 123 DETACH DELETE n"
);

// Path query
const result = await skill.executeQuery(
    "MATCH p=(n:Person)-[*1..3]->(m) WHERE n.name = '张三' RETURN p"
);
```

## Inline Execution (No Temp Files)

Execute Cypher queries directly via `skill action=exec` without creating any script files.

> **Note:** When running via `skill action=exec`, the working directory is the project root. The installed skill is located under `.agents/skills/huawei-cloud-ges-graph`, **not** under `skills/ai/ges/`.

**Python:**
```bash
skill exec py -c "
import sys, os; cwd=os.getcwd()
skill_dir = os.path.join(cwd, '.agents', 'skills', 'huawei-cloud-ges-graph')
sys.path.insert(0, os.path.join(skill_dir, 'scripts'))
from ges_graph_skill import get_skill
import json
r = get_skill().execute_query('MATCH (n) RETURN n LIMIT 5')
print(json.dumps(r, ensure_ascii=False, indent=2))
"
```

**Node.js:**
```bash
skill exec node -e "
const path = require('path');
const cwd = process.cwd();
const scriptPath = path.join(cwd, '.agents', 'skills', 'huawei-cloud-ges-graph', 'scripts', 'ges_graph_skill.js');
const { GESGraphSkill } = require(scriptPath);
(async () => {
    const r = await new GESGraphSkill().executeQuery('MATCH (n) RETURN n LIMIT 5');
    console.log(JSON.stringify(r, null, 2));
})();
"
```

## Common Cypher Statements

| Category | Statement | Description |
|----------|-----------|-------------|
| Schema | `call db.schema()` | Get graph schema information |
| Indexes | `call db.indexes()` | View all indexes |
| Kill query | `call dbms.killQuery('queryId')` | Terminate a running query |
| Running queries | `call dbms.listQueries()` | View current queries |
| System parameters | `call dbms.parameter('needNodeIndex', false)` | Remove index constraint (large graph scenarios) |

## GQL Usage (Supported by this Skill)

GQL is the ISO/IEC 39075 standardized graph query language. GES invokes it via `action_id=execute-gql-query`.

```python
# GQL requires the underlying _request method (or skill.execute_gql)
client = GESClient()
result = client._request('POST', '/action?action_id=execute-gql-query', json={
    "statements": [{
        "statement": "INSERT (n:Person{_ID_:'p001', firstName:'Eywa'}) RETURN n",
        "parameters": {},
        "resultDataContents": ["row"]
    }]
})
```

## Common GQL Statements

| Category | Statement | Description |
|----------|-----------|-------------|
| Insert | `INSERT (n:Person{_ID_:'p001', firstName:'Eywa'}) RETURN n` | Insert node |
| Match | `MATCH (n:Person WHERE element_id(n)='p001') RETURN n` | Conditional match |
| Update | `MATCH (n:Person WHERE element_id(n)='p001') SET n.lastName='Higgo' RETURN n` | Update properties |
| Remove property | `MATCH (n:Person WHERE element_id(n)='p001') REMOVE n.lastName RETURN n` | Remove property |
| Delete node | `MATCH (n:Person WHERE element_id(n)='p001') DELETE n` | Delete node |
| Filter | `MATCH (n:Person)-[:KNOWS]->(m) FILTER element_id(n)='7933' AND m.gender='male' RETURN m` | Filter results |
| FOR loop | `FOR a IN [1,2,3] RETURN a` | Loop statement |
| LET variable | `LET a = 1, b = 2 RETURN a, b` | Variable definition |
| UNION | `... UNION ALL ...` | Merge result sets |

## Cypher vs GQL Key Differences

| Feature | Cypher | GQL |
|---------|--------|-----|
| Internal ID | `id(n)` | `element_id(n)` |
| Custom ID (insert only) | `_ID_` property | `_ID_` property |
| Node matching | `MATCH (n)` | `MATCH (n WHERE ...)` |
| SET statement | `SET n.prop = value` | `SET n.prop = value` |
| Remove property | `REMOVE n.prop` | `REMOVE n.prop` |
| Loops | Not supported | `FOR x IN [...]` |
| Variable definition | Not supported | `LET x = value` |