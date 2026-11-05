# Operational Notes

Auxiliary reference material for `huawei-cloud-cci-instance-management`: namespace flavors,
quota limits, output formatting and debugging. Moved out of `SKILL.md` to keep it within the
500-line limit.

## Namespace Flavor Types

Every namespace must carry the flavor annotation `namespace.kubernetes.io/flavor`
(hyphen form: `namespace-kubernetes-io/flavor`). Two values are supported:

| Flavor Value | Description | Use Case |
|---|---|---|
| `general-computing` | General computing type | Standard workloads, web services, microservices |
| `gpu-accelerated` | GPU accelerated type | AI, ML, high-performance computing |

> **⚠️ The two flavors do not have the same creation path.** The hyphen form
> `--metadata.annotations.namespace-kubernetes-io/flavor=general-computing` works **only** for
> `general-computing`. For `gpu-accelerated` CCI silently ignores the hyphenated key and the
> namespace falls back to `general-computing`; the dotted key `namespace.kubernetes.io/flavor` is
> required and hcloud CLI cannot pass dotted annotation keys. Use the helper script:
>
> ```bash
> python scripts/cci_network_helper.py create-namespace \
>   --name=<ns-name> \
>   --flavor=gpu-accelerated \
>   --region=<region>
> ```
>
> Then verify the effective value:
>
> ```bash
> hcloud CCI readCoreV1Namespace --name=<ns-name> --cli-region=<region> --cli-output=json
> ```

## Resource Quota and Limits

CCI enforces resource quotas per namespace. The concrete limits vary by region, so query them
for the namespace you are working in rather than assuming a default:

```bash
hcloud CCI listCoreV1NamespacedResourceQuota --namespace=<ns-name> --cli-region=<region> --cli-output=json
```

An `OutOfpods` or resource-exhaustion symptom on a workload should be diagnosed against this
quota output before changing anything — see
[diagnosis-playbooks.md](diagnosis-playbooks.md).

## Output Format

### JSON (recommended)

```bash
hcloud CCI <Operation> --cli-region=<region> --cli-output=json
```

### Table (for manual viewing)

```bash
hcloud CCI <Operation> --cli-region=<region> --cli-output=table
```

### JMESPath Filtering

```bash
# Filter deployment status
hcloud CCI readAppsV1NamespacedDeploymentStatus --name=<deploy> --namespace=<ns> --cli-region=<region> --cli-output=json --cli-query="{replicas:status.replicas,ready:status.readyReplicas,available:status.availableReplicas}"

# Filter pod phase
hcloud CCI readCoreV1NamespacedPodStatus --name=<pod> --namespace=<ns> --cli-region=<region> --cli-output=json --cli-query="status.phase"
```

## Debugging

Debug output is enabled by the **global** `--debug` switch, which must be placed **before** the
service name. A `cli`-prefixed debug parameter is rejected by hcloud as an invalid parameter
(`[USE_ERROR]不正确的参数:cli-debug`).

```bash
hcloud --debug CCI <Operation> --cli-region=<region>
```

## Best Practices

1. **Namespace isolation**: Use different namespaces for different teams/projects to avoid resource conflicts.
2. **EIPPool on-demand**: Only create an EIPPool when Pod public IP access is needed — EIPs and
   bandwidth are billable, so creating one requires a cost warning and explicit user confirmation.
