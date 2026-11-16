# CLI Installation Guide (Out-of-Scope Operations)

This skill is a **read-only SDK query skill**. Every query in this skill runs through
`.venv/bin/python3 scripts/huawei_<service>.py <subcommand>`; `hcloud`, `openstack`, `curl` and
hand-written API calls are **not** execution paths for this skill.

This page exists only for requests that cross the read-only boundary (create, resize, reinstall,
delete, scale). Those operations are owned by other skills or the console. When no skill covers the
operation, Huawei Cloud KooCLI (`hcloud`) is the supported fallback — install and use it **outside**
this skill, never as a substitute for a query subcommand here.

## Boundary map

| Request | Where to go |
|---------|-------------|
| ECS create / start / stop / reboot / delete / resize | `huawei-cloud-ecs-manage` |
| ECS reinstall OS | ECS console, or KooCLI `hcloud ECS ReinstallServerWithCloudInit` / `ReinstallServerWithoutCloudInit` |
| CCE workloads, namespaces, events, pod logs | kubectl-based `container/cce/` skills |
| CCE node pool resize / scale-out | `huawei-cloud-cce-cluster-management` |
| EVS / OBS / SFS / CBR queries | `huawei-cloud-storage-query` |
| AS batch decommission and other AS writes | No skill yet; use the AS console |

The KooCLI commands listed above are **documentation only** and must not be copied into a shell as
part of this skill's workflow. They also require a `server_id` (or the equivalent resource ID) that
this skill can help you look up first.

## Installing KooCLI

KooCLI is distributed by Huawei Cloud. Install it from the official package for your platform and
confirm the version with the interactive help. A typical Linux installation uses the official install
script published by Huawei Cloud; Windows and macOS use the matching official package.

| Platform | Recommended source |
|----------|--------------------|
| Linux | Official KooCLI install script from the Huawei Cloud KooCLI documentation |
| Windows | Official KooCLI MSI package |
| macOS | Official KooCLI package from the Huawei Cloud KooCLI documentation |

After installation, configure credentials with `hcloud configure set` and verify access with
`hcloud configure list`. Keep AK/SK out of shell history and logs.

## Why this skill does not call KooCLI

- The skill venv already contains the Huawei Cloud Python SDK; a second CLI adds startup cost and a
  second credential path.
- KooCLI syntax is easy to mis-copy; this skill's subcommands are validated by `-h` and return clear
  exit codes.
- Read-only guarantees are simpler to enforce inside the SDK scripts.

## Related references

- `references/verification-method.md` — how to verify this skill without KooCLI
- `references/iam-policies.md` — read-only IAM actions used by the SDK queries
