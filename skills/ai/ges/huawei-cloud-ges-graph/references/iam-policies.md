# IAM Permission Policies - huawei-cloud-ges-graph

This document describes the Huawei Cloud IAM permissions required by the
`huawei-cloud-ges-graph` skill.

## Table of Contents

- [1. Minimum Required Permissions](#1-minimum-required-permissions)
  - [1.1 GES (Graph Engine Service) Permissions](#11-ges-graph-engine-service-permissions)
  - [1.2 OBS Permissions (Import/Export only)](#12-obs-permissions-importexport-only)
  - [1.3 IAM Permissions](#13-iam-permissions)
- [2. Recommended IAM Policy](#2-recommended-iam-policy)
- [3. Predefined Permission Policies](#3-predefined-permission-policies)
- [4. Authentication Methods](#4-authentication-methods)
- [5. Verification](#5-verification)

---

## 1. Minimum Required Permissions

The skill talks to the GES business endpoint (`/ges/v1.0/{project_id}/graphs/{graph_name}/action`)
using a token obtained from IAM. The minimum permissions depend on the operations used:

### 1.1 GES (Graph Engine Service) Permissions

The service-level policy action for reading/writing graph data is
`ges:graph:access` (access the GES graph business API). For reading schema/statistics
and common queries, `read` scopes are sufficient:

| Action | Scope | Required By |
|--------|-------|-------------|
| `ges:graph:access` | Graph business API access (Cypher/GQL execution, node/edge CRUD) | All operations |
| `ges:graph:getDetail` | Get graph detail / summary / statistics | `get_graph_summary`, `get_statistics` |
| `ges:graph:getSchema` | Read schema / labels | `get_schema_info` |

> **Write operations** (add/update/delete nodes & edges, import/export) are exercised
> through the same `ges:graph:access` action on the business endpoint — no separate
> write action is required for business-API operations.

### 1.2 OBS Permissions (Import/Export only)

Import/export jobs read/write files in OBS. The skill performs OBS object operations
(via `OBSClient`) and submits GES import/export jobs:

| Action | Description | Required By |
|--------|-------------|-------------|
| `obs:object:GetObject` | Read schema/vertex/edge files from OBS for import | `import_graph` |
| `obs:object:PutObject` | Write exported data to OBS | `export_graph` |
| `obs:bucket:HeadBucket` | Check bucket availability | `import_graph` / `export_graph` |
| `obs:object:ListObjects` | List objects by prefix | `list_objects` |

### 1.3 IAM Permissions

| Action | Description | Required By |
|--------|-------------|-------------|
| `iam:projects:list` | Resolve the project / region for token scope | Token acquisition |

---

## 2. Recommended IAM Policy

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ges:graph:access",
                "ges:graph:getDetail",
                "ges:graph:getSchema",
                "obs:object:GetObject",
                "obs:object:PutObject",
                "obs:bucket:HeadBucket",
                "obs:object:ListObjects",
                "iam:projects:list"
            ]
        }
    ]
}
```

> **Least-privilege note**: if a user only needs **queries** (no import/export/write),
> the `obs:*` actions and `ges:graph:access` write scope can be narrowed further. The
> policy above covers the full skill capability.

---

## 3. Predefined Permission Policies

- **GES ReadOnlyAccess** — GES read-only permission (schema/statistics reads).
- **GES FullAccess** — Full GES management + graph access.
- **OBS ReadOnlyAccess** / **OBS OperateAccess** — OBS read / read-write for import/export files.
- **IAM ReadOnlyAccess** — Read-only IAM (`iam:projects:list`).

Grant the user/agency a combination matching their actual usage (e.g. `GES ReadOnlyAccess`
+ `OBS ReadOnlyAccess` for pure query + import, or `GES FullAccess` + `OBS OperateAccess`
for the full workflow).

---

## 4. Authentication Methods

The skill supports three auth methods (priority high → low):

1. **`GES_TOKEN`** — a pre-provisioned token (no extra IAM action needed).
2. **AK/SK** (`HUAWEI_CLOUD_AK` / `HUAWEI_CLOUD_SK`) — the IAM user owning the AK/SK must have the permissions above.
3. **Username/Password** (`GES_USERNAME`, `GES_PASSWORD`, `GES_DOMAIN_NAME`) — the IAM user must be granted the permissions above.

Credentials are **only read from environment variables / the `config/ges_env.csv` file at
runtime**; they are never hardcoded in the scripts and never printed.

---

## 5. Verification

After configuring IAM, run the skill in `GES_DRY_RUN=1` mock mode first, then against a
real GES instance:

```bash
# Dry-run (no IAM/token actually used) — validates wiring
GES_DRY_RUN=1 python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
from ges_graph_skill import get_skill
s = get_skill()
print(s.execute_query("MATCH (n) RETURN n LIMIT 3"))
PY

# Real instance — a 401/403 means the IAM permissions are missing
python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
from ges_graph_skill import get_skill
s = get_skill()
print(s.get_schema_info())
PY
```

If the second command returns `403 Forbidden`, check that the IAM user/agency has the
GES (`ges:graph:access`) and IAM (`iam:projects:list`) permissions listed above.