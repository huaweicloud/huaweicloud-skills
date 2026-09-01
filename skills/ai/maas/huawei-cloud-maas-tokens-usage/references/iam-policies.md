# IAM Permission Policies - Huawei Cloud MaaS Tokens Usage

IAM permissions required for querying MaaS tokens usage statistics.

## Table of Contents

- [Minimum Required Permissions](#minimum-required-permissions)
  - [ModelArts Permissions](#modelarts-permissions)
  - [IAM Permissions](#iam-permissions)
- [Recommended IAM Policy](#recommended-iam-policy)
- [Predefined Permission Policies](#predefined-permission-policies)
- [Verification](#verification)

---

## Minimum Required Permissions

### ModelArts Permissions

| Action | API | Description |
|--------|-----|-------------|
| `modelarts:monitoring:get` | POST /v1/{project_id}/maas/monitoring/show-statistics | Query MaaS monitoring statistics (Python SDK signing) |
| `modelarts:service:get` | GET /v1/{project_id}/services | Query service list etc. |

### IAM Permissions

| Action | API | Description |
|--------|-----|-------------|
| `iam:projects:get` | GET /v1/projects | Auto-resolve project_id from region |

> **Read-only scope**: All permissions are `get` only. The query workflow never modifies or deletes any MaaS resource.

---

## Recommended IAM Policy

```json
{
    "Version": "1.1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "modelarts:monitoring:get",
                "modelarts:service:get",
                "iam:projects:get"
            ]
        }
    ]
}
```

---

## Predefined Permission Policies

- **ModelArts CommonOperations** — ModelArts common operations (includes `modelarts:service:get`, `modelarts:monitoring:get`)
- **IAM ReadOnlyAccess** — IAM read-only access (includes `iam:projects:get`)

---

## Verification

After configuring IAM, verify permissions by running the query script:

```bash
# Verify ModelArts monitoring access
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21
```

If the script returns `403 Forbidden`, the corresponding permission is missing. Check:
- `modelarts:monitoring:get` — if ShowStatistics returns 403
- `modelarts:service:get` — if service list query returns 403
- `iam:projects:get` — if project_id auto-resolution fails

---

## References

| Document | Description |
|----------|-------------|
| [SKILL.md](../SKILL.md) | Skill overview and core workflows |
| [troubleshooting.md](troubleshooting.md) | Permission issue troubleshooting |
