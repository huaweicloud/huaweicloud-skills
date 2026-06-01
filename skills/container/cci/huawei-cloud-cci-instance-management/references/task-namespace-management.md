# Namespace Lifecycle Management

Namespaces are the foundational isolation boundary in CCI. All workload operations (Deployments, Pods, Networks) require a namespace.

## Create Namespace

```bash
hcloud CCI createCoreV1Namespace \
  --metadata.name=<ns-name> \
  --metadata.annotations.namespace-kubernetes-io/flavor=general-computing \
  --cli-region=<region> \
  --cli-output=json
```

The flavor annotation is **MANDATORY**. Accepted values:

| Flavor | Description |
|--------|-------------|
| `general-computing` | Standard compute instances |
| `gpu-accelerated` | GPU instances — requires additional GPU quota approval |

> GPU-accelerated namespaces require GPU quota to be approved before workloads can be created.

## List Namespaces

```bash
hcloud CCI listCoreV1Namespace --cli-region=<region> --cli-output=json
```

Filter output with JMESPath:

```bash
hcloud CCI listCoreV1Namespace --cli-region=<region> --cli-output=json \
  --cli-query="items[].{Name:metadata.name,Status:status.phase,Flavor:metadata.annotations.namespace\.kubernetes\.io/flavor}"
```

## Read Namespace

```bash
hcloud CCI readCoreV1Namespace --name=<ns-name> --cli-region=<region> --cli-output=json
```

## Delete Namespace

**TWO-STEP CONFIRMATION REQUIRED — this operation is irreversible and cascading.**

### Step 1: Preview

Show namespace details and warn the user:

```bash
hcloud CCI readCoreV1Namespace --name=<ns-name> --cli-region=<region> --cli-output=json
```

> **WARNING**: Deleting a namespace cascades to ALL resources under it — Networks, Deployments, Pods, ConfigMaps, Secrets, etc. This cannot be undone.

### Step 2: Execute (only after explicit user confirmation)

```bash
hcloud CCI deleteCoreV1Namespace --name=<ns-name> --cli-region=<region>
```

- This is **irreversible** — no undo, no recovery
- This is **cascading** — all child resources are destroyed
- Always run `readCoreV1Namespace` first so the user can review what will be lost

## Namespace Naming Rules

- Must follow DNS_LABEL format: lowercase alphanumeric and hyphens only
- Must start with a lowercase letter or digit
- Maximum 63 characters
- Examples: `my-app`, `test-ns-01`, `production`

## Namespace Status Phases

| Phase | Meaning |
|-------|---------|
| `Active` | Namespace is ready for use |
| `Terminating` | Namespace is being deleted — all resources are being cleaned up |