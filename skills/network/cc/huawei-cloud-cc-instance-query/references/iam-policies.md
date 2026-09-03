# IAM Policies for CC Query Skill

## System Policy (Recommended)

Huawei Cloud provides a built-in read-only policy that covers all Cloud Connect query operations:

- **CC ReadOnlyAccess** — Grants read-only access to all Cloud Connect resources.

Assign it via the console: IAM → Permissions → System Policies → search "CC ReadOnlyAccess" → assign to the user or group.

This system policy is sufficient for all commands in this skill (List and Show operations on cloud connections, bandwidth packages, inter-region bandwidths, network instances, routes, and cross-account authorisations).

## Notes

- All operations in this skill are read-only (List/Get) — no `create`, `update`, or `delete` permissions are needed.
- The `domain_id` parameter required by all CC APIs corresponds to the account ID, not the user ID.
