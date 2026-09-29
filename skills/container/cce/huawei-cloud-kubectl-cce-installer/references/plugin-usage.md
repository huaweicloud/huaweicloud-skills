# kubectl-cce Plugin Usage

If `kubectl` or the `kubectl-cce` plugin is unavailable, use the `huawei-cloud-kubectl-cce-installer` skill to install or repair the local prerequisites
before querying cluster resources.

## Resource Query Constraints

Use this plugin for read-only CCE resource queries. Always provide `--cluster-id` and `--region`; for namespaced resources, provide
`--namespace <namespace>` whenever the tool input supports it. Default to a specific namespace or resource name instead of `-A` or `--all-namespaces`.

Before invoking `kubectl cce`, validate that `cluster_id` resolves to one existing CCE cluster UUID in the supplied region. If the region or cluster ID is
missing, invalid, or cannot be resolved, do not run the resource query; ask the user to provide the correct region and cluster ID.

Cluster-wide reads are allowed only when a tool explicitly requires a read-only aggregation or inventory, such as default Warning Event collection,
Pod/Service/Ingress metric aggregation, LogConfig discovery, or node inventory. In those cases, query only the required resource type and apply an
available namespace, label selector, field selector, or result limit to reduce returned data. For cluster-scoped resources, prefer an exact resource
name unless the tool explicitly requires inventory. Do not use mutation commands or print Secret data, credentials, tokens, or kubeconfig contents.

## Credential Options

The plugin accepts two credential modes. Name the mechanism **names** below (public plugin docs); never show, print, log, or persist credential **values**.

### Mode 1 — Environment variables (default; ordinary interactive environments)

For users whose environment cannot inject CLI args. The plugin reads credentials from the process environment. Set them through an approved local credential
provider (protected shell rc, systemd environment file, or secrets manager) before invoking the plugin:

- `HW_ACCESS_KEY` / `HW_SECRET_KEY` — permanent AK/SK
- `HW_SECURITY_TOKEN` — required when using temporary AK/SK
- `HW_PROJECT_ID` / `HW_REGION` — target project and region

### Mode 2 — CLI flags (v0.2.1+; sandboxed/agent runtimes)

For trusted sandbox/agent runtimes that inject credentials per invocation and control process visibility. Pass:

- `--cli-access-key <ak>` / `--cli-secret-key <sk>`
- `--cli-security-token <token>` — for temporary credentials

> ⚠️ **Risk notice:** CLI arguments can be visible in process listings such as `ps aux`, which may expose credentials to other local users or processes.
> Prefer Mode 1 where process visibility is not controlled, and use Mode 2 only after evaluating this exposure risk for the current environment.

## Read-only Resource Queries

```bash
# Mode 1 (env vars)
kubectl cce --cluster-id <cluster-id> --region "${HW_REGION}" get pod <pod-name> --namespace <namespace>

# Mode 2 (runtime injection — runtime supplies the real values; never log them)
kubectl cce --cluster-id <cluster-id> --region <region> \
  --cli-access-key <access-key> --cli-secret-key <secret-key> \
  [--cli-security-token <token>] get pod <pod-name> --namespace <namespace>
```

Do not run write operations during installation verification.

## x509 TLS Retry

If a `kubectl cce` command returns an `x509` certificate-validation error, repeat the same command with `--cce-insecure-upstream-tls=true` immediately after `cce`. For example: `kubectl cce --cce-insecure-upstream-tls=true --cluster-id <cluster-id> ...`. Use this option only when that TLS validation error occurs.
