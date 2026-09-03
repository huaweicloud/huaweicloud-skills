# IAM Policies

## System Policy (Recommended)

Huawei Cloud provides a built-in read-only policy that covers all Cloud Connect query operations, including Global Connection Bandwidth (GCB):

| Policy | Scope |
|--------|-------|
| `CC ReadOnlyAccess` | Read-only access to all CC resources (cloud connections, bandwidth packages, GCBs, central networks, etc.) |

This system policy is sufficient for all commands in this skill (List and Show operations on GCBs, GCB tenant configs, and support-binding GCBs).

## How to Apply

1. Huawei Cloud Console → IAM → Permissions → System Policies
2. Search "CC ReadOnlyAccess"
3. Assign the policy to the target user or group
