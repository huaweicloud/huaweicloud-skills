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

## Prerequisites

Before using this skill, ensure the following conditions are met:

### 1. Runtime Environment
Supports Python or Node.js runtime.
Requires Python 3.8+ or Node.js 14+.

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

**Configuration File (`.env/ges_env.csv`)**

Config file path: `.env/ges_env.csv`

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

> **This skill prohibits the following operations:**

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

### Cypher Usage

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

# Delete a node
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

// Create a node (_ID_ is used only during creation to set a custom ID)
const result = await skill.executeQuery(
    "CREATE (n:Person {_ID_: 'p001', name: '张三'}) RETURN n"
);

// Match query
const result = await skill.executeQuery(
    "MATCH (n:Person)-[:KNOWS]->(m) WHERE n.name = '张三' RETURN m"
);

// Update a node
const result = await skill.executeQuery(
    "MATCH (n) WHERE id(n) = 123 SET n.name = '李四' RETURN n"
);

// Delete a node
const result = await skill.executeQuery(
    "MATCH (n) WHERE id(n) = 123 DETACH DELETE n"
);

// Aggregate query
const result = await skill.executeQuery(
    "MATCH (n:Person) RETURN n.city, count(*) as cnt ORDER BY cnt DESC"
);

// Path query
const result = await skill.executeQuery(
    "MATCH p=(n:Person)-[*1..3]->(m) WHERE n.name = '张三' RETURN p"
);
```

### Inline Execution (No Temp Files)

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

#### Common Cypher Statements

| Category | Statement | Description |
|----------|-----------|-------------|
| Schema | `call db.schema()` | Get graph schema information |
| Indexes | `call db.indexes()` | View all indexes |
| Kill query | `call dbms.killQuery('queryId')` | Terminate a running query |
| Running queries | `call dbms.listQueries()` | View current queries |
| System parameters | `call dbms.parameter('needNodeIndex', false)` | Remove index constraint (large graph scenarios) |

### GQL Usage (Supported by this Skill)

GQL is the ISO/IEC 39075 standardized graph query language. GES invokes it via `action_id=execute-gql-query`.

```python
# GQL requires the underlying _request method
client = GESClient()
result = client._request('POST', '/action?action_id=execute-gql-query', json={
    "statements": [{
        "statement": "INSERT (n:Person{_ID_:'p001', firstName:'Eywa'}) RETURN n",
        "parameters": {},
        "resultDataContents": ["row"]
    }]
})
```

#### Common GQL Statements

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

#### Cypher vs GQL Key Differences

| Feature | Cypher | GQL |
|---------|--------|-----|
| Internal ID | `id(n)` | `element_id(n)` |
| Custom ID (insert only) | `_ID_` property | `_ID_` property |
| Node matching | `MATCH (n)` | `MATCH (n WHERE ...)` |
| SET statement | `SET n.prop = value` | `SET n.prop = value` |
| Remove property | `REMOVE n.prop` | `REMOVE n.prop` |
| Loops | Not supported | `FOR x IN [...]` |
| Variable definition | Not supported | `LET x = value` |## Core Interfaces (Core Commands)

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

# Batch add nodes
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

# Clear all data in the graph (dangerous operation)
result = skill.clear_all_memories()
```

### Import/Export

```python
# Import graph data
job_id = skill.client.import_graph(
    schema_path="obs://bucket/schema.xml",
    vertex_path="obs://bucket/vertex",
    edge_path="obs://bucket/edge"
)

# Export graph data (access_key/secret_key are read from .env automatically)
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

## Reference Documentation

- **Configuration file format**: `references/ges_env.csv.example` — Environment configuration file template and field descriptions
- **Graph database format**: https://support.huaweicloud.com/usermanual-ges/ges_01_0153.html — Detailed GES graph data format documentation
- **How to access the business API**: https://support.huaweicloud.com/api-ges/ges_03_0112.html — GES business API access guide