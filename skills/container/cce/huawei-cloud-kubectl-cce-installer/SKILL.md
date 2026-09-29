---
name: huawei-cloud-kubectl-cce-installer
description: >
  Query specific Kubernetes resources in Huawei Cloud CCE clusters through kubectl cce. Trigger when users ask to get, describe, inspect, or view a Pod,
  workload, Service, ConfigMap, node, namespace, or other CCE Kubernetes resource, or when they ask to install or repair the local kubectl-cce
  prerequisites. Install kubectl and kubectl-cce only when they are missing locally.
tags: [kubectl, kubectl-cce, cce, kubernetes, resource-query]
version: 1.0.0
---

# Huawei Cloud CCE Kubectl Resource Query

Use this skill to retrieve specific CCE Kubernetes resources through `kubectl cce`. Resource access is the primary task. Local installation is only a
prerequisite recovery step when `kubectl` or the `kubectl-cce` plugin is unavailable.

## Overview And Safety

- Use `kubectl cce`; do not use a direct Kubernetes API client.
- Read-only commands only: `get`, `describe`, and `logs`.
- Never use `-A`, `--all-namespaces`, or another whole-cluster resource query.
- For namespaced resources, require `--namespace <namespace>` and, where feasible, a specific resource name.
- For cluster-scoped resources such as `node`, `namespace`, `persistentvolume`, and `storageclass`, require an exact resource name. Do not list every
  instance.
- Never run `apply`, `create`, `delete`, `edit`, `patch`, `replace`, `scale`, `rollout`, `cordon`, `drain`, or `exec`.
- Do not print credentials, tokens, kubeconfig content, or Secret data.

## Prerequisites And Required Context

| Input | Requirement |
| --- | --- |
| `cluster_id` | Required standard UUID. An exact name may be resolved with `hcloud CCE ListClusters`, but never run `kubectl cce` until it resolves to one UUID. |
| `region` | Required. Obtain it from the request or current context, then `HW_REGION_NAME`; otherwise ask the user. |
| Resource kind | Required, for example `pod`, `deployment`, `service`, `configmap`, or `node`. |
| Namespace or exact name | At least one is required. Namespaced resources require a namespace; cluster-scoped resources require an exact name. |

Credentials follow the plugin rules in [plugin-usage.md](references/plugin-usage.md). Use explicit `--cli-access-key`, `--cli-secret-key`, and optional
`--cli-security-token` only when the caller supplies them. Do not fall back to other credentials in that case.

## Workflow

1. Before any resource query, validate the target region and cluster ID. If either is missing, or the cluster ID cannot be resolved to one existing UUID in that
   region, do not run `kubectl cce`; ask the user to provide the correct region and cluster ID.
2. Confirm the resource kind, namespace, and exact resource name when required.
3. Check local prerequisites:

   ```bash
   bash scripts/install_kubectl_cce.sh --check
   ```

4. When both `kubectl` and `kubectl-cce` are available, query the requested resource.
5. When either executable is missing, read [installation.md](references/installation.md), then show the installer plan. Installation or replacement is an R1
   local change and requires explicit confirmation:

   ```bash
   bash scripts/install_kubectl_cce.sh --bin-dir <directory>
   sudo bash scripts/install_kubectl_cce.sh --execute --bin-dir <directory>
   ```

6. Verify installation with `kubectl version --client` and `kubectl plugin list`, then run only the requested read-only resource query.

## Core Commands

Use one explicit namespace per namespaced query:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> \
  get pod <pod-name> --namespace <namespace> -o yaml

kubectl cce --cluster-id <cluster-id> --region <region> \
  describe deployment <deployment-name> --namespace <namespace>

kubectl cce --cluster-id <cluster-id> --region <region> \
  get service <service-name> --namespace <namespace> -o yaml
```

For a cluster-scoped resource, use an exact name:

```bash
kubectl cce --cluster-id <cluster-id> --region <region> \
  get node <node-name> -o yaml
```

For credential modes, command forms, and x509 retry behavior, read [plugin-usage.md](references/plugin-usage.md). For Windows usage and installation
fallbacks, read [installation.md](references/installation.md). If a command fails with an x509 upstream TLS validation error, retry that same command once
with `--cce-insecure-upstream-tls=true` immediately after `cce`.

## Risk Levels

| Operation | Level | Guidance |
| --- | --- | --- |
| Resource query and local prerequisite check | R3 | May run automatically. |
| Local binary installation, source build, or plugin replacement | R1 | Preview first and require explicit confirmation before `--execute`. |

## Output Format

Return the cluster ID, region, resource kind, namespace when applicable, resource name, and requested status or fields. State clearly whether the resource is
not found, access is denied, prerequisites are missing, or an installation confirmation is needed.

## Parameters And Confirmation

Confirm `cluster_id`, `region`, resource kind, namespace, and exact resource name before issuing a query. If `cluster_id` is missing or cannot be resolved in
the supplied region, stop and ask the user for the correct region and cluster ID. Confirm the target installation directory before any `--execute` action.

## Verification

After installation, run `kubectl version --client` and `kubectl plugin list`; after a query, verify that the returned resource identity matches the requested cluster, namespace, and name.

## Best Practices

Use the narrowest requested resource query and avoid broad list operations even when the caller can access the whole cluster.

## Notes

When the requested resource cannot be scoped to a namespace or exact name, ask the user to narrow the target instead of expanding to a cluster-wide query.

## References

| Document | Use |
| --- | --- |
| [Plugin Usage](references/plugin-usage.md) | Credentials, command forms, and x509 retry. |
| [Installation](references/installation.md) | Local prerequisites, installer parameters, Windows usage, source fallback, confirmation, and troubleshooting. |
| [Acceptance Criteria](references/acceptance-criteria.md) | Resource-query and installation acceptance checks. |
